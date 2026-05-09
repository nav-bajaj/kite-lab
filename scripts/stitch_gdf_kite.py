"""Stitch GDF historical [2009-2019] + Kite live [2020-now] into a unified panel.

GDF and Kite differ in how they handle corporate actions (e.g. GDF adjusted
the RIL Jio Financial demerger retroactively; Kite did not). Naively
concatenating creates a price discontinuity at the boundary.

Fix: rescale GDF prices by the ratio (kite_first_close / gdf_overlap_close)
so the two series join continuously. We use the **most recent overlapping
trading day** present in both sources as the anchor — typically a date
in the first week of January 2020, since GDF reaches 2019-12-30 and
Kite usually starts 2020-01-01.

Output: nse500_data_merged/{SYM}_day.csv with same schema as Kite files.

Usage:
    python scripts/stitch_gdf_kite.py
    python scripts/stitch_gdf_kite.py --boundary-jump-warn 5  # warn if >5% gap remains

Reports symbols where the rescale anchor needed >2% adjustment (signals
likely corporate actions handled differently by the two sources).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KITE_DIR = ROOT / "nse500_data"
GDF_DIR = ROOT / "nse500_data_historical"
OUT_DIR = ROOT / "nse500_data_merged"

OHLCV = ["open", "high", "low", "close", "volume"]


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = df["date"].dt.tz_localize(None).dt.normalize()
    return df.sort_values("date").reset_index(drop=True)


def stitch_one(symbol: str, warn_pct: float) -> dict:
    kite = load_csv(KITE_DIR / f"{symbol}_day.csv")
    gdf = load_csv(GDF_DIR / f"{symbol}_day.csv")

    if kite.empty and gdf.empty:
        return {"symbol": symbol, "status": "no_data"}

    if gdf.empty:
        # nothing to stitch; just copy kite
        kite.to_csv(OUT_DIR / f"{symbol}_day.csv", index=False,
                    date_format="%Y-%m-%d")
        return {"symbol": symbol, "status": "kite_only", "kite_rows": len(kite)}

    if kite.empty:
        gdf.to_csv(OUT_DIR / f"{symbol}_day.csv", index=False,
                   date_format="%Y-%m-%d")
        return {"symbol": symbol, "status": "gdf_only", "gdf_rows": len(gdf)}

    kite_first = kite["date"].min()
    # Use GDF rows strictly before the first Kite date. If they overlap, find
    # the most recent shared date and use it as the rescale anchor.
    overlap = gdf.merge(kite[["date", "close"]], on="date",
                        suffixes=("_gdf", "_kite"))
    if not overlap.empty:
        anchor = overlap.iloc[-1]
        rescale = anchor["close_kite"] / anchor["close_gdf"]
        anchor_date = anchor["date"]
    else:
        # No date overlap. Use kite first close vs gdf last close.
        kite_first_close = kite.iloc[0]["close"]
        gdf_last_close = gdf.iloc[-1]["close"]
        rescale = kite_first_close / gdf_last_close
        anchor_date = gdf.iloc[-1]["date"]

    rescale_pct = (rescale - 1.0) * 100

    pre = gdf[gdf["date"] < kite_first].copy()
    if pre.empty:
        # all GDF data is on/after Kite first date; fall back to Kite only
        kite.to_csv(OUT_DIR / f"{symbol}_day.csv", index=False,
                    date_format="%Y-%m-%d")
        return {"symbol": symbol, "status": "no_pre_history",
                "kite_rows": len(kite), "rescale_pct": 0.0}

    for col in ("open", "high", "low", "close"):
        if col in pre.columns:
            pre[col] = pre[col] * rescale

    cols = ["date"] + [c for c in OHLCV if c in kite.columns or c in pre.columns]
    pre = pre[[c for c in cols if c in pre.columns]]
    kite_keep = kite[[c for c in cols if c in kite.columns]]
    merged = pd.concat([pre, kite_keep], ignore_index=True)
    merged = merged.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{symbol}_day.csv"
    merged.to_csv(out_path, index=False, date_format="%Y-%m-%d")

    # boundary jump check (post-rescale)
    if not pre.empty:
        last_pre = pre.iloc[-1]["close"]
        first_kite = kite.iloc[0]["close"]
        boundary_pct = (first_kite / last_pre - 1.0) * 100
    else:
        boundary_pct = 0.0

    return {
        "symbol": symbol,
        "status": "stitched",
        "merged_rows": len(merged),
        "kite_rows": len(kite),
        "gdf_rows_used": len(pre),
        "anchor_date": anchor_date.date(),
        "rescale_pct": rescale_pct,
        "boundary_pct": boundary_pct,
        "warn": abs(rescale_pct) > warn_pct,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boundary-jump-warn", type=float, default=2.0,
                    help="Warn when rescale > this percent")
    ap.add_argument("--symbols", nargs="*", default=None)
    args = ap.parse_args()

    if args.symbols:
        symbols = args.symbols
    else:
        gdf_syms = {p.stem.replace("_day", "") for p in GDF_DIR.glob("*_day.csv")}
        kite_syms = {p.stem.replace("_day", "") for p in KITE_DIR.glob("*_day.csv")}
        symbols = sorted(gdf_syms | kite_syms)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for sym in symbols:
        try:
            r = stitch_one(sym, args.boundary_jump_warn)
        except Exception as e:
            r = {"symbol": sym, "status": f"error: {e}"}
        rows.append(r)

    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_DIR / "_stitch_summary.csv", index=False)

    n = len(summary)
    by_status = summary["status"].value_counts().to_dict()
    print(f"\n[stitch] {n} symbols  status={by_status}")
    if "rescale_pct" in summary.columns:
        warn_rows = summary[summary.get("warn", False) == True]
        if not warn_rows.empty:
            print(f"\n[warn] {len(warn_rows)} symbols with rescale > {args.boundary_jump_warn}% "
                  "(likely post-2020 corporate action handled differently by GDF vs Kite)")
            print(warn_rows[["symbol", "rescale_pct", "anchor_date"]]
                  .sort_values("rescale_pct", key=abs, ascending=False)
                  .head(20).to_string(index=False))


if __name__ == "__main__":
    main()
