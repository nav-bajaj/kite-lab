"""Group D of TESTS_DATA.md — point-in-time index membership (D-20..D-25)."""
from __future__ import annotations

import pandas as pd

from _store import master, membership, scan, warn_count

TARGETS = {"nifty250": 250, "nse500": 500, "nifty100": 100, "nifty50": 50}
# Bands measured on the 2026-09-12 store: the reconstruction's 2006-08 spells are the loosest (nse500 reaches 493).
BANDS = {"nifty250": 5, "nse500": 8, "nifty100": 2, "nifty50": 2}
FAR = pd.Timestamp("2099-12-31")
HISTORY_START = pd.Timestamp("2006-01-02")     # the reconstruction is only claimed exact from 2006


def _counts(df: pd.DataFrame, sessions: pd.DatetimeIndex) -> pd.Series:
    f = df["effective_from"].values.astype("datetime64[ns]")
    t = df["effective_to"].fillna(FAR).values.astype("datetime64[ns]")
    s = sessions.values.astype("datetime64[ns]")
    return pd.Series(((f[None, :] <= s[:, None]) & (t[None, :] > s[:, None])).sum(axis=1), index=sessions)


def test_d20_membership_files_load_through_the_production_loader():
    mem = membership()
    assert set(mem) == set(TARGETS), f"D-20: membership files present {sorted(mem)}, expected {sorted(TARGETS)}"
    for idx, df in mem.items():
        assert not df.empty and df["effective_from"].notna().all(), f"D-20: {idx} has rows without effective_from"


def test_d21_no_symbol_holds_overlapping_membership_windows():
    for idx, df in membership().items():
        bad = []
        for sym, g in df.assign(_to=df["effective_to"].fillna(FAR)).sort_values("effective_from").groupby("symbol"):
            a = g["effective_from"].values; b = g["_to"].values
            if len(g) > 1 and (a[1:] < b[:-1]).any():
                bad.append(sym)
        assert not bad, f"D-21: {idx} has {len(bad)} symbols with overlapping windows (double-counted members): {bad[:8]}"


def test_d22_nifty250_holds_exactly_250_members_on_every_recent_session():
    recent = scan().sessions[-250:]
    cnt = _counts(membership()["nifty250"], recent)
    off = cnt[cnt != 250]
    assert off.empty, (f"D-22: the Nifty 250 point-in-time file is off target on {len(off)} of the last 250 sessions: "
                       f"{[(str(d.date()), int(v)) for d, v in list(off.items())[:8]]}")


def test_d23_member_counts_stay_within_band_over_full_history():
    sessions = scan().sessions
    sessions = sessions[sessions >= HISTORY_START]
    report, off_total, breach = [], 0, []
    for idx, target in TARGETS.items():
        cnt = _counts(membership()[idx], sessions)
        dev = (cnt - target).abs()
        off = cnt[cnt != target]
        by_year = off.groupby(off.index.year).size().to_dict()
        report.append(f"{idx}: max deviation {int(dev.max())} (band {BANDS[idx]}), {len(off)} off-target sessions, by year {by_year}")
        off_total += len(off)
        if dev.max() > BANDS[idx]:
            breach.append((idx, int(dev.max()), [(str(d.date()), int(cnt[d])) for d in dev.sort_values().index[-4:]]))
    assert not breach, f"D-23: member counts outside the measured band (index, worst deviation, worst sessions): {breach}"
    warn_count("D-23", "sessions where a point-in-time member count is off target — " + " | ".join(report), off_total, cap=12_000)


def test_d24_every_member_has_a_price_file_covering_its_window():
    sc = scan()
    store_first, store_last = sc.sessions[0], sc.sessions[-1]
    report, warn_total = [], 0
    for idx, df in membership().items():
        missing, uncovered = [], []
        for sym, g in df.groupby("symbol"):
            if sym not in sc.summary.index:
                if (g["effective_to"].fillna(FAR) > store_first).any():
                    missing.append(sym)
                continue
            first, last = pd.Timestamp(sc.summary.loc[sym, "first"]), pd.Timestamp(sc.summary.loc[sym, "last"])
            for r in g.itertuples():
                lo = max(r.effective_from, store_first)
                hi = min(r.effective_to if pd.notna(r.effective_to) else store_last, store_last)
                if lo >= hi:
                    continue
                if first > lo + pd.Timedelta(days=10) or last < hi - pd.Timedelta(days=10):
                    uncovered.append((sym, str(lo.date()), str(hi.date()), str(first.date()), str(last.date())))
        if idx == "nifty250":
            assert not missing, f"D-24: {len(missing)} Nifty 250 members have no adjusted_pr file: {missing[:10]}"
            assert not uncovered, (f"D-24: {len(uncovered)} Nifty 250 membership windows are not covered by the symbol's price file, so "
                                   f"the ranked universe was short of 250 names for those spells "
                                   f"(symbol, window start, window end, file first, file last): {uncovered[:8]}")
        else:
            report.append(f"{idx}: {len(missing)} members with no price file {missing[:6]}, {len(uncovered)} windows uncovered")
            warn_total += len(missing) + len(uncovered)
    warn_count("D-24", "membership rows the store has no prices for — " + " | ".join(report), warn_total, cap=60)


def test_d25_effective_dates_and_renames_are_coherent():
    sc = scan()
    sessions = set(sc.sessions)
    non_session = 0
    for df in membership().values():
        for col in ("effective_from", "effective_to"):
            d = df[col].dropna()
            non_session += int(sum(1 for x in d if x >= sc.sessions[0] and x not in sessions))
    changes = pd.read_csv(master() / "symbol_changes.csv", parse_dates=["date"])
    overlaps = []
    for idx, df in membership().items():
        by_sym = {s: g.assign(_to=g["effective_to"].fillna(FAR)) for s, g in df.groupby("symbol")}
        for r in changes.itertuples():
            if r.old in by_sym and r.new in by_sym:
                for a in by_sym[r.old].itertuples():
                    for b in by_sym[r.new].itertuples():
                        if a.effective_from < b._to and b.effective_from < a._to:
                            overlaps.append((idx, r.old, r.new, str(a.effective_from.date()), str(b.effective_from.date())))
    warn_count("D-25", "membership effective dates that are not trading days (pre-2006 reconstruction spells and staged future "
                       "reconstitutions)", non_session, cap=320)
    assert not overlaps, (f"D-25: {len(overlaps)} renamed ticker pairs hold membership windows that overlap, so the company is counted "
                          f"twice across its rename: {overlaps[:8]}")
