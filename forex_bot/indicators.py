from __future__ import annotations

from forex_bot.models import Candle


def sma(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")

    output: list[float | None] = []
    rolling_sum = 0.0
    for index, value in enumerate(values):
        rolling_sum += value
        if index >= period:
            rolling_sum -= values[index - period]
        output.append(rolling_sum / period if index >= period - 1 else None)
    return output


def rsi(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) <= period:
        return [None] * len(values)

    output: list[float | None] = [None] * len(values)
    gains: list[float] = []
    losses: list[float] = []

    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    output[period] = _rsi_from_averages(avg_gain, avg_loss)

    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0.0)
        loss = abs(min(change, 0.0))
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        output[index] = _rsi_from_averages(avg_gain, avg_loss)

    return output


def atr(candles: list[Candle], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    if len(candles) <= period:
        return [None] * len(candles)

    true_ranges: list[float] = [candles[0].high - candles[0].low]
    for index in range(1, len(candles)):
        candle = candles[index]
        previous_close = candles[index - 1].close
        true_ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        )

    output: list[float | None] = [None] * len(candles)
    current_atr = sum(true_ranges[1 : period + 1]) / period
    output[period] = current_atr

    for index in range(period + 1, len(candles)):
        current_atr = ((current_atr * (period - 1)) + true_ranges[index]) / period
        output[index] = current_atr

    return output


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))
