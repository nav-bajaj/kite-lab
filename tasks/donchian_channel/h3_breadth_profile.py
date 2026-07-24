"""H3 — Donchian breadth: descriptive profile (breadth-atlas methodology).

Metrics per N in {20, 55, 252}, denominator = symbols with a valid prior
N-day band that day (partially offsets the current-snapshot survivorship
skew; disclosed regardless):

  pct_above_high_N   share of universe with close > prior N-day high
                     (continuation included)
  pct_fresh_high_N   share printing a FRESH breakout (cross today only)
  pct_below_low_N    share with close < prior N-day low
  net_channel_N      pct_above_high_N - pct_below_low_N
  med_chanpos_N      median channel position (close - low)/(high - low),
                     form-identical to stochastic %K -- not a novel feature

Boundary gate: a replica of the production `net_new_highs_pct`
(close == inclusive 252d close-max, min_periods=100) must match
`data/breadth/breadth_daily.csv` on common dates (corr > 0.99).

Descriptive only -- no forward returns, per the atlas discipline.

Run:
    python tasks/donchian_channel/h3_breadth_profile.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols, donchian_upper, donchian_lower,
    channel_position, breakout_cross,
)

NS = (20, 55, 252)
EXISTING_BREADTH = ROOT / "data/breadth/breadth_daily.csv"
OUT_CSV = ROOT / "tasks/donchian_channel/donchian_breadth_daily.csv"


def ar1_halflife(s: pd.Series) -> tuple[float, float]:
    x = s.dropna()
    if len(x) < 100:
        return np.nan, np.nan
    rho = x.autocorr(1)
    hl = np.log(0.5) / np.log(abs(rho)) if 0 < abs(rho) < 1 else np.nan
    return round(float(rho), 3), round(float(hl), 1) if not np.isnan(hl) else np.nan


def dwell_stats(mask: pd.Series) -> dict:
    runs, cur = [], 0
    for v in mask.fillna(False).values:
        if v:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    if not runs:
        return {"episodes": 0, "median_days": None, "max_days": None}
    return {"episodes": len(runs), "median_days": float(np.median(runs)),
            "max_days": int(max(runs))}


def main():
    print("[h3] loading OHLC panels")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    high, low, close = panels["high"], panels["low"], panels["close"]

    out = {}
    for n in NS:
        up = donchian_upper(high, n)
        lo = donchian_lower(low, n)
        valid = up.notna() & lo.notna() & close.notna()
        denom = valid.sum(axis=1).astype(float).replace(0, np.nan)
        above = ((close > up) & valid).sum(axis=1) / denom
        fresh = (breakout_cross(close, up) & valid).sum(axis=1) / denom
        below = ((close < lo) & valid).sum(axis=1) / denom
        pos = channel_position(close, up, lo).where(valid)
        out[f"pct_above_high_{n}"] = above
        out[f"pct_fresh_high_{n}"] = fresh
        out[f"pct_below_low_{n}"] = below
        out[f"net_channel_{n}"] = above - below
        out[f"med_chanpos_{n}"] = pos.median(axis=1)

    df = pd.DataFrame(out)
    df.index.name = "date"

    # Boundary gate vs production breadth definition
    close_ff = close.ffill(limit=5)
    high_252c = close_ff.rolling(252, min_periods=100).max()
    low_252c = close_ff.rolling(252, min_periods=100).min()
    have = high_252c.notna().sum(axis=1).astype(float)
    replica_net = ((close_ff == high_252c).sum(axis=1)
                   - (close_ff == low_252c).sum(axis=1)) / have
    existing = pd.read_csv(EXISTING_BREADTH, parse_dates=["date"]).set_index("date")
    common = replica_net.index.intersection(existing.index)
    rho = replica_net.loc[common].corr(existing.loc[common, "net_new_highs_pct"])
    gate = "OK" if rho > 0.99 else "FAIL"
    print(f"[gate] replica net_new_highs_pct corr vs production: {rho:.4f} -> {gate}")

    df.to_csv(OUT_CSV)
    print(f"[wrote] {OUT_CSV.relative_to(ROOT)}  shape={df.shape}")

    print("\n=== Distributions (2010-06 onward, matching production panel) ===")
    prof = df.loc[df.index >= pd.Timestamp("2010-06-01")]
    stats = prof.describe(percentiles=[.05, .25, .5, .75, .95]).T.round(4)
    print(stats[["mean", "std", "5%", "25%", "50%", "75%", "95%"]].to_string())

    print("\n=== Persistence (AR1 / half-life days) ===")
    for c in prof.columns:
        rho1, hl = ar1_halflife(prof[c])
        print(f"  {c:22s} ar1={rho1}  halflife={hl}")

    print("\n=== Dwell in extremes (net_channel_N > p90 / < p10) ===")
    for n in NS:
        s = prof[f"net_channel_{n}"]
        hi, lo_q = s.quantile(.9), s.quantile(.1)
        print(f"  net_channel_{n}: hot(>{hi:.3f}) {dwell_stats(s > hi)}  "
              f"cold(<{lo_q:.3f}) {dwell_stats(s < lo_q)}")

    print("\n=== Extreme dates (net_channel_252) ===")
    s = prof["net_channel_252"]
    print("  top:    ", [str(d.date()) for d in s.nlargest(8).index])
    print("  bottom: ", [str(d.date()) for d in s.nsmallest(8).index])

    print("\n=== Correlation vs existing production breadth metrics ===")
    joined = prof.join(existing, how="inner")
    exist_cols = ["pct_above_200dma", "net_new_highs_pct", "pct_at_52w_high",
                  "mcclellan_osc", "ad_net_pct"]
    new_cols = [f"net_channel_{n}" for n in NS] + \
               [f"med_chanpos_{n}" for n in NS] + ["pct_fresh_high_55"]
    cm = joined[new_cols + exist_cols].corr().loc[new_cols, exist_cols].round(3)
    print(cm.to_string())

    print("\n=== Cross-N correlation (are 20/55/252 distinct?) ===")
    print(prof[[f"net_channel_{n}" for n in NS]].corr().round(3).to_string())


if __name__ == "__main__":
    main()
