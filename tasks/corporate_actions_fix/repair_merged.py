"""Path B repair (offline): rebuild a merged file from a clean live file
plus a re-based pre-seam history. No Kite token needed.

Per symbol:
  1. Require the live file to be clean (no CA-signature cliffs) — heal
     live first (guard --heal + refetch) if not.
  2. Compute the re-base factor as the median live/merged close ratio
     over their overlapping dates (refuses mixed-regime overlaps).
  3. Replace merged rows >= seam with live rows; multiply pre-seam
     prices by the factor and volume by 1/factor.
  4. Verify the result has no NEW cliffs at the seam.

Pre-seam cliffs older than the live era (e.g. ADANIENT 2015 demerger)
are NOT fixed here — Path A (refetch_history.py) or a manual factor in
corporate_actions.json covers those.

Usage:
  --symbols A,B,C | --from-queue | --from-inventory   [--apply]

Run:  .venv/bin/python tasks/corporate_actions_fix/repair_merged.py --from-inventory
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.corporate_actions_fix.ca_lib import (  # noqa: E402
    classify_cliffs, detect_cliffs, file_is_clean, seam_ratio,
)

LIVE_DIR = ROOT / "nse500_data"
MERGED_DIR = ROOT / "nse500_data_merged"
HERE = Path(__file__).resolve().parent
PRICE_COLS = ["open", "high", "low", "close"]


def repair(symbol: str, apply: bool) -> str:
    live_f = LIVE_DIR / f"{symbol}_day.csv"
    merged_f = MERGED_DIR / f"{symbol}_day.csv"
    if not live_f.exists():
        return "live_missing (healed but not refetched yet?)"
    if not merged_f.exists():
        return "merged_missing"
    live = pd.read_csv(live_f, parse_dates=["date"]).sort_values("date")
    merged = pd.read_csv(merged_f, parse_dates=["date"]).sort_values("date")
    if not file_is_clean(live.set_index("date")["close"]):
        return "live_dirty — heal live first"

    seam = live["date"].min()
    old_overlap = merged[merged["date"] >= seam].set_index("date")["close"]
    r = seam_ratio(old_overlap, live.set_index("date")["close"])
    if r is None:
        return "overlap_unstable — needs Path A refetch"

    pre = merged[merged["date"] < seam].copy()
    if abs(r - 1) > 0.005:
        for col in PRICE_COLS:
            pre[col] = pre[col] * r
        if "volume" in pre.columns:
            pre["volume"] = (pre["volume"] / r).round().astype("int64")
    rebuilt = pd.concat([pre, live], ignore_index=True).sort_values("date")

    # verify: no new cliff at the seam, live era matches live exactly
    check = rebuilt.set_index("date")["close"]
    win = check[(check.index >= seam - pd.Timedelta(days=10))
                & (check.index <= seam + pd.Timedelta(days=10))]
    seam_cliffs = classify_cliffs(detect_cliffs(win))
    seam_cliffs = seam_cliffs[seam_cliffs.label != "unclassified"]
    if len(seam_cliffs):
        return f"seam_check_failed ({seam_cliffs.iloc[0].label})"

    n_left = len(classify_cliffs(detect_cliffs(check))
                 .query("label != 'unclassified'"))
    msg = (f"rebase x{r:.4f}, pre-seam {len(pre)} rows, "
           f"{n_left} CA cliff(s) remain pre-seam")
    if not apply:
        return "dry_run: " + msg
    rebuilt.to_csv(merged_f, index=False)
    return "applied: " + msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols")
    ap.add_argument("--from-queue", action="store_true")
    ap.add_argument("--from-inventory", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    elif args.from_queue:
        q = HERE / "merged_rebase_queue.txt"
        symbols = sorted({ln.strip() for ln in q.read_text().splitlines()
                          if ln.strip()}) if q.exists() else []
    elif args.from_inventory:
        inv = pd.read_csv(HERE / "inventory.csv")
        symbols = sorted(inv[inv.definitive].symbol.unique())
    else:
        ap.error("need --symbols, --from-queue, or --from-inventory")

    print(f"{'Applying' if args.apply else 'Dry-run'} merged repair, "
          f"{len(symbols)} symbols")
    for sym in symbols:
        print(f"  {sym:14s} {repair(sym, args.apply)}")


if __name__ == "__main__":
    main()
