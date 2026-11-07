import unittest
from datetime import datetime, timedelta, timezone
from dataclasses import replace

from forex_bot.breakout import BreakoutConfig, ChannelBreakoutStrategy
from forex_bot.backtest import Backtester
from forex_bot.config import RiskConfig
from forex_bot.models import Candle, Side


def trend(direction=1, n=300):
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return [Candle(start + timedelta(hours=i), 1.2 + direction * i * .0002,
                   max(1.2 + direction * i * .0002, 1.2 + direction * (i+1) * .0002) + .00005,
                   min(1.2 + direction * i * .0002, 1.2 + direction * (i+1) * .0002) - .00005,
                   1.2 + direction * (i+1) * .0002) for i in range(n)]


class BreakoutTests(unittest.TestCase):
    def test_both_directions_and_bracket_distances(self):
        for direction, side in ((1, Side.BUY), (-1, Side.SELL)):
            signals = ChannelBreakoutStrategy().generate_signals(trend(direction))
            self.assertTrue(all(s is None for s in signals[:200]))
            signal = signals[200]
            self.assertEqual(signal.side, side)
            self.assertAlmostEqual(abs(signal.entry-signal.stop_loss), .0006)
            self.assertAlmostEqual(abs(signal.take_profit-signal.entry), .0012)

    def test_channel_excludes_signal_bar(self):
        data = trend()
        # Today's high does not belong to the prior 55-bar channel.
        data[200] = replace(data[200], high=1.9)
        self.assertIsNotNone(ChannelBreakoutStrategy().generate_signals(data)[200])

    def test_wick_without_close_breakout_is_ignored(self):
        data = trend()
        data[200] = replace(data[200], high=1.9, close=data[199].close)
        self.assertIsNone(ChannelBreakoutStrategy().generate_signals(data)[200])

    def test_flat_market_has_no_signals(self):
        data = [replace(c, open=1.2, high=1.2, low=1.2, close=1.2) for c in trend()]
        self.assertTrue(all(s is None for s in ChannelBreakoutStrategy().generate_signals(data)))

    def test_future_data_cannot_change_past_signals(self):
        data = trend()
        strategy = ChannelBreakoutStrategy()
        self.assertEqual(strategy.generate_signals(data)[:220], strategy.generate_signals(data[:220]))

    def test_execution_and_planned_stop_risk(self):
        data = trend()
        engine = Backtester(ChannelBreakoutStrategy(), RiskConfig(risk_per_trade=.0025))
        result = engine.run(data)
        self.assertGreater(len(result.trades), 0)
        first = result.trades[0]
        self.assertEqual(first.entry_time, data[201].time)
        self.assertLessEqual(first.units * (.0006 + .00002), 25)
        self.assertAlmostEqual(result.ending_balance, 10000 + sum(t.pnl for t in result.trades))

    def test_invalid_configuration(self):
        for kwargs in (dict(channel_period=1), dict(trend_period=2.5),
                       dict(stop_atr=float("nan")), dict(reward_risk=0)):
            with self.assertRaises(ValueError):
                BreakoutConfig(**kwargs)
