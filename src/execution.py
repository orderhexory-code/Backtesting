"""Simulates position sizing (% of fund / fixed risk), slippage, commissions, and intrabar exits."""
from __future__ import annotations
from typing import Tuple, Optional
import math
from src.models import Candle, Direction, Trade, TradeStatus
from src.config import BacktestConfig


class ExecutionSimulator:
    @staticmethod
    def calculate_position_size(
        entry_price: float,
        stop_price: float,
        config: BacktestConfig,
        current_equity: float = 10000.0
    ) -> int:
        stop_dist_pts = abs(entry_price - stop_price)
        if stop_dist_pts <= 0:
            return 1

        pt_val = config.instrument.point_value

        if config.position.mode == "fixed_contracts":
            return max(1, config.position.contracts)
        
        elif config.position.mode == "percent_risk":
            # Dynamic Compounding: Risk % of Current Account Equity
            risk_pct = getattr(config.position, "risk_percent", 1.0)
            risk_money = current_equity * (risk_pct / 100.0)
            risk_per_contract = stop_dist_pts * pt_val
            contracts = math.floor(risk_money / risk_per_contract)
            return max(1, int(contracts))

        else:  # Fixed money risk mode
            risk_per_trade = config.position.risk_per_trade
            risk_per_contract = stop_dist_pts * pt_val
            contracts = math.floor(risk_per_trade / risk_per_contract)
            return max(1, int(contracts))

    @staticmethod
    def apply_slippage(price: float, direction: Direction, is_entry: bool, config: BacktestConfig) -> float:
        ticks = config.execution.slippage_ticks
        tick_size = config.instrument.tick_size
        slip_points = ticks * tick_size

        if is_entry:
            return price + slip_points if direction == Direction.LONG else price - slip_points
        else:
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
        assume stop loss was hit first to prevent optimistic bias.
        """
        sl = trade.current_stop

        if trade.direction == Direction.LONG:
            if candle.low <= sl:
                raw_exit = min(candle.open, sl) if candle.open < sl else sl
                exit_price = ExecutionSimulator.apply_slippage(raw_exit, trade.direction, False, config)
                return exit_price, "TRAILING_STOP_HIT" if trade.trailing_r >= 1.0 else "INITIAL_STOP_HIT"

        elif trade.direction == Direction.SHORT:
            if candle.high >= sl:
                raw_exit = max(candle.open, sl) if candle.open > sl else sl
                exit_price = ExecutionSimulator.apply_slippage(raw_exit, trade.direction, False, config)
                return exit_price, "TRAILING_STOP_HIT" if trade.trailing_r >= 1.0 else "INITIAL_STOP_HIT"

        return None
