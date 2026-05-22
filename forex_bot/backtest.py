from __future__ import annotations

from dataclasses import dataclass

from forex_bot.config import ExecutionConfig, RiskConfig
from forex_bot.models import Candle, Side, Signal, Trade
from forex_bot.risk import RiskManager
from forex_bot.strategy import TrendRsiAtrStrategy


@dataclass(frozen=True)
class BacktestResult:
    starting_balance: float
    ending_balance: float
    total_return_pct: float
    max_drawdown_pct: float
    trades: list[Trade]

    @property
    def win_rate_pct(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for trade in self.trades if trade.pnl > 0)
        return wins / len(self.trades) * 100.0

    @property
    def gross_profit(self) -> float:
        return sum(trade.pnl for trade in self.trades if trade.pnl > 0)

    @property
    def gross_loss(self) -> float:
        return abs(sum(trade.pnl for trade in self.trades if trade.pnl < 0))

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return self.gross_profit / self.gross_loss

    @property
    def average_win(self) -> float:
        wins = [trade.pnl for trade in self.trades if trade.pnl > 0]
        return sum(wins) / len(wins) if wins else 0.0

    @property
    def average_loss(self) -> float:
        losses = [trade.pnl for trade in self.trades if trade.pnl < 0]
        return sum(losses) / len(losses) if losses else 0.0

    @property
    def max_consecutive_losses(self) -> int:
        worst = 0
        current = 0
        for trade in self.trades:
            if trade.pnl < 0:
                current += 1
                worst = max(worst, current)
            else:
                current = 0
        return worst


class Backtester:
    def __init__(
        self,
        strategy: TrendRsiAtrStrategy | None = None,
        risk_config: RiskConfig | None = None,
        execution_config: ExecutionConfig | None = None,
    ) -> None:
        self.strategy = strategy or TrendRsiAtrStrategy()
        self.risk = RiskManager(risk_config)
        self.execution = execution_config or ExecutionConfig()

    def run(self, candles: list[Candle]) -> BacktestResult:
        signals = self.strategy.generate_signals(candles)
        trades: list[Trade] = []
        equity_curve = [self.risk.state.balance]
        open_signal: Signal | None = None
        open_units = 0
        entry_time = None

        for index, candle in enumerate(candles):
            self.risk.on_new_day(candle.time.date())

            if open_signal is not None and entry_time is not None:
                exit_price, reason = self._maybe_exit(open_signal, candle)
                if exit_price is not None:
                    pnl = self._pnl(open_signal.side, open_signal.entry, exit_price, open_units)
                    self.risk.apply_pnl(pnl)
                    self.risk.state.open_trades = 0
                    trades.append(
                        Trade(
                            side=open_signal.side,
                            entry_time=entry_time,
                            exit_time=candle.time,
                            entry=open_signal.entry,
                            exit=exit_price,
                            units=open_units,
                            pnl=pnl,
                            reason=reason,
                        )
                    )
                    open_signal = None
                    open_units = 0
                    entry_time = None

            signal = signals[index]
            if open_signal is None and signal is not None and self.risk.can_trade():
                executable = self._apply_entry_costs(signal)
                units = self.risk.size_units(executable)
                if units > 0:
                    open_signal = executable
                    open_units = units
                    entry_time = candle.time
                    self.risk.state.open_trades = 1

            equity_curve.append(self.risk.state.balance)

        return BacktestResult(
            starting_balance=self.risk.config.starting_balance,
            ending_balance=self.risk.state.balance,
            total_return_pct=(self.risk.state.balance / self.risk.config.starting_balance - 1.0) * 100.0,
            max_drawdown_pct=_max_drawdown_pct(equity_curve),
            trades=trades,
        )

    def _apply_entry_costs(self, signal: Signal) -> Signal:
        half_spread = self.execution.spread_pips * self.execution.pip_size / 2.0
        slippage = self.execution.slippage_pips * self.execution.pip_size
        cost = half_spread + slippage
        entry = signal.entry + cost if signal.side == Side.BUY else signal.entry - cost
        stop_delta = abs(signal.entry - signal.stop_loss)
        target_delta = abs(signal.take_profit - signal.entry)
        return Signal(
            side=signal.side,
            entry=entry,
            stop_loss=entry - stop_delta if signal.side == Side.BUY else entry + stop_delta,
            take_profit=entry + target_delta if signal.side == Side.BUY else entry - target_delta,
            reason=signal.reason,
        )

    def _maybe_exit(self, signal: Signal, candle: Candle) -> tuple[float | None, str]:
        if signal.side == Side.BUY:
            if candle.low <= signal.stop_loss:
                return signal.stop_loss, "stop_loss"
            if candle.high >= signal.take_profit:
                return signal.take_profit, "take_profit"
        else:
            if candle.high >= signal.stop_loss:
                return signal.stop_loss, "stop_loss"
            if candle.low <= signal.take_profit:
                return signal.take_profit, "take_profit"
        return None, ""

    @staticmethod
    def _pnl(side: Side, entry: float, exit_price: float, units: int) -> float:
        if side == Side.BUY:
            return (exit_price - entry) * units
        return (entry - exit_price) * units


def _max_drawdown_pct(equity_curve: list[float]) -> float:
    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown * 100.0
