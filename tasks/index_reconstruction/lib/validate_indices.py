"""Checks for the three indices reconstructed backwards from today's list.

Each is verified three ways:
  1. the derived seed must be exactly the index's fixed size - a wrong seed
     shows up immediately because the count is an invariant;
  2. neither the backward derivation nor the forward replay may hit an event
     it cannot apply;
  3. the reconstruction must reproduce NSE's March 2022 factsheet, which is
     an independent document that neither source feeds.

The factsheet check compares SYMBOLS, so 2022-vintage tickers are bridged to
today's through ticker_vintage. Companies merged away since (HDFC into HDFC
Bank, MindTree into LTIMindtree, ICICI Securities delisted) have no tradeable
successor and are reported as unresolved rather than guessed.
"""
from __future__ import annotations

import csv, datetime, os, sys
sys.path.insert(0, "lib")
import build_index as bi
import resolve_symbols as rs
from parse_factsheet import symbols
from ticker_vintage import to_today

FACTSHEET_DIR = "/Users/navdeep/Downloads/indices_dataMar2022"
FILES = {"nifty50": "ind_nifty50list", "nifty100": "ind_nifty100list",
         "nifty250": "ind_niftylargemidcap250list"}
FACTSHEETS = {
    "nifty50": ["NIFTY_50_Mar2022.pdf"],
    "nifty100": ["NIFTY_100_Mar2022.pdf"],
    # LargeMidcap 250 is Nifty 100 + Nifty Midcap 150, which NSE publishes
    # as two factsheets rather than one
    "nifty250": ["NIFTY_100_Mar2022.pdf", "NIFTY_Midcap_150_Mar2022.pdf"],
}
ASOF = datetime.date(2022, 3, 31)
# Windows where the index legitimately carried one extra LINE rather than one
# extra company: Tata Motors' 'A' Ordinary (DVR) shares traded alongside the
# parent. Each index took the DVR in and out on its own dates, so the windows
# are per-index rather than shared.
DVR_WINDOWS = {
    "nifty50": [(datetime.date(2016, 4, 1), datetime.date(2017, 9, 29))],
    "nifty100": [(datetime.date(2016, 4, 1), datetime.date(2020, 6, 26)),
                 (datetime.date(2023, 9, 29), datetime.date(2024, 8, 30))],
    "nifty250": [(datetime.date(2016, 4, 1), datetime.date(2020, 6, 26)),
                 (datetime.date(2023, 9, 29), datetime.date(2024, 8, 30))],
}


def main() -> int:
    by_name, by_norm = rs.current_maps()
    by_instr = rs.instrument_map()
    fails = []
    for slug, (name, size) in bi.SPECS.items():
        cur = {bi.canonicalise(r["Company Name"].strip())
               for r in csv.DictReader(
                   open(f"data/raw/{FILES[slug]}_2026-09-08.csv",
                        encoding="utf-8-sig"))}
        events = bi.events_for(slug)
        seed, back = bi.derive_seed(slug, cur, events)
        seed_date = min(e["date"] for e in events) - datetime.timedelta(days=1)
        mem, timeline, fwd = bi.replay_forward(seed, events, seed_date)

        def expected(d, _slug=slug, _size=size):
            for lo, hi in DVR_WINDOWS.get(_slug, []):
                if lo <= d < hi:
                    return _size + 1
            return _size

        off = [(d, c) for d, c in timeline if c != expected(d)]

        at, _, _ = bi.replay_forward(seed, [e for e in events
                                            if e["date"] <= ASOF], seed_date)
        got, unresolved = set(), []
        for n, r in at.items():
            s = rs.resolve(n, r["symbol"], by_name, by_norm, by_instr)
            got.add(s) if s else unresolved.append(n)
        want = {to_today(s) for f in FACTSHEETS[slug]
                for s in symbols(os.path.join(FACTSHEET_DIR, f))}
        extra = sorted(got - want)
        missing = sorted(s for s in want - got)

        print(f"\n{name}")
        print(f"  seed {seed_date} = {len(seed)}/{size}"
              f"   back-problems {len(back)}   fwd-problems {len(fwd)}")
        print(f"  final {len(mem)}/{size}   dates off expected count {len(off)}")
        print(f"  Mar-2022 factsheet: {len(want)} constituents,"
              f" reconstruction resolved {len(got)}, unresolved {len(unresolved)}")
        print(f"    extra in reconstruction (must be 0): {extra}")
        print(f"    missing, all explained by unresolved: {missing}")

        if len(seed) != size:
            fails.append(f"{name}: seed {len(seed)} != {size}")
        if back or fwd:
            fails.append(f"{name}: replay problems {back[:2]}{fwd[:2]}")
        if off:
            fails.append(f"{name}: count anomalies {off[:3]}")
        if extra:
            fails.append(f"{name}: factsheet extras {extra}")
        if len(missing) != len(unresolved):
            fails.append(f"{name}: {len(missing)} missing vs "
                         f"{len(unresolved)} unresolved - not fully explained")

    print()
    if fails:
        for f in fails:
            print("FAIL:", f)
        return 1
    print("ALL INDEX CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
