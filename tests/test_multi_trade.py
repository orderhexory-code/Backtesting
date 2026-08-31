from datetime import datetime, timezone, timedelta
from src.config import BacktestConfig
from src.models import Candle
from src.backtester import Backtester
from src.data_loader import DataLoader


def test_trade_survives_hourly_and_session_boundaries():
    config = BacktestConfig()
    start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    # Generate 6 hours of continuous data
    df = DataLoader.generate_synthetic_data(start, hours=6, scenario="upside_breakout")
    candles = DataLoader.dataframe_to_candles(df)
    
    backtester = Backtester(config)
    trades = backtester.run(candles)
    
    assert len(trades) > 0
    # Confirm trade holding time spans across hour boundaries (> 60 minutes)
    assert any(t.holding_minutes > 60 for t in trades)