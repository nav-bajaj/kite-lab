"""SIP (monthly contribution) analysis — the way Indian retail actually invests.

Lump-sum entry-day statistics answer "what if I put everything in on day X".
A SIP spreads entry across every month of the holding period, which changes
the risk profile: drawdowns become buying opportunities rather than pure pain.

For every possible start month, simulates a fixed monthly contribution over
each horizon, then computes the money-weighted return (XIRR) and the corpus.

Usage:
  python tasks/portfolio_risk_2026/sip_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
START, END = "2013-07-01", "2026-08-21"
MONTHLY = 10_000
HORIZONS = [("1y", 12), ("2y", 24), ("3y", 36), ("5y", 60), ("10y", 120)]


def load(f, col="pv"):
    d = pd.read_csv(R / f, parse_dates=["date"]).set_index("date")
    return d[col].astype(float).dropna().loc[START:END]


def monthly_prices(pv):
    """One NAV per month — first trading day, the usual SIP debit date."""
    return pv.groupby([pv.index.year, pv.index.month]).first()


def xirr_monthly(n_months, corpus, contrib=MONTHLY):
    """Annualised money-weighted return for n level monthly contributions
    followed by a single redemption. Bisection on monthly NPV."""
    def npv(r):
        if r <= -0.999999:
            return float("inf")
        v = -sum(contrib / (1 + r) ** t for t in range(n_months))
        return v + corpus / (1 + r) ** n_months
    lo, hi = -0.99, 1.0
    if npv(lo) * npv(hi) > 0:
        return np.nan
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    m = (lo + hi) / 2
    return ((1 + m) ** 12 - 1) * 100


def sip_runs(pv, n_months):
    """Every start month with a full horizon available."""
    nav = monthly_prices(pv)
    out = []
    for i in range(len(nav) - n_months):
        window = nav.iloc[i:i + n_months]
        redeem = nav.iloc[i + n_months]
        units = (MONTHLY / window.values).sum()
        corpus = units * redeem
        invested = MONTHLY * n_months
        out.append({"corpus": corpus, "invested": invested,
                    "multiple": corpus / invested,
                    "xirr": xirr_monthly(n_months, corpus)})
    return pd.DataFrame(out)


def main():
    bench = load("recent_production.csv", "benchmark")
    series = {
        "production OM25": load("recent_production.csv"),
        "candidate (fixed)": load("recent_candidate_n100.csv"),
        "candidate (walk-fwd)": load("om25_wf_n100_long/walkforward_equity.csv"),
        "NIFTY 100": bench,
    }
    all_rows = []
    for hname, n in HORIZONS:
        for k, pv in series.items():
            df = sip_runs(pv, n)
            if df.empty:
                continue
            x = df["xirr"].dropna()
            all_rows.append({
                "horizon": hname, "series": k, "n_start_months": len(df),
                "pct_positive": round((x > 0).mean() * 100, 1),
                "median_xirr": round(x.median(), 1),
                "p5_xirr": round(x.quantile(0.05), 1),
                "p25_xirr": round(x.quantile(0.25), 1),
                "worst_xirr": round(x.min(), 1),
                "best_xirr": round(x.max(), 1),
                "median_corpus": round(df["corpus"].median() / 1e5, 1),
                "worst_corpus": round(df["corpus"].min() / 1e5, 1),
                "invested_lakh": round(df["invested"].iloc[0] / 1e5, 1),
                "median_multiple": round(df["multiple"].median(), 2),
                "worst_multiple": round(df["multiple"].min(), 2),
            })
    res = pd.DataFrame(all_rows)
    res.to_csv(R / "sip_analysis.csv", index=False)

    print(f"=== SIP of Rs {MONTHLY:,}/month, every start month, "
          f"{START} -> {END} ===")
    for hname, _ in HORIZONS:
        sub = res[res.horizon == hname]
        if sub.empty:
            continue
        print(f"\n--- {hname} SIP  (invested Rs {sub['invested_lakh'].iloc[0]}L, "
              f"{sub['n_start_months'].iloc[0]} start months) ---")
        print(sub[["series", "pct_positive", "median_xirr", "p5_xirr",
                   "p25_xirr", "worst_xirr", "best_xirr", "median_corpus",
                   "worst_corpus", "median_multiple", "worst_multiple"]]
              .to_string(index=False))

    # SIP vs lump-sum dispersion at matched horizons
    print("\n=== dispersion: SIP XIRR vs lump-sum CAGR (spread p5 -> p95) ===")
    rows = []
    for hname, n in HORIZONS:
        h_days = int(n / 12 * 252)
        for k, pv in series.items():
            df = sip_runs(pv, n)
            if df.empty or "xirr" not in df.columns:
                continue
            x = df["xirr"].dropna()
            r = (pv.shift(-h_days) / pv - 1.0).dropna()
            cagr = ((1 + r) ** (252 / h_days) - 1) * 100
            if x.empty or cagr.empty:
                continue
            rows.append({"horizon": hname, "series": k,
                         "SIP p5": round(x.quantile(.05), 1),
                         "SIP p95": round(x.quantile(.95), 1),
                         "SIP spread": round(x.quantile(.95) - x.quantile(.05), 1),
                         "lump p5": round(cagr.quantile(.05), 1),
                         "lump p95": round(cagr.quantile(.95), 1),
                         "lump spread": round(cagr.quantile(.95) - cagr.quantile(.05), 1)})
    d = pd.DataFrame(rows)
    for hname, _ in HORIZONS:
        sub = d[d.horizon == hname]
        if not sub.empty:
            print(f"\n--- {hname} ---")
            print(sub.drop(columns=["horizon"]).to_string(index=False))


if __name__ == "__main__":
    main()
