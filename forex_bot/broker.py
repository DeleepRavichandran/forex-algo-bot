from __future__ import annotations

from dataclasses import dataclass, field

from forex_bot.models import Signal


@dataclass
class PaperOrder:
    instrument: str
    units: int
    signal: Signal


@dataclass
class PaperBroker:
    orders: list[PaperOrder] = field(default_factory=list)

    def place_order(self, instrument: str, units: int, signal: Signal) -> PaperOrder:
        if units <= 0:
            raise ValueError("units must be positive")
        order = PaperOrder(instrument=instrument, units=units, signal=signal)
        self.orders.append(order)
        return order


class LiveBrokerDisabled:
    def place_order(self, *_args: object, **_kwargs: object) -> None:
        raise RuntimeError(
            "Live broker execution is disabled. Validate the strategy with backtests and paper trading first."
        )
