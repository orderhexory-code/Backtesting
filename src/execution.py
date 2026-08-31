"""Simulates order fills, slippage, commissions, and intrabar ambiguity."""
from __future__ import annotations
from typing import Tuple, Optional
from src.models import Candle, Direction, Trade, TradeStatus
from src.config import BacktestConfig


class ExecutionSimulator:
    @staticmethod
    def calculate_position_size(entry_price: float, stop_price: float, config: BacktestConfig) -> int:
        if config.position.mode == "fixed_contracts":
            return config.position.contracts
        
        # Fixed Risk mode
        risk_per_trade = config.position.risk_per_trade
        stop_dist_pts = abs(entry_price - stop_price)
        if stop_dist_pts <= 0:
            return 1
        risk_per_contract = stop_dist_pts * config.instrument.point_value
        contracts = int(risk_per_trade // risk_per_contract)
        return max(1, contracts)

    @staticmethod
    def apply_slippage(price: float, direction: Direction, is_entry: bool, config: BacktestConfig) -> float:
        ticks = config.execution.slippage_ticks
        tick_size = config.instrument.tick_size
        slip_points = ticks * tick_size

        if is_entry:
            return price + slip_points if direction == Direction.LONG else price - slip_points
        else:
            # Exit execution
            return price - slip_points if direction == Direction.LONG else price + slip_points

    @staticmethod
    def evaluate_bar_exit(
        trade: Trade,
        candle: Candle,
        config: BacktestConfig
    ) -> Optional[Tuple[float, str]]:
        """
        Conservative Intrabar Evaluation:
        If both stop loss and new trailing level are reached in the same 1M bar,
        assume stop loss hit first to eliminate optimistic bias.
        """
        sl = trade.current_stop

        if trade.direction == Direction.LONG:
            # SL hit if Low <= SL
            if candle.low <= sl:
                raw_exit = min(candle.open, sl) if candle.open < sl else sl
                exit_price = ExecutionSimulator.apply_slippage(raw_exit, trade.direction, False, config)
                return exit_price, "TRAILING_STOP_HIT" if trade.trailing_r >= 1.0 else "INITIAL_STOP_HIT"

        elif trade.direction == Direction.SHORT:
            # SL hit if High >= SL
            if candle.high >= sl:
                raw_exit = max(candle.open, sl) if candle.open > sl else sl
                exit_price = ExecutionSimulator.apply_slippage(raw_exit, trade.direction, False, config)
                return exit_price, "TRAILING_STOP_HIT" if trade.trailing_r >= 1.0 else "INITIAL_STOP_HIT"

        return None