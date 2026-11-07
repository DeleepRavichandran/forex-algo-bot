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

            # Enter on a recovery through the fast average within an established
            # trend, or on its initial crossover. All inputs end at this close.
            crossed_up = fast[index] > slow[index] and (
                fast[index - 1] <= slow[index - 1]
                or closes[index - 1] <= fast[index - 1] < close
            )
            crossed_down = fast[index] < slow[index] and (
                fast[index - 1] >= slow[index - 1]
                or closes[index - 1] >= fast[index - 1] > close
            )

            if crossed_up and 50 <= rsi_values[index] < self.config.long_rsi_ceiling:
                signals[index] = Signal(
                    side=Side.BUY,
                    entry=close,
                    stop_loss=close - stop_distance,
                    take_profit=close + (stop_distance * self.config.reward_risk),
                    reason="trend_pullback_recovery_long",
                )

            if crossed_down and self.config.short_rsi_floor < rsi_values[index] <= 50:
                signals[index] = Signal(
                    side=Side.SELL,
                    entry=close,
                    stop_loss=close + stop_distance,
                    take_profit=close - (stop_distance * self.config.reward_risk),
                    reason="trend_pullback_recovery_short",
                )

        return signals
