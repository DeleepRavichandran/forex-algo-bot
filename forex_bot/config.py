from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


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

    def __post_init__(self):
        if not 0 < self.fast_sma < self.slow_sma or min(self.rsi_period, self.atr_period) < 1:
            raise ValueError("Invalid indicator periods")
        if not all(isfinite(v) and v > 0 for v in (self.atr_stop_multiple, self.reward_risk)):
            raise ValueError("Invalid stop/reward multiples")
        if not 0 <= self.short_rsi_floor < 50 < self.long_rsi_ceiling <= 100:
            raise ValueError("Invalid RSI thresholds")


@dataclass(frozen=True)
class RiskConfig:
    starting_balance: float = 10_000.0
    risk_per_trade: float = 0.005
    max_daily_loss: float = 0.02
    max_open_trades: int = 1
    max_units: int = 100_000
    account_currency: str = "USD"
    # Number of account-currency units per one quote-currency unit.  Supply an
    # historical rate for cross-currency studies rather than assuming parity.
    quote_to_account_rate: float = 1.0
    max_drawdown: float = 0.10

    def __post_init__(self):
        if not all(isfinite(v) and v > 0 for v in (self.starting_balance, self.quote_to_account_rate)):
            raise ValueError("Invalid balance or currency conversion")
        if not all(isfinite(v) and 0 < v < 1 for v in
                   (self.risk_per_trade, self.max_daily_loss, self.max_drawdown)):
            raise ValueError("Risk fractions must be between zero and one")
        if self.max_units < 1 or self.max_open_trades != 1:
            raise ValueError("Single-position engine requires max_open_trades=1 and positive max_units")


@dataclass(frozen=True)
class ExecutionConfig:
    spread_pips: float = 1.2
    slippage_pips: float = 0.2
    pip_size: float = 0.0001
    # Candles are mid prices. Spread is applied as bid=mid-half and ask=mid+half.
    intrabar_priority: str = "stop"  # conservative when stop and target touch

    def __post_init__(self):
        if not all(isfinite(v) and v >= 0 for v in (self.spread_pips, self.slippage_pips)):
            raise ValueError("Invalid execution costs")
        if not isfinite(self.pip_size) or self.pip_size <= 0 or self.intrabar_priority != "stop":
            raise ValueError("Require positive pip size and conservative stop priority")
