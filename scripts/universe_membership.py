"""Effective-dated universe membership.

Replaces the anachronistic snapshot semantics of data/static/*_universe.csv
for the portfolio engines: a stock is *entry-eligible* on signal date d iff
it has a membership row with effective_from <= d < effective_to (open-ended
when effective_to is blank). Rows are append-only; index reconstitutions add
new rows instead of editing history, so daily full-history recomputes keep
reproducing the published track record.

Grandfather rule (decided 2026-07-14): membership gates NEW ENTRIES only.
A position opened while the stock was a member exits by portfolio logic
(rank/min-hold/stops), never by the membership change itself. The engine
implements this via run_strategy(membership_fn=...): the per-date ranking is
filtered to members(d) | current holdings, and entrants must be members.

File schema (data/static/<universe>_membership.csv):
    symbol,effective_from,effective_to,note
    AKUMS,1900-01-01,2026-07-15,dropped in 2026-07 NSE500 refresh
    CPPLUS,2026-07-15,,added in 2026-07 NSE500 refresh (Aditya Infotech)

Symbols are OUR canonical symbols (matching price-file names); when NSE
renames a ticker the fetch layer aliases it (scripts/history_utils
.SYMBOL_ALIASES) and the membership row carries a note, so history stays
continuous under one symbol.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SCHEMA_COLS = ["symbol", "effective_from", "effective_to", "note"]


def load_membership(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in SCHEMA_COLS[:3] if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing membership columns {missing}")
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["effective_from"] = pd.to_datetime(df["effective_from"])
    df["effective_to"] = pd.to_datetime(df["effective_to"])  # NaT = open
    if df["effective_from"].isna().any():
        bad = df.loc[df["effective_from"].isna(), "symbol"].tolist()
        raise ValueError(f"{path}: rows without effective_from: {bad}")
    closed = df["effective_to"].notna()
    if (df.loc[closed, "effective_to"] <= df.loc[closed, "effective_from"]).any():
        raise ValueError(f"{path}: effective_to must be > effective_from")
    return df


def all_ever_members(df: pd.DataFrame) -> set:
    """Every symbol with any membership window — the score-panel universe."""
    return set(df["symbol"])


def members_asof(df: pd.DataFrame, asof) -> set:
    """Symbols entry-eligible on `asof` (from inclusive, to exclusive)."""
    d = pd.Timestamp(asof)
    open_ended = df["effective_to"].isna()
    live = (df["effective_from"] <= d) & (open_ended | (df["effective_to"] > d))
    return set(df.loc[live, "symbol"])


def make_membership_fn(df: pd.DataFrame):
    """Return callable(date) -> frozenset for run_strategy(membership_fn=...).

    Membership changes are rare (a handful of cutover dates), so cache the
    member set per unique boundary interval rather than per date.
    """
    boundaries = sorted(
        set(df["effective_from"]) | set(df["effective_to"].dropna())
    )
    cache: dict = {}

    def membership_fn(date) -> frozenset:
        d = pd.Timestamp(date)
        # interval key: index of the last boundary <= d
        lo, hi = 0, len(boundaries)
        while lo < hi:
            mid = (lo + hi) // 2
            if boundaries[mid] <= d:
                lo = mid + 1
            else:
                hi = mid
        key = lo
        if key not in cache:
            cache[key] = frozenset(members_asof(df, d))
        return cache[key]

    return membership_fn
