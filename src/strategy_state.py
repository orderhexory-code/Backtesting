"""State machine tracking completed 1H references, 15M breakouts/sweeps, and 5M confirmations."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from src.models import (
    Candle, ReferenceHour, Direction, SetupType, SignalType
)
from src.config import BacktestConfig


class SetupIntent:
    def __init__(
        self,
        setup_id: str,
        reference: ReferenceHour,
        signal_type: SignalType,
        direction: Direction,
        signal_candle_15m: Candle,
        target_confirmation_level: float
    ):
        self.setup_id = setup_id
        self.reference = reference
        self.signal_type = signal_type
        self.direction = direction
        self.signal_candle_15m = signal_candle_15m
        self.target_confirmation_level = target_confirmation_level
        self.is_confirmed_5m: bool = False
        self.confirmation_5m_time: Optional[datetime] = None
        self.confirmation_5m_price: Optional[float] = None
        self.is_entry_triggered: bool = False
        self.entries_count: int = 0
        self.is_expired: bool = False


class StrategyStateMachine:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.current_reference: Optional[ReferenceHour] = None
        self.active_setups: List[SetupIntent] = []
        self.setup_counter = 0

    def on_1h_completed(self, candle_1h: Candle) -> None:
        """New 1H candle finalized. Sets new reference levels without resetting active open trades."""
        hour_id = f"1H_{candle_1h.timestamp.strftime('%Y%m%d_%H%M')}"
        self.current_reference = ReferenceHour(
            hour_id=hour_id,
            start_time=candle_1h.timestamp,
            end_time=candle_1h.timestamp,
            high=candle_1h.high,
            low=candle_1h.low,
            open=candle_1h.open,
            close=candle_1h.close,
            is_completed=True
        )

        # Expire pending setups if configured
        if self.config.setup.expiration == "next_reference_hour":
            for s in self.active_setups:
                if not s.is_entry_triggered:
                    s.is_expired = True
            self.active_setups = [s for s in self.active_setups if not s.is_expired]

    def on_15m_completed(self, candle_15m: Candle) -> Optional[SetupIntent]:
        """Evaluates 15M breakout / sweep against the completed 1H reference."""
        if not self.current_reference or not self.current_reference.is_completed:
            return None

        ref_h = self.current_reference.high
        ref_l = self.current_reference.low

        signal_type: Optional[SignalType] = None
        direction: Optional[Direction] = None
        target_confirm_level = 0.0

        # 1. Upside Breakout: High > 1H High AND Close > 1H High -> LONG
        if candle_15m.high > ref_h and candle_15m.close > ref_h:
            signal_type = SignalType.UP_BREAKOUT
            direction = Direction.LONG
            target_confirm_level = ref_h

        # 2. Downside Breakout: Low < 1H Low AND Close < 1H Low -> SHORT
        elif candle_15m.low < ref_l and candle_15m.close < ref_l:
            signal_type = SignalType.DOWN_BREAKOUT
            direction = Direction.SHORT
            target_confirm_level = ref_l

        # 3. Upside Sweep: High > 1H High AND Close <= 1H High -> Potential SHORT
        elif candle_15m.high > ref_h and candle_15m.close <= ref_h:
            signal_type = SignalType.UPSWEEP
            direction = Direction.SHORT
            target_confirm_level = ref_l  # Wait for downside confirmation

        # 4. Downside Sweep: Low < 1H Low AND Close >= 1H Low -> Potential LONG
        elif candle_15m.low < ref_l and candle_15m.close >= ref_l:
            signal_type = SignalType.DOWNSWEEP
            direction = Direction.LONG
            target_confirm_level = ref_h  # Wait for upside confirmation

        if signal_type and direction:
            self.setup_counter += 1
            setup = SetupIntent(
                setup_id=f"SETUP_{self.setup_counter}_{candle_15m.timestamp.strftime('%H%M')}",
                reference=self.current_reference,
                signal_type=signal_type,
                direction=direction,
                signal_candle_15m=candle_15m,
                target_confirmation_level=target_confirm_level
            )
            self.active_setups.append(setup)
            return setup

        return None

    def on_5m_completed(self, candle_5m: Candle) -> List[SetupIntent]:
        """Evaluates 5M confirmation for active setups. Note: 5M sweeps are ignored per rule #26."""
        confirmed_setups: List[SetupIntent] = []
        for setup in self.active_setups:
            if setup.is_confirmed_5m or setup.is_expired:
                continue

            if setup.direction == Direction.LONG:
                # 5M confirms upside break
                if candle_5m.close > setup.target_confirmation_level:
                    setup.is_confirmed_5m = True
                    setup.confirmation_5m_time = candle_5m.timestamp
                    setup.confirmation_5m_price = candle_5m.close
                    confirmed_setups.append(setup)
            elif setup.direction == Direction.SHORT:
                # 5M confirms downside break
                if candle_5m.close < setup.target_confirmation_level:
                    setup.is_confirmed_5m = True
                    setup.confirmation_5m_time = candle_5m.timestamp
                    setup.confirmation_5m_price = candle_5m.close
                    confirmed_setups.append(setup)

        return confirmed_setups