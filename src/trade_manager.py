"""Manages concurrent independent trades, accounting, and lifecycle."""
from __future__ import annotations
from datetime import datetime
from typing import List
from src.models import Trade, TradeStatus, Candle, Direction
from src.config import BacktestConfig
from src.execution import ExecutionSimulator
from src.stop_manager import StopManager


class TradeManager:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.open_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []

    def can_open_trade(self) -> bool:
        max_c = self.config.risk.max_concurrent_trades
        if max_c is not None and len(self.open_trades) >= max_c:
            return False
        return True

    def open_trade(self, trade: Trade) -> None:
        trade.status = TradeStatus.OPEN
        trade.log_event(trade.entry_time, "TRADE_OPENED", trade.entry_price, f"Contracts: {trade.contracts}")
        self.open_trades.append(trade)

    def process_1m_candle(self, candle: Candle) -> None:
        """
        Independent trade lifecycle check:
        1. Check exit against current SL.
        2. If survived, update trailing SL for next bars.
        Trades persist across 1H and session boundaries.
        """
        remaining_trades = []
        for trade in self.open_trades:
            # 1. Evaluate Exit with Conservative Intrabar Handling
            exit_result = ExecutionSimulator.evaluate_bar_exit(trade, candle, self.config)
            if exit_result:
                exit_price, reason = exit_result
                self._close_trade(trade, candle.timestamp, exit_price, reason)
                self.closed_trades.append(trade)
            else:
                # 2. Update trailing stop
                StopManager.update_trailing_stop(trade, candle, self.config)
                remaining_trades.append(trade)

        self.open_trades = remaining_trades

    def _close_trade(self, trade: Trade, exit_time: datetime, exit_price: float, reason: str) -> None:
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.status = TradeStatus.CLOSED
        trade.holding_minutes = (exit_time - trade.entry_time).total_seconds() / 60.0

        pt_val = self.config.instrument.point_value
        comm_per_c = self.config.execution.commission_per_contract

        if trade.direction == Direction.LONG:
            points = trade.exit_price - trade.entry_price
        else:
            points = trade.entry_price - trade.exit_price

        trade.gross_pnl = points * pt_val * trade.contracts
        trade.commission = comm_per_c * trade.contracts * 2  # roundtrip
        trade.slippage = (self.config.execution.slippage_ticks * self.config.instrument.tick_size * pt_val * 2) * trade.contracts
        trade.net_pnl = trade.gross_pnl - trade.commission

        if trade.initial_risk_points > 0:
            trade.r_multiple = points / trade.initial_risk_points
        else:
            trade.r_multiple = 0.0

        trade.log_event(exit_time, f"TRADE_CLOSED_{reason}", exit_price, f"Net PnL: ${trade.net_pnl:.2f}, R: {trade.r_multiple:.2f}")