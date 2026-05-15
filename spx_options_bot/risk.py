from __future__ import annotations

from dataclasses import dataclass

from .config import BotConfig
from .models import MarketSnapshot, TradeAction, TradeSignal


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str


class RiskManager:
    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def evaluate(self, snapshot: MarketSnapshot, signal: TradeSignal) -> RiskDecision:
        if signal.action is TradeAction.NONE:
            return RiskDecision(False, signal.reason)

        if snapshot.open_positions >= self.config.max_open_positions:
            return RiskDecision(False, "Maximum open positions reached.")

        if not self.config.can_submit_orders:
            return RiskDecision(False, "Dry-run mode: order would not be submitted.")

        return RiskDecision(True, "Approved.")
