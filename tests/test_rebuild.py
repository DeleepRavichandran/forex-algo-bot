import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from math import sin

from forex_bot.backtest import Backtester
from forex_bot.config import ExecutionConfig, RiskConfig
from forex_bot.indicators import rsi
from forex_bot.models import Candle, Side, Signal
from forex_bot.strategy import TrendRsiAtrStrategy
from forex_bot.broker import LiveBrokerDisabled


def fixture(n=600):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    prices = [1.1 + .008 * sin(i / 25) + .002 * sin(i / 3) for i in range(n + 1)]
    return [Candle(start + timedelta(hours=i), prices[i],
                   max(prices[i:i+2]) + .0003, min(prices[i:i+2]) - .0003,
                   prices[i+1]) for i in range(n)]


class Once:
    def __init__(self, side):
        self.side = side

    def generate_signals(self, candles):
        s = Signal(self.side, 1.1, 1.09 if self.side == Side.BUY else 1.11,
                   1.12 if self.side == Side.BUY else 1.08, "fixture")
        return [s] + [None] * (len(candles) - 1)


class RebuildTests(unittest.TestCase):
    def test_prefix_invariance(self):
        data = fixture()
        strategy = TrendRsiAtrStrategy()
        full = strategy.generate_signals(data)
        self.assertTrue(any(full))
        for cutoff in (70, 140, 299):
            self.assertEqual(full[:cutoff], strategy.generate_signals(data[:cutoff]))

    def test_repeatability_and_cash_reconciliation(self):
        engine = Backtester()
        first = engine.run(fixture())
        self.assertEqual(first, engine.run(fixture()))
        self.assertGreater(len(first.trades), 0)
        self.assertAlmostEqual(first.ending_balance,
                               first.starting_balance + sum(t.pnl for t in first.trades))

    def test_entry_bar_stop_both_sides(self):
        for side in Side:
            data = fixture(2)
            data[1] = replace(data[1], open=1.1, high=1.13, low=1.07, close=1.1)
            result = Backtester(Once(side), execution_config=ExecutionConfig(
                spread_pips=0, slippage_pips=0)).run(data)
            self.assertEqual(result.trades[0].reason, "stop_loss")
            self.assertEqual(result.trades[0].entry_time, result.trades[0].exit_time)
            self.assertLess(result.trades[0].pnl, 0)

    def test_open_target_gap_precedes_later_stop(self):
        engine = Backtester(execution_config=ExecutionConfig(spread_pips=0, slippage_pips=0))
        for side, opening, expected in ((Side.BUY, 1.13, 1.13), (Side.SELL, 1.07, 1.07)):
            signal = Once(side).generate_signals([None])[0]
            candle = replace(fixture(1)[0], open=opening, high=1.14, low=1.06, close=1.1)
            self.assertEqual(engine._maybe_exit(signal, candle), (expected, "take_profit"))

    def test_reject_bad_data(self):
        good = fixture(3)
        cases = [good[::-1], [good[0], good[0]],
                 [replace(good[0], close=float("nan"))],
                 [replace(good[0], low=2)]]
        for data in cases:
            with self.assertRaises(ValueError):
                Backtester().run(data)

    def test_flat_rsi_is_neutral(self):
        self.assertEqual(rsi([1.] * 20, 14)[-1], 50.)

    def test_daily_latch_resets_but_total_drawdown_does_not(self):
        from forex_bot.risk import RiskManager
        manager = RiskManager()
        manager.on_new_day(fixture(1)[0].time.date())
        manager.mark_equity(9700)
        manager.mark_equity(10000)
        self.assertFalse(manager.can_trade())
        manager.on_new_day((fixture(1)[0].time + timedelta(days=1)).date())
        self.assertTrue(manager.can_trade())
        manager.mark_equity(8000)
        manager.on_new_day((fixture(1)[0].time + timedelta(days=2)).date())
        self.assertFalse(manager.can_trade())

    def test_live_broker_remains_disabled(self):
        with self.assertRaises(RuntimeError):
            LiveBrokerDisabled().place_order()
