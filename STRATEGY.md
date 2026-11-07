# Channel breakout v1

Initial research assumption: EUR/USD hourly mid-price candles, USD account.
Parameters are fixed hypotheses, not selected for returns on historical data.

At each completed candle:

1. Calculate the highest high and lowest low of the preceding 55 candles,
   excluding the current candle.
2. Buy when the close exceeds the upper channel and is above a rising 200-bar SMA.
3. Sell when the close falls below the lower channel and is below a falling SMA.
4. Enter at the next open, using the engine's spread and slippage model.
5. Freeze ATR(20) from the signal close. Stop distance is 2 ATR from the actual
   entry; target distance is twice the stop distance (4 ATR).

The CLI breakout preset budgets 0.25% of equity per trade, capped by remaining
risk allowance, with a 1% daily loss halt and 5% total drawdown halt. One position
at a time; no averaging down or pyramiding. Gaps can exceed planned loss.
Brackets do not trail; there is no time exit or opposite-signal exit.
Final open positions are liquidated when a backtest ends.

    python -m forex_bot.main backtest --strategy breakout --data path/to/EUR_USD_H1.csv
    python -m unittest discover tests -v

The existing optimize and walk-forward commands still target the trend-RSI
strategy, not this fixed breakout baseline. Do not interpret their results as
validation of the breakout strategy.

Hypothesis: persistence after a channel break may offset repeated small losses
in sideways markets. The fixed target can truncate trends; false breakouts,
spread expansion, gaps, and prolonged sideways periods may dominate returns.
No market profitability is established. See RESEARCH_LIMITATIONS.md for the
engine's currency, margin, financing and bar-level execution limitations.
