import unittest
from datetime import datetime, timedelta, timezone

from forex_bot.models import Candle
from forex_bot.optimizer import optimize


class OptimizerTests(unittest.TestCase):
    def test_optimizer_returns_ranked_candidates(self) -> None:
        candles = []
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for index in range(160):
            close = 1.10 + (index * 0.0001 if index < 80 else (160 - index) * 0.0001)
            candles.append(
                Candle(
                    time=start + timedelta(hours=index),
                    open=close - 0.0002,
                    high=close + 0.0010,
                    low=close - 0.0010,
                    close=close,
                )
            )

        candidates = optimize(candles)

        self.assertGreater(len(candidates), 1)
        self.assertGreaterEqual(candidates[0].score, candidates[-1].score)


if __name__ == "__main__":
    unittest.main()
