from datetime import datetime, timezone
from src.config import BacktestConfig
from src.models import Trade, Candle, Direction, SetupType, SignalType
from src.stop_manager import StopManager


def test_trailing_sl_progression_1r_3r_step():
    config = BacktestConfig()
    t = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    trade = Trade(
        trade_id="TR_TEST",
        symbol="MNQ",
        direction=Direction.LONG,
        setup_type=SetupType.LONG_BREAKOUT,
        reference_hour_id="REF1",
        reference_start=t,
        reference_end=t,
        reference_high=18050.0,
        reference_low=17950.0,
        signal_15m_time=t,
        signal_15m_type=SignalType.UP_BREAKOUT,
        confirmation_5m_time=t,
        confirmation_5m_price=18055.0,
        entry_signal_1m_time=t,
        entry_time=t,
        entry_price=18050.0,
        contracts=1,
        initial_stop=18040.0,  # 10 pts risk => 1R = 18060, 3R = 18080, 4R = 18090
        initial_risk_points=10.0,
        initial_risk_money=20.0,
        current_stop=18040.0,
        highest_price=18050.0,
        lowest_price=18050.0
    )

    # 1. Price touches 1R (18060) -> SL moves to +1R (18060)
    c1 = Candle(t, 18055, 18062, 18055, 18061, 10)
    StopManager.update_trailing_stop(trade, c1, config)
    assert trade.trailing_r == 1.0
    assert trade.current_stop == 18060.0

    # 2. Price touches 3R (18080) -> SL moves to +3R (18080)
    c2 = Candle(t, 18070, 18085, 18070, 18082, 10)
    StopManager.update_trailing_stop(trade, c2, config)
    assert trade.trailing_r == 3.0
    assert trade.current_stop == 18080.0

    # 3. Price touches 4.5R (18095) -> SL moves to +4R (18090)
    c3 = Candle(t, 18085, 18096, 18085, 18094, 10)
    StopManager.update_trailing_stop(trade, c3, config)
    assert trade.trailing_r == 4.0
    assert trade.current_stop == 18090.0