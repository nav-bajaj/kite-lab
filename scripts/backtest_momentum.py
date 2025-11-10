import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def load_price_panels(prices_dir: Path):
    rows = []
    for csv_path in sorted(prices_dir.glob("*_day.csv")):
        symbol = csv_path.stem.replace("_day", "")
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty or "close" not in df.columns:
            continue
        df["symbol"] = symbol
        if {"open", "high", "low", "close"}.issubset(df.columns):
            df["trade_price"] = df[["open", "high", "low", "close"]].mean(axis=1)
        else:
            df["trade_price"] = df["close"]
        rows.append(df[["date", "symbol", "close", "trade_price"]])
    if not rows:
        raise RuntimeError(f"No price files found in {prices_dir}")
    combined = pd.concat(rows, ignore_index=True)
    close_panel = combined.pivot(index="date", columns="symbol", values="close").sort_index()
    trade_panel = combined.pivot(index="date", columns="symbol", values="trade_price").sort_index()
    close_panel = close_panel.ffill()
    trade_panel = trade_panel.ffill()
    return close_panel, trade_panel


def load_signals(path: Path, top_n: int):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["rank"] <= top_n]
    grouped = df.groupby("date")["symbol"].apply(list)
    return grouped


def load_benchmark(path: Path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    df = df.set_index("date")
    return df["close"].ffill()


def nearest_trading_day(target_date, calendar):
    if target_date in calendar:
        return target_date
    for offset in [1, 2]:
        candidate = target_date - pd.Timedelta(days=offset)
        if candidate in calendar:
            return candidate
    return None


def run_backtest(prices_dir, signals_path, benchmark_path, output_dir, initial_capital,
                 top_n, slippage):
    close_panel, trade_panel = load_price_panels(prices_dir)
    signals = load_signals(signals_path, top_n)
    benchmark = load_benchmark(benchmark_path)
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    schedule = {}
    for signal_date, symbols in signals.items():
        trade_date = nearest_trading_day(signal_date, calendar)
        if trade_date is not None:
            schedule[pd.Timestamp(trade_date)] = symbols

    rebalance_dates = sorted(schedule.keys())

    holdings = {}
    last_prices = {}
    cash = initial_capital
    trade_records = []
    equity_records = []
    turnover_records = []
    peak_equity = initial_capital
    drawdown_lock = False

    for date in calendar:
        close_row = close_panel.loc[date]
        benchmark_price = benchmark_aligned.loc[date]

        portfolio_value = cash
        for symbol, shares in list(holdings.items()):
            price = close_row.get(symbol)
            if pd.isna(price):
                price = last_prices.get(symbol)
            else:
                last_prices[symbol] = price
            if price is None or pd.isna(price):
                continue
            portfolio_value += shares * price

        peak_equity = max(peak_equity, portfolio_value)
        drawdown = portfolio_value / peak_equity - 1
        if drawdown <= -0.25:
            drawdown_lock = True

        equity_records.append({
            "date": date,
            "portfolio_value": portfolio_value,
            "cash": cash,
            "invested": portfolio_value - cash,
            "benchmark": benchmark_price,
            "drawdown": drawdown,
            "drawdown_lock": drawdown_lock,
        })

        if drawdown_lock:
            holdings.clear()
            continue

        if date not in rebalance_dates:
            continue

        target_symbols = schedule.get(date)
        if target_symbols is None:
            continue

        target_symbols = target_symbols[:top_n]
        current_symbols = set(holdings.keys())
        target_set = set(target_symbols)

        exits = [sym for sym in current_symbols if sym not in target_set]
        rebalance_turnover = 0
        for sym in exits:
            shares = holdings.pop(sym)
            price = trade_panel.loc[date].get(sym)
            if pd.isna(price):
                price = close_row.get(sym)
            if pd.isna(price) or price <= 0:
                holdings[sym] = shares
                continue
            proceeds = shares * price * (1 - slippage)
            cash += proceeds
            notional = shares * price
            cost = notional * slippage
            rebalance_turnover += abs(notional)
            trade_records.append({
                "date": date,
                "symbol": sym,
                "side": "SELL",
                "shares": shares,
                "price": price,
                "notional": notional,
                "slippage": cost,
                "cash_after": cash,
            })

        entrants = [sym for sym in target_symbols if sym not in holdings]
        if entrants:
            allocation = cash / len(entrants)
            for sym in entrants:
                price = trade_panel.loc[date].get(sym)
                if pd.isna(price):
                    price = close_row.get(sym)
                if pd.isna(price) or price <= 0:
                    continue
                gross = allocation
                shares = gross / (price * (1 + slippage))
                cost = shares * price * (1 + slippage)
                if cost > cash:
                    continue
                holdings[sym] = holdings.get(sym, 0) + shares
                cash -= cost
                notional = shares * price
                rebalance_turnover += abs(notional)
                trade_records.append({
                    "date": date,
                    "symbol": sym,
                    "side": "BUY",
                    "shares": shares,
                    "price": price,
                    "notional": notional,
                    "slippage": shares * price * slippage,
                    "cash_after": cash,
                })

        if rebalance_turnover:
            turnover_records.append({
                "date": date,
                "turnover": rebalance_turnover,
                "turnover_pct": rebalance_turnover / portfolio_value if portfolio_value else 0,
            })

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(equity_records).to_csv(output_dir / "momentum_equity.csv", index=False)
    pd.DataFrame(trade_records).to_csv(output_dir / "momentum_trades.csv", index=False)
    pd.DataFrame(turnover_records).to_csv(output_dir / "momentum_turnover.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="Backtest NSE 500 momentum strategy")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--signals", type=Path, default=Path("data/momentum/top25_signals.csv"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/backtests"))
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--slippage", type=float, default=0.002)
    args = parser.parse_args()

    run_backtest(
        args.prices_dir,
        args.signals,
        args.benchmark,
        args.output_dir,
        args.initial_capital,
        args.top_n,
        args.slippage,
    )


if __name__ == "__main__":
    main()
