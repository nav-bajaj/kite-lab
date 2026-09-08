"""Second-pass symbol resolution for reconstructed ex-members.

The first pass (resolve_symbols.py) does exact normalised-name matching
against NSE's current constituent file and the NSE-cash rows of the Kite
instruments dump. It leaves 577 companies unmapped. Two fixable reasons:

  * the company is in the dump under BSE rather than NSE, and
  * Kite truncates and abbreviates names to ~30 characters
    ("NETWORK18 MEDIA & INV", "TAMILNADU NEWSPRT & PAPER", "JKUMAR INFR.LTD.")
    so an exact normalised match cannot fire.

The second reason needs token matching where a dump token may be a PREFIX of
the real word ("INV" for "Investments", "NEWSPRT" for "Newsprint"). That is
loose enough to produce false positives, so nothing here is auto-adopted:
this module scores candidates and the caller decides. A candidate that also
has a price file on disk is far more likely to be right, and is the only
kind worth acting on anyway.
"""
from __future__ import annotations

import csv
import os
import re
import sys

sys.path.insert(0, "lib")

INSTRUMENTS = "/Users/navdeep/kite-lab/data/instruments_full.csv"
PRICE_DIRS = [
    "/Users/navdeep/kite-lab/nse500_data",
    "/Users/navdeep/kite-lab/nse500_data_merged",
    "/Users/navdeep/Documents/stock_data/nse500_data_full",
    # ex-member backfill fetched for this task
    "/Users/navdeep/kite-lab/nse500_data_backfill",
    "/Users/navdeep/kite-lab/nse500_data_backfill_gdf",
]
# Deliberately short. "Corporation" and "India" are NOT dropped: stripping
# them turns "Corporation Bank" into "Bank" and "Indian Bank" into "Bank",
# which then match each other perfectly. They are different banks.
STOP = {"ltd", "limited", "the", "inc"}


def tokens(name: str) -> list[str]:
    name = name.lower().replace("&", " and ")
    parts = re.split(r"[^a-z0-9]+", name)
    return [p for p in parts if p and p not in STOP]


def price_symbols() -> set[str]:
    out = set()
    for d in PRICE_DIRS:
        try:
            for f in os.listdir(d):
                if f.endswith("_day.csv"):
                    out.add(f[: -len("_day.csv")])
        except OSError:
            continue
    return out


def instrument_rows() -> list[tuple[str, str, str]]:
    """(symbol, name, exchange) for cash equities on NSE and BSE."""
    rows = []
    for r in csv.DictReader(open(INSTRUMENTS, encoding="utf-8")):
        seg, exch = r.get("segment"), r.get("exchange")
        if (exch, seg) not in {("NSE", "NSE"), ("BSE", "BSE")}:
            continue
        sym = r["tradingsymbol"].strip()
        for series in ("-BE", "-BZ"):
            if sym.endswith(series):
                sym = sym[: -len(series)]
        rows.append((sym, r.get("name", "").strip(), exch))
    return rows


def _token_match(c: str, d: str) -> bool:
    """Does dump token `d` stand for company token `c`?

    Kite/BSE abbreviate by truncation ("INFRASTRUCTU", "NEWSPRT"), so a prefix
    counts - but only a long one. Short prefixes are what produced the wrong
    matches on the first pass: "MAN" is a prefix of "Mandhana", and a bare
    "D"/"B" is a prefix of almost anything.
    """
    if c == d:
        return True
    if len(d) >= 4 and c.startswith(d):
        return True
    return len(c) >= 4 and d.startswith(c)


def score(company: str, dump_name: str) -> float:
    """How well a dump name explains a company name, 0..1.

    Requires EVERY dump token to be accounted for and EVERY company token to
    be covered - a one-sided match is how "Corporation Bank" got mapped onto
    "Indian Bank". Single-token names must match exactly, since a lone
    abbreviation carries too little signal to identify a company.
    """
    ct, dt = tokens(company), tokens(dump_name)
    if not ct or not dt:
        return 0.0
    if len(dt) == 1 and dt[0] != (ct[0] if len(ct) == 1 else None):
        return 0.0
    remaining = list(ct)
    for d in dt:
        hit = next((c for c in remaining if _token_match(c, d)), None)
        if hit is None:
            return 0.0
        remaining.remove(hit)
    if remaining:
        return 0.0              # company words the dump name never explains
    return 1.0


def best_candidates(company: str, rows, have_prices, limit=3):
    scored = []
    for sym, name, exch in rows:
        s = score(company, name)
        if s <= 0:
            continue
        # a symbol we already hold prices for is much more likely correct
        scored.append((s + (0.15 if sym in have_prices else 0.0), s, sym, name, exch))
    scored.sort(reverse=True)
    return scored[:limit]
