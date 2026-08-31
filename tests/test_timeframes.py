from datetime import datetime, timezone, timedelta
from src.models import Candle
from src.candle_engine import CandleEngine


def test_candle_aggregator_boundary():
    engine = CandleEngine()
    start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    candles = [
        Candle(start + timedelta(minutes=i), 100 + i, 105 + i, 95 + i, 102 + i, 10)
        for i in range(15)
    ]
    events = list(engine.process_candles(candles))
    
    # 5M candle should complete at 9:04, 9:09, 9:14
    completed_5m = [e.completed_5m for e in events if e.completed_5m is not None]
    assert len(completed_5m) == 3

    # 15M candle should complete on minute 14 (15th bar)
    completed_15m = [e.completed_15m for e in events if e.completed_15m is not None]
    assert len(completed_15m) == 1
    assert completed_15m[0].open == 100
    assert completed_15m[0].close == 102 + 14