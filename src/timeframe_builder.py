"""Timeframe resampler and candle aggregator with strict anti-lookahead logic."""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from src.models import Candle


class CandleAggregator:
    """Aggregates stream of 1M candles into higher timeframe bars (5M, 15M, 1H)."""
    def __init__(self, minutes_window: int):
        self.minutes_window = minutes_window
        self.current_candles: List[Candle] = []
        self.window_start: Optional[datetime] = None

    def add_1m(self, candle: Candle) -> Optional[Candle]:
        """
        Ingests a 1M candle. If this candle completes the aggregate window,
        returns the completed higher timeframe Candle, otherwise returns None.
        """
        # Align timestamp based on UTC minute/hour boundaries
        ts = candle.timestamp
        # Target boundary: a 15M bar starting at 10:00 includes 10:00..10:14 and closes at 10:15
        # The window_id is determined by floor rounding
        minute = ts.minute
        window_idx = (minute // self.minutes_window) * self.minutes_window
        expected_start = ts.replace(minute=window_idx, second=0, microsecond=0)

        if self.window_start is None:
            self.window_start = expected_start

        if expected_start != self.window_start:
            # We stepped into a new window! The previous window is complete.
            completed_candle = self._build_aggregate()
            self.window_start = expected_start
            self.current_candles = [candle]
            return completed_candle
        else:
            self.current_candles.append(candle)
            # Check if this candle is the exact boundary end (e.g. minute 14 in 0..14)
            if (candle.timestamp.minute % self.minutes_window) == (self.minutes_window - 1):
                completed_candle = self._build_aggregate()
                self.window_start = None
                self.current_candles = []
                return completed_candle
            return None

    def _build_aggregate(self) -> Optional[Candle]:
        if not self.current_candles:
            return None
        o = self.current_candles[0].open
        h = max(c.high for c in self.current_candles)
        l = min(c.low for c in self.current_candles)
        c = self.current_candles[-1].close
        vol = sum(c.volume for c in self.current_candles)
        end_ts = self.current_candles[-1].timestamp
        return Candle(timestamp=end_ts, open=o, high=h, low=l, close=c, volume=vol)