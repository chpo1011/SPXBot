from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs) -> None:
        return None


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _whole_percent(name: str, default: float) -> float:
    value = _float(name, default)
    if 0 < value < 1:
        return value * 100
    return value


@dataclass(frozen=True)
class BotConfig:
    ib_host: str
    ib_port: int
    ib_client_id: int
    account_id: Optional[str]
    dry_run: bool
    live_trading: bool
    account_size_usd: float
    max_risk_per_trade_usd: float
    max_daily_loss_usd: float
    max_open_positions: int
    underlying: str
    exchange: str
    currency: str
    strategy: str
    target_dte: int
    short_delta: float
    spread_width: float
    take_profit_pct: float
    stop_loss_multiple: float
    stop_loss_pct: float
    contracts: int
    max_daily_trades: int
    min_otm_distance_pct: float
    max_otm_distance_pct: float
    put_spread_width: float
    call_spread_width: float
    max_vix: float
    max_overnight_gap_pct: float
    entry_after_minutes: int
    force_close_before_minutes: int
    market_timezone: str
    use_delayed_market_data: bool

    @classmethod
    def from_env(cls) -> "BotConfig":
        load_dotenv(override=True)
        account_id = os.getenv("ACCOUNT_ID", "").strip() or None
        return cls(
            ib_host=os.getenv("IB_HOST", "127.0.0.1"),
            ib_port=_int("IB_PORT", 7497),
            ib_client_id=_int("IB_CLIENT_ID", 17),
            account_id=account_id,
            dry_run=_bool("DRY_RUN", True),
            live_trading=_bool("LIVE_TRADING", False),
            account_size_usd=_float("ACCOUNT_SIZE_USD", 25_000),
            max_risk_per_trade_usd=_float("MAX_RISK_PER_TRADE_USD", 600),
            max_daily_loss_usd=_float("MAX_DAILY_LOSS_USD", 500),
            max_open_positions=_int("MAX_OPEN_POSITIONS", 1),
            underlying=os.getenv("UNDERLYING", "SPX"),
            exchange=os.getenv("EXCHANGE", "CBOE"),
            currency=os.getenv("CURRENCY", "USD"),
            strategy=os.getenv("STRATEGY", "noop").strip().lower(),
            target_dte=_int("TARGET_DTE", 0),
            short_delta=_float("SHORT_DELTA", 0.15),
            spread_width=_float("SPREAD_WIDTH", 5),
            take_profit_pct=_whole_percent("TAKE_PROFIT_PCT", 70),
            stop_loss_multiple=_float("STOP_LOSS_MULTIPLE", 3.0),
            stop_loss_pct=_whole_percent("STOP_LOSS_PCT", 300),
            contracts=_int("CONTRACTS", 1),
            max_daily_trades=_int("MAX_DAILY_TRADES", 1),
            min_otm_distance_pct=_whole_percent("MIN_OTM_DISTANCE_PCT", 1.7),
            max_otm_distance_pct=_whole_percent("MAX_OTM_DISTANCE_PCT", 2.0),
            put_spread_width=_float("PUT_SPREAD_WIDTH", _float("SPREAD_WIDTH", 5)),
            call_spread_width=_float("CALL_SPREAD_WIDTH", _float("SPREAD_WIDTH", 5)),
            max_vix=_float("MAX_VIX", 25),
            max_overnight_gap_pct=_float("MAX_OVERNIGHT_GAP_PCT", 0.005),
            entry_after_minutes=_int("ENTRY_AFTER_MINUTES", 60),
            force_close_before_minutes=_int("FORCE_CLOSE_BEFORE_MINUTES", 60),
            market_timezone=os.getenv("MARKET_TIMEZONE", "America/New_York"),
            use_delayed_market_data=_bool("USE_DELAYED_MARKET_DATA", True),
        )

    @property
    def can_submit_orders(self) -> bool:
        return self.live_trading and not self.dry_run
