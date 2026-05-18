"""Stitch indices_data_historical/ (GDF 2009-2019) + indices_data/ (Kite 2020+)
into a unified panel at indices_data_merged/.

Same rescale-anchored approach as stitch_gdf_kite.py — find the most
recent overlapping trading day and rescale the historical series to
match the post-2020 file's level on that date. For indices the
methodology shouldn't introduce big rescales (no corporate-action
adjustments at the index level), but small differences in calculation
(e.g., total-return vs price-return treatment) can produce step changes
that would corrupt 200-DMA signals if not fixed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HIST_DIR = ROOT / "indices_data_historical"
DEFAULT_KITE_DIR = ROOT / "indices_data"
DEFAULT_OUT_DIR = ROOT / "indices_data_merged"

OHLCV = ["open", "high", "low", "close", "volume"]


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = df["date"].dt.tz_localize(None).dt.normalize()
    return df.sort_values("date").reset_index(drop=True)


def stitch_one(stem: str, *, hist_dir: Path, kite_dir: Path,
                out_dir: Path, warn_pct: float) -> dict:
    hist = load_csv(hist_dir / f"{stem}.csv")
    kite = load_csv(kite_dir / f"{stem}.csv")

    if hist.empty and kite.empty:
        return {"index": stem, "status": "no_data"}

    if hist.empty:
        kite.to_csv(out_dir / f"{stem}.csv", index=False, date_format="%Y-%m-%d")
        return {"index": stem, "status": "kite_only", "kite_rows": len(kite)}

    if kite.empty:
        hist.to_csv(out_dir / f"{stem}.csv", index=False, date_format="%Y-%m-%d")
        return {"index": stem, "status": "hist_only", "hist_rows": len(hist)}

    kite_first = kite["date"].min()
    overlap = hist.merge(kite[["date", "close"]], on="date",
                          suffixes=("_hist", "_kite"))
    if not overlap.empty:
        anchor = overlap.iloc[-1]
        rescale = anchor["close_kite"] / anchor["close_hist"]
        anchor_date = anchor["date"]
    else:
        kite_first_close = kite.iloc[0]["close"]
        hist_last_close = hist.iloc[-1]["close"]
        rescale = kite_first_close / hist_last_close
        anchor_date = hist.iloc[-1]["date"]

    rescale_pct = (rescale - 1.0) * 100

    pre = hist[hist["date"] < kite_first].copy()
    if pre.empty:
        kite.to_csv(out_dir / f"{stem}.csv", index=False, date_format="%Y-%m-%d")
        return {"index": stem, "status": "no_pre_history",
                "kite_rows": len(kite), "rescale_pct": 0.0}

    for col in ("open", "high", "low", "close"):
        if col in pre.columns:
            pre[col] = pre[col] * rescale

    cols = ["date"] + [c for c in OHLCV if c in kite.columns or c in pre.columns]
    pre = pre[[c for c in cols if c in pre.columns]]
    kite_keep = kite[[c for c in cols if c in kite.columns]]
    merged = pd.concat([pre, kite_keep], ignore_index=True)
    merged = merged.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_dir / f"{stem}.csv", index=False, date_format="%Y-%m-%d")

    return {
        "index": stem,
        "status": "stitched",
        "merged_rows": len(merged),
        "kite_rows": len(kite),
        "hist_rows_used": len(pre),
        "anchor_date": anchor_date.date(),
        "rescale_pct": round(rescale_pct, 4),
        "warn": abs(rescale_pct) > warn_pct,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hist-dir", type=Path, default=DEFAULT_HIST_DIR,
                    help=f"Historical source dir (default: {DEFAULT_HIST_DIR})")
    ap.add_argument("--kite-dir", type=Path, default=DEFAULT_KITE_DIR,
                    help=f"Kite source dir (default: {DEFAULT_KITE_DIR})")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                    help=f"Stitched output dir (default: {DEFAULT_OUT_DIR})")
    ap.add_argument("--warn", type=float, default=2.0,
                    help="Warn when rescale > this percent")
    ap.add_argument("--stems", nargs="*", default=None)
    args = ap.parse_args()

    hist_dir, kite_dir, out_dir = args.hist_dir, args.kite_dir, args.out_dir
    print(f"[stitch] hist-dir = {hist_dir}")
    print(f"[stitch] kite-dir = {kite_dir}")
    print(f"[stitch] out-dir  = {out_dir}")

    if args.stems:
        stems = args.stems
    else:
        hist_stems = {p.stem for p in hist_dir.glob("*.csv")} if hist_dir.exists() else set()
        kite_stems = {p.stem for p in kite_dir.glob("*.csv")} if kite_dir.exists() else set()
        stems = sorted(hist_stems | kite_stems)

    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for stem in stems:
        try:
            r = stitch_one(stem, hist_dir=hist_dir, kite_dir=kite_dir,
                           out_dir=out_dir, warn_pct=args.warn)
        except Exception as e:
            r = {"index": stem, "status": f"error: {e}"}
        rows.append(r)

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "_stitch_summary.csv", index=False)

    n = len(summary)
    by_status = summary["status"].value_counts().to_dict()
    print(f"\n[stitch] {n} indices  status={by_status}")
    if "rescale_pct" in summary.columns:
        warn_rows = summary[summary.get("warn", False) == True]
        if not warn_rows.empty:
            print(f"\n[warn] {len(warn_rows)} indices with rescale > {args.warn}%:")
            print(warn_rows[["index", "rescale_pct", "anchor_date"]]
                  .sort_values("rescale_pct", key=abs, ascending=False)
                  .head(20).to_string(index=False))


if __name__ == "__main__":
    main()
