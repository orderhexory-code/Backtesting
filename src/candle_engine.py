"""Event-driven candle coordinator feeding 1M, 5M, 15M, and 1H events chronologically."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Generator
from src.models import Candle
from src.timeframe_builder import CandleAggregator


@dataclass
class CandleEvent:
    candle_1m: Candle
    completed_5m: Optional[Candle] = None
    completed_15m: Optional[Candle] = None
    completed_1h: Optional[Candle] = None


class CandleEngine:
    def __init__(self):
        self.agg_5m = CandleAggregator(5)
        self.agg_15m = CandleAggregator(15)
        self.agg_1h = CandleAggregator(60)

    def process_candles(self, candles: list[Candle]) -> Generator[CandleEvent, None, None]:
        for c in candles:
            c5 = self.agg_5m.add_1m(c)
            c15 = self.agg_15m.add_1m(c)
            c1h = self.agg_1h.add_1m(c)

            yield CandleEvent(
                candle_1m=c,
                completed_5m=c5,
                completed_15m=c15,
                completed_1h=c1h
            )