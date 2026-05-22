from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyConfig:
    fast_sma: int = 20
    slow_sma: int = 50
    rsi_period: int = 14
    atr_period: int = 14
    atr_stop_multiple: float = 1.8
    reward_risk: float = 2.0
    long_rsi_ceiling: float = 68.0
    short_rsi_floor: float = 32.0


@dataclass(frozen=True)
class RiskConfig:
    starting_balance: float = 10_000.0
    risk_per_trade: float = 0.005
    max_daily_loss: float = 0.02
    max_open_trades: int = 1
    max_units: int = 100_000


@dataclass(frozen=True)
class ExecutionConfig:
    spread_pips: float = 1.2
    slippage_pips: float = 0.2
    pip_size: float = 0.0001
