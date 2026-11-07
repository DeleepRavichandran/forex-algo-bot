import unittest
from datetime import datetime, timedelta, timezone

from forex_bot.models import Candle
from forex_bot.optimizer import rolling_walk_forward


class WalkForwardTests(unittest.TestCase):
    def test_folds_are_chronological_and_non_overlapping_by_default(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        candles = [
            Candle(start + timedelta(hours=i), 1.1, 1.101, 1.099, 1.1 + (i % 31) * 0.00001)
            for i in range(360)
        ]
        folds = rolling_walk_forward(candles, train_size=120, test_size=60)
        self.assertEqual([(f.test_start, f.test_end) for f in folds], [(120, 180), (180, 240), (240, 300), (300, 360)])
        self.assertTrue(all(f.train_end == f.test_start for f in folds))
