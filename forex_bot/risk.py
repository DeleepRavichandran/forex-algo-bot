from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from forex_bot.config import RiskConfig
from forex_bot.models import Signal


@dataclass
class RiskState:
    balance: float
    current_day: date | None = None
    daily_start_balance: float | None = None
    open_trades: int = 0


class RiskManager:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()
        self.state = RiskState(balance=self.config.starting_balance)

    def on_new_day(self, trading_day: date) -> None:
        if self.state.current_day != trading_day:
            self.state.current_day = trading_day
            self.state.daily_start_balance = self.state.balance

    def can_trade(self) -> bool:
        if self.state.open_trades >= self.config.max_open_trades:
            return False
        if self.state.daily_start_balance is None:
            return True
        max_loss = self.state.daily_start_balance * self.config.max_daily_loss
        return self.state.balance >= self.state.daily_start_balance - max_loss

    def size_units(self, signal: Signal, pip_value_per_unit: float = 0.0001) -> int:
        risk_amount = self.state.balance * self.config.risk_per_trade
        stop_distance = abs(signal.entry - signal.stop_loss)
        if stop_distance <= 0:
            return 0
        raw_units = int(risk_amount / (stop_distance / pip_value_per_unit * pip_value_per_unit))
        return max(0, min(raw_units, self.config.max_units))

    def apply_pnl(self, pnl: float) -> None:
        self.state.balance += pnl
