"""Attach an NSE trading symbol to each reconstructed member.

Symbols come from three places, in order of authority:
  1. the press release that added or removed the company (2020 onwards, where
     NSE prints name AND symbol);
  2. SURVIVOR_IDENTITY, for companies renamed while continuously a member;
  3. a name match against NSE's current constituent file;
  4. a name match against the Kite NSE instruments dump, which reaches
     companies that left the index but are still listed and tradeable;
  5. BACKFILL_SYMBOLS, the reviewed second-pass table (rename chasing plus
     strict token matching against NSE *and* BSE dump rows).

Companies that left the index before the press releases start carrying
symbols (roughly pre-2020) and are not in today's list cannot be resolved
this way - most are delisted or merged and have no tradeable symbol at all.
"""
from __future__ import annotations

import csv
import re
import sys

sys.path.insert(0, "lib")
from renames import SURVIVOR_IDENTITY
from backfill_map import BACKFILL_SYMBOLS

CURRENT = "data/raw/ind_nifty500list_2026-09-08.csv"
INSTRUMENTS = "/Users/navdeep/kite-lab/data/instruments_full.csv"


def _norm(t: str) -> str:
    t = t.lower().replace("&", " and ")
    t = re.sub(r"\b(ltd|limited|co|company|corporation|corp|the|inc)\b", " ", t)
    return re.sub(r"[^a-z0-9]", "", t)


def instrument_map():
    """Normalised company name -> trading symbol for NSE cash equities.

    Kite prints short upper-case names ("AARTI INDUSTRIES") which normalise
    onto NSE's index-file names ("Aarti Industries Ltd.") once the suffixes
    are stripped. Ambiguous names (the same normalised key on more than one
    symbol) are dropped rather than guessed.
    """
    out: dict = {}
    dup = set()
    try:
        rows = csv.DictReader(open(INSTRUMENTS, encoding="utf-8"))
    except OSError:
        return {}
    for r in rows:
        if r.get("exchange") != "NSE" or r.get("segment") != "NSE":
            continue
        k = _norm(r.get("name", ""))
        if not k:
            continue
        sym = r["tradingsymbol"].strip()
        # Kite appends the NSE series for non-EQ scrips ("3IINFOLTD-BE");
        # price files are keyed on the bare symbol. Only -BE/-BZ are series
        # markers - BAJAJ-AUTO and NAM-INDIA are real symbols.
        for series in ("-BE", "-BZ"):
            if sym.endswith(series):
                sym = sym[: -len(series)]
        if k in out and out[k] != sym:
            dup.add(k)
        out[k] = sym
    for k in dup:
        out.pop(k, None)
    return out


CURRENT_FILES = [
    "data/raw/ind_nifty500list_2026-09-08.csv",
    "data/raw/ind_nifty50list_2026-09-08.csv",
    "data/raw/ind_nifty100list_2026-09-08.csv",
    "data/raw/ind_niftylargemidcap250list_2026-09-08.csv",
]


def current_maps():
    rows = []
    for f in CURRENT_FILES:
        try:
            rows += list(csv.DictReader(open(f, encoding="utf-8-sig")))
        except OSError:
            continue
    by_name = {r["Company Name"].strip(): r["Symbol"].strip() for r in rows}
    by_norm = {_norm(n): s for n, s in by_name.items()}
    return by_name, by_norm


def resolve_with_source(name, symbol, by_name, by_norm, by_instr=None):
    """-> (symbol, how_it_was_resolved). symbol is None when unresolved."""
    if name in SURVIVOR_IDENTITY:
        return SURVIVOR_IDENTITY[name], "survivor-rename"
    if symbol:
        return symbol, "press-release"
    if name in by_name:
        return by_name[name], "current-list"
    n = _norm(name)
    if n in by_norm:
        return by_norm[n], "current-list"
    if n in (by_instr or {}):
        return by_instr[n], "kite-dump"
    if name in BACKFILL_SYMBOLS:
        return BACKFILL_SYMBOLS[name], "backfill-map"
    return None, "unresolved"


def resolve(name, symbol, by_name, by_norm, by_instr=None):
    return resolve_with_source(name, symbol, by_name, by_norm, by_instr)[0]
