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
    peak_equity: float = 0.0
    equity: float = 0.0
    halted: bool = False
    daily_halted: bool = False


class RiskManager:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()
        self.state = RiskState(
            balance=self.config.starting_balance,
            peak_equity=self.config.starting_balance,
            equity=self.config.starting_balance,
        )

    def on_new_day(self, trading_day: date) -> None:
        if self.state.current_day != trading_day:
            self.state.current_day = trading_day
            self.state.daily_start_balance = self.state.equity
            self.state.daily_halted = False

    def mark_equity(self, equity: float) -> None:
        self.state.equity = equity
        baseline = self.state.daily_start_balance
        if baseline is not None and equity <= baseline * (1 - self.config.max_daily_loss):
            self.state.daily_halted = True
        self.state.peak_equity = max(self.state.peak_equity, equity)
        if equity <= 0 or self.drawdown_pct(equity) >= self.config.max_drawdown:
            self.state.halted = True

    def drawdown_pct(self, equity: float | None = None) -> float:
        value = self.state.equity if equity is None else equity
        return (self.state.peak_equity - value) / self.state.peak_equity if self.state.peak_equity else 0.0

    def can_trade(self, equity: float | None = None) -> bool:
        if self.state.halted or self.state.daily_halted:
            return False
        if self.state.open_trades >= self.config.max_open_trades:
            return False
        value = self.state.equity if equity is None else equity
        if self.state.daily_start_balance is None:
            return True
        max_loss = self.state.daily_start_balance * self.config.max_daily_loss
        return value >= self.state.daily_start_balance - max_loss

    def size_units(self, signal: Signal, exit_cost: float = 0.0) -> int:
        from math import isfinite
        if not isfinite(exit_cost) or exit_cost < 0:
            raise ValueError("Invalid exit cost")
        budget = min(self.state.balance, self.state.equity) * self.config.risk_per_trade
        drawdown_room = self.state.equity - self.state.peak_equity * (1 - self.config.max_drawdown)
        daily_room = (self.state.equity - self.state.daily_start_balance * (1 - self.config.max_daily_loss)
                      if self.state.daily_start_balance is not None else budget)
        risk_amount = max(0, min(budget, drawdown_room, daily_room))
        stop_distance = abs(signal.entry - signal.stop_loss) + exit_cost
        if stop_distance <= 0:
            return 0
        if self.config.quote_to_account_rate <= 0:
            raise ValueError("quote_to_account_rate must be positive")
        # A one-unit move in a XXX/YYY pair is denominated in YYY (quote).
        loss_per_unit_in_account = stop_distance * self.config.quote_to_account_rate
        raw_units = int(risk_amount / loss_per_unit_in_account)
        return max(0, min(raw_units, self.config.max_units))

    def apply_pnl(self, pnl: float) -> None:
        self.state.balance += pnl
        self.mark_equity(self.state.balance)
