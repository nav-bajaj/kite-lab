"""Daily price-integrity guard (candidate for the production pipeline).

Scans the trailing window of every live CSV for corporate-action
signatures. Report-only by default. With --heal, deletes flagged live
CSVs — the next fetch re-downloads full adjusted history, which
reproduces real crashes identically and cures CA cliffs — and appends
the symbols to merged_rebase_queue.txt for the merged-panel repair.

Intended pipeline slot (after founder sign-off): between the data fetch
and apply_corporate_actions in scripts/run_daily_pipeline.py.

Run:  .venv/bin/python tasks/corporate_actions_fix/reconcile_price_integrity.py [--heal] [--window 20]
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
    classify_cliffs, definitive_ca_mask, detect_cliffs,
)

LIVE_DIR = ROOT / "nse500_data"
QUEUE = Path(__file__).resolve().parent / "merged_rebase_queue.txt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heal", action="store_true",
                    help="delete flagged live CSVs (refetch self-heals) "
                         "and queue symbols for merged re-base")
    ap.add_argument("--window", type=int, default=20,
                    help="trailing sessions to scan (default 20)")
    args = ap.parse_args()

    flagged, crashes = [], []
    for f in sorted(LIVE_DIR.glob("*_day.csv")):
        sym = f.name[: -len("_day.csv")]
        df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        tail = df["close"].iloc[-(args.window + 1):]
        # detect over full history (flip-flop partners can predate the
        # window) but only act on cliffs inside the trailing window
        c = classify_cliffs(detect_cliffs(df["close"]))
        if c.empty:
            continue
        c["definitive"] = definitive_ca_mask(c)
        recent = c[pd.to_datetime(c["date"]) >= tail.index[0]]
        for r in recent.itertuples():
            row = (sym, str(r.date.date()), r.move_pct, r.label)
            (flagged if r.definitive else crashes).append(row)

    print(f"[guard] scanned {args.window} trailing sessions")
    if not flagged and not crashes:
        print("[guard] clean — no cliffs in the trailing window")
        return
    if flagged:
        print(f"[guard] {len(flagged)} CA-signature cliffs:")
        for sym, d, mv, lab in flagged:
            print(f"  {sym:14s} {d}  {mv:+.1f}%  {lab}")
    if crashes:
        print(f"[guard] {len(crashes)} large moves not definitively CA "
              "(real events, demergers, or isolated ratio-matches — check manually):")
        for sym, d, mv, _ in crashes:
            print(f"  {sym:14s} {d}  {mv:+.1f}%")

    if args.heal and flagged:
        syms = sorted({s for s, *_ in flagged})
        queued = set()
        if QUEUE.exists():
            queued = {ln.strip() for ln in QUEUE.read_text().splitlines() if ln.strip()}
        for sym in syms:
            (LIVE_DIR / f"{sym}_day.csv").unlink(missing_ok=True)
            queued.add(sym)
            print(f"[heal] deleted live CSV for {sym} (refetch will restore adjusted)")
        QUEUE.write_text("\n".join(sorted(queued)) + "\n")
        print(f"[heal] {len(syms)} symbols queued for merged re-base -> {QUEUE.name}")
    elif flagged:
        print("[guard] report-only (pass --heal to act)")


if __name__ == "__main__":
    main()
