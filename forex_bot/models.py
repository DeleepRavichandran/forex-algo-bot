from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Signal:
    side: Side
    entry: float
    stop_loss: float
    take_profit: float
    reason: str


@dataclass(frozen=True)
class Trade:
    side: Side
    entry_time: datetime
    exit_time: datetime
    entry: float
    exit: float
    units: int
    pnl: float
    reason: str
