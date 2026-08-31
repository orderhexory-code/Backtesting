"""Calculates initial structural SL and executes multi-stage R-based trailing stop updates."""
from __future__ import annotations
from typing import List, Optional
from src.models import Candle, Direction, Trade
from src.config import BacktestConfig


class StopManager:
    @staticmethod
    def calculate_initial_sl(
        direction: Direction,
        entry_price: float,
        recent_1m_bars: List[Candle],
        config: BacktestConfig
    ) -> float:
        """
        Determines structural SL based on previous 1M bars (anti-lookahead).
        Uses buffer ticks according to configuration.
        """
        tick_size = config.instrument.tick_size
        buffer_pts = config.stop_loss.buffer_ticks * tick_size

        if not recent_1m_bars:
            default_risk = 20 * tick_size
            return entry_price - default_risk if direction == Direction.LONG else entry_price + default_risk

        # Look back over last 3-5 1M bars for structural swing/low
        window = recent_1m_bars[-5:]
        if direction == Direction.LONG:
            lowest_structure = min(b.low for b in window)
            sl = lowest_structure - buffer_pts
            if sl >= entry_price:
                sl = entry_price - (4 * tick_size)
            return round(sl, 2)
        else:
            highest_structure = max(b.high for b in window)
            sl = highest_structure + buffer_pts
            if sl <= entry_price:
                sl = entry_price + (4 * tick_size)
            return round(sl, 2)

    @staticmethod
    def update_trailing_stop(trade: Trade, candle: Candle, config: BacktestConfig) -> None:
        """
        Applies PRD Trailing Logic:
        1. When price reaches +1R -> Move SL to +1R (No profit booking, 100% position open)
        2. When price reaches +3R -> Move SL to +3R
        3. After +3R -> For every additional +1R (4R, 5R, 6R...), advance SL by +1R
        """
        risk = trade.initial_risk_points
        if risk <= 0:
            return

        if trade.direction == Direction.LONG:
            trade.highest_price = max(trade.highest_price, candle.high)
            current_favorable_points = trade.highest_price - trade.entry_price
            current_r = current_favorable_points / risk
            trade.highest_r_reached = max(trade.highest_r_reached, current_r)

            # Check 1R trigger
            if current_r >= 1.0 and trade.trailing_r < 1.0:
                trade.trailing_r = 1.0
                trade.current_stop = trade.entry_price + (1.0 * risk)
                trade.log_event(candle.timestamp, "1R_REACHED_SL_TRAILED", trade.current_stop, "+1R reached, SL -> +1R")

            # Check 3R trigger
            if current_r >= 3.0 and trade.trailing_r < 3.0:
                trade.trailing_r = 3.0
                trade.current_stop = trade.entry_price + (3.0 * risk)
                trade.log_event(candle.timestamp, "3R_REACHED_SL_TRAILED", trade.current_stop, "+3R reached, SL -> +3R")

            # Check Post-3R step trailing (4R, 5R, 6R...)
            if current_r >= 4.0:
                next_integer_r = int(current_r)
                if next_integer_r > trade.trailing_r:
                    trade.trailing_r = float(next_integer_r)
                    trade.current_stop = trade.entry_price + (trade.trailing_r * risk)
                    trade.log_event(
                        candle.timestamp,
                        f"{next_integer_r}R_REACHED_SL_TRAILED",
                        trade.current_stop,
                        f"+{next_integer_r}R reached, SL -> +{next_integer_r}R"
                    )

        elif trade.direction == Direction.SHORT:
            trade.lowest_price = min(trade.lowest_price, candle.low)
            current_favorable_points = trade.entry_price - trade.lowest_price
            current_r = current_favorable_points / risk
            trade.highest_r_reached = max(trade.highest_r_reached, current_r)

            # Check 1R trigger
            if current_r >= 1.0 and trade.trailing_r < 1.0:
                trade.trailing_r = 1.0
                trade.current_stop = trade.entry_price - (1.0 * risk)
                trade.log_event(candle.timestamp, "1R_REACHED_SL_TRAILED", trade.current_stop, "+1R reached, SL -> -1R")

            # Check 3R trigger
            if current_r >= 3.0 and trade.trailing_r < 3.0:
                trade.trailing_r = 3.0
                trade.current_stop = trade.entry_price - (3.0 * risk)
                trade.log_event(candle.timestamp, "3R_REACHED_SL_TRAILED", trade.current_stop, "+3R reached, SL -> -3R")

            # Check Post-3R step trailing
            if current_r >= 4.0:
                next_integer_r = int(current_r)
                if next_integer_r > trade.trailing_r:
                    trade.trailing_r = float(next_integer_r)
                    trade.current_stop = trade.entry_price - (trade.trailing_r * risk)
                    trade.log_event(
                        candle.timestamp,
                        f"{next_integer_r}R_REACHED_SL_TRAILED",
                        trade.current_stop,
                        f"+{next_integer_r}R reached, SL -> -{next_integer_r}R"
                    )