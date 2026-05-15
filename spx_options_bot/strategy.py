from __future__ import annotations

from zoneinfo import ZoneInfo
from typing import Optional

from .config import BotConfig
from .models import MarketSnapshot, SpreadLeg, TradeAction, TradeSignal


class Strategy:
    name = "base"

    def generate_signal(self, snapshot: MarketSnapshot) -> TradeSignal:
        raise NotImplementedError


class NoOpStrategy(Strategy):
    name = "noop"

    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def generate_signal(self, snapshot: MarketSnapshot) -> TradeSignal:
        return TradeSignal.none(
            "No strategy is active yet. Set STRATEGY after defining entry rules."
        )


class SpxZeroDteIronCondorStrategy(Strategy):
    name = "spx_0dte_iron_condor"

    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def generate_signal(self, snapshot: MarketSnapshot) -> TradeSignal:
        reason = self._blocked_reason(snapshot)
        if reason:
            return TradeSignal.none(reason)

        assert snapshot.underlying_price is not None
        assert snapshot.timestamp is not None

        expiry = snapshot.timestamp.strftime("%Y%m%d")
        strikes = tuple(sorted(snapshot.available_strikes))
        if expiry not in snapshot.available_expirations:
            return TradeSignal.none(f"No 0DTE SPX option expiry found for {expiry}.")
        if not strikes:
            return TradeSignal.none("No SPX option strikes available.")

        min_distance = self.config.min_otm_distance_pct / 100
        put_short_target = snapshot.underlying_price * (1 - min_distance)
        call_short_target = snapshot.underlying_price * (1 + min_distance)

        put_short = self._nearest_at_or_below(strikes, put_short_target)
        call_short = self._nearest_at_or_above(strikes, call_short_target)
        if put_short is None or call_short is None:
            return TradeSignal.none("Could not select short strikes from option chain.")

        if not self._inside_distance_band(snapshot.underlying_price, put_short, "put"):
            return TradeSignal.none("Selected put strike is outside distance band.")
        if not self._inside_distance_band(snapshot.underlying_price, call_short, "call"):
            return TradeSignal.none("Selected call strike is outside distance band.")

        put_long = self._nearest_at_or_below(
            strikes, put_short - self.config.put_spread_width
        )
        call_long = self._nearest_at_or_above(
            strikes, call_short + self.config.call_spread_width
        )
        if put_long is None or call_long is None:
            return TradeSignal.none("Could not select long hedge strikes.")

        width = max(put_short - put_long, call_long - call_short)
        max_loss = width * 100 * self.config.contracts

        legs = (
            SpreadLeg("P", put_short, expiry, "SELL", self.config.contracts),
            SpreadLeg("P", put_long, expiry, "BUY", self.config.contracts),
            SpreadLeg("C", call_short, expiry, "SELL", self.config.contracts),
            SpreadLeg("C", call_long, expiry, "BUY", self.config.contracts),
        )

        return TradeSignal(
            action=TradeAction.SELL_IRON_CONDOR,
            reason=(
                f"0DTE Iron Condor candidate: short put {put_short}, "
                f"short call {call_short}, VIX {snapshot.vix_price:.2f}."
            ),
            max_loss_usd=max_loss,
            legs=legs,
        )

    def _blocked_reason(self, snapshot: MarketSnapshot) -> Optional[str]:
        if snapshot.underlying_price is None:
            return "No SPX market price available."
        if snapshot.timestamp is None:
            return "No market timestamp available."
        if snapshot.vix_price is None:
            return "No VIX price available."
        if snapshot.vix_price >= self.config.max_vix:
            return f"VIX {snapshot.vix_price:.2f} is above limit {self.config.max_vix:.2f}."
        if snapshot.overnight_gap_pct is None:
            return "No overnight gap value available."
        if abs(snapshot.overnight_gap_pct) >= self.config.max_overnight_gap_pct:
            return (
                f"Overnight gap {snapshot.overnight_gap_pct:.2%} is above limit "
                f"{self.config.max_overnight_gap_pct:.2%}."
            )
        if snapshot.open_positions >= self.config.max_open_positions:
            return "Maximum open positions reached."
        if snapshot.trades_opened_today >= self.config.max_daily_trades:
            return "Maximum daily trade count reached."
        if not self._inside_entry_window(snapshot):
            return "Outside entry window."
        return None

    def _inside_entry_window(self, snapshot: MarketSnapshot) -> bool:
        tz = ZoneInfo(self.config.market_timezone)
        timestamp = snapshot.timestamp.astimezone(tz)
        market_open_minutes = 9 * 60 + 30
        market_close_minutes = 16 * 60
        current_minutes = timestamp.hour * 60 + timestamp.minute
        earliest = market_open_minutes + self.config.entry_after_minutes
        latest = market_close_minutes - self.config.force_close_before_minutes
        return earliest <= current_minutes <= latest

    def _inside_distance_band(self, price: float, strike: float, right: str) -> bool:
        if right == "put":
            distance = (price - strike) / price
        else:
            distance = (strike - price) / price
        min_distance = self.config.min_otm_distance_pct / 100
        max_distance = self.config.max_otm_distance_pct / 100
        return min_distance <= distance <= max_distance

    @staticmethod
    def _nearest_at_or_below(
        strikes: tuple[float, ...], target: float
    ) -> Optional[float]:
        candidates = [strike for strike in strikes if strike <= target]
        return candidates[-1] if candidates else None

    @staticmethod
    def _nearest_at_or_above(
        strikes: tuple[float, ...], target: float
    ) -> Optional[float]:
        candidates = [strike for strike in strikes if strike >= target]
        return candidates[0] if candidates else None


def build_strategy(config: BotConfig) -> Strategy:
    if config.strategy == "noop":
        return NoOpStrategy(config)
    if config.strategy == "spx_0dte_iron_condor":
        return SpxZeroDteIronCondorStrategy(config)
    raise ValueError(
        "Unknown strategy "
        f"'{config.strategy}'. Currently available: noop, spx_0dte_iron_condor."
    )
