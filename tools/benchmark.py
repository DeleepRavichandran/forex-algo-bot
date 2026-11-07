"""Reproducible synthetic execution benchmark; it does not demonstrate profitability."""
import json
from hashlib import sha256
from pathlib import Path
import sys
from math import sin
from datetime import datetime, timedelta, timezone

# Support the documented `python tools/benchmark.py` invocation from any
# checkout without requiring an editable installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from forex_bot.backtest import Backtester
from forex_bot.config import ExecutionConfig
from forex_bot.data import load_candles_csv
from forex_bot.models import Candle
from forex_bot.optimizer import rolling_walk_forward


def main() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    prices = [round(1.1 + .008 * sin(i / 25) + .002 * sin(i / 3), 8) for i in range(1201)]
    candles = [Candle(start + timedelta(hours=i), prices[i],
               max(prices[i:i+2]) + .0003, min(prices[i:i+2]) - .0003, prices[i+1])
               for i in range(1200)]
    digest = sha256(json.dumps(prices, separators=(",", ":")).encode()).hexdigest()
    runs = []
    for spread, slip in ((0, 0), (1.2, .2), (3, 1), (6, 2)):
        engine = Backtester(execution_config=ExecutionConfig(spread_pips=spread, slippage_pips=slip))
        result = engine.run(candles)
        assert result == engine.run(candles), "Run state leaked"
        assert result.trades, "Benchmark did not exercise execution"
        runs.append(dict(spread_pips=spread, slippage_pips=slip, trades=len(result.trades),
                         return_pct=result.total_return_pct, drawdown_pct=result.max_drawdown_pct))
    folds = rolling_walk_forward(candles, train_size=600, test_size=200)
    print(json.dumps(dict(fixture="oscillating-trend-v1", data_sha256=digest,
          candles=len(candles), costs=runs,
          folds=[dict(start=f.test_start, end=f.test_end, trades=len(f.out_of_sample.trades),
                      return_pct=f.out_of_sample.total_return_pct) for f in folds],
          warning="Synthetic mechanical regression only; no evidence of a market edge."),
          sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
