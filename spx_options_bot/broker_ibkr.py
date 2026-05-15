from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from ib_insync import IB, Index

from .config import BotConfig
from .models import MarketSnapshot


class IbkrConnectionError(RuntimeError):
    pass


@dataclass
class IbkrBroker:
    config: BotConfig

    def __post_init__(self) -> None:
        self.ib = IB()

    def connect(self) -> None:
        try:
            self.ib.connect(
                self.config.ib_host,
                self.config.ib_port,
                clientId=self.config.ib_client_id,
                readonly=not self.config.can_submit_orders,
            )
            if self.config.use_delayed_market_data:
                self.ib.reqMarketDataType(3)
        except ConnectionRefusedError as exc:
            raise IbkrConnectionError(
                "IBKR connection refused. Start TWS or IB Gateway, log in, "
                "enable API socket connections, and make sure IB_PORT matches "
                f"the running app. Current target: "
                f"{self.config.ib_host}:{self.config.ib_port}."
            ) from exc
        except OSError as exc:
            raise IbkrConnectionError(
                "Could not connect to IBKR. Check that TWS or IB Gateway is "
                f"running and reachable at {self.config.ib_host}:{self.config.ib_port}."
            ) from exc
        except TimeoutError as exc:
            raise IbkrConnectionError(
                "IBKR accepted the network connection but did not complete the API "
                "handshake. In TWS, allow API clients from this Mac, disable "
                "'localhost only' restrictions, check Trusted IPs, and confirm no "
                "TWS security dialog is waiting. Current target: "
                f"{self.config.ib_host}:{self.config.ib_port}, clientId "
                f"{self.config.ib_client_id}."
            ) from exc
        except asyncio.TimeoutError as exc:
            raise IbkrConnectionError(
                "IBKR accepted the network connection but timed out during the API "
                "handshake. Check remote API permissions, Trusted IPs, and any "
                "pending TWS confirmation dialog."
            ) from exc

    def disconnect(self) -> None:
        if self.ib.isConnected():
            self.ib.disconnect()

    def snapshot(self) -> MarketSnapshot:
        contract = Index(
            self.config.underlying,
            self.config.exchange,
            self.config.currency,
        )
        qualified = self.ib.qualifyContracts(contract)
        if not qualified:
            raise RuntimeError(f"Could not qualify {self.config.underlying}.")

        qualified_contract = qualified[0]
        price = self._market_price(qualified_contract)
        vix_price = self._market_price(Index("VIX", "CBOE", self.config.currency))
        gap = self._overnight_gap_pct(qualified_contract)
        expirations, strikes = self._option_chain(qualified_contract)

        positions = self.ib.positions()
        open_spx_positions = sum(
            1
            for position in positions
            if getattr(position.contract, "symbol", "") == self.config.underlying
        )

        return MarketSnapshot(
            underlying_symbol=self.config.underlying,
            underlying_price=price,
            open_positions=open_spx_positions,
            realized_pnl_today=self._realized_pnl_today(),
            timestamp=datetime.now(ZoneInfo(self.config.market_timezone)),
            vix_price=vix_price,
            overnight_gap_pct=gap,
            available_expirations=expirations,
            available_strikes=strikes,
        )

    def _market_price(self, contract) -> Optional[float]:
        qualified = self.ib.qualifyContracts(contract)
        if not qualified:
            return None
        ticker = self.ib.reqMktData(qualified[0], "", False, False)
        self.ib.sleep(2)
        price = self._ticker_price(ticker)
        self.ib.cancelMktData(qualified[0])
        if price is None:
            price = self._last_historical_price(qualified[0])
        return price

    def _ticker_price(self, ticker) -> Optional[float]:
        values = [
            ticker.marketPrice(),
            ticker.last,
            ticker.close,
            getattr(ticker, "delayedLast", None),
            getattr(ticker, "delayedClose", None),
            getattr(ticker, "delayedBid", None),
            getattr(ticker, "delayedAsk", None),
        ]
        for value in values:
            if value is not None and value == value and value > 0:
                return float(value)
        return None

    def _last_historical_price(self, contract) -> Optional[float]:
        for what_to_show in ("TRADES", "MIDPOINT"):
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="1 D",
                barSizeSetting="1 min",
                whatToShow=what_to_show,
                useRTH=True,
                formatDate=1,
            )
            if bars:
                close = bars[-1].close
                if close == close and close > 0:
                    return float(close)
        return None

    def _overnight_gap_pct(self, contract) -> Optional[float]:
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="3 D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )
        if len(bars) < 2:
            return None
        previous = bars[-2]
        current = bars[-1]
        if previous.close <= 0:
            return None
        return (current.open - previous.close) / previous.close

    def _option_chain(self, contract) -> tuple[tuple[str, ...], tuple[float, ...]]:
        chains = self.ib.reqSecDefOptParams(
            self.config.underlying,
            "",
            contract.secType,
            contract.conId,
        )
        matching = [
            chain
            for chain in chains
            if chain.exchange == self.config.exchange
            and chain.tradingClass in {"SPX", "SPXW"}
        ]
        if not matching:
            matching = list(chains)
        expirations = sorted(
            {expiration for chain in matching for expiration in chain.expirations}
        )
        strikes = sorted({float(strike) for chain in matching for strike in chain.strikes})
        return tuple(expirations), tuple(strikes)

    def _realized_pnl_today(self) -> float:
        account_values = self.ib.accountSummary(self.config.account_id or "")
        for item in account_values:
            if item.tag == "RealizedPnL" and item.currency == self.config.currency:
                try:
                    return float(item.value)
                except ValueError:
                    return 0.0
        return 0.0
