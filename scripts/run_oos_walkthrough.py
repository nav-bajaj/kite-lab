"""End-to-end out-of-sample walkthrough on the GDF-stitched price panel.

Supports three strategies:
- momentum: NSE 500 L6-1W, min-hold 8d (production NSE 500 portfolio)
- om25: OM25 Omega Ratio composite (production OM25 portfolio)
- tl25: Trend Leaders 25 (production TL25 portfolio)

Each pipeline:
1. Build signals on merged panel (covers ~2009 to today)
2. Run backtest on merged panel
3. Slice the equity curve at --is-start (default 2020-07-10) and compute
   period-level metrics for OOS vs IS.

Outputs:
   experiments/oos_walkthrough/<strategy>_<timestamp>/
     - signals.csv
     - <strategy>_*.csv  (equity, trades, ...)
     - oos_summary.csv / oos_summary.txt / oos_yearly.txt

Usage:
    python scripts/run_oos_walkthrough.py --strategy momentum
    python scripts/run_oos_walkthrough.py --strategy om25
    python scripts/run_oos_walkthrough.py --strategy tl25
    python scripts/run_oos_walkthrough.py --strategy all
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

EQUITY_FILES = {
    "momentum": "momentum_equity.csv",
    "om25": "om25_equity.csv",
    "tl25": "tl20_equity.csv",
}
TRADES_FILES = {
    "momentum": "momentum_trades.csv",
    "om25": "om25_trades.csv",
    "tl25": "tl20_trades.csv",
}


def run_cmd(args: list, cwd: Path = ROOT) -> None:
    print(f"\n>>> {' '.join(str(a) for a in args)}")
    r = subprocess.run(args, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {args}")


def build_and_backtest_momentum(prices_dir: str, out: Path, top_n: int,
                                lookback_months: int, rebalance_weeks: int,
                                vol_floor: float, min_hold_days: int,
                                initial_capital: float) -> None:
    signals = out / "signals.csv"
    run_cmd([PYTHON, "scripts/build_momentum_signals_flexible.py",
             "--prices-dir", prices_dir, "--output", str(signals),
             "--lookback-months", str(lookback_months),
             "--rebalance-weeks", str(rebalance_weeks),
             "--top-n", str(top_n), "--vol-floor", str(vol_floor),
             "--skip-days", "0"])
    run_cmd([PYTHON, "scripts/backtest_momentum.py",
             "--prices-dir", prices_dir, "--signals", str(signals),
             "--benchmark", "data/benchmarks/nifty100.csv",
             "--output-dir", str(out), "--scenario", "baseline",
             "--top-n", str(top_n),
             "--initial-capital", str(initial_capital),
             "--min-hold-days", str(min_hold_days)])


def build_and_backtest_om25(prices_dir: str, out: Path,
                            initial_capital: float) -> None:
    signals = out / "signals.csv"
    audit = out / "om25_audit.csv"
    run_cmd([PYTHON, "scripts/build_om25_signals.py",
             "--prices-dir", prices_dir,
             "--universe", "data/static/nse500_universe.csv",
             "--output", str(signals),
             "--audit-output", str(audit),
             "--top-n", "25"])
    run_cmd([PYTHON, "scripts/backtest_om25.py",
             "--prices-dir", prices_dir, "--signals", str(signals),
             "--benchmark", "data/benchmarks/nifty100.csv",
             "--output-dir", str(out), "--top-n", "25",
             "--initial-capital", str(initial_capital)])


def build_and_backtest_tl25(prices_dir: str, out: Path,
                            initial_capital: float) -> None:
    signals = out / "signals.csv"
    audit = out / "tl25_audit.csv"
    run_cmd([PYTHON, "scripts/build_trend_leaders_signals.py",
             "--prices-dir", prices_dir,
             "--universe", "data/static/nse500_universe.csv",
             "--output", str(signals),
             "--audit-output", str(audit),
             "--top-n", "25",
             "--rebalance-freq", "biweekly"])
    run_cmd([PYTHON, "scripts/backtest_trend_leaders.py",
             "--prices-dir", prices_dir, "--signals", str(signals),
             "--benchmark", "data/benchmarks/nifty100.csv",
             "--output-dir", str(out), "--top-n", "25",
             "--initial-capital", str(initial_capital),
             "--variant", "base",
             "--atr-mult", "5.0",
             "--atr-min-floor", "0.0"])


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


def yearly_breakdown(equity: pd.DataFrame, is_boundary: pd.Timestamp) -> pd.DataFrame:
    pv = equity.set_index("date")["portfolio_value"].astype(float).sort_index()
    rows = []
    for y, gp in pv.groupby(pv.index.year):
        if len(gp) < 5:
            continue
        r = gp.pct_change().dropna()
        cagr = gp.iloc[-1] / gp.iloc[0] - 1
        vol = r.std() * math.sqrt(252)
        sh = (r.mean() * 252) / vol if vol > 0 else float("nan")
        cum = gp / gp.cummax()
        dd = (cum.min() - 1) * 100
        era = "OOS" if y < is_boundary.year else ("IS-bridge" if y == is_boundary.year else "IS")
        rows.append({"year": y, "ret_pct": round(cagr * 100, 2),
                     "vol_pct": round(vol * 100, 1),
                     "sharpe": round(sh, 2),
                     "max_dd_pct": round(dd, 1), "era": era})
    return pd.DataFrame(rows)


def report(strategy: str, out: Path, is_start: pd.Timestamp) -> dict:
    eq = pd.read_csv(out / EQUITY_FILES[strategy], parse_dates=["date"])
    tr_path = out / TRADES_FILES[strategy]
    tr = pd.read_csv(tr_path, parse_dates=["date"]) if tr_path.exists() else pd.DataFrame()

    full = period_metrics(eq, tr, f"{strategy} full")
    oos = period_metrics(eq[eq["date"] < is_start], tr, f"{strategy} OOS")
    isp = period_metrics(eq[eq["date"] >= is_start], tr, f"{strategy} IS")
    summary = pd.DataFrame([full, oos, isp])
    summary.to_csv(out / "oos_summary.csv", index=False)

    yr = yearly_breakdown(eq, is_start)
    with open(out / "oos_summary.txt", "w") as f:
        f.write(f"{strategy.upper()} OOS WALKTHROUGH — split at {is_start.date()}\n\n")
        f.write(summary.to_string(index=False))
    with open(out / "oos_yearly.txt", "w") as f:
        f.write(f"{strategy.upper()} year-by-year\n")
        f.write(yr.to_string(index=False))

    print("\n" + "=" * 80)
    print(f"{strategy.upper()} OOS WALKTHROUGH — split at {is_start.date()}")
    print("=" * 80)
    print(summary.to_string(index=False))
    print()
    print(yr.to_string(index=False))
    return {"strategy": strategy, **{k: v for k, v in oos.items()
                                      if k in ("cagr_pct", "sharpe", "max_dd_pct", "vol_pct")},
            "is_cagr_pct": isp.get("cagr_pct"), "is_sharpe": isp.get("sharpe"),
            "is_max_dd_pct": isp.get("max_dd_pct"),
            "full_cagr_pct": full.get("cagr_pct"), "full_sharpe": full.get("sharpe")}


def run_strategy(strategy: str, prices_dir: str, is_start: pd.Timestamp,
                 initial_capital: float, ts: str) -> dict:
    out = ROOT / f"experiments/oos_walkthrough/{strategy}_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    if strategy == "momentum":
        build_and_backtest_momentum(prices_dir, out, top_n=24,
                                    lookback_months=6, rebalance_weeks=1,
                                    vol_floor=0.05, min_hold_days=8,
                                    initial_capital=initial_capital)
    elif strategy == "om25":
        build_and_backtest_om25(prices_dir, out, initial_capital=initial_capital)
    elif strategy == "tl25":
        build_and_backtest_tl25(prices_dir, out, initial_capital=initial_capital)
    else:
        raise ValueError(strategy)
    return report(strategy, out, is_start)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["momentum", "om25", "tl25", "all"],
                    default="all")
    ap.add_argument("--prices-dir", default="nse500_data_merged")
    ap.add_argument("--is-start", default="2020-07-10")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    args = ap.parse_args()

    is_start = pd.Timestamp(args.is_start)
    ts = dt.datetime.now().strftime("%Y%m%d%H%M%S")

    strategies = ["momentum", "om25", "tl25"] if args.strategy == "all" else [args.strategy]
    headlines = []
    for s in strategies:
        try:
            headlines.append(run_strategy(s, args.prices_dir, is_start,
                                           args.initial_capital, ts))
        except Exception as e:
            print(f"\n[FAIL] {s}: {e}")
            headlines.append({"strategy": s, "error": str(e)[:200]})

    if len(headlines) > 1:
        print("\n" + "=" * 80)
        print("CROSS-STRATEGY OOS COMPARISON")
        print("=" * 80)
        print(pd.DataFrame(headlines).to_string(index=False))
        comp_dir = ROOT / f"experiments/oos_walkthrough/_comparison_{ts}"
        comp_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(headlines).to_csv(comp_dir / "comparison.csv", index=False)
        print(f"\n[wrote] {comp_dir/'comparison.csv'}")


if __name__ == "__main__":
    main()
