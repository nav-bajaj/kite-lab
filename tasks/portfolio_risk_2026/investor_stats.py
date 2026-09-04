"""Investor-facing statistics for the OM25 v3 candidate vs production.

Horizon analysis (the "how long do I need to hold" question), capture ratios,
batting averages and recovery behaviour. Common window across all series.

Usage:
  python tasks/portfolio_risk_2026/investor_stats.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
START, END = "2013-07-01", "2026-08-21"
HORIZONS = [("6m", 126), ("1y", 252), ("2y", 504), ("3y", 756), ("5y", 1260)]


def load(f, col="pv"):
    d = pd.read_csv(R / f, parse_dates=["date"]).set_index("date")
    return d[col].astype(float).dropna().loc[START:END]


def horizon_table(pv, bench, label):
    """Every trading day treated as an entry; outcome after each holding period."""
    rows = []
    for name, h in HORIZONS:
        r = (pv.shift(-h) / pv - 1.0).dropna() * 100
        b = (bench.shift(-h) / bench - 1.0).dropna() * 100
        common = r.index.intersection(b.index)
        r, b = r.loc[common], b.loc[common]
        if len(r) < 30:
            continue
        yrs = h / 252
        ann = ((1 + r / 100) ** (1 / yrs) - 1) * 100
        rows.append({
            "series": label, "horizon": name, "n_start_days": len(r),
            "pct_positive": round((r > 0).mean() * 100, 1),
            "pct_beat_bench": round((r > b).mean() * 100, 1),
            "median_%": round(r.median(), 1),
            "median_ann_%": round(ann.median(), 1),
            "p5_%": round(r.quantile(0.05), 1),
            "p25_%": round(r.quantile(0.25), 1),
            "worst_%": round(r.min(), 1),
            "best_%": round(r.max(), 1),
        })
    return rows


def capture(pv, bench):
    rp = pv.pct_change().dropna()
    rb = bench.pct_change().dropna()
    c = rp.index.intersection(rb.index)
    rp, rb = rp.loc[c], rb.loc[c]
    up, dn = rb > 0, rb < 0
    uc = rp[up].mean() / rb[up].mean() if rb[up].mean() != 0 else np.nan
    dc = rp[dn].mean() / rb[dn].mean() if rb[dn].mean() != 0 else np.nan
    mp = pv.resample("ME").last().pct_change().dropna()
    mb = bench.resample("ME").last().pct_change().dropna()
    cm = mp.index.intersection(mb.index)
    qp = pv.resample("QE").last().pct_change().dropna()
    qb = bench.resample("QE").last().pct_change().dropna()
    cq = qp.index.intersection(qb.index)
    return {
        "up_capture": round(uc * 100, 0), "down_capture": round(dc * 100, 0),
        "capture_ratio": round(uc / dc, 2) if dc else np.nan,
        "beta": round(rp.cov(rb) / rb.var(), 2),
        "corr": round(rp.corr(rb), 2),
        "pct_months_positive": round((mp > 0).mean() * 100, 1),
        "pct_months_beat_bench": round((mp.loc[cm] > mb.loc[cm]).mean() * 100, 1),
        "pct_quarters_beat_bench": round((qp.loc[cq] > qb.loc[cq]).mean() * 100, 1),
    }


def recovery(pv):
    dd = pv / pv.cummax() - 1
    uw, runs, st = dd < -1e-9, [], None
    for d, f in uw.items():
        if f and st is None:
            st = d
        elif not f and st is not None:
            runs.append(((d - st).days, dd.loc[st:d].min() * 100))
            st = None
    ongoing = None
    if st is not None:
        ongoing = ((uw.index[-1] - st).days, dd.loc[st:].min() * 100)
    deep = [r for r in runs if r[1] <= -15]
    return {
        "n_dd_over_15pct": len(deep),
        "median_recovery_days_dd15": int(np.median([d for d, _ in deep])) if deep else 0,
        "worst_recovery_days": max([d for d, _ in runs]) if runs else 0,
        "ongoing_uw_days": ongoing[0] if ongoing else 0,
        "ongoing_uw_trough": round(ongoing[1], 1) if ongoing else 0,
    }


def main():
    bench = load("recent_production.csv", "benchmark")
    series = {
        "production OM25": load("recent_production.csv"),
        "candidate (fixed)": load("recent_candidate_n100.csv"),
        "candidate (walk-fwd)": load("om25_wf_n100_long/walkforward_equity.csv"),
        "NIFTY 100": bench,
    }
    rows = []
    for k, pv in series.items():
        rows += horizon_table(pv, bench, k)
    h = pd.DataFrame(rows)
    h.to_csv(R / "investor_horizon.csv", index=False)

    print(f"=== HOLDING-PERIOD OUTCOMES, every trading day as an entry "
          f"({START} -> {END}) ===")
    for name, _ in HORIZONS:
        sub = h[h.horizon == name]
        if sub.empty:
            continue
        print(f"\n--- held for {name} ---")
        print(sub[["series", "n_start_days", "pct_positive", "pct_beat_bench",
                   "median_%", "median_ann_%", "p5_%", "p25_%", "worst_%",
                   "best_%"]].to_string(index=False))

    print("\n=== CAPTURE / CONSISTENCY vs NIFTY 100 ===")
    print(pd.DataFrame([{"series": k, **capture(pv, bench)}
                        for k, pv in series.items()]).to_string(index=False))

    print("\n=== DRAWDOWN RECOVERY ===")
    print(pd.DataFrame([{"series": k, **recovery(pv)}
                        for k, pv in series.items()]).to_string(index=False))


if __name__ == "__main__":
    main()
