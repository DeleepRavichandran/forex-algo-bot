from __future__ import annotations

from forex_bot.config import StrategyConfig
from forex_bot.indicators import atr, rsi, sma
from forex_bot.models import Candle, Side, Signal


class TrendRsiAtrStrategy:
    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig()

    def generate_signals(self, candles: list[Candle]) -> list[Signal | None]:
        closes = [candle.close for candle in candles]
        fast = sma(closes, self.config.fast_sma)
        slow = sma(closes, self.config.slow_sma)
        rsi_values = rsi(closes, self.config.rsi_period)
        atr_values = atr(candles, self.config.atr_period)
        signals: list[Signal | None] = [None] * len(candles)

        for index in range(1, len(candles)):
            if any(
                value is None
                for value in (
                    fast[index],
                    slow[index],
                    fast[index - 1],
                    slow[index - 1],
                    rsi_values[index],
                    atr_values[index],
                )
            ):
                continue

            close = closes[index]
            stop_distance = atr_values[index] * self.config.atr_stop_multiple  # type: ignore[operator]
            if stop_distance <= 0:
                continue

            crossed_up = fast[index - 1] <= slow[index - 1] and fast[index] > slow[index]  # type: ignore[operator]
            crossed_down = fast[index - 1] >= slow[index - 1] and fast[index] < slow[index]  # type: ignore[operator]

            if crossed_up and rsi_values[index] < self.config.long_rsi_ceiling:  # type: ignore[operator]
                signals[index] = Signal(
                    side=Side.BUY,
                    entry=close,
                    stop_loss=close - stop_distance,
                    take_profit=close + (stop_distance * self.config.reward_risk),
                    reason="fast_sma_crossed_above_slow_sma",
                )

            if crossed_down and rsi_values[index] > self.config.short_rsi_floor:  # type: ignore[operator]
                signals[index] = Signal(
                    side=Side.SELL,
                    entry=close,
                    stop_loss=close + stop_distance,
                    take_profit=close - (stop_distance * self.config.reward_risk),
                    reason="fast_sma_crossed_below_slow_sma",
                )

        return signals
