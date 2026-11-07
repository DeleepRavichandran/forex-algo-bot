import unittest
from datetime import datetime, timedelta, timezone

from forex_bot.backtest import Backtester
from forex_bot.config import ExecutionConfig, RiskConfig
from forex_bot.models import Candle, Side, Signal


class _OneSignalStrategy:
    def __init__(self, signal_index: int, signal: Signal) -> None:
        self.signal_index, self.signal = signal_index, signal

    def generate_signals(self, candles):
        return [self.signal if i == self.signal_index else None for i in range(len(candles))]


def _candle(index, open_, high, low, close):
    return Candle(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=index), open_, high, low, close)


class ExecutionAdversarialTests(unittest.TestCase):
    def _run(self, candles, signal, **risk):
        return Backtester(_OneSignalStrategy(0, signal), RiskConfig(starting_balance=10_000, max_units=100_000, **risk), ExecutionConfig(spread_pips=2, slippage_pips=1)).run(candles)

    def test_entry_waits_for_next_open(self):
        signal = Signal(Side.BUY, 1.1, 1.09, 1.12, "test")
        result = self._run([_candle(0, 1.1, 1.1, 1.1, 1.1), _candle(1, 1.2, 1.201, 1.199, 1.2)], signal)
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_time, _candle(1, 1, 1, 1, 1).time)
        self.assertAlmostEqual(result.trades[0].entry, 1.2002)
        self.assertEqual(result.trades[0].reason, "end_of_data")

    def test_buy_stop_gap_uses_worse_bid_open_and_slippage(self):
        signal = Signal(Side.BUY, 1.1, 1.09, 1.12, "test")
        result = self._run([_candle(0, 1.1, 1.1, 1.1, 1.1), _candle(1, 1.1, 1.101, 1.099, 1.1), _candle(2, 1.08, 1.081, 1.079, 1.08)], signal)
        self.assertEqual(len(result.trades), 1)
        self.assertAlmostEqual(result.trades[0].exit, 1.0798, places=6)

    def test_same_bar_stop_and_target_is_conservative_stop(self):
        signal = Signal(Side.BUY, 1.1, 1.09, 1.11, "test")
        result = self._run([_candle(0, 1.1, 1.1, 1.1, 1.1), _candle(1, 1.1, 1.101, 1.099, 1.1), _candle(2, 1.1, 1.12, 1.08, 1.1)], signal)
        self.assertEqual(result.trades[0].reason, "stop_loss")

    def test_size_respects_remaining_drawdown_budget(self):
        signal = Signal(Side.BUY, 1.1, 1.0, 1.3, "test")
        result = self._run(
            [_candle(0, 1.1, 1.1, 1.1, 1.1), _candle(1, 1.1, 1.101, 1.099, 1.1), _candle(2, 1.08, 1.081, 1.079, 1.08)],
            signal,
            max_drawdown=0.001,
        )
        self.assertEqual(result.trades[0].reason, "end_of_data")
        self.assertLess(abs(result.trades[0].pnl), 10)

