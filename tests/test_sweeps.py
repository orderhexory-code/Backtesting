from datetime import datetime, timezone
from src.config import BacktestConfig
from src.data_loader import DataLoader
from src.backtester import Backtester
from src.models import Direction, SetupType


def test_upside_sweep_generates_short():
    config = BacktestConfig()
    start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    df = DataLoader.generate_synthetic_data(start, hours=4, scenario="upside_sweep")
    candles = DataLoader.dataframe_to_candles(df)
    
    backtester = Backtester(config)
    trades = backtester.run(candles)
    
    assert len(trades) >= 1
    assert trades[0].direction == Direction.SHORT
    assert trades[0].setup_type == SetupType.SHORT_AFTER_UPSWEEP