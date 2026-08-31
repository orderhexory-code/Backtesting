from datetime import datetime, timezone
from src.config import BacktestConfig
from src.data_loader import DataLoader
from src.backtester import Backtester
from src.models import Direction


def test_upside_breakout_strategy_execution():
    config = BacktestConfig()
    start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    df = DataLoader.generate_synthetic_data(start, hours=4, scenario="upside_breakout")
    candles = DataLoader.dataframe_to_candles(df)
    
    backtester = Backtester(config)
    trades = backtester.run(candles)
    
    assert len(trades) >= 1
    assert trades[0].direction == Direction.LONG
    assert trades[0].highest_r_reached >= 1.0