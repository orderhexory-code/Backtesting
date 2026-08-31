"""Data validation and quality metrics generator."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd


class DataValidator:
    @staticmethod
    def validate_ohlcv_dataframe(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        report: Dict[str, Any] = {
            "rows": len(df),
            "date_start": None,
            "date_end": None,
            "duplicates": 0,
            "invalid_ohlc": 0,
            "missing_intervals": 0,
            "largest_gap_minutes": 0,
            "validation_status": "FAILED",
            "errors": []
        }

        if df.empty:
            report["errors"].append("DataFrame is empty")
            return False, report

        required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required_cols.issubset(set(df.columns)):
            report["errors"].append(f"Missing required columns: {required_cols - set(df.columns)}")
            return False, report

        # Ensure timestamp is datetime and sorted
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            report["errors"].append("Timestamp column is not datetime type")
            return False, report

        # Duplicates
        duplicates = df["timestamp"].duplicated().sum()
        report["duplicates"] = int(duplicates)
        if duplicates > 0:
            report["errors"].append(f"Found {duplicates} duplicate timestamps")

        # Sorted check
        if not df["timestamp"].is_monotonic_increasing:
            report["errors"].append("Timestamps are not strictly monotonically increasing")

        # OHLC logic check: high >= max(open, close), low <= min(open, close), high >= low
        invalid_high = df["high"] < df[["open", "close"]].max(axis=1)
        invalid_low = df["low"] > df[["open", "close"]].min(axis=1)
        invalid_hl = df["high"] < df["low"]
        total_invalid_ohlc = (invalid_high | invalid_low | invalid_hl).sum()
        report["invalid_ohlc"] = int(total_invalid_ohlc)
        if total_invalid_ohlc > 0:
            report["errors"].append(f"Found {total_invalid_ohlc} bars with invalid OHLC geometry")

        # Timestamps & Gap analysis (1-minute standard)
        time_diffs = df["timestamp"].diff()
        if len(df) > 1:
            gaps = time_diffs[time_diffs > pd.Timedelta(minutes=1)]
            report["missing_intervals"] = int(len(gaps))
            if not gaps.empty:
                largest_gap = gaps.max().total_seconds() / 60.0
                report["largest_gap_minutes"] = round(largest_gap, 2)

        report["date_start"] = df["timestamp"].iloc[0].isoformat()
        report["date_end"] = df["timestamp"].iloc[-1].isoformat()

        is_valid = (duplicates == 0) and (total_invalid_ohlc == 0) and (len(report["errors"]) == 0)
        report["validation_status"] = "PASSED" if is_valid else "FAILED"

        return is_valid, report

    @staticmethod
    def save_report(report: Dict[str, Any], filepath: Path | str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)