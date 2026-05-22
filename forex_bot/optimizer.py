from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from forex_bot.backtest import Backtester, BacktestResult
from forex_bot.config import StrategyConfig
from forex_bot.models import Candle
from forex_bot.strategy import TrendRsiAtrStrategy


@dataclass(frozen=True)
class OptimizationCandidate:
    config: StrategyConfig
    result: BacktestResult

    @property
    def score(self) -> float:
        trade_penalty = 25.0 if len(self.result.trades) < 10 else 0.0
        return self.result.total_return_pct - self.result.max_drawdown_pct - trade_penalty


def optimize(candles: list[Candle]) -> list[OptimizationCandidate]:
    candidates: list[OptimizationCandidate] = []
    for fast_sma, slow_sma, atr_multiple, reward_risk in product(
        [10, 20, 30],
        [40, 60, 90],
        [1.5, 2.0, 2.5],
        [1.5, 2.0, 2.5],
    ):
        if fast_sma >= slow_sma:
            continue
        config = StrategyConfig(
            fast_sma=fast_sma,
            slow_sma=slow_sma,
            atr_stop_multiple=atr_multiple,
            reward_risk=reward_risk,
        )
        result = Backtester(strategy=TrendRsiAtrStrategy(config)).run(candles)
        candidates.append(OptimizationCandidate(config=config, result=result))

    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)


def walk_forward(candles: list[Candle], train_fraction: float = 0.7) -> tuple[OptimizationCandidate, BacktestResult]:
    if not 0.5 <= train_fraction < 0.9:
        raise ValueError("train_fraction must be between 0.5 and 0.9")
    split_index = int(len(candles) * train_fraction)
    train = candles[:split_index]
    test = candles[split_index:]
    if len(train) < 100 or len(test) < 60:
        raise ValueError("Need more candles for walk-forward validation")

    best = optimize(train)[0]
    out_of_sample = Backtester(strategy=TrendRsiAtrStrategy(best.config)).run(test)
    return best, out_of_sample
