from datetime import datetime, timezone
import pandas as pd
from src.data_validator import DataValidator
from src.data_loader import DataLoader


def test_data_validation_success():
    start = datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc)
    df = DataLoader.generate_synthetic_data(start, hours=2)
    is_valid, report = DataValidator.validate_ohlcv_dataframe(df)
    assert is_valid is True
    assert report["validation_status"] == "PASSED"
    assert report["invalid_ohlc"] == 0
    assert report["duplicates"] == 0


def test_data_validation_detects_invalid_high_low():
    df = pd.DataFrame([{
        "timestamp": pd.Timestamp("2026-01-01 09:30:00", tz="UTC"),
        "open": 100.0,
        "high": 90.0,  # Invalid: High < Open
        "low": 105.0,
        "close": 95.0,
        "volume": 10
    }])
    is_valid, report = DataValidator.validate_ohlcv_dataframe(df)
    assert is_valid is False
    assert report["invalid_ohlc"] > 0