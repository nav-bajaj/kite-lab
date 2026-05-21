"""T1 — Walk-forward (rolling 1-year OOS) robustness check.

Since neither A_PROD nor D_BREADTH has tunable parameters, "walk-forward"
here means: take the full-history equity curves, slide a 1-year window
across every trading day, and compute per-variant Sharpe / CAGR / MaxDD
in each window. Compare D_BREADTH against A_PROD.

Decision criterion (from PLAN.md):
  - Win in ≥70% of rolling windows = deployable upgrade
  - Win in ≥85% = strong upgrade

Reads equity curves from the latest combo_breadth_<ts>/ run dir.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


RUNS = ROOT / "tasks/breadth_atlas/combo_3state/runs"


def load_equity(p: Path) -> pd.Series:
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date")
    return df["pv"].astype(float)


def rolling_metric(pv: pd.Series, window_days: int) -> pd.DataFrame:
    """For each business-day start position, compute window-Sharpe and
    window-CAGR and window-MaxDD over the next `window_days` of equity.
    Returns DataFrame indexed by window-start date.
    """
    pv = pv.sort_index()
    rets = pv.pct_change()
    rows = []
    dates = pv.index
    for i in range(len(dates) - window_days):
        start = dates[i]; end = dates[i + window_days]
        seg = pv.iloc[i:i + window_days + 1]
        if len(seg) < window_days // 2:
            continue
        r = seg.pct_change().dropna()
        if len(r) < 60:
            continue
        years = (seg.index[-1] - seg.index[0]).days / 365.25
        cagr = (seg.iloc[-1] / seg.iloc[0]) ** (1 / years) - 1 if years > 0 else 0
        vol = r.std() * math.sqrt(252)
        sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
        dd = (seg / seg.cummax() - 1).min()
        rows.append({
            "start": start, "end": end,
            "cagr": cagr, "sharpe": sharpe,
            "max_dd": dd, "vol": vol,
        })
    return pd.DataFrame(rows).set_index("start")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path,
                    default=RUNS / "combo_breadth_20260521_203419")
    ap.add_argument("--window-days", type=int, default=252,
                    help="Rolling window length in trading days (252 = 1y)")
    ap.add_argument("--stride-days", type=int, default=1,
                    help="Stride between rolling windows (1 = daily)")
    args = ap.parse_args()

    print(f"[load] equity from {args.run_dir.relative_to(ROOT)}")
    a = load_equity(args.run_dir / "A_PROD_equity.csv")
    b = load_equity(args.run_dir / "B_BEAR_ENTRIES_equity.csv")
    d = load_equity(args.run_dir / "D_BREADTH_equity.csv")
    print(f"  A_PROD:         {len(a)} days, {a.index[0].date()} → {a.index[-1].date()}")
    print(f"  B_BEAR_ENTRIES: {len(b)} days")
    print(f"  D_BREADTH:      {len(d)} days")

    print(f"\n[rolling] window={args.window_days}d, stride={args.stride_days}d")
    a_metrics = rolling_metric(a, args.window_days)
    b_metrics = rolling_metric(b, args.window_days)
    d_metrics = rolling_metric(d, args.window_days)

    # Align on common start dates
    common_start = a_metrics.index.intersection(d_metrics.index).intersection(b_metrics.index)
    common_start = common_start[::args.stride_days]
    print(f"  {len(common_start)} comparable rolling windows")

    # Per-window diffs
    diff = pd.DataFrame({
        "A_sharpe": a_metrics.loc[common_start, "sharpe"],
        "B_sharpe": b_metrics.loc[common_start, "sharpe"],
        "D_sharpe": d_metrics.loc[common_start, "sharpe"],
        "A_cagr":   a_metrics.loc[common_start, "cagr"],
        "B_cagr":   b_metrics.loc[common_start, "cagr"],
        "D_cagr":   d_metrics.loc[common_start, "cagr"],
        "A_dd":     a_metrics.loc[common_start, "max_dd"],
        "B_dd":     b_metrics.loc[common_start, "max_dd"],
        "D_dd":     d_metrics.loc[common_start, "max_dd"],
    })
    diff["D_vs_A_sharpe"] = diff["D_sharpe"] - diff["A_sharpe"]
    diff["D_vs_A_cagr"]   = diff["D_cagr"] - diff["A_cagr"]
    diff["D_vs_A_dd"]     = diff["D_dd"] - diff["A_dd"]   # positive = D worse (deeper neg dd is more neg)

    out = args.run_dir / "walkforward_rolling.csv"
    diff.to_csv(out)
    print(f"[wrote] {out.relative_to(ROOT)}")

    # === Summary ===
    print("\n=== Rolling-window summary ===")
    n = len(diff)
    print(f"Total windows: {n}")
    print()

    def line(label, series):
        print(f"  {label:30s}  mean={series.mean():+.4f}  median={series.median():+.4f}  "
              f"std={series.std():.4f}  p25={series.quantile(0.25):+.4f}  p75={series.quantile(0.75):+.4f}")

    line("D - A Sharpe", diff["D_vs_A_sharpe"])
    line("D - A CAGR",   diff["D_vs_A_cagr"])
    line("D - A MaxDD",  diff["D_vs_A_dd"])
    print()

    print("Win-rate (D vs A):")
    d_sharpe_win = (diff["D_vs_A_sharpe"] > 0).mean() * 100
    d_cagr_win   = (diff["D_vs_A_cagr"]   > 0).mean() * 100
    d_dd_win     = (diff["D_vs_A_dd"]     > 0).mean() * 100  # D's dd more positive (less negative) = D better
    print(f"  D Sharpe > A Sharpe : {d_sharpe_win:5.1f}%")
    print(f"  D CAGR   > A CAGR   : {d_cagr_win:5.1f}%")
    print(f"  D MaxDD  > A MaxDD  : {d_dd_win:5.1f}%  (D better drawdown)")
    print()

    # PLAN.md decision criteria
    print("Decision gates (from PLAN.md):")
    if d_sharpe_win >= 85: verdict = "STRONG UPGRADE"
    elif d_sharpe_win >= 70: verdict = "DEPLOYABLE UPGRADE"
    elif d_sharpe_win >= 50: verdict = "NEUTRAL (no consistent edge)"
    else: verdict = "PRODUCTION A IS BETTER"
    print(f"  D wins Sharpe {d_sharpe_win:.1f}% of windows  →  {verdict}")
    print()

    # Worst and best windows for D vs A
    print("=== Worst-5 windows for D (D - A Sharpe smallest, i.e. D underperforms most) ===")
    worst = diff.nsmallest(5, "D_vs_A_sharpe")[["A_sharpe", "D_sharpe", "D_vs_A_sharpe",
                                                  "A_cagr", "D_cagr", "A_dd", "D_dd"]]
    print(worst.to_string())
    print()

    print("=== Best-5 windows for D (D - A Sharpe largest) ===")
    best = diff.nlargest(5, "D_vs_A_sharpe")[["A_sharpe", "D_sharpe", "D_vs_A_sharpe",
                                               "A_cagr", "D_cagr", "A_dd", "D_dd"]]
    print(best.to_string())
    print()

    # Also report by epoch — break the rolling windows into rough eras
    print("=== Win-rate by epoch (rolling-window start date) ===")
    epochs = [
        ("2010–2012", "2010-01-01", "2013-01-01"),
        ("2013–2015", "2013-01-01", "2016-01-01"),
        ("2016–2018", "2016-01-01", "2019-01-01"),
        ("2019–2021", "2019-01-01", "2022-01-01"),
        ("2022–2024", "2022-01-01", "2025-01-01"),
        ("2025+",     "2025-01-01", "2027-01-01"),
    ]
    for label, lo, hi in epochs:
        sub = diff.loc[(diff.index >= lo) & (diff.index < hi)]
        if len(sub) == 0:
            continue
        win_pct = (sub["D_vs_A_sharpe"] > 0).mean() * 100
        med_diff = sub["D_vs_A_sharpe"].median()
        print(f"  {label:12s}  n={len(sub):4d}  D-wins={win_pct:5.1f}%  median(D-A Sharpe)={med_diff:+.3f}")


if __name__ == "__main__":
    main()
