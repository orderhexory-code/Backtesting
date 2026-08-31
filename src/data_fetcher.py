"""Automated free 1-minute data downloader using yfinance with automatic chunking."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import pandas as pd
import yfinance as yf


class FreeDataFetcher:
    @staticmethod
    def fetch_yfinance_1m(
        symbol: str = "NQ=F",
        days: int = 7,
        output_path: str = "data/processed/MNQ_1m.parquet"
    ) -> pd.DataFrame:
        """
        Downloads 1-minute OHLCV data from Yahoo Finance.
        Yahoo allows max 7-8 days of 1m data per request within the last 30 days.
        This function downloads in valid chunks and combines them.
        
        Recommended symbols:
          - 'NQ=F'  (E-mini NASDAQ Futures)
          - 'QQQ'   (Invesco QQQ Trust - NASDAQ 100 ETF)
          - 'MNQ=F' (Micro E-mini NASDAQ Futures)
        """
        # Yahoo Finance limits intraday 1m to last 30 days max
        days = min(days, 29)
        print(f"[*] Starting download for '{symbol}' (Last {days} days, 1-minute intervals)...")

        ticker = yf.Ticker(symbol)
        now = datetime.now(timezone.utc)
        all_frames = []

        # Download in 5-day windows to strictly respect Yahoo's API constraints
        step_days = 5
        current_end = now
        total_steps = (days // step_days) + (1 if days % step_days != 0 else 0)

        for step in range(total_steps):
            current_start = max(current_end - timedelta(days=step_days), now - timedelta(days=days))
            print(f"    -> Fetching chunk: {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}")

            try:
                chunk = ticker.history(
                    start=current_start.strftime("%Y-%m-%d"),
                    end=current_end.strftime("%Y-%m-%d"),
                    interval="1m",
                    auto_adjust=False
                )
                if not chunk.empty:
                    all_frames.append(chunk)
            except Exception as e:
                print(f"    [!] Warning: Failed to fetch chunk: {e}")

            current_end = current_start
            if current_end <= (now - timedelta(days=days)):
                break

        if not all_frames:
            # Fallback single request with period="7d"
            print("    [*] Trying direct 7-day fallback fetch...")
            df = ticker.history(period="7d", interval="1m", auto_adjust=False)
            if df.empty:
                raise ValueError(
                    f"No data returned from Yahoo Finance for symbol '{symbol}'. "
                    f"Yahoo market might be closed or symbol rate-limited. Try using 'QQQ'."
                )
        else:
            df = pd.concat(all_frames)

        df.reset_index(inplace=True)

        # Standardize columns
        rename_dict = {}
        for col in df.columns:
            c_lower = str(col).lower()
            if "date" in c_lower or "time" in c_lower:
                rename_dict[col] = "timestamp"
            elif "open" in c_lower:
                rename_dict[col] = "open"
            elif "high" in c_lower:
                rename_dict[col] = "high"
            elif "low" in c_lower:
                rename_dict[col] = "low"
            elif "close" in c_lower and "adj" not in c_lower:
                rename_dict[col] = "close"
            elif "vol" in c_lower:
                rename_dict[col] = "volume"

        df.rename(columns=rename_dict, inplace=True)
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        df = df[required_cols].copy()

        # Handle missing volume
        df["volume"] = df["volume"].fillna(100.0)

        # Timezone UTC normalization
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(timezone.utc)
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert(timezone.utc)

        # Clean duplicates & sort
        df.drop_duplicates(subset=["timestamp"], inplace=True)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Drop incomplete rows
        df.dropna(subset=["open", "high", "low", "close"], inplace=True)

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)

        print(f"[+] Download complete! Successfully saved {len(df)} 1-minute bars to: {out.resolve()}\n")
        return df