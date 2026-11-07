# Research rebuild

The previous implementation missed entry-bar exits, omitted remaining positions
from final cash, retained account state across runs, and discarded indicator
history before out-of-sample windows. Those behaviors are now covered by regression
tests. Opening gaps are evaluated before the ambiguous high/low portion of a bar.

## Strategy hypothesis

The strategy seeks trend continuation after a recovery across the fast average,
with fast/slow averages defining trend and RSI confirming direction (50 to the
long ceiling; short floor to 50). An initial average crossover can also qualify.
ATR defines bracket distances, anchored to the actual next-open entry fill.
No parameters have been selected using real market results in this rebuild.
This is a testable hypothesis, not an established profitable strategy.

## Execution contract

- One position at a time; close-bar signals execute at the following open.
- Input OHLC represents mid prices; a constant half-spread constructs bid/ask.
- Adverse fixed slippage applies to market entry, stops, and forced exits.
- Opening target gaps fill before subsequent intrabar excursions. Otherwise
  stop wins when both brackets touch; target orders receive no adverse slippage.
- Entry-bar brackets are active. Remaining positions liquidate on the final close.
- Each run starts from fresh account state. No positions cross fold boundaries.
- Daily loss halts latch until the next input timestamp's calendar day.
  Total drawdown halts latch for the remainder of the run.
- Equity risk liquidation is checked at bar close, not tick by tick. Daily baselines
  use preceding observed equity. Intrabar drawdown can exceed reported drawdown.
- Position budgets include stop slippage and remaining daily/drawdown allowance.
  Gaps can still exceed those allowances.

## Validation contract

Rolling folds train only on preceding bars; training history warms indicators
without opening trades in that history. Test windows cannot overlap.
Folds reset capital and flatten at their ends; their returns are not a continuous
portfolio equity curve. The parameter grid and ranking remain exploratory and
can overfit. A separate untouched historical holdout is still required.

Run:

    python -m unittest discover tests -v
    python tools/benchmark.py

The deterministic 1,200-bar benchmark checks nonzero trade activity, repeatability,
four execution-cost scenarios, and three walk-forward folds. Synthetic returns
provide no evidence of profitability.

## Remaining boundaries

No historical broker bid/ask dataset or paper-account reconciliation has been
provided. Conversion remains an explicitly configured fixed quote-to-account
rate: changing exchange rates are not modeled. There are no margin calls, leverage
caps based on notional, financing, commissions, variable spreads, order rejections,
partial fills, or latency simulation. This engine cannot certify suitability for
real-money use. LiveBrokerDisabled remains enforced.
