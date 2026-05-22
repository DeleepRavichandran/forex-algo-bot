# Forex Algo Bot

A risk-first Forex trading bot scaffold for research, backtesting, and paper trading.

This project does **not** promise profit. It is built to test whether a strategy has a durable edge before any live broker integration is enabled.

## What is included

- CSV market data loader
- Indicator utilities: SMA, RSI, ATR
- Trend-following strategy with volatility and RSI filters
- Position sizing and risk limits
- Backtester with spread/slippage modeling
- Parameter optimization and walk-forward validation
- Paper broker for dry runs
- CLI entry point
- Unit tests for core behavior

## Quick start

```powershell
python -m forex_bot.main backtest --data sample_data\EUR_USD_H1.csv
python -m forex_bot.main optimize --data path\to\historical\EUR_USD_H1.csv
python -m forex_bot.main walk-forward --data path\to\historical\EUR_USD_H1.csv
python -m unittest discover tests
```

## Live trading safety

Live trading is intentionally not implemented in this first pass. The intended path is:

1. Backtest on several years of data.
2. Run walk-forward validation.
3. Paper trade with the intended broker.
4. Add broker execution only after the strategy survives realistic costs and risk limits.

## Example strategy

The default strategy is a conservative trend-following setup:

- Fast SMA above slow SMA for long bias.
- Fast SMA below slow SMA for short bias.
- RSI filter avoids chasing very overbought/oversold moves.
- ATR sets stop distance and take-profit distance.
- Risk manager caps position size and daily drawdown.

## Disclaimer

Forex trading involves substantial risk, especially with leverage. This software is for research and automation engineering; it is not financial advice.
