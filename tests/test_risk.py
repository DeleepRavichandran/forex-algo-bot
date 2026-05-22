import unittest

from forex_bot.config import RiskConfig
from forex_bot.models import Side, Signal
from forex_bot.risk import RiskManager


class RiskManagerTests(unittest.TestCase):
    def test_size_units_is_capped(self) -> None:
        manager = RiskManager(RiskConfig(starting_balance=10_000, risk_per_trade=0.01, max_units=1_000))
        signal = Signal(Side.BUY, entry=1.1000, stop_loss=1.0900, take_profit=1.1200, reason="test")

        self.assertEqual(manager.size_units(signal), 1_000)

    def test_daily_loss_limit_blocks_trading(self) -> None:
        manager = RiskManager(RiskConfig(starting_balance=10_000, max_daily_loss=0.02))
        manager.on_new_day(__import__("datetime").date(2026, 5, 22))
        manager.apply_pnl(-250)

        self.assertFalse(manager.can_trade())


if __name__ == "__main__":
    unittest.main()
