"""End-to-end checks on the reconstructed Nifty 500 history.

Run after any change to the parser, the rename tables or the source data.
Every check is a property NSE's own published data must satisfy, so a
failure means the reconstruction has drifted from the record rather than
that a threshold needs loosening.
"""
from __future__ import annotations

import csv, datetime, json, sys
from pathlib import Path

sys.path.insert(0, "lib")
sys.path.insert(0, "/Users/navdeep/kite-lab/scripts")
import build_chain
import resolve_symbols as rs
from universe_membership import load_membership, members_asof

TODAY = datetime.date(2026, 9, 8)
CURRENT = "data/raw/ind_nifty500list_2026-09-08.csv"
MEMBERSHIP = "data/nse500_membership_reconstructed.csv"

# The index carries an extra line whenever a second share class or a
# demerger placeholder sits alongside its parent company.
KNOWN_501 = [
    (datetime.date(2016, 4, 1), datetime.date(2024, 8, 30),
     "Tata Motors 'A' Ordinary (DVR) traded as a second line"),
    (datetime.date(2026, 9, 7), None,
     "DUMMYHEG zero-price placeholder for the HEG graphite demerger"),
]


def _expected(d: datetime.date) -> int:
    for lo, hi, _ in KNOWN_501:
        if lo <= d and (hi is None or d < hi):
            return 501
    return 500


def main() -> int:
    fails = []

    # 1. every press release balances: the Nifty 500 is a fixed-size index,
    #    so a review that removes N names must add N.
    rels = json.load(open("data/pr_nifty500_changes.json"))
    imbalanced = [r for r in rels if len(r["excluded"]) != len(r["included"])]
    print(f"[1] press releases parsed        : {len(rels)}")
    print(f"    imbalanced (must be 0)       : {len(imbalanced)}")
    if imbalanced:
        fails.append(f"imbalanced releases: {[r['file'] for r in imbalanced]}")

    # 2. the replay never tries to remove a non-member or add a duplicate
    members, timeline, problems = build_chain.build(stop=TODAY)
    print(f"[2] replay problems (must be 0)  : {len(problems)}")
    if problems:
        fails.append(f"replay problems: {problems[:5]}")

    # 3. constituent count holds at 500 except for the documented spells
    bad = [(d, c) for d, c in timeline if c != _expected(d)]
    print(f"[3] dates off expected count     : {len(bad)}")
    if bad:
        fails.append(f"count anomalies: {bad[:5]}")

    # 4. the emitted file, read by the PRODUCTION loader, reproduces the
    #    published constituent list exactly
    df = load_membership(Path(MEMBERSHIP))
    got = members_asof(df, TODAY)
    cur = list(csv.DictReader(open(CURRENT, encoding="utf-8-sig")))
    want = {r["Symbol"].strip() for r in cur} - {"DUMMYHEG"}
    print(f"[4] members_asof(today)          : {len(got)} vs published {len(want)}")
    if got != want:
        fails.append(f"missing={sorted(want - got)[:5]} extra={sorted(got - want)[:5]}")

    # 5. symbol coverage by year - reported, not enforced; resolution decays
    #    going back because companies that left pre-2020 were never printed
    #    with a symbol and many are delisted
    by_name, by_norm = rs.current_maps()
    by_instr = rs.instrument_map()
    print("[5] symbol coverage:")
    for y in (2010, 2016, 2020, 2023, 2026):
        mem, _, _ = build_chain.build(stop=datetime.date(y, 6, 30))
        k = sum(1 for n, r in mem.items()
                if rs.resolve(n, r["symbol"], by_name, by_norm, by_instr))
        print(f"      {y}: {k}/{len(mem)} ({k / len(mem) * 100:.0f}%)")

    print()
    if fails:
        for f in fails:
            print("FAIL:", f)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
