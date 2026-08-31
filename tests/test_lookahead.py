from datetime import datetime, timezone
import copy
from src.config import BacktestConfig
from src.data_loader import DataLoader
from src.backtester import Backtester


def test_anti_lookahead_integrity():
    """
    Mandatory PRD Rule #69:
    1. Run backtest on dataset A.
    2. Mutate only bars far after the entry candle.
    3. Verify entry timestamp, entry price, and initial SL are strictly identical.
    """
    config = BacktestConfig()
    start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    df_a = DataLoader.generate_synthetic_data(start, hours=5, scenario="upside_breakout")
    candles_a = DataLoader.dataframe_to_candles(df_a)

    bt_a = Backtester(config)
    trades_a = bt_a.run(candles_a)
    assert len(trades_a) > 0
    first_trade_a = trades_a[0]

    # Mutate future candles past the entry point (e.g. index 80 onwards)
    candles_b = copy.deepcopy(candles_a)
    for c in candles_b[80:]:
        # Alter future prices significantly
        object.__setattr__(c, 'open', c.open + 50.0)
        object.__setattr__(c, 'high', c.high + 50.0)
        object.__setattr__(c, 'close', c.close + 50.0)

    bt_b = Backtester(config)
    trades_b = bt_b.run(candles_b)
    first_trade_b = trades_b[0]

    # Look-ahead verification: Entry conditions MUST remain identical
    assert first_trade_a.entry_time == first_trade_b.entry_time, "FAIL: Look-ahead bias changed entry time"
    assert first_trade_a.entry_price == first_trade_b.entry_price, "FAIL: Look-ahead bias changed entry price"
    assert first_trade_a.initial_stop == first_trade_b.initial_stop, "FAIL: Look-ahead bias changed initial SL"