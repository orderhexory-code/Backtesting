"""Automated real market 1-minute historical data fetcher."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf


class FreeDataFetcher:
    @staticmethod
    def fetch_real_30d_1m(
        symbol: str = "NQ=F",
        days: int = 28,
        output_path: str = "data/processed/MNQ_1m.parquet"
    ) -> pd.DataFrame:
        """
        Downloads 100% REAL 1-minute market candles from Yahoo Finance.
        Uses rolling 5-day intervals to fetch up to 30 days of real intraday data.
        """
        days = min(days, 29)  # Yahoo Finance strictly limits 1m data to last 29-30 days
        print(f"[*] Fetching 100% REAL 1-minute data for '{symbol}' (Last {days} days)...")

        ticker = yf.Ticker(symbol)
        now = datetime.now(timezone.utc)
        all_chunks = []

        step = 5  # Safe 5-day chunk size per API request
        end_time = now

        for i in range(0, days, step):
            start_time = max(end_time - timedelta(days=step), now - timedelta(days=days))
            print(f"    -> Downloading real market chunk: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")

            try:
                chunk = ticker.history(
                    start=start_time.strftime("%Y-%m-%d"),
                    end=end_time.strftime("%Y-%m-%d"),
                    interval="1m",
                    auto_adjust=False
                )
                if not chunk.empty:
                    all_chunks.append(chunk)
            except Exception as e:
                print(f"    [!] Chunk fetch warning: {e}")

            end_time = start_time
            if end_time <= (now - timedelta(days=days)):
                break

        if not all_chunks:
            # Direct 7-day fallback if chunking failed
            print("    [*] Attempting direct single fetch...")
            df = ticker.history(period="7d", interval="1m", auto_adjust=False)
            if df.empty:
                raise ValueError(f"Yahoo Finance returned 0 bars for '{symbol}'. Try symbol 'QQQ'.")
        else:
            df = pd.concat(all_chunks)

        df.reset_index(inplace=True)

        # Standardize column headers
        rename_map = {}
        for col in df.columns:
            c = str(col).lower()
            if "date" in c or "time" in c:
                rename_map[col] = "timestamp"
            elif "open" in c:
                rename_map[col] = "open"
            elif "high" in c:
                rename_map[col] = "high"
            elif "low" in c:
                rename_map[col] = "low"
            elif "close" in c and "adj" not in c:
                rename_map[col] = "close"
            elif "vol" in c:
                rename_map[col] = "volume"

        df.rename(columns=rename_map, inplace=True)
        df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()

        # Timezone UTC normalization
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(timezone.utc)
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert(timezone.utc)

        # Deduplicate and sort chronologically
        df.drop_duplicates(subset=["timestamp"], inplace=True)
        df.sort_values("timestamp", inplace=True)
        df.dropna(subset=["open", "high", "low", "close"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        if len(df) == 0:
            raise ValueError("No valid candles after cleaning.")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False)

        print(f"[+] SUCCESS: Fetched {len(df):,} REAL 1-minute candles from Yahoo Finance.")
        print(f"[+] Date Range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}\n")
        return df
