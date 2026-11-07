"""Fixed-rule channel breakout hypothesis; parameters are not market-validated."""
from dataclasses import dataclass
from math import isfinite

from forex_bot.indicators import atr, sma
from forex_bot.models import Candle, Side, Signal


@dataclass(frozen=True)
class BreakoutConfig:
    channel_period: int = 55
    trend_period: int = 200
    atr_period: int = 20
    stop_atr: float = 2.0
    reward_risk: float = 2.0

    def __post_init__(self):
        for value in (self.channel_period, self.trend_period, self.atr_period):
            if type(value) is not int or value < 2:
                raise ValueError("Periods must be integers >= 2")
        for value in (self.stop_atr, self.reward_risk):
            if not isfinite(value) or value <= 0:
                raise ValueError("Stop and target multiples must be finite and positive")


class ChannelBreakoutStrategy:
    """Close-confirmed breakout, filtered by the direction of the slow average.

    Channel excludes the signal candle. The engine executes at the next open
    and anchors frozen ATR bracket distances to that actual executable entry.
    Consecutive qualifying closes may emit signals; engine ignores them while
    holding a position. No pyramiding, trailing stop, or optimized parameters.
    """

    def __init__(self, config: BreakoutConfig | None = None):
        self.config = config or BreakoutConfig()

    def generate_signals(self, candles: list[Candle]) -> list[Signal | None]:
        cfg = self.config
        averages = sma([c.close for c in candles], cfg.trend_period)
        volatility = atr(candles, cfg.atr_period)
        result = [None] * len(candles)
        start = max(cfg.channel_period, cfg.trend_period, cfg.atr_period)
        for i in range(start, len(candles)):
            close = candles[i].close
            previous = candles[i - cfg.channel_period:i]
            distance = volatility[i] * cfg.stop_atr
            if distance <= 0:
                continue
            side = None
            if (close > max(c.high for c in previous)
                    and close > averages[i] > averages[i - 1]):
                side = Side.BUY
            elif (close < min(c.low for c in previous)
                    and close < averages[i] < averages[i - 1]):
                side = Side.SELL
            if side is not None:
                direction = 1 if side == Side.BUY else -1
                stop = close - direction * distance
                target = close + direction * distance * cfg.reward_risk
                if min(stop, target) > 0:
                    result[i] = Signal(side, close, stop, target, "channel_breakout")
        return result
