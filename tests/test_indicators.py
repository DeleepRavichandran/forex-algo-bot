import unittest

from forex_bot.indicators import rsi, sma


class IndicatorTests(unittest.TestCase):
    def test_sma_returns_none_until_period_is_available(self) -> None:
        self.assertEqual(sma([1, 2, 3, 4], 3), [None, None, 2.0, 3.0])

    def test_rsi_handles_constant_uptrend(self) -> None:
        values = list(range(1, 20))
        output = rsi(values, 14)
        self.assertEqual(output[14], 100.0)


if __name__ == "__main__":
    unittest.main()
