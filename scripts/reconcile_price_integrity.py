"""Daily price-integrity guard — detects corporate-action cliffs in the
live price store and self-heals by deletion (the next fetch rebuilds
full adjusted history from Kite, which reproduces real events
identically and cures CA cliffs).

Runs BEFORE the fetch step in run_daily_pipeline.py, so a file deleted
here is rebuilt in the same pipeline run (a cliff created by today's
fetch is caught tomorrow). Only DEFINITIVE signatures heal (flip-flop
pair or >=40% step that snaps to a known CA ratio); large moves without
a definitive signature are reported for eyes, never touched.

Healed symbols are appended to the merged-rebase queue sidecar
(.merged_rebase_queue.txt in the price dir, persistent-volume safe) for
the merged-panel repair. Detection logic: data_pipeline/corporate_actions.py
(tests: tests/test_corporate_actions.py). History and research tools:
tasks/corporate_actions_fix/.

Usage: reconcile_price_integrity.py [--report-only] [--window 20]
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from data_pipeline.corporate_actions import (  # noqa: E402
    classify_cliffs, definitive_ca_mask, detect_cliffs,
)

LIVE_DIR = os.path.join(ROOT_DIR, "nse500_data")
QUEUE = os.path.join(LIVE_DIR, ".merged_rebase_queue.txt")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-only", action="store_true",
                    help="detect and report, but do not delete/queue")
    ap.add_argument("--window", type=int, default=20)
    args = ap.parse_args()

    flagged, watch = [], []
    for name in sorted(os.listdir(LIVE_DIR)):
        if not name.endswith("_day.csv"):
            continue
        sym = name[: -len("_day.csv")]
        df = pd.read_csv(os.path.join(LIVE_DIR, name), parse_dates=["date"])
        closes = df.set_index("date")["close"]
        tail_start = closes.index[-(args.window + 1):][0] if len(closes) else None
        cliffs = classify_cliffs(detect_cliffs(closes))
        if cliffs.empty:
            continue
        cliffs["definitive"] = definitive_ca_mask(cliffs)
        recent = cliffs[pd.to_datetime(cliffs["date"]) >= tail_start]
        for r in recent.itertuples():
            row = (sym, str(pd.Timestamp(r.date).date()), r.move_pct, r.label)
            (flagged if r.definitive else watch).append(row)

    print(f"[guard] scanned trailing {args.window} sessions of {LIVE_DIR}")
    if not flagged and not watch:
        print("[guard] clean")
        return 0
    for sym, d, mv, lab in flagged:
        print(f"[guard] DEFINITIVE {sym} {d} {mv:+.1f}% {lab}")
    for sym, d, mv, _ in watch:
        print(f"[guard] watch      {sym} {d} {mv:+.1f}% (not definitive — verify manually)")

    if flagged and not args.report_only:
        queued = set()
        if os.path.exists(QUEUE):
            with open(QUEUE) as f:
                queued = {ln.strip() for ln in f if ln.strip()}
        for sym in sorted({s for s, *_ in flagged}):
            path = os.path.join(LIVE_DIR, f"{sym}_day.csv")
            if os.path.exists(path):
                os.remove(path)
            queued.add(sym)
            print(f"[guard] healed {sym}: deleted live CSV (fetch step rebuilds "
                  "full adjusted history); queued for merged re-base")
        with open(QUEUE, "w") as f:
            f.write("\n".join(sorted(queued)) + "\n")
    elif flagged:
        print("[guard] report-only mode — no action taken")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
