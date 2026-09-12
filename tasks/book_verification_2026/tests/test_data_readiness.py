"""Group F of TESTS_DATA.md — book-facing readiness: the store as scripts/rebuilt_books.py loads it (D-30..D-35)."""
from __future__ import annotations

import pandas as pd

from _store import current_members, master, pr_panels, scan, warn_count

MIN_OBS = 220            # the stricter of the two locked books (om25_v4); mm_v1 uses 219
RECENT_ENTRANT_SESSIONS = 300
NSE_SECTOR_COUNT = 21


def test_d30_panel_loader_loads_the_store_the_books_read():
    close, trade = pr_panels()
    sessions = scan().sessions
    assert close.index.equals(sessions), (f"D-30: the panel index is not the store session calendar "
                                          f"({len(close.index)} vs {len(sessions)} sessions)")
    assert close.index[-1] == sessions[-1], f"D-30: panel ends {close.index[-1].date()}, store ends {sessions[-1].date()}"
    empty = list(close.columns[close.isna().all()])
    assert not empty, f"D-30: {len(empty)} panel columns are entirely NaN: {empty[:8]}"
    assert close.shape == trade.shape, f"D-30: close panel {close.shape} and trade panel {trade.shape} disagree"


def test_d31_current_members_have_enough_history_or_are_recent_entrants():
    close, _ = pr_panels()
    cutoff = scan().sessions[-RECENT_ENTRANT_SESSIONS]
    short, entrants = [], []
    for sym in sorted(current_members()):
        if sym not in close.columns:
            short.append((sym, 0, "no panel column")); continue
        s = close[sym]
        obs = int(s.notna().sum())
        if obs >= MIN_OBS:
            continue
        first = s.first_valid_index()
        if first is not None and first >= cutoff:
            entrants.append((sym, obs, str(first.date())))
        else:
            short.append((sym, obs, str(first.date()) if first is not None else "never"))
    warn_count("D-31", f"current members not yet scoreable because they listed recently (min_obs {MIN_OBS}): {entrants}",
               len(entrants), cap=25)
    assert not short, (f"D-31: {len(short)} current Nifty 250 members have fewer than {MIN_OBS} observed closes without being recent "
                       f"entrants, so their price file is truncated: {short}")


def test_d32_current_members_all_have_a_sector_label():
    from data_pipeline.strategies.sectors import load_sector_map
    sectors = load_sector_map()
    members = current_members()
    missing = sorted(s for s in members if s not in sectors)
    assert not missing, (f"D-32: {len(missing)} current Nifty 250 members have no sector label, so the engine's sector_cap treats them "
                         f"as unconstrained: {missing}")
    labels = {sectors[s] for s in members}
    assert len(labels) <= NSE_SECTOR_COUNT, (f"D-32: {len(labels)} distinct sector labels across current members, expected at most "
                                             f"{NSE_SECTOR_COUNT}: {sorted(labels)}")


def test_d33_regime_series_computes_over_the_full_calendar():
    from data_pipeline.strategies.regime import roc_regime
    close, _ = pr_panels()
    reg = roc_regime(master() / "benchmarks/NIFTY_100.csv", 31, 3, close.index)
    assert len(reg) == len(close.index), f"D-33: regime series length {len(reg)} != calendar {len(close.index)}"
    assert int(reg.isna().sum()) == 0, (f"D-33: regime series has {int(reg.isna().sum())} NaN readings, which fillna(True) would mask "
                                        f"as bull")
    states = set(pd.Series(reg).astype(bool).unique())
    assert states == {True, False}, f"D-33: the regime never leaves state {states} — the bear branch of both books would be dead code"


def test_d34_no_current_member_price_series_is_stale():
    sc = scan()
    stale_file = master() / "qa/stale_tails.csv"
    known = set(pd.read_csv(stale_file)["symbol"]) if stale_file.exists() else set()
    latest = sc.sessions[-1]
    stale = [(s, str(pd.Timestamp(sc.summary.loc[s, "last"]).date())) for s in sorted(current_members())
             if s in sc.summary.index and pd.Timestamp(sc.summary.loc[s, "last"]) < latest and s not in known]
    assert not stale, (f"D-34: {len(stale)} current Nifty 250 members end before the store's latest session ({latest.date()}) and are "
                       f"not listed in qa/stale_tails.csv; the loader ffills, so the book would size on a stale quote: {stale[:10]}")


def test_d35_store_latest_session_is_recent():
    latest = scan().sessions[-1]
    today = pd.Timestamp.today().normalize()
    behind = len(pd.bdate_range(latest + pd.Timedelta(days=1), today)) if today > latest else 0
    warn_count("D-35", f"weekdays between the store's latest session ({latest.date()}) and today ({today.date()}) — a book run is only "
                       f"as current as the store", behind, cap=3)
