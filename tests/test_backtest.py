import unittest
from datetime import datetime, timedelta, timezone

from forex_bot.backtest import Backtester
from forex_bot.config import ExecutionConfig, RiskConfig, StrategyConfig
from forex_bot.models import Candle
from forex_bot.strategy import TrendRsiAtrStrategy


class BacktesterTests(unittest.TestCase):
    def test_backtest_reports_trade_metrics(self) -> None:
        candles = _tradeable_candles()
        strategy = TrendRsiAtrStrategy(
            StrategyConfig(
                fast_sma=3,
                slow_sma=8,
                rsi_period=3,
                atr_period=3,
                atr_stop_multiple=1.0,
                reward_risk=1.2,
                long_rsi_ceiling=100,
                short_rsi_floor=0,
            )
        )
        backtester = Backtester(
            strategy=strategy,
            risk_config=RiskConfig(starting_balance=10_000, risk_per_trade=0.01, max_units=10_000),
            execution_config=ExecutionConfig(spread_pips=0, slippage_pips=0),
        )

        result = backtester.run(candles)

        self.assertGreater(len(result.trades), 0)
        self.assertGreaterEqual(result.gross_profit, 0)
        self.assertGreaterEqual(result.gross_loss, 0)
        self.assertGreaterEqual(result.max_consecutive_losses, 0)


def _tradeable_candles() -> list[Candle]:
    candles: list[Candle] = []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    price = 1.1000
    changes = (
        [-0.00025] * 20
        + [0.00045] * 18
        + [-0.00045] * 18
        + [0.00040] * 18
        + [-0.00040] * 18
    )
    for index, change in enumerate(changes):
        price += change
        candles.append(
            Candle(
                time=start + timedelta(hours=index),
                open=price - change,
                high=price + 0.0006,
                low=price - 0.0006,
                close=price,
                volume=100,
            )
        )
    return candles


if __name__ == "__main__":
    unittest.main()
