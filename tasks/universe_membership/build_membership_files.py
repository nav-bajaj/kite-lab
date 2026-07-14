"""Seed data/static/*_membership.csv from old snapshots + 2026-07-14 NSE lists.

Seeding rule (tasks/universe_membership/PLAN.md): the pre-cutover universe
must equal the old snapshot exactly so the daily full-history recompute keeps
reproducing the published track record byte-for-byte.

  - symbols in old snapshot and new list  -> from=START, open-ended
  - symbols only in old snapshot          -> from=START, to=CUTOVER (dropped;
                                             grandfathered if currently held)
  - symbols only in new list              -> from=CUTOVER, open-ended
  - NSE renames (SYMBOL_ALIASES)          -> kept under OUR canonical symbol,
                                             note records the new NSE ticker
  - DUMMY* placeholder rows               -> excluded, warned

nifty50 has no old snapshot: seeded from=START (same current-members-
approximate-history convention as every other universe's pre-cutover seed;
research backtests on it carry the usual survivorship caveat).

Usage: python tasks/universe_membership/build_membership_files.py [--cutover 2026-07-15]
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
NEW_DIR = Path(__file__).resolve().parent / "data" / "nse_lists_2026-07-14"
STATIC = ROOT / "data" / "static"

START = "1900-01-01"

# our canonical symbol <- current NSE ticker (scripts/history_utils.SYMBOL_ALIASES)
CANONICAL = {"JSWDULUX": "AKZOINDIA", "LTM": "LTIM"}

PAIRS = [
    ("nse500", "nse500_universe.csv", "ind_nifty500list.csv"),
    ("nifty250", "nifty250_universe.csv", "ind_nifty250list.csv"),
    ("nifty100", "nifty100_universe.csv", "ind_nifty100list.csv"),
    ("nifty50", None, "ind_nifty50list.csv"),
]


def load_symbols(path: Path, canonicalize: bool) -> dict:
    """symbol -> company name; drops DUMMY placeholder rows."""
    df = pd.read_csv(path)
    out = {}
    for _, r in df.iterrows():
        sym = str(r["Symbol"]).strip()
        if sym.startswith("DUMMY"):
            print(f"  [skip] placeholder row {sym} in {path.name}")
            continue
        if canonicalize:
            sym = CANONICAL.get(sym, sym)
        out[sym] = str(r.get("Company Name", "")).strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutover", default="2026-07-15",
                    help="First date the refreshed membership applies "
                         "(must be >= the merge/deploy date)")
    args = ap.parse_args()
    cutover = pd.Timestamp(args.cutover).strftime("%Y-%m-%d")

    for uid, old_name, new_name in PAIRS:
        print(f"[{uid}]")
        new = load_symbols(NEW_DIR / new_name, canonicalize=True)
        rows = []
        if old_name is None:
            for sym, name in sorted(new.items()):
                rows.append((sym, START, "", f"nifty50 initial seed {cutover}"))
        else:
            old = load_symbols(STATIC / old_name, canonicalize=False)
            for sym in sorted(set(old) | set(new)):
                renote = ""
                if sym in CANONICAL.values():
                    nse_tick = {v: k for k, v in CANONICAL.items()}[sym]
                    renote = f"; NSE ticker now {nse_tick} (fetch alias)"
                if sym in old and sym in new:
                    rows.append((sym, START, "", renote.lstrip("; ")))
                elif sym in old:
                    rows.append((sym, START, cutover,
                                 f"dropped in {cutover} {uid} refresh"))
                else:
                    rows.append((sym, cutover, "",
                                 f"added in {cutover} {uid} refresh ({new[sym]})"))
        out = STATIC / f"{uid}_membership.csv"
        pd.DataFrame(rows, columns=["symbol", "effective_from",
                                    "effective_to", "note"]).to_csv(out, index=False)
        n_open = sum(1 for r in rows if r[2] == "")
        n_closed = len(rows) - n_open
        n_new = sum(1 for r in rows if r[1] == cutover)
        print(f"  wrote {out.relative_to(ROOT)}: {len(rows)} rows "
              f"({n_open} open, {n_closed} closing at cutover, {n_new} opening at cutover)")


if __name__ == "__main__":
    main()
