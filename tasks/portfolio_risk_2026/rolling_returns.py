"""Investor-experience comparison: buffer=0 (production L6 v2) vs buffered variants.

Answers "what does a person who joins on a random day actually live through?"
rather than "what does the strategy earn end-to-end". Reports rolling 6m/12m
return distributions, underwater/pain statistics, and worst-case entry points.

Usage:
  python tasks/portfolio_risk_2026/rolling_returns.py
  python tasks/portfolio_risk_2026/rolling_returns.py --buffers 0 20 --window OOS
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"

PERIODS = {
    "FULL": ("2009-09-01", "2026-08-21"),
    "OOS":  ("2017-01-01", "2026-08-21"),
}
H6, H12 = 126, 252   # trading days


def load_pv(buf: int, start, end) -> pd.DataFrame:
    eq = pd.read_csv(RUNS / f"buf{buf:02d}_equity.csv", parse_dates=["date"])
    eq = eq[(eq["date"] >= start) & (eq["date"] <= end)]
    return eq.set_index("date")[["pv", "benchmark"]].astype(float)


def rolling_stats(pv: pd.Series, h: int) -> dict:
    """Distribution of h-day holding-period returns across every entry day."""
    r = (pv.shift(-h) / pv - 1.0).dropna() * 100
    if r.empty:
        return {}
    return {
        "n_entry_days": len(r),
        "mean": round(r.mean(), 1),
        "median": round(r.median(), 1),
        "std": round(r.std(), 1),
        "min": round(r.min(), 1),
        "p5": round(r.quantile(0.05), 1),
        "p10": round(r.quantile(0.10), 1),
        "p25": round(r.quantile(0.25), 1),
        "p75": round(r.quantile(0.75), 1),
        "p90": round(r.quantile(0.90), 1),
        "max": round(r.max(), 1),
        "pct_negative": round((r < 0).mean() * 100, 1),
        "pct_below_10": round((r < 10).mean() * 100, 1),
        "iqr": round(r.quantile(0.75) - r.quantile(0.25), 1),
    }


def underwater_stats(pv: pd.Series) -> dict:
    """Depth, breadth and duration of the pain, not just the max."""
    dd = pv / pv.cummax() - 1.0
    underwater = dd < -1e-9

    # Longest contiguous underwater run, in calendar days.
    runs, cur_start = [], None
    for date, uw in underwater.items():
        if uw and cur_start is None:
            cur_start = date
        elif not uw and cur_start is not None:
            runs.append((date - cur_start).days)
            cur_start = None
    if cur_start is not None:
        runs.append((underwater.index[-1] - cur_start).days)

    # Ulcer index: RMS of the drawdown path. Penalises deep AND long, which is
    # what "can I live with this" actually means; max_dd alone hides duration.
    ulcer = float(np.sqrt((dd.mul(100) ** 2).mean()))

    return {
        "max_dd_pct": round(dd.min() * 100, 1),
        "avg_dd_pct": round(dd.mean() * 100, 1),
        "pct_days_underwater": round(underwater.mean() * 100, 1),
        "pct_days_dd_gt_10": round((dd < -0.10).mean() * 100, 1),
        "pct_days_dd_gt_20": round((dd < -0.20).mean() * 100, 1),
        "longest_uw_days": max(runs) if runs else 0,
        "median_uw_days": int(np.median(runs)) if runs else 0,
        "n_uw_episodes": len(runs),
        "ulcer_index": round(ulcer, 2),
    }


def worst_entries(pv: pd.Series, h: int, n: int = 3) -> list:
    r = (pv.shift(-h) / pv - 1.0).dropna() * 100
    w = r.nsmallest(n)
    return [(d.date().isoformat(), round(v, 1)) for d, v in w.items()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffers", type=int, nargs="+", default=[0, 10, 15, 20])
    ap.add_argument("--periods", nargs="+", default=["OOS", "FULL"])
    args = ap.parse_args()

    for pname in args.periods:
        start, end = PERIODS[pname]
        print(f"\n{'#'*100}")
        print(f"# {pname}   {start} -> {end}")
        print(f"{'#'*100}")

        rows6, rows12, rowsu = [], [], []
        bench_done = False
        for buf in args.buffers:
            df = load_pv(buf, start, end)
            pv = df["pv"]
            rows6.append({"config": f"buf{buf}", **rolling_stats(pv, H6)})
            rows12.append({"config": f"buf{buf}", **rolling_stats(pv, H12)})
            rowsu.append({"config": f"buf{buf}", **underwater_stats(pv)})
            if not bench_done:
                bm = df["benchmark"].dropna()
                if len(bm) > H12:
                    rows6.append({"config": "NIFTY100", **rolling_stats(bm, H6)})
                    rows12.append({"config": "NIFTY100", **rolling_stats(bm, H12)})
                    rowsu.append({"config": "NIFTY100", **underwater_stats(bm)})
                bench_done = True

        cols = ["config", "median", "mean", "std", "iqr", "min", "p5", "p10",
                "p25", "p75", "p90", "max", "pct_negative", "pct_below_10"]
        print(f"\n--- 6-month holding-period returns (%), every entry day ---")
        print(pd.DataFrame(rows6)[cols].to_string(index=False))
        print(f"\n--- 12-month holding-period returns (%), every entry day ---")
        print(pd.DataFrame(rows12)[cols].to_string(index=False))
        print(f"\n--- Underwater / pain profile ---")
        print(pd.DataFrame(rowsu).to_string(index=False))

        print(f"\n--- Worst 12m entry dates ---")
        for buf in args.buffers:
            pv = load_pv(buf, start, end)["pv"]
            print(f"  buf{buf:<3} {worst_entries(pv, H12)}")

    # Persist the OOS rolling series for charting.
    start, end = PERIODS["OOS"]
    out = pd.DataFrame()
    for buf in args.buffers:
        pv = load_pv(buf, start, end)["pv"]
        out[f"buf{buf}_r12"] = (pv.shift(-H12) / pv - 1.0) * 100
        out[f"buf{buf}_dd"] = (pv / pv.cummax() - 1.0) * 100
    bm = load_pv(args.buffers[0], start, end)["benchmark"].dropna()
    out["nifty100_r12"] = (bm.shift(-H12) / bm - 1.0) * 100
    out.to_csv(RUNS / "rolling_oos.csv")
    print(f"\n[wrote] {RUNS / 'rolling_oos.csv'}")


if __name__ == "__main__":
    main()
