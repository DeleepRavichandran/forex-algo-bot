from __future__ import annotations

import argparse
from pathlib import Path

from forex_bot.backtest import Backtester
from forex_bot.config import StrategyConfig
from forex_bot.data import load_candles_csv
from forex_bot.optimizer import optimize, walk_forward
from forex_bot.strategy import TrendRsiAtrStrategy


def main() -> None:
    parser = argparse.ArgumentParser(description="Risk-first Forex algo bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest_parser = subparsers.add_parser("backtest", help="Run a CSV backtest")
    backtest_parser.add_argument("--data", required=True, type=Path, help="CSV with time,open,high,low,close")
    _add_strategy_args(backtest_parser)

    optimize_parser = subparsers.add_parser("optimize", help="Grid-search strategy parameters")
    optimize_parser.add_argument("--data", required=True, type=Path, help="CSV with time,open,high,low,close")

    walk_forward_parser = subparsers.add_parser("walk-forward", help="Optimize on train data, test out of sample")
    walk_forward_parser.add_argument("--data", required=True, type=Path, help="CSV with time,open,high,low,close")

    args = parser.parse_args()

    if args.command == "backtest":
        candles = load_candles_csv(args.data)
        result = Backtester(strategy=TrendRsiAtrStrategy(_strategy_config_from_args(args))).run(candles)
        _print_result(result)

    if args.command == "optimize":
        candles = load_candles_csv(args.data)
        for candidate in optimize(candles)[:10]:
            config = candidate.config
            print(
                f"score={candidate.score:7.2f} return={candidate.result.total_return_pct:7.2f}% "
                f"dd={candidate.result.max_drawdown_pct:6.2f}% trades={len(candidate.result.trades):3d} "
                f"fast={config.fast_sma} slow={config.slow_sma} atr={config.atr_stop_multiple} rr={config.reward_risk}"
            )

    if args.command == "walk-forward":
        candles = load_candles_csv(args.data)
        best, out_of_sample = walk_forward(candles)
        print("Best in-sample config:")
        print(best.config)
        print()
        print("Out-of-sample result:")
        _print_result(out_of_sample)


def _print_result(result: object) -> None:
    print(f"Starting balance: {result.starting_balance:.2f}")
    print(f"Ending balance:   {result.ending_balance:.2f}")
    print(f"Total return:     {result.total_return_pct:.2f}%")
    print(f"Max drawdown:     {result.max_drawdown_pct:.2f}%")
    print(f"Trades:           {len(result.trades)}")
    print(f"Win rate:         {result.win_rate_pct:.2f}%")
    print(f"Profit factor:    {_format_profit_factor(result.profit_factor)}")
    print(f"Gross profit:     {result.gross_profit:.2f}")
    print(f"Gross loss:       {result.gross_loss:.2f}")
    print(f"Average win:      {result.average_win:.2f}")
    print(f"Average loss:     {result.average_loss:.2f}")
    print(f"Max loss streak:  {result.max_consecutive_losses}")


def _format_profit_factor(value: float) -> str:
    if value == float("inf"):
        return "inf"
    return f"{value:.2f}"


def _add_strategy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--fast-sma", type=int, default=20)
    parser.add_argument("--slow-sma", type=int, default=50)
    parser.add_argument("--rsi-period", type=int, default=14)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--atr-stop-multiple", type=float, default=1.8)
    parser.add_argument("--reward-risk", type=float, default=2.0)
    parser.add_argument("--long-rsi-ceiling", type=float, default=68.0)
    parser.add_argument("--short-rsi-floor", type=float, default=32.0)


def _strategy_config_from_args(args: argparse.Namespace) -> StrategyConfig:
    return StrategyConfig(
        fast_sma=args.fast_sma,
        slow_sma=args.slow_sma,
        rsi_period=args.rsi_period,
        atr_period=args.atr_period,
        atr_stop_multiple=args.atr_stop_multiple,
        reward_risk=args.reward_risk,
        long_rsi_ceiling=args.long_rsi_ceiling,
        short_rsi_floor=args.short_rsi_floor,
    )


if __name__ == "__main__":
    main()
