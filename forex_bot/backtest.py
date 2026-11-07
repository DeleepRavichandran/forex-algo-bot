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

    def run(self, candles: list[Candle], *, warmup: list[Candle] | None = None) -> BacktestResult:
        if not candles:
            raise ValueError("Need at least one candle")
        from math import isfinite
        history = list(warmup or []) + candles
        for i, c in enumerate(history):
            if c.time.utcoffset() is None or (i and c.time <= history[i - 1].time):
                raise ValueError("Require timezone-aware, strictly increasing timestamps")
            if not all(isfinite(v) and v > 0 for v in (c.open, c.high, c.low, c.close)):
                raise ValueError("Invalid price")
            if not c.low <= min(c.open, c.close) <= max(c.open, c.close) <= c.high:
                raise ValueError("Invalid OHLC bounds")
        self.risk = RiskManager(self.risk.config)
        signals = self.strategy.generate_signals(history)[len(warmup or []):]
        trades: list[Trade] = []
        equity_curve = [self.risk.state.balance]
        open_signal: Signal | None = None
        pending_signal: Signal | None = None
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

            # Signals are known only after the preceding bar closes.  Execute
            # them on this bar's open, never at the signal bar's close.
            if open_signal is None and pending_signal is not None and self.risk.can_trade():
                executable = self._entry_at_open(pending_signal, candle)
                units = self.risk.size_units(executable,
                    exit_cost=self.execution.slippage_pips * self.execution.pip_size)
                if units > 0:
                    open_signal, open_units, entry_time = executable, units, candle.time
                    self.risk.state.open_trades = 1
            pending_signal = None

            # New positions also have active brackets during their entry bar.
            if open_signal is not None and entry_time == candle.time:
                price, reason = self._maybe_exit(open_signal, candle)
                if price is not None:
                    pnl = self._pnl(open_signal.side, open_signal.entry, price, open_units)
                    self.risk.apply_pnl(pnl)
                    trades.append(Trade(open_signal.side, entry_time, candle.time,
                                        open_signal.entry, price, open_units, pnl, reason))
                    self.risk.state.open_trades = 0
                    open_signal, open_units, entry_time = None, 0, None

            signal = signals[index]
            if open_signal is None and signal is not None:
                pending_signal = signal

            equity = self.risk.state.balance
            if open_signal is not None:
                equity += self._pnl(open_signal.side, open_signal.entry, self._forced_exit_price(open_signal.side, candle.close), open_units)
            self.risk.mark_equity(equity)
            if open_signal is not None and (self.risk.state.halted or self.risk.state.daily_halted or index == len(candles) - 1):
                exit_price = self._forced_exit_price(open_signal.side, candle.close)
                pnl = self._pnl(open_signal.side, open_signal.entry, exit_price, open_units)
                self.risk.apply_pnl(pnl)
                self.risk.state.open_trades = 0
                reason = "equity_risk_limit" if self.risk.state.halted or self.risk.state.daily_halted else "end_of_data"
                trades.append(Trade(open_signal.side, entry_time, candle.time, open_signal.entry, exit_price, open_units, pnl, reason))
                open_signal, open_units, entry_time = None, 0, None
                equity = self.risk.state.balance
            equity_curve.append(equity)

        return BacktestResult(
            starting_balance=self.risk.config.starting_balance,
            ending_balance=self.risk.state.balance,
            total_return_pct=(self.risk.state.balance / self.risk.config.starting_balance - 1.0) * 100.0,
            max_drawdown_pct=_max_drawdown_pct(equity_curve),
            trades=trades,
        )

    def _entry_at_open(self, signal: Signal, candle: Candle) -> Signal:
        half_spread = self.execution.spread_pips * self.execution.pip_size / 2.0
        slippage = self.execution.slippage_pips * self.execution.pip_size
        cost = half_spread + slippage
        entry = candle.open + cost if signal.side == Side.BUY else candle.open - cost
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
        half = self.execution.spread_pips * self.execution.pip_size / 2.0
        slip = self.execution.slippage_pips * self.execution.pip_size
        bid_open, bid_high, bid_low = candle.open - half, candle.high - half, candle.low - half
        ask_open, ask_high, ask_low = candle.open + half, candle.high + half, candle.low + half
        if signal.side == Side.BUY:
            if bid_open <= signal.stop_loss:
                return bid_open - slip, "stop_loss"
            if bid_open >= signal.take_profit:
                return bid_open, "take_profit"
            stop = bid_low <= signal.stop_loss
            target = bid_high >= signal.take_profit
            if stop and (not target or self.execution.intrabar_priority == "stop"):
                return min(signal.stop_loss, bid_open) - slip, "stop_loss"
            if target:
                return max(signal.take_profit, bid_open), "take_profit"
        else:
            if ask_open >= signal.stop_loss:
                return ask_open + slip, "stop_loss"
            if ask_open <= signal.take_profit:
                return ask_open, "take_profit"
            stop = ask_high >= signal.stop_loss
            target = ask_low <= signal.take_profit
            if stop and (not target or self.execution.intrabar_priority == "stop"):
                return max(signal.stop_loss, ask_open) + slip, "stop_loss"
            if target:
                return min(signal.take_profit, ask_open), "take_profit"
        return None, ""

    def _close_price(self, side: Side, mid: float) -> float:
        half = self.execution.spread_pips * self.execution.pip_size / 2.0
        return mid - half if side == Side.BUY else mid + half

    def _forced_exit_price(self, side: Side, mid: float) -> float:
        slippage = self.execution.slippage_pips * self.execution.pip_size
        price = self._close_price(side, mid)
        return price - slippage if side == Side.BUY else price + slippage

    def _pnl(self, side: Side, entry: float, exit_price: float, units: int) -> float:
        quote_pnl = (exit_price - entry) * units if side == Side.BUY else (entry - exit_price) * units
        return quote_pnl * self.risk.config.quote_to_account_rate


def _max_drawdown_pct(equity_curve: list[float]) -> float:
    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown * 100.0
