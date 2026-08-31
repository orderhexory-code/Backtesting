"""Data ingestion, normalization, and synthetic dataset generation."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List
import pandas as pd
import numpy as np
from src.models import Candle


class DataLoader:
    @staticmethod
    def load_from_parquet(path: Path | str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        df = pd.read_parquet(path)
        return DataLoader._filter_and_normalize(df, start_date, end_date)

    @staticmethod
    def load_from_csv(path: Path | str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        df = pd.read_csv(path)
        return DataLoader._filter_and_normalize(df, start_date, end_date)

    @staticmethod
    def _filter_and_normalize(df: pd.DataFrame, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        df.columns = [c.lower().strip() for c in df.columns]
        if "time" in df.columns and "timestamp" not in df.columns:
            df.rename(columns={"time": "timestamp"}, inplace=True)
        if "vol" in df.columns and "volume" not in df.columns:
            df.rename(columns={"vol": "volume"}, inplace=True)

        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        elif df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(timezone.utc)
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert(timezone.utc)

        df.sort_values("timestamp", inplace=True)
        df.drop_duplicates(subset=["timestamp"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        if start_date:
            s_dt = pd.to_datetime(start_date, utc=True)
            df = df[df["timestamp"] >= s_dt]
        if end_date:
            e_dt = pd.to_datetime(end_date, utc=True)
            df = df[df["timestamp"] <= e_dt]

        df.reset_index(drop=True, inplace=True)
        return df

    @staticmethod
    def dataframe_to_candles(df: pd.DataFrame) -> List[Candle]:
        candles = []
        for row in df.itertuples(index=False):
            candles.append(
                Candle(
                    timestamp=row.timestamp.to_pydatetime(),
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    volume=float(getattr(row, "volume", 0.0))
                )
            )
        return candles

    @staticmethod
    def generate_synthetic_data(
        start: datetime,
        hours: int = 10,
        base_price: float = 18000.0,
        scenario: str = "upside_breakout"
    ) -> pd.DataFrame:
        """
        Creates synthetic deterministic 1-minute data for testing specific multi-timeframe setups.
        Scenarios:
          - upside_breakout: 1H reference, 15M break high, 5M confirm, 1M pullback & entry, trailing run.
          - downside_breakout: 1H reference, 15M break low, 5M confirm, 1M entry, trailing run.
          - upside_sweep: 1H reference, 15M sweeps high & closes below, 5M downside confirm, 1M short entry.
          - downside_sweep: 1H reference, 15M sweeps low & closes above, 5M upside confirm, 1M long entry.
        """
        records = []
        current_time = start
        current_price = base_price

        total_minutes = hours * 60
        # Reference hour 0:00 to 1:00: High 18050, Low 17950
        for m in range(total_minutes):
            minute_of_hour = m % 60
            hour_index = m // 60
            
            o = current_price
            h = o
            l = o
            c = o
            
            if hour_index == 0:
                # Build 1H reference: High 18050, Low 17950, Close 18000
                if minute_of_hour < 20:
                    c = 17950.0 + (minute_of_hour * 2.0)
                    h = c + 1.0
                    l = c - 1.0
                elif minute_of_hour < 40:
                    c = 18050.0 - ((minute_of_hour - 20) * 2.0)
                    h = c + 2.0
                    l = c - 1.0
                else:
                    c = 18000.0
                    h = 18005.0
                    l = 17995.0
            elif hour_index == 1:
                # Scenarios trigger in hour 1
                if scenario == "upside_breakout":
                    if minute_of_hour < 15:
                        # 15M bar completes at 15: High 18060, Close 18055 (> 18050 breakout)
                        c = 18010.0 + (minute_of_hour * 3.0)
                        h = c + 2.0
                        l = c - 1.0
                    elif minute_of_hour < 20:
                        # 5M bar closes at 20: breaks extreme confirm
                        c = 18065.0
                        h = 18070.0
                        l = 18060.0
                    elif minute_of_hour == 20:
                        # 1M entry setup
                        c = 18064.0
                        h = 18066.0
                        l = 18060.0
                    elif minute_of_hour == 21:
                        # Execution candle
                        c = 18066.0
                        h = 18068.0
                        l = 18063.0
                    else:
                        # Trailing run up
                        step = (minute_of_hour - 21) * 4.0
                        c = 18070.0 + step
                        h = c + 2.0
                        l = c - 2.0
                elif scenario == "upside_sweep":
                    if minute_of_hour < 15:
                        # 15M bar sweeps high 18055, but closes at 18045 (<= 18050)
                        c = 18045.0
                        h = 18055.0
                        l = 18030.0
                    elif minute_of_hour < 20:
                        # 5M confirm down
                        c = 17940.0
                        h = 17950.0
                        l = 17935.0
                    elif minute_of_hour == 20:
                        # 1M entry
                        c = 17938.0
                        h = 17942.0
                        l = 17935.0
                    else:
                        # Short trailing run down
                        step = (minute_of_hour - 20) * 4.0
                        c = 17935.0 - step
                        h = c + 2.0
                        l = c - 2.0
                else:
                    c = 18000.0 + np.sin(m) * 10
                    h = c + 2.0
                    l = c - 2.0
            else:
                c = current_price + 1.0
                h = c + 2.0
                l = c - 1.0

            h = max(h, o, c)
            l = min(l, o, c)
            current_price = c

            records.append({
                "timestamp": current_time,
                "open": round(o, 2),
                "high": round(h, 2),
                "low": round(l, 2),
                "close": round(c, 2),
                "volume": 100.0
            })
            current_time += timedelta(minutes=1)

        return pd.DataFrame(records)