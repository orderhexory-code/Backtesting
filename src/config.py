"""Configuration parser and validator."""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field
import yaml


class InstrumentConfig(BaseModel):
    symbol: str = "MNQ"
    tick_size: float = 0.25
    tick_value: float = 0.50
    point_value: float = 2.00


class TimezoneConfig(BaseModel):
    data: str = "UTC"
    strategy: str = "America/New_York"


class TimeframesConfig(BaseModel):
    base: str = "1m"
    confirmation: str = "5m"
    setup: str = "15m"
    reference: str = "1h"


class LevelsConfig(BaseModel):
    breakout_reference: str = "reference_extreme"
    confirmation_level: str = "reference_extreme"


class EntryConfig(BaseModel):
    execution: Literal["next_bar_open", "signal_close", "breakout_price"] = "next_bar_open"


class StopLossConfig(BaseModel):
    method: Literal["entry_structure", "entry_candle", "pullback", "recent_swing"] = "entry_structure"
    buffer_ticks: int = 1


class PositionConfig(BaseModel):
    mode: Literal["fixed_contracts", "fixed_risk"] = "fixed_contracts"
    contracts: int = 1
    risk_per_trade: float = 100.0


class AccountConfig(BaseModel):
    initial_balance: float = 10000.0


class RiskConfig(BaseModel):
    max_concurrent_trades: Optional[int] = None
    max_total_risk: Optional[float] = None


class ExecutionConfig(BaseModel):
    commission_per_contract: float = 0.0
    slippage_ticks: int = 0
    intrabar_mode: Literal["conservative", "optimistic"] = "conservative"


class TrailingConfig(BaseModel):
    activate_at_r: float = 1.0
    second_stage_at_r: float = 3.0
    trail_increment_r: float = 1.0


class SetupConfig(BaseModel):
    expiration: Literal["next_reference_hour", "session_end"] = "next_reference_hour"


class StrategyParamsConfig(BaseModel):
    max_entries_per_setup: int = 1


class BacktestConfig(BaseModel):
    instrument: InstrumentConfig = Field(default_factory=InstrumentConfig)
    timezone: TimezoneConfig = Field(default_factory=TimezoneConfig)
    timeframes: TimeframesConfig = Field(default_factory=TimeframesConfig)
    levels: LevelsConfig = Field(default_factory=LevelsConfig)
    entry: EntryConfig = Field(default_factory=EntryConfig)
    stop_loss: StopLossConfig = Field(default_factory=StopLossConfig)
    position: PositionConfig = Field(default_factory=PositionConfig)
    account: AccountConfig = Field(default_factory=AccountConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    trailing: TrailingConfig = Field(default_factory=TrailingConfig)
    setup: SetupConfig = Field(default_factory=SetupConfig)
    strategy: StrategyParamsConfig = Field(default_factory=StrategyParamsConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> BacktestConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def get_hash(self) -> str:
        serialized = self.model_dump_json(exclude_none=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]