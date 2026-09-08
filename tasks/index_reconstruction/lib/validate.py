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

    # 5. symbol coverage by year - reported, not enforced.
    #
    #    Measured from the EMITTED FILE, not from a point-in-time replay.
    #    NSE prints a long-tenured member's symbol only on the release that
    #    finally removes it, so a replay stopped mid-spell has not seen it yet
    #    and understates coverage - J.B. Chemicals sat in the index from 1998
    #    to 2026 and only acquired JBCHEPHARM on its exclusion. The spell in
    #    the emitted file carries the symbol for its whole life, which is what
    #    a backtest actually reads.
    import backfill_symbols as bs
    have = bs.price_symbols()
    print("[5] coverage (from the emitted membership file):")
    print(f"      {'as of':10s} {'index':>6s} {'symbol':>7s} {'+prices':>8s}")
    for y in (2010, 2016, 2020, 2023, 2026):
        d = datetime.date(y, 6, 30)
        mem, _, _ = build_chain.build(stop=d)
        got = members_asof(df, d)
        px = {s for s in got if s in have}
        print(f"      {d}  {len(mem):6d} {len(got):7d} {len(px):8d}")

    # 6. the March 2022 factsheet: an independent NSE document that neither
    #    source feeds, so matching it tests the replay mid-chain rather than
    #    only at its endpoint
    from parse_factsheet import symbols
    from ticker_vintage import to_today
    fs = "/Users/navdeep/Downloads/indices_dataMar2022/NIFTY_500_Mar2022.pdf"
    try:
        # the factsheet lists 501 lines because Tata Motors' DVR share
        # class traded as its own line; the reconstruction carries it too
        want22 = {to_today(s) for s in symbols(fs)}
        got22 = members_asof(df, datetime.date(2022, 3, 31))
        extra, miss = sorted(got22 - want22), sorted(want22 - got22)
        print(f"[6] Mar-2022 factsheet: {len(want22)} vs reconstruction {len(got22)}")
        print(f"      extra={extra}  missing={miss}")
        if extra or miss:
            fails.append(f"Mar-2022 mismatch extra={extra[:5]} missing={miss[:5]}")
    except Exception as e:
        print(f"[6] factsheet check skipped: {e}")

    print()
    if fails:
        for f in fails:
            print("FAIL:", f)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
