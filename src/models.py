"""Domain models and data structures for NASDAQ backtester."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SetupType(str, Enum):
    LONG_BREAKOUT = "LONG_BREAKOUT"
    SHORT_BREAKOUT = "SHORT_BREAKOUT"
    LONG_AFTER_DOWNSWEEP = "LONG_AFTER_DOWNSWEEP"
    SHORT_AFTER_UPSWEEP = "SHORT_AFTER_UPSWEEP"


class SignalType(str, Enum):
    UP_BREAKOUT = "UP_BREAKOUT"
    DOWN_BREAKOUT = "DOWN_BREAKOUT"
    UPSWEEP = "UPSWEEP"
    DOWNSWEEP = "DOWNSWEEP"


class ExecutionMode(str, Enum):
    NEXT_BAR_OPEN = "next_bar_open"
    SIGNAL_CLOSE = "signal_close"
    BREAKOUT_PRICE = "breakout_price"


class IntrabarMode(str, Enum):
    CONSERVATIVE = "conservative"
    OPTIMISTIC = "optimistic"


class TradeStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(slots=True, frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def is_valid(self) -> bool:
        return (
            self.high >= max(self.open, self.close)
            and self.low <= min(self.open, self.close)
            and self.high >= self.low
        )


@dataclass
class ReferenceHour:
    hour_id: str
    start_time: datetime
    end_time: datetime
    high: float
    low: float
    open: float
    close: float
    is_completed: bool = False


@dataclass
class TradeAuditTrail:
    timestamp: datetime
    event: str
    price: float
    details: str = ""


@dataclass
class Trade:
    trade_id: str
    symbol: str
    direction: Direction
    setup_type: SetupType
    
    reference_hour_id: str
    reference_start: datetime
    reference_end: datetime
    reference_high: float
    reference_low: float
    
    signal_15m_time: datetime
    signal_15m_type: SignalType
    
    confirmation_5m_time: datetime
    confirmation_5m_price: float
    
    entry_signal_1m_time: datetime
    entry_time: datetime
    entry_price: float
    contracts: int
    
    initial_stop: float
    initial_risk_points: float
    initial_risk_money: float
    
    current_stop: float
    highest_price: float
    lowest_price: float
    
    highest_r_reached: float = 0.0
    trailing_r: float = 0.0
    
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    gross_pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    net_pnl: float = 0.0
    r_multiple: float = 0.0
    holding_minutes: float = 0.0
    status: TradeStatus = TradeStatus.PENDING
    
    audit_trail: List[TradeAuditTrail] = field(default_factory=list)

    def log_event(self, timestamp: datetime, event: str, price: float, details: str = ""):
        self.audit_trail.append(TradeAuditTrail(timestamp, event, price, details))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "setup_type": self.setup_type.value,
            "reference_start": self.reference_start.isoformat(),
            "reference_end": self.reference_end.isoformat(),
            "reference_high": self.reference_high,
            "reference_low": self.reference_low,
            "15m_signal_time": self.signal_15m_time.isoformat(),
            "15m_signal_type": self.signal_15m_type.value,
            "5m_confirmation_time": self.confirmation_5m_time.isoformat(),
            "1m_entry_signal_time": self.entry_signal_1m_time.isoformat(),
            "entry_time": self.entry_time.isoformat(),
            "entry_price": round(self.entry_price, 2),
            "initial_sl": round(self.initial_stop, 2),
            "initial_risk": round(self.initial_risk_points, 2),
            "contracts": self.contracts,
            "max_r": round(self.highest_r_reached, 2),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_price": round(self.exit_price, 2) if self.exit_price is not None else None,
            "exit_reason": self.exit_reason,
            "gross_pnl": round(self.gross_pnl, 2),
            "commission": round(self.commission, 2),
            "slippage": round(self.slippage, 2),
            "net_pnl": round(self.net_pnl, 2),
            "r_multiple": round(self.r_multiple, 2),
            "holding_minutes": round(self.holding_minutes, 1),
            "status": self.status.value
        }