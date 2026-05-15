from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .broker_ibkr import IbkrBroker, IbkrConnectionError
from .config import BotConfig
from .models import MarketSnapshot, TradeSignal
from .risk import RiskManager
from .risk import RiskDecision
from .strategy import build_strategy


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logging.getLogger("ib_insync.wrapper").setLevel(logging.WARNING)
logging.getLogger("ib_insync.client").setLevel(logging.WARNING)


@dataclass(frozen=True)
class BotRunResult:
    snapshot: MarketSnapshot
    signal: TradeSignal
    decision: RiskDecision


def _fmt(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def _log_snapshot(snapshot: MarketSnapshot) -> None:
    logging.info(
        "Market snapshot: %s price=%s vix=%s gap=%s open_positions=%s "
        "expirations=%s strikes=%s",
        snapshot.underlying_symbol,
        _fmt(snapshot.underlying_price),
        _fmt(snapshot.vix_price),
        "n/a" if snapshot.overnight_gap_pct is None else f"{snapshot.overnight_gap_pct:.2%}",
        snapshot.open_positions,
        len(snapshot.available_expirations),
        len(snapshot.available_strikes),
    )


def _log_signal(signal: TradeSignal) -> None:
    logging.info("Signal: action=%s reason=%s", signal.action.value, signal.reason)
    if signal.legs:
        logging.info("Signal legs: %s", signal.legs)


def main() -> None:
    config = BotConfig.from_env()
    logging.info(
        "Starting SPX bot: strategy=%s dry_run=%s live_trading=%s",
        config.strategy,
        config.dry_run,
        config.live_trading,
    )

    try:
        result = run_once(config)

        _log_snapshot(result.snapshot)
        _log_signal(result.signal)
        logging.info("Risk decision: %s", result.decision)

        if result.decision.approved:
            logging.warning("Order submission is not implemented until strategy is chosen.")
    except IbkrConnectionError as exc:
        logging.error("%s", exc)


def run_once(config: BotConfig) -> BotRunResult:
    broker = IbkrBroker(config)
    strategy = build_strategy(config)
    risk = RiskManager(config)

    try:
        broker.connect()
        snapshot = broker.snapshot()
        signal = strategy.generate_signal(snapshot)
        decision = risk.evaluate(snapshot, signal)
        return BotRunResult(snapshot=snapshot, signal=signal, decision=decision)
    finally:
        broker.disconnect()
