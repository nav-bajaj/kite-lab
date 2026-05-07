"""
Backtest engine for OM25 — Omega Ratio portfolio

Monthly rebalance, equal weight 4% per stock, cash when <25 qualify.
No weekly exits (distinct from TL25).

Usage:
    python scripts/backtest_om25.py --signals data/om25/signals/om25_signals.csv
"""

import argparse
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.backtest_momentum import load_price_panels, load_benchmark, map_signal_to_trade


def run_backtest(
    prices_dir: Path,
    signals_path: Path,
    benchmark_path: Path,
    output_dir: Path,
    initial_capital: float = 1_000_000,
    top_n: int = 25,
    target_weight: float = 0.04,
    slippage: float = 0.002,
):
    # Load
    close_panel, trade_panel = load_price_panels(prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(benchmark_path)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    # Parse signals
    sig_df = pd.read_csv(signals_path, parse_dates=["date"])
    signals_by_date = {}
    for date, group in sig_df.groupby("date"):
        signals_by_date[pd.Timestamp(date)] = group["symbol"].tolist()[:top_n]

    # Map signal dates to trade dates
    entry_schedule = {}
    for sig_date in sorted(signals_by_date.keys()):
        td = map_signal_to_trade(sig_date, calendar)
        if td:
            entry_schedule[pd.Timestamp(td)] = pd.Timestamp(sig_date)

    rebalance_dates = set(entry_schedule.keys())
    first_trade = min(rebalance_dates)
    active_cal = calendar[calendar >= first_trade]

    print(f"Backtest: {active_cal[0].date()} to {active_cal[-1].date()} ({len(active_cal)} days)")
    print(f"Rebalance dates: {len(rebalance_dates)}")

    # State
    holdings = {}  # symbol -> shares
    cost_basis = {}
    entry_meta = {}
    cash = initial_capital
    peak_equity = initial_capital
    last_prices = {}
    equity_records = []
    trade_records = []
    exit_records = []

    for date in active_cal:
        close_row = close_panel.loc[date]

        for sym in holdings:
            p = close_row.get(sym, np.nan)
            if not pd.isna(p):
                last_prices[sym] = p

        # Mark-to-market
        portfolio_value = cash
        for sym, shares in holdings.items():
            price = close_row.get(sym, last_prices.get(sym, 0))
            if pd.isna(price):
                price = last_prices.get(sym, 0)
            portfolio_value += shares * price

        peak_equity = max(peak_equity, portfolio_value)
        dd = portfolio_value / peak_equity - 1 if peak_equity > 0 else 0
        cash_pct = cash / portfolio_value if portfolio_value > 0 else 1

        equity_records.append({
            "date": date, "portfolio_value": portfolio_value,
            "cash": cash, "invested": portfolio_value - cash,
            "cash_pct": cash_pct, "holdings_count": len(holdings),
            "benchmark": benchmark_aligned.get(date, np.nan), "drawdown": dd,
        })

        # Monthly rebalance: full rebalance to equal weight
        if date in rebalance_dates:
            signal_date = entry_schedule[date]
            target_symbols = signals_by_date.get(signal_date, [])
            target_set = set(target_symbols)
            n_targets = len(target_symbols)

            # Sell everything not in new target
            for sym in list(holdings.keys()):
                if sym not in target_set:
                    shares = holdings.pop(sym, 0)
                    if shares == 0:
                        continue
                    price = trade_panel.loc[date, sym] if sym in trade_panel.columns else np.nan
                    if pd.isna(price):
                        price = close_row.get(sym, last_prices.get(sym, np.nan))
                    if pd.isna(price) or price <= 0:
                        holdings[sym] = shares
                        continue
                    proceeds = shares * price * (1 - slippage)
                    cash += proceeds
                    avg_cost = cost_basis.get(sym, 0) / shares if shares else 0
                    meta = entry_meta.pop(sym, {"date": date})
                    pnl_pct = price / avg_cost - 1 if avg_cost > 0 else None
                    exit_records.append({"symbol": sym, "entry_date": meta.get("date"),
                        "exit_date": date, "pnl_pct": pnl_pct,
                        "holding_days": (date - meta["date"]).days if meta.get("date") else None})
                    cost_basis.pop(sym, None)
                    trade_records.append({"date": date, "symbol": sym, "side": "SELL",
                        "shares": shares, "price": price, "notional": shares * price,
                        "slippage": shares * price * slippage, "reason": "exit"})

            # Rebalance all positions to target weight
            # Recalc PV after sells
            pv = cash
            for sym, shares in holdings.items():
                p = close_row.get(sym, last_prices.get(sym, 0))
                if pd.isna(p):
                    p = last_prices.get(sym, 0)
                pv += shares * p

            if n_targets > 0:
                per_stock = pv * target_weight  # 4% each

                for sym in target_symbols:
                    price = trade_panel.loc[date, sym] if sym in trade_panel.columns else np.nan
                    if pd.isna(price):
                        price = close_row.get(sym, np.nan)
                    if pd.isna(price) or price <= 0:
                        continue

                    current_shares = holdings.get(sym, 0)
                    current_value = current_shares * price
                    target_value = per_stock

                    delta_value = target_value - current_value

                    if abs(delta_value) < price * 0.5:
                        continue  # Skip tiny adjustments

                    if delta_value > 0:
                        # Buy
                        shares_to_buy = math.floor(delta_value / (price * (1 + slippage)))
                        if shares_to_buy < 1:
                            continue
                        cost = shares_to_buy * price * (1 + slippage)
                        if cost > cash:
                            shares_to_buy = math.floor(cash / (price * (1 + slippage)))
                            cost = shares_to_buy * price * (1 + slippage)
                        if shares_to_buy < 1:
                            continue
                        holdings[sym] = holdings.get(sym, 0) + shares_to_buy
                        cost_basis[sym] = cost_basis.get(sym, 0) + cost
                        if sym not in entry_meta:
                            entry_meta[sym] = {"date": date}
                        cash -= cost
                        trade_records.append({"date": date, "symbol": sym, "side": "BUY",
                            "shares": shares_to_buy, "price": price,
                            "notional": shares_to_buy * price,
                            "slippage": shares_to_buy * price * slippage, "reason": "entry"})
                    else:
                        # Sell excess
                        shares_to_sell = math.floor(abs(delta_value) / price)
                        if shares_to_sell < 1 or shares_to_sell > current_shares:
                            continue
                        proceeds = shares_to_sell * price * (1 - slippage)
                        cash += proceeds
                        holdings[sym] -= shares_to_sell
                        if holdings[sym] <= 0:
                            holdings.pop(sym, None)
                        trade_records.append({"date": date, "symbol": sym, "side": "SELL",
                            "shares": shares_to_sell, "price": price,
                            "notional": shares_to_sell * price,
                            "slippage": shares_to_sell * price * slippage, "reason": "rebalance"})

    # Output
    eq_df = pd.DataFrame(equity_records)
    tr_df = pd.DataFrame(trade_records)

    # Metrics
    start_val = eq_df["portfolio_value"].iloc[0]; end_val = eq_df["portfolio_value"].iloc[-1]
    total_ret = end_val / start_val - 1
    years = (eq_df["date"].iloc[-1] - eq_df["date"].iloc[0]).days / 365.25
    cagr = (1 + total_ret) ** (1 / years) - 1
    daily_ret = eq_df["portfolio_value"].pct_change().dropna()
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = cagr / ann_vol if ann_vol > 0 else 0
    max_dd = eq_df["drawdown"].min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0
    downside = daily_ret[daily_ret < 0].std() * np.sqrt(252)
    sortino = cagr / downside if downside > 0 else 0
    monthly_pv = eq_df.set_index("date")["portfolio_value"].resample("ME").last().dropna()
    monthly_ret = monthly_pv.pct_change().dropna()
    exit_df = pd.DataFrame(exit_records)
    hit_rate = (exit_df["pnl_pct"].dropna() > 0).mean() if not exit_df.empty else 0

    # Portfolio omega ratio
    port_gains = daily_ret[daily_ret > 0].sum()
    port_losses = abs(daily_ret[daily_ret < 0].sum())
    port_omega = port_gains / port_losses if port_losses > 0 else 0

    # Save
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    eq_df.to_csv(output_dir / "om25_equity.csv", index=False)
    tr_df.to_csv(output_dir / "om25_trades.csv", index=False)

    metrics = pd.DataFrame([{
        "start": eq_df["date"].iloc[0], "end": eq_df["date"].iloc[-1],
        "total_return": total_ret, "cagr": cagr, "annualized_volatility": ann_vol,
        "sharpe_ratio": sharpe, "sortino_ratio": sortino, "max_drawdown": max_dd,
        "calmar_ratio": calmar, "portfolio_omega": port_omega,
        "hit_rate": hit_rate, "avg_holding_days": exit_df["holding_days"].mean() if not exit_df.empty else 0,
        "avg_holdings": eq_df["holdings_count"].mean(), "avg_cash_pct": eq_df["cash_pct"].mean(),
        "win_rate_monthly": (monthly_ret > 0).mean(),
        "trades_total": len(tr_df),
    }])
    metrics.to_csv(output_dir / "om25_metrics.csv", index=False)

    print(f"\n=== OM25 Performance ===")
    print(f"CAGR: {cagr:.1%} | Max DD: {max_dd:.1%} | Sharpe: {sharpe:.2f} | Sortino: {sortino:.2f}")
    print(f"Calmar: {calmar:.2f} | Portfolio Omega: {port_omega:.2f}")
    print(f"Hit Rate: {hit_rate:.1%} | Monthly Win: {(monthly_ret > 0).mean():.0%}")
    print(f"Avg Holdings: {eq_df['holdings_count'].mean():.1f} | Avg Cash: {eq_df['cash_pct'].mean():.1%}")
    print(f"Trades: {len(tr_df)} | Saved to {output_dir}/")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Backtest OM25 Omega Ratio portfolio")
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--benchmark", default="data/benchmarks/nifty100.csv", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--target-weight", type=float, default=0.04)
    parser.add_argument("--slippage", type=float, default=0.002)
    args = parser.parse_args()

    run_backtest(
        prices_dir=args.prices_dir,
        signals_path=args.signals,
        benchmark_path=args.benchmark,
        output_dir=args.output_dir,
        initial_capital=args.initial_capital,
        top_n=args.top_n,
        target_weight=args.target_weight,
        slippage=args.slippage,
    )


if __name__ == "__main__":
    main()
