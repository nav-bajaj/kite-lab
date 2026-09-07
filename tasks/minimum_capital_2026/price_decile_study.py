"""Is there a real low-price effect, or is the cap sweep just noise?

Motivation: the OM25 cap sweep is non-monotonic, and the Rs 2,000 arm
beat every one of 30 random-exclusion placebo draws. That needed an
explanation other than path noise. This tests the obvious one directly:
sort the universe by price at each rebalance and measure forward returns
by price decile.

If cheap names genuinely outperformed in-sample, then a tight price cap
is not a free operational change -- it is a size tilt, and the by-year
table shows whether that tilt is stable or cyclical.

Usage:
    python tasks/minimum_capital_2026/price_decile_study.py
    python tasks/minimum_capital_2026/price_decile_study.py --horizon 63
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "runs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.loaders import load_price_panels
from scripts._clean_engine import biweekly_fridays
from scripts.om25_v3 import LOCKED
from scripts.universe_membership import resolve_universe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=63,
                    help="forward return horizon in trading days")
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--deciles", type=int, default=10)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    close_panel, _ = load_price_panels(ROOT / "nse500_data")
    cal = close_panel.index
    universe, membership_fn, _ = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv",
        ROOT / LOCKED["universe_csv"])
    cols = [c for c in close_panel.columns if c in universe]
    dates = [d for d in biweekly_fridays(cal)
             if d >= pd.Timestamp(args.start) and d in cal]

    H = args.horizon
    rows = []
    for d in dates:
        i = cal.get_loc(d)
        if i + H >= len(cal):
            continue
        px = close_panel.loc[d].reindex(cols).dropna()
        if membership_fn is not None:
            members = membership_fn(d)
            px = px[[c for c in px.index if c in members]]
        if len(px) < args.deciles * 2:
            continue
        fwd = close_panel.iloc[i + H][px.index] / px - 1
        # rank before qcut so ties can't collapse a bucket
        dec = pd.qcut(px.rank(method="first"), args.deciles, labels=False)
        for k in range(args.deciles):
            sel = fwd[dec == k].dropna()
            if len(sel):
                rows.append({"date": d, "decile": k + 1,
                             "fwd_pct": sel.mean() * 100,
                             "median_price": px[dec == k].median(),
                             "n": len(sel)})

    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"price_deciles_h{H}.csv", index=False)

    g = df.groupby("decile").agg(fwd=("fwd_pct", "mean"),
                                 median_price=("median_price", "median"))
    print(f"Nifty 250 forward {H}-day return by PRICE decile "
          f"(1=cheapest), {len(dates)} rebalance dates from {args.start}\n")
    print(f"{'decile':>7} {'median price':>13} {'mean fwd':>10}")
    for k, r in g.iterrows():
        print(f"{k:>7} {r['median_price']:13,.0f} {r['fwd']:9.2f}%")
    spread = g.loc[1, "fwd"] - g.loc[args.deciles, "fwd"]
    print(f"\ncheapest minus dearest: {spread:+.2f}pp per {H} days")

    df["year"] = df["date"].dt.year
    print(f"\nSame spread (D1 - D{args.deciles}) by year — is the tilt stable?")
    by_year = {}
    for y, gg in df.groupby("year"):
        a = gg[gg.decile == 1]["fwd_pct"].mean()
        b = gg[gg.decile == args.deciles]["fwd_pct"].mean()
        by_year[int(y)] = round(a - b, 2)
        flag = "  <-- REVERSED" if a - b < 0 else ""
        print(f"  {y}: {a-b:+6.2f}pp   (D1 {a:+6.2f}%  "
              f"D{args.deciles} {b:+6.2f}%){flag}")

    summary = {
        "horizon_days": H, "start": args.start,
        "n_rebalance_dates": len(dates),
        "by_decile": {int(k): {"median_price": round(r["median_price"]),
                               "fwd_pct": round(r["fwd"], 2)}
                      for k, r in g.iterrows()},
        "spread_pp": round(spread, 2),
        "spread_by_year_pp": by_year,
        "years_reversed": [y for y, v in by_year.items() if v < 0],
    }
    (OUT / f"price_deciles_h{H}_summary.json").write_text(
        json.dumps(summary, indent=2))
    print(f"\n[wrote] {OUT}/price_deciles_h{H}*.{'csv,json'}")


if __name__ == "__main__":
    main()
