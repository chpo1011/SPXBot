from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TradeAction(str, Enum):
    NONE = "none"
    SELL_PUT_CREDIT_SPREAD = "sell_put_credit_spread"
    SELL_CALL_CREDIT_SPREAD = "sell_call_credit_spread"
    SELL_IRON_CONDOR = "sell_iron_condor"


@dataclass(frozen=True)
class MarketSnapshot:
    underlying_symbol: str
    underlying_price: Optional[float]
    open_positions: int
    realized_pnl_today: float
    timestamp: Optional[datetime] = None
    vix_price: Optional[float] = None
    overnight_gap_pct: Optional[float] = None
    available_expirations: tuple[str, ...] = ()
    available_strikes: tuple[float, ...] = ()
    trades_opened_today: int = 0


@dataclass(frozen=True)
class SpreadLeg:
    right: str
    strike: float
    expiry: str
    action: str
    quantity: int


@dataclass(frozen=True)
class TradeSignal:
    action: TradeAction
    reason: str
    max_loss_usd: float = 0.0
    credit_usd: float = 0.0
    take_profit_debit_usd: float = 0.0
    stop_loss_debit_usd: float = 0.0
    legs: tuple[SpreadLeg, ...] = ()

    @classmethod
    def none(cls, reason: str) -> "TradeSignal":
        return cls(action=TradeAction.NONE, reason=reason)
