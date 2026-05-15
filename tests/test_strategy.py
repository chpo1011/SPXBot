from datetime import datetime
from zoneinfo import ZoneInfo

from spx_options_bot.config import BotConfig
from spx_options_bot.models import MarketSnapshot, TradeAction
from spx_options_bot.strategy import SpxZeroDteIronCondorStrategy


def _config(**overrides):
    values = dict(
        ib_host="127.0.0.1",
        ib_port=7497,
        ib_client_id=17,
        account_id=None,
        dry_run=True,
        live_trading=False,
        account_size_usd=25_000,
        max_risk_per_trade_usd=1_000,
        max_daily_loss_usd=500,
        max_open_positions=1,
        underlying="SPX",
        exchange="CBOE",
        currency="USD",
        strategy="spx_0dte_iron_condor",
        target_dte=0,
        short_delta=0.15,
        spread_width=5,
        take_profit_pct=70,
        stop_loss_multiple=3.0,
        stop_loss_pct=300,
        contracts=1,
        max_daily_trades=1,
        min_otm_distance_pct=1.7,
        max_otm_distance_pct=2.0,
        put_spread_width=5,
        call_spread_width=5,
        max_vix=25,
        max_overnight_gap_pct=0.005,
        entry_after_minutes=60,
        force_close_before_minutes=60,
        market_timezone="America/New_York",
        use_delayed_market_data=True,
    )
    values.update(overrides)
    return BotConfig(**values)


def _snapshot(**overrides):
    now = datetime(2026, 5, 15, 10, 45, tzinfo=ZoneInfo("America/New_York"))
    values = dict(
        underlying_symbol="SPX",
        underlying_price=5000,
        open_positions=0,
        realized_pnl_today=0,
        timestamp=now,
        vix_price=18,
        overnight_gap_pct=0.002,
        available_expirations=("20260515",),
        available_strikes=tuple(float(strike) for strike in range(4800, 5210, 5)),
        trades_opened_today=0,
    )
    values.update(overrides)
    return MarketSnapshot(**values)


def test_creates_iron_condor_signal_inside_rules():
    signal = SpxZeroDteIronCondorStrategy(_config()).generate_signal(_snapshot())

    assert signal.action is TradeAction.SELL_IRON_CONDOR
    assert len(signal.legs) == 4
    assert signal.legs[0].strike == 4915
    assert signal.legs[2].strike == 5085


def test_uses_separate_put_and_call_spread_widths():
    signal = SpxZeroDteIronCondorStrategy(
        _config(put_spread_width=10, call_spread_width=15)
    ).generate_signal(_snapshot())

    assert signal.legs[1].strike == 4905
    assert signal.legs[3].strike == 5100


def test_blocks_when_vix_is_too_high():
    signal = SpxZeroDteIronCondorStrategy(_config()).generate_signal(
        _snapshot(vix_price=26)
    )

    assert signal.action is TradeAction.NONE
    assert "VIX" in signal.reason


def test_blocks_when_gap_is_too_large():
    signal = SpxZeroDteIronCondorStrategy(_config()).generate_signal(
        _snapshot(overnight_gap_pct=0.007)
    )

    assert signal.action is TradeAction.NONE
    assert "Overnight gap" in signal.reason


def test_blocks_outside_entry_window():
    timestamp = datetime(2026, 5, 15, 9, 45, tzinfo=ZoneInfo("America/New_York"))
    signal = SpxZeroDteIronCondorStrategy(_config()).generate_signal(
        _snapshot(timestamp=timestamp)
    )

    assert signal.action is TradeAction.NONE
    assert "entry window" in signal.reason
