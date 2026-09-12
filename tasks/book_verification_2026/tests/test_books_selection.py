"""Group A of tasks/book_verification_2026/TESTS_BOOKS.md — stock selection.

Spec: tasks/mm_rebuild/MECHANICS.md (universe, score, eligibility, the buffer draw).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from _harness import BOOKS
from data_pipeline.strategies.capture import make_capture_score
from data_pipeline.strategies.momentum import make_momentum_score

SAMPLE_EVERY = 17          # sampled signal dates for the expensive score re-derivations


def _sample_dates(ctx, every: int = SAMPLE_EVERY):
    return list(ctx.entries)[::every]


@pytest.mark.parametrize("book", BOOKS)
def test_a01_entrants_come_from_the_top_45_by_rank(replays, book):
    """A-01: entrants are drawn by rank from the top 45 (top 35 in a bear, bear_n + buffer)."""
    bad = [(str(r.exec_date.date()), s) for r in replays[book].rebalances
           for s in r.actual_buys if s not in r.entry_pool]
    assert bad == [], f"{book}: entrants outside the buffer draw: {bad[:10]}"


@pytest.mark.parametrize("book", BOOKS)
def test_a02_entrants_are_members_as_of_the_signal_date(replays, ctxs, book):
    """A-02: point-in-time Nifty 250 membership; no name the index had not yet added."""
    ctx = ctxs[book]
    bad = []
    for r in replays[book].rebalances:
        members = ctx.members_at(r.signal_date)
        bad += [(str(r.exec_date.date()), s) for s in r.actual_buys if s not in members]
    assert bad == [], f"{book}: non-member entrants: {bad[:10]}"


@pytest.mark.parametrize("book", BOOKS)
def test_a02b_score_never_sees_a_future_index_addition(ctxs, book):
    """A-02: the score cross-section is point-in-time — no symbol first added after the signal date."""
    ctx = ctxs[book]
    first_from = ctx.membership.groupby("symbol")["effective_from"].min()
    bad = []
    for sd in _sample_dates(ctx):
        sc = ctx.score(sd)
        if sc is None or sc.empty:
            continue
        bad += [(str(sd.date()), s) for s in sc.index if s in first_from.index and first_from[s] > sd]
    assert bad == [], f"{book}: future index additions scored: {bad[:10]}"


@pytest.mark.parametrize("book", BOOKS)
def test_a03_entrants_meet_min_obs(replays, ctxs, book):
    """A-03: eligibility is >= min_obs priced sessions in the score window (219 MM / 220 OM25)."""
    ctx = ctxs[book]
    min_obs = ctx.cfg["min_obs"]
    bad = []
    for r in replays[book].rebalances:
        counts = ctx.score_window(r.signal_date).notna().sum()
        for s in r.actual_buys:
            n = int(counts.get(s, 0))
            if n < min_obs:
                bad.append((str(r.exec_date.date()), s, n))
    assert bad == [], f"{book}: entrants below min_obs={min_obs}: {bad[:10]}"


@pytest.mark.parametrize("book", BOOKS)
def test_a04_score_window_ends_21_sessions_before_the_signal(ctxs, book):
    """A-04: the 12-1 skip — perturbing the last 21 sessions must leave the score unchanged."""
    ctx = ctxs[book]
    sd = ctx.entries[120]
    i = ctx.returns.index.get_loc(sd)
    bumped = ctx.returns.copy()
    bumped.iloc[i - ctx.cfg["skip"] + 1: i + 1] *= 3.0
    kw = dict(kind="voladj", lookback=ctx.cfg["lookback"], min_obs=ctx.cfg["min_obs"],
              skip=ctx.cfg["skip"], candidate_fn=ctx.candidate_fn)
    a = make_momentum_score(ctx.returns, **kw)(sd).sort_index()
    b = make_momentum_score(bumped, **kw)(sd).sort_index()
    pd.testing.assert_series_equal(a, b)


def test_a05_mm_score_is_vol_adjusted_momentum_with_the_five_percent_floor(ctxs):
    """A-05: MM's score is window return / annualised vol, vol floored at 5%."""
    ctx = ctxs["mm_v1"]
    for sd in _sample_dates(ctx, 41):
        win = ctx.score_window(sd)
        got = ctx.raw_score(sd)
        if got is None or got.empty:
            continue
        cols = list(got.index)
        w = win[cols]
        mom = (1 + w.fillna(0)).prod() - 1
        vol = (w.std() * np.sqrt(252)).clip(lower=0.05)
        expected = (mom / vol).reindex(cols)
        np.testing.assert_allclose(got.reindex(cols).values, expected.values, rtol=1e-9, atol=1e-12)


@pytest.mark.parametrize("book", BOOKS)
def test_a05b_no_entrant_relies_on_the_vol_floor(replays, ctxs, book):
    """A-05: the 5% vol floor must never be what makes a name rank — a floored denominator means a
    stale or barely-traded series, and the numerator is then meaningless."""
    ctx = ctxs[book]
    bad = []
    for r in replays[book].rebalances:
        vol = ctx.score_window(r.signal_date).std() * np.sqrt(252)
        for s in r.actual_buys:
            if s in vol and float(vol[s]) < 0.05:
                bad.append((str(r.exec_date.date()), s, round(float(vol[s]), 4)))
    assert bad == [], f"{book}: entrants whose vol was floored: {bad[:10]}"


def test_a06_om25_score_is_the_fifty_fifty_rank_blend(ctxs):
    """A-06: OM25's score is 0.5 * rank(vol-adj momentum) + 0.5 * rank(capture ratio)."""
    ctx = ctxs["om25_v4"]
    cfg = ctx.cfg
    assert cfg["mix_w"] == 0.5
    mom = make_momentum_score(ctx.returns, kind="voladj", lookback=cfg["lookback"], min_obs=cfg["min_obs"],
                              skip=cfg["skip"], candidate_fn=ctx.candidate_fn)
    cap = make_capture_score(ctx.returns, None, w_uc_bull=0.0, w_cr_bull=1.0, return_filter=True,
                             lookback=cfg["lookback"], min_obs=cfg["min_obs"], candidate_fn=ctx.candidate_fn)
    for sd in _sample_dates(ctx, 41):
        a, b = mom(sd), cap(sd)
        idx = a.index.intersection(b.index)
        if len(idx) == 0:
            continue
        expected = (0.5 * a[idx].rank(pct=True) + 0.5 * b[idx].rank(pct=True)).sort_index()
        got = ctx.raw_score(sd).sort_index()
        pd.testing.assert_series_equal(got, expected, check_names=False)


def test_a07_return_filter_applies_to_the_blend_and_not_to_mm(replays, ctxs):
    """A-07: OM25's capture leg requires a positive window return; MM has no such filter."""
    om, mm = ctxs["om25_v4"], ctxs["mm_v1"]

    bad = []
    for sd in _sample_dates(om, 13):
        sc = om.score(sd)
        if sc is None or sc.empty:
            continue
        total = (1 + om.capture_window(sd).fillna(0)).prod() - 1
        bad += [(str(sd.date()), s) for s in sc.index if s in total and float(total[s]) <= 0]
    assert bad == [], f"om25_v4: names with a non-positive window return survived the filter: {bad[:10]}"

    for r in replays["om25_v4"].rebalances:
        total = (1 + om.capture_window(r.signal_date).fillna(0)).prod() - 1
        for s in r.actual_buys:
            assert float(total.get(s, 1.0)) > 0, f"om25_v4 {r.exec_date.date()}: {s} entered with a flat/negative year"

    negatives = 0
    for sd in _sample_dates(mm, 13):
        sc = mm.score(sd)
        if sc is None or sc.empty:
            continue
        total = (1 + mm.capture_window(sd).fillna(0)).prod() - 1
        negatives += sum(1 for s in sc.index if s in total and float(total[s]) <= 0)
    assert negatives > 0, "mm_v1 appears to have acquired a return filter it is not supposed to have"


@pytest.mark.parametrize("book", BOOKS)
def test_a08_entrants_are_priced_not_forward_filled(replays, ctxs, master, book):
    """A-08: the panel is forward-filled, so an entrant must be shown to have actually traded on its
    signal date, and its score window must not be mostly flat sessions."""
    ctx = ctxs[book]
    wanted = {s for r in replays[book].rebalances for s in r.actual_buys}
    have: dict[str, set] = {}
    for s in wanted:
        f = master / "panels" / "pr" / f"{s}_day.csv"
        have[s] = set(pd.read_csv(f, usecols=["date"], parse_dates=["date"]).date) if f.exists() else set()

    missing = [(str(r.exec_date.date()), s) for r in replays[book].rebalances
               for s in r.actual_buys if r.signal_date not in have[s]]
    assert missing == [], f"{book}: entrants with no traded row on the signal date: {missing[:10]}"

    worst = 0.0
    worst_at = None
    for r in replays[book].rebalances:
        win = ctx.score_window(r.signal_date)
        share = (win == 0).sum() / win.notna().sum()
        for s in r.actual_buys:
            if s in share and float(share[s]) > worst:
                worst, worst_at = float(share[s]), (str(r.exec_date.date()), s)
    assert worst < 0.25, f"{book}: entrant with {worst:.1%} flat sessions in its score window at {worst_at}"


@pytest.mark.parametrize("book", BOOKS)
def test_a09_signals_file_reproduces_the_ranking(runs, ctxs, book):
    """A-09: the published signals file is the ranking the engine used — structure, depth, regime
    label and, at the 45/35 boundary, the same set of names."""
    ctx, run = ctxs[book], runs[book]
    depth_bull = ctx.cfg["top_n"] + ctx.cfg["exit_buffer"]
    depth_bear = ctx.cfg["bear_n"] + ctx.cfg["bear_buffer"]
    set_diffs = []
    for sd, g in run.signals.groupby("date"):
        g = g.sort_values("rank")
        assert list(g["rank"]) == list(range(1, len(g) + 1)), f"{book} {sd.date()}: ranks are not 1..N"
        assert (g["score"].diff().dropna() <= 1e-12).all(), f"{book} {sd.date()}: score not monotone in rank"
        bull = ctx.is_bull(sd)
        assert len(g) <= (depth_bull if bull else depth_bear), f"{book} {sd.date()}: depth {len(g)}"
        assert g["regime"].iloc[0] == ("bull" if bull else "bear"), f"{book} {sd.date()}: regime label"
        engine = ctx.engine_ranking(sd)[:len(g)]
        if set(g.symbol) != set(engine):
            set_diffs.append((str(sd.date()), sorted(set(g.symbol) ^ set(engine))))
    assert set_diffs == [], (
        f"{book}: the signals file's buy list differs from the ranking the engine used on "
        f"{len(set_diffs)} signal dates (tie ordering: rebuilt_books.py uses sort_values().head(), "
        f"the engine uses nlargest()): {set_diffs[:5]}")
