"""Central chronological backtesting engine."""
from __future__ import annotations
from typing import List, Optional
import pandas as pd
from src.config import BacktestConfig
from src.models import Candle, Trade, TradeStatus, Direction, SetupType, SignalType
from src.candle_engine import CandleEngine
from src.strategy_state import StrategyStateMachine, SetupIntent
from src.trade_manager import TradeManager
from src.stop_manager import StopManager
from src.execution import ExecutionSimulator


class Backtester:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.candle_engine = CandleEngine()
        self.state_machine = StrategyStateMachine(config)
        self.trade_manager = TradeManager(config)
        self.recent_1m_bars: List[Candle] = []
        self.pending_entry_setups: List[SetupIntent] = []
        self.trade_id_seq = 0

    def run(self, candles: List[Candle]) -> List[Trade]:
        for event in self.candle_engine.process_candles(candles):
            candle_1m = event.candle_1m
            self.recent_1m_bars.append(candle_1m)
            if len(self.recent_1m_bars) > 100:
                self.recent_1m_bars.pop(0)

            # 1. Higher Timeframe Finalizations (Strict Anti-Lookahead)
            if event.completed_1h:
                self.state_machine.on_1h_completed(event.completed_1h)

            if event.completed_15m:
                self.state_machine.on_15m_completed(event.completed_15m)

            if event.completed_5m:
                newly_confirmed = self.state_machine.on_5m_completed(event.completed_5m)
                for setup in newly_confirmed:
                    if setup.entries_count < self.config.strategy.max_entries_per_setup:
                        self.pending_entry_setups.append(setup)

            # 2. Process Existing Active Trades
            self.trade_manager.process_1m_candle(candle_1m)

            # 3. Process Pending Entries at Next 1M Open / Trigger
            if self.pending_entry_setups and self.trade_manager.can_open_trade():
                to_remove = []
                for setup in self.pending_entry_setups:
                    if not setup.is_expired and setup.entries_count < self.config.strategy.max_entries_per_setup:
                        trade = self._create_trade(setup, candle_1m)
                        if trade:
                            self.trade_manager.open_trade(trade)
                            setup.is_entry_triggered = True
                            setup.entries_count += 1
                            to_remove.append(setup)
                    else:
                        to_remove.append(setup)

                self.pending_entry_setups = [s for s in self.pending_entry_setups if s not in to_remove]

        return self.trade_manager.closed_trades

    def _create_trade(self, setup: SetupIntent, candle_1m: Candle) -> Optional[Trade]:
        direction = setup.direction
        entry_price = ExecutionSimulator.apply_slippage(
            candle_1m.open if self.config.entry.execution == "next_bar_open" else candle_1m.close,
            direction,
            True,
            self.config
        )

        initial_sl = StopManager.calculate_initial_sl(
            direction, entry_price, self.recent_1m_bars, self.config
        )

        risk_pts = abs(entry_price - initial_sl)
        if risk_pts <= 0:
            return None

        contracts = ExecutionSimulator.calculate_position_size(entry_price, initial_sl, self.config)
        risk_money = risk_pts * self.config.instrument.point_value * contracts

        # Setup classification
        if setup.signal_type == SignalType.UP_BREAKOUT:
            stype = SetupType.LONG_BREAKOUT
        elif setup.signal_type == SignalType.DOWN_BREAKOUT:
            stype = SetupType.SHORT_BREAKOUT
        elif setup.signal_type == SignalType.UPSWEEP:
            stype = SetupType.SHORT_AFTER_UPSWEEP
        else:
            stype = SetupType.LONG_AFTER_DOWNSWEEP

        self.trade_id_seq += 1
        trade = Trade(
            trade_id=f"TR_{self.trade_id_seq:04d}",
            symbol=self.config.instrument.symbol,
            direction=direction,
            setup_type=stype,
            reference_hour_id=setup.reference.hour_id,
            reference_start=setup.reference.start_time,
            reference_end=setup.reference.end_time,
            reference_high=setup.reference.high,
            reference_low=setup.reference.low,
            signal_15m_time=setup.signal_candle_15m.timestamp,
            signal_15m_type=setup.signal_type,
            confirmation_5m_time=setup.confirmation_5m_time or candle_1m.timestamp,
            confirmation_5m_price=setup.confirmation_5m_price or candle_1m.open,
            entry_signal_1m_time=candle_1m.timestamp,
            entry_time=candle_1m.timestamp,
            entry_price=entry_price,
            contracts=contracts,
            initial_stop=initial_sl,
            initial_risk_points=risk_pts,
            initial_risk_money=risk_money,
            current_stop=initial_sl,
            highest_price=entry_price,
            lowest_price=entry_price,
            status=TradeStatus.PENDING
        )
        return trade