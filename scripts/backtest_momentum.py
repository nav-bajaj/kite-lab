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


def load_signals(path: Path, top_n: int, exit_buffer: int = 0):
    df = pd.read_csv(path, parse_dates=["date"])
    entry_df = df[df["rank"] <= top_n]
    entry_grouped = entry_df.groupby("date")["symbol"].apply(list)

    exit_threshold = top_n + exit_buffer
    exit_df = df[df["rank"] <= exit_threshold]
    rank_map_by_date = {}
    for date, group in exit_df.groupby("date"):
        rank_map_by_date[pd.Timestamp(date)] = dict(zip(group["symbol"], group["rank"]))

    max_rank = df["rank"].max()
    if exit_threshold > max_rank:
        print(f"Warning: exit threshold ({exit_threshold}) exceeds max rank in signals ({max_rank}). Missing ranks will be treated as inf.")

    return entry_grouped, rank_map_by_date, df


def load_benchmark(path: Path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    df = df.set_index("date")
    return df["close"].ffill()


def map_signal_to_trade(signal_date, calendar):
    preferred = signal_date + pd.Timedelta(days=1)
    if preferred in calendar:
        return preferred
    for offset in [0, -1, -2]:
        candidate = signal_date + pd.Timedelta(days=offset)
        if candidate in calendar:
            return candidate
    return None


def run_backtest(
    prices_dir,
    signals_path,
    benchmark_path,
    output_dir,
    initial_capital,
    top_n,
    slippage,
    scenario,
    cooldown_weeks=1,
    staged_step=0.25,
    vol_lookback=63,
    target_vol=0.15,
    exit_buffer=0,
    pnl_hold_threshold=None,
):
    close_panel, trade_panel = load_price_panels(prices_dir)
    entry_signals, rank_map_by_date, _signals_df = load_signals(signals_path, top_n, exit_buffer)
    benchmark = load_benchmark(benchmark_path)
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    schedule = {}
    for signal_date, symbols in entry_signals.items():
        trade_date = map_signal_to_trade(signal_date, calendar)
        if trade_date is not None:
            schedule[pd.Timestamp(trade_date)] = symbols

    rebalance_dates = sorted(schedule.keys())

    holdings = {}
    cost_basis = {}
    last_prices = {}
    cash = initial_capital
    trade_records = []
    equity_records = []
    turnover_records = []
    peak_equity = initial_capital
    exposure = 1.0 if scenario != "vol_trigger" else 0.0
    cooldown_counter = 0

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
        drawdown_hit = drawdown <= -0.25

        if scenario == "baseline":
            pass
        elif scenario == "cooldown":
            if drawdown_hit and cooldown_counter == 0:
                cooldown_counter = cooldown_weeks
                exposure = 0.0
            if cooldown_counter > 0 and date in rebalance_dates:
                cooldown_counter -= 1
                exposure = min(1.0, exposure + staged_step)
        elif scenario == "vol_trigger":
            realized_vol = close_panel.pct_change().rolling(vol_lookback).std().loc[date].mean()
            if pd.isna(realized_vol) or realized_vol == 0:
                realized_vol = target_vol
            exposure = min(1.0, target_vol / realized_vol)

        equity_records.append({
            "date": date,
            "portfolio_value": portfolio_value,
            "cash": cash,
            "invested": portfolio_value - cash,
            "benchmark": benchmark_price,
            "drawdown": drawdown,
            "exposure": exposure,
        })

        if date not in rebalance_dates:
            continue

        target_symbols = schedule.get(date)
        if target_symbols is None:
            continue

        target_symbols = target_symbols[:top_n]
        if exposure <= 0:
            holdings.clear()
            continue
        current_symbols = set(holdings.keys())
        target_set = set(target_symbols)

        exit_threshold = top_n + exit_buffer
        current_ranks = rank_map_by_date.get(date, {})
        exits = []
        for sym in current_symbols:
            if sym in target_set:
                continue
            rank = current_ranks.get(sym, float("inf"))
            price_for_pnl = trade_panel.loc[date].get(sym)
            if pd.isna(price_for_pnl):
                price_for_pnl = close_row.get(sym)
            pnl_pct = None
            if price_for_pnl is not None and not pd.isna(price_for_pnl):
                avg_cost = cost_basis.get(sym, 0) / holdings.get(sym, 1)
                if avg_cost > 0:
                    pnl_pct = price_for_pnl / avg_cost - 1
            should_exit = rank > exit_threshold
            if pnl_hold_threshold is not None and should_exit and pnl_pct is not None and pnl_pct > pnl_hold_threshold:
                should_exit = False
            if should_exit:
                exits.append(sym)
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
            avg_cost = cost_basis.get(sym, 0) / shares if shares else 0
            cost_basis[sym] = cost_basis.get(sym, 0) - avg_cost * shares
            if holdings.get(sym, 0) == 0:
                cost_basis.pop(sym, None)
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
            target_cash = cash + sum(close_row.get(sym, last_prices.get(sym, 0)) * qty for sym, qty in holdings.items())
            deploy_cash = target_cash * exposure - (target_cash - cash)
            deploy_cash = max(0, deploy_cash)
            allocation = deploy_cash / len(entrants) if entrants else 0
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
                cost_basis[sym] = cost_basis.get(sym, 0) + cost
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

    equity_df = pd.DataFrame(equity_records)
    trades_df = pd.DataFrame(trade_records)
    turnover_df = pd.DataFrame(turnover_records)

    if not trades_df.empty:
        first_trade = trades_df["date"].min()
        equity_df = equity_df[equity_df["date"] >= first_trade]
        turnover_df = turnover_df[turnover_df["date"] >= first_trade]

    output_dir.mkdir(parents=True, exist_ok=True)
    equity_df.to_csv(output_dir / "momentum_equity.csv", index=False)
    trades_df.to_csv(output_dir / "momentum_trades.csv", index=False)
    turnover_df.to_csv(output_dir / "momentum_turnover.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="Backtest NSE 500 momentum strategy")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--signals", type=Path, default=Path("data/momentum/top25_signals.csv"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/backtests"))
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--slippage", type=float, default=0.002)
    parser.add_argument("--scenario", choices=["baseline", "cooldown", "vol_trigger"], default="baseline")
    parser.add_argument("--cooldown-weeks", type=int, default=1)
    parser.add_argument("--staged-step", type=float, default=0.25)
    parser.add_argument("--vol-lookback", type=int, default=63)
    parser.add_argument("--target-vol", type=float, default=0.15)
    parser.add_argument("--exit-buffer", type=int, default=0, help="Allow exits only when rank exceeds top_n + buffer (hysteresis)")
    parser.add_argument("--pnl-hold-threshold", type=float, help="If set, defer exit when rank is outside band but unrealized PnL > threshold (e.g., 0.05 for +5%)")
    args = parser.parse_args()

    run_backtest(
        args.prices_dir,
        args.signals,
        args.benchmark,
        args.output_dir,
        args.initial_capital,
        args.top_n,
        args.slippage,
        args.scenario,
        cooldown_weeks=args.cooldown_weeks,
        staged_step=args.staged_step,
        vol_lookback=args.vol_lookback,
        target_vol=args.target_vol,
        exit_buffer=args.exit_buffer,
        pnl_hold_threshold=args.pnl_hold_threshold,
    )


if __name__ == "__main__":
    main()
