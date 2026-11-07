"""Reproducible synthetic execution benchmark; it does not demonstrate profitability."""
import json
from hashlib import sha256
from pathlib import Path
import sys

# Support the documented `python tools/benchmark.py` invocation from any
# checkout without requiring an editable installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from forex_bot.backtest import Backtester
from forex_bot.config import ExecutionConfig
from forex_bot.data import load_candles_csv


def main() -> None:
    path = Path("sample_data/EUR_USD_DEMO_H1.csv")
    candles = load_candles_csv(path)
    result = Backtester(execution_config=ExecutionConfig(spread_pips=1.2, slippage_pips=0.2)).run(candles)
    print(json.dumps({"data_sha256": sha256(path.read_bytes()).hexdigest(), "candles": len(candles), "trades": len(result.trades), "return_pct": result.total_return_pct, "max_drawdown_pct": result.max_drawdown_pct, "warning": "Synthetic data only; no profitability inference."}, sort_keys=True))


if __name__ == "__main__":
    main()
