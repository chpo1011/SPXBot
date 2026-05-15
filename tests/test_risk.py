from spx_options_bot.config import BotConfig
from spx_options_bot.models import MarketSnapshot, TradeAction, TradeSignal
from spx_options_bot.risk import RiskManager


def _config(**overrides):
    values = dict(
        ib_host="127.0.0.1",
        ib_port=7497,
        ib_client_id=17,
        account_id=None,
        dry_run=True,
        live_trading=False,
        account_size_usd=25_000,
        max_risk_per_trade_usd=250,
        max_daily_loss_usd=500,
        max_open_positions=1,
        underlying="SPX",
        exchange="CBOE",
        currency="USD",
        strategy="noop",
        target_dte=0,
        short_delta=0.15,
        spread_width=5,
        take_profit_pct=70,
        stop_loss_multiple=2.0,
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
    values = dict(
        underlying_symbol="SPX",
        underlying_price=5200,
        open_positions=0,
        realized_pnl_today=0,
    )
    values.update(overrides)
    return MarketSnapshot(**values)


def test_blocks_live_submission_in_dry_run():
    signal = TradeSignal(
        action=TradeAction.SELL_PUT_CREDIT_SPREAD,
        reason="test",
        max_loss_usd=100,
    )

    decision = RiskManager(_config()).evaluate(_snapshot(), signal)

    assert not decision.approved
    assert "Dry-run" in decision.reason


def test_does_not_block_by_trade_risk_or_daily_loss():
    signal = TradeSignal(
        action=TradeAction.SELL_PUT_CREDIT_SPREAD,
        reason="test",
        max_loss_usd=10_000,
    )

    decision = RiskManager(_config(dry_run=False, live_trading=True)).evaluate(
        _snapshot(realized_pnl_today=-10_000), signal
    )

    assert decision.approved


def test_approves_when_live_and_within_limits():
    signal = TradeSignal(
        action=TradeAction.SELL_PUT_CREDIT_SPREAD,
        reason="test",
        max_loss_usd=100,
    )

    decision = RiskManager(_config(dry_run=False, live_trading=True)).evaluate(
        _snapshot(), signal
    )

    assert decision.approved
