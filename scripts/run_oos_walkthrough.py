"""End-to-end out-of-sample walkthrough using GDF-stitched price panel.

1. Build momentum signals on merged panel (nse500_data_merged/)
2. Run NSE 500 L6-1W backtest with min-hold-days 8
3. Slice the equity curve at the in-sample boundary (default 2020-07-10
   = start of current production backtest) and compute period-level metrics
   for OOS [2010-...-2020-07-09] vs IS [2020-07-10-...-today].

Outputs:
   experiments/oos_walkthrough/<timestamp>/
     - signals.csv
     - momentum_*.csv  (equity, trades, turnover, metrics)
     - oos_summary.csv
     - oos_summary.txt  (human-readable comparison)
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_cmd(args: list, cwd: Path = ROOT) -> None:
    print(f"\n>>> {' '.join(str(a) for a in args)}")
    r = subprocess.run(args, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {args}")


def period_metrics(equity: pd.DataFrame, trades: pd.DataFrame, label: str) -> dict:
    if equity.empty:
        return {"period": label}
    pv = equity.set_index("date")["portfolio_value"].astype(float)
    rets = pv.pct_change().dropna()
    if rets.empty or pv.iloc[0] <= 0:
        return {"period": label, "rows": len(pv)}

    days = (pv.index[-1] - pv.index[0]).days
    years = max(days / 365.25, 1e-9)
    total_return = pv.iloc[-1] / pv.iloc[0] - 1
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (rets.mean() * 252) / vol if vol > 0 else float("nan")
    cum = pv / pv.cummax()
    max_dd = (cum.min() - 1)

    n_buys = n_sells = 0
    hit = float("nan")
    if trades is not None and not trades.empty:
        t = trades.copy()
        t["date"] = pd.to_datetime(t["date"])
        t = t[(t["date"] >= pv.index[0]) & (t["date"] <= pv.index[-1])]
        if "side" in t.columns:
            n_buys = int((t["side"].str.lower() == "buy").sum())
            n_sells = int((t["side"].str.lower() == "sell").sum())
        if "pnl_pct" in t.columns:
            sells = t[(t.get("side", "").str.lower() == "sell") & t["pnl_pct"].notna()]
            if not sells.empty:
                hit = float((sells["pnl_pct"] > 0).mean())

    return {
        "period": label,
        "start": pv.index[0].date(),
        "end": pv.index[-1].date(),
        "years": round(years, 2),
        "rows": int(len(pv)),
        "start_value": round(pv.iloc[0], 2),
        "end_value": round(pv.iloc[-1], 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "vol_pct": round(vol * 100, 2),
        "sharpe": round(sharpe, 2),
        "max_dd_pct": round(max_dd * 100, 2),
        "buys": n_buys,
        "sells": n_sells,
        "hit_rate": round(hit, 3) if not math.isnan(hit) else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", default="nse500_data_merged")
    ap.add_argument("--top-n", type=int, default=24)
    ap.add_argument("--lookback-months", type=int, default=6)
    ap.add_argument("--rebalance-weeks", type=int, default=1)
    ap.add_argument("--vol-floor", type=float, default=0.05)
    ap.add_argument("--min-hold-days", type=int, default=8)
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--is-start", default="2020-07-10",
                    help="Date that splits OOS vs IS")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    ts = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    out = ROOT / (args.out or f"experiments/oos_walkthrough/run_{ts}")
    out.mkdir(parents=True, exist_ok=True)

    signals = out / "signals.csv"

    # 1. Build signals
    run_cmd([
        PYTHON, "scripts/build_momentum_signals_flexible.py",
        "--prices-dir", args.prices_dir,
        "--output", str(signals),
        "--lookback-months", str(args.lookback_months),
        "--rebalance-weeks", str(args.rebalance_weeks),
        "--top-n", str(args.top_n),
        "--vol-floor", str(args.vol_floor),
        "--skip-days", "0",
    ])

    # 2. Run backtest
    run_cmd([
        PYTHON, "scripts/backtest_momentum.py",
        "--prices-dir", args.prices_dir,
        "--signals", str(signals),
        "--benchmark", "data/benchmarks/nifty100.csv",
        "--output-dir", str(out),
        "--scenario", "baseline",
        "--top-n", str(args.top_n),
        "--initial-capital", str(args.initial_capital),
        "--min-hold-days", str(args.min_hold_days),
    ])

    # 3. Slice and report
    equity = pd.read_csv(out / "momentum_equity.csv", parse_dates=["date"])
    trades_path = out / "momentum_trades.csv"
    trades = pd.read_csv(trades_path, parse_dates=["date"]) if trades_path.exists() else pd.DataFrame()

    boundary = pd.Timestamp(args.is_start)
    oos_eq = equity[equity["date"] < boundary]
    is_eq = equity[equity["date"] >= boundary]
    full = period_metrics(equity, trades, "full")
    oos = period_metrics(oos_eq, trades, "OOS (pre-IS)")
    is_ = period_metrics(is_eq, trades, "IS")

    rows = [full, oos, is_]
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "oos_summary.csv", index=False)

    print("\n" + "=" * 80)
    print(f"OOS WALKTHROUGH — split at {boundary.date()}")
    print("=" * 80)
    print(summary.to_string(index=False))

    txt = out / "oos_summary.txt"
    with open(txt, "w") as f:
        f.write(f"OOS WALKTHROUGH — split at {boundary.date()}\n")
        f.write(f"prices_dir={args.prices_dir}  top_n={args.top_n}  "
                f"lookback={args.lookback_months}m  rebalance={args.rebalance_weeks}w  "
                f"vol_floor={args.vol_floor}  min_hold={args.min_hold_days}d\n\n")
        f.write(summary.to_string(index=False))
    print(f"\n[wrote] {txt}")


if __name__ == "__main__":
    main()
