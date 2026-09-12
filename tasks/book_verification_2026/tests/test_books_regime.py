"""Group F of tasks/book_verification_2026/TESTS_BOOKS.md — regime and bear behaviour.

Spec: "NIFTY 100 31-session rate of change, sign, 3-day confirmation to flip, decided from the prior
close"; "entries capped so the book holds <= 15 names; exits at rank 35; the top names stay fully
sized; residual cash tolerated"; "after a bear the book rebuilds over the following rebalances as
positions exit".
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from _harness import BOOKS


def _independent_regime(index_csv, n: int, confirm: int, calendar) -> pd.Series:
    """ROC sign with `confirm`-day hysteresis, lagged one session — written out longhand so this is
    not a re-run of data_pipeline/strategies/regime.py."""
    s = pd.read_csv(index_csv, parse_dates=["date"])
    s["date"] = pd.to_datetime(s["date"]).dt.tz_localize(None).dt.normalize()
    s = s.sort_values("date").set_index("date")["close"]
    roc = s / s.shift(n) - 1.0
    on = roc > 0
    state = True
    out = []
    for i in range(len(roc)):
        window_roc = roc.iloc[max(0, i - confirm + 1): i + 1]
        window_on = on.iloc[max(0, i - confirm + 1): i + 1]
        if len(window_roc) < confirm or window_roc.isna().any():
            out.append(state)
            continue
        if state and not window_on.any():
            state = False
        elif not state and window_on.all():
            state = True
        out.append(state)
    lagged = pd.Series(out, index=roc.index).shift(1)
    return lagged.reindex(calendar).ffill().fillna(True).astype(bool)


@pytest.mark.parametrize("book", BOOKS)
def test_f01_regime_is_nifty100_roc31_with_three_day_confirmation_lagged(ctxs, runs, master, book):
    """F-01: the regime series equals an independent recomputation, and the signals file agrees."""
    ctx = ctxs[book]
    expected = _independent_regime(master / f"benchmarks/{ctx.cfg['regime_index']}.csv",
                                  ctx.cfg["roc_n"], ctx.cfg["confirm"], ctx.panels.calendar)
    diff = (expected != ctx.regime).sum()
    assert diff == 0, f"{book}: regime differs from the independent recomputation on {diff} sessions"
    labels = runs[book].signals.groupby("date").regime.first()
    bad = [(str(d.date()), v) for d, v in labels.items() if v != ("bull" if bool(ctx.regime.get(d, True)) else "bear")]
    assert bad == [], f"{book}: signals-file regime labels disagree: {bad[:5]}"
    assert 0 < (~ctx.regime).sum() < len(ctx.regime), f"{book}: the regime never changes state"


@pytest.mark.parametrize("book", BOOKS)
def test_f02_bull_books_hold_at_most_twenty_five(replays, runs, ctxs, book):
    """F-02: up to 25 names."""
    top_n = ctxs[book].cfg["top_n"]
    assert runs[book].equity.holdings.max() <= top_n, f"{book}: holdings peak at {runs[book].equity.holdings.max()}"
    bad = [(str(r.exec_date.date()), len(r.held_pre_entry) + len(r.actual_buys))
           for r in replays[book].rebalances
           if r.is_bull and len(r.held_pre_entry) + len(r.actual_buys) > top_n]
    assert bad == [], f"{book}: bull action days over {top_n} names: {bad[:5]}"


@pytest.mark.parametrize("book", BOOKS)
def test_f03_bear_entries_are_capped_at_fifteen(replays, ctxs, book):
    """F-03: in a bear, entries are capped so the book holds <= 15 — the cap never forces a sale."""
    bear_n = ctxs[book].cfg["bear_n"]
    bad = []
    for r in replays[book].rebalances:
        if r.is_bull:
            continue
        after = len(r.held_pre_entry) + len(r.actual_buys)
        if after > max(bear_n, len(r.held_pre_entry)):
            bad.append((str(r.exec_date.date()), len(r.held_pre_entry), after))
    assert bad == [], f"{book}: bear action days above the {bear_n}-name cap: {bad[:5]}"
    bears = [r for r in replays[book].rebalances if not r.is_bull]
    assert len(bears) > 20, f"{book}: only {len(bears)} bear action days — the cap is barely exercised"


@pytest.mark.parametrize("book", BOOKS)
def test_f04_bear_exit_rank_is_thirty_five(runs, ctxs, book):
    """F-04: bear signal dates are scored to bear_n + bear_buffer = 35, bull dates to 45."""
    ctx = ctxs[book]
    bull_depth = ctx.cfg["top_n"] + ctx.cfg["exit_buffer"]
    bear_depth = ctx.cfg["bear_n"] + ctx.cfg["bear_buffer"]
    depths = runs[book].signals.groupby("date")["rank"].max()
    for d, n in depths.items():
        want = bull_depth if ctx.is_bull(d) else bear_depth
        assert int(n) == want, f"{book} {d.date()}: scored depth {int(n)}, expected {want}"


@pytest.mark.parametrize("book", BOOKS)
def test_f05_a_bear_runs_the_book_down_only_as_positions_exit(replays, runs, book):
    """F-05: no pro-rata de-risking — holdings fall only by that day's exits, never by forced sales."""
    assert (runs[book].trades.reason == "regime_bear").sum() == 0, f"{book}: forced bear sales present"
    bad = []
    for r in replays[book].rebalances:
        if r.is_bull:
            continue
        expected_after_exits = len(r.held_at_open) - len(r.actual_stops | r.actual_rank_exits)
        if len(r.held_pre_entry) != expected_after_exits:
            bad.append((str(r.exec_date.date()), len(r.held_at_open), len(r.held_pre_entry), expected_after_exits))
    assert bad == [], f"{book}: bear holdings fell by more than the recorded exits: {bad[:5]}"
    carried = [r for r in replays[book].rebalances if not r.is_bull and len(r.held_pre_entry) > 15]
    assert carried, f"{book}: no bear day ever carried more than 15 names — the run-down rule is untested here"


@pytest.mark.parametrize("book", BOOKS)
def test_f06_bear_entrants_keep_full_inverse_vol_size(replays, book):
    """F-06: bear entrants are sized at the unscaled inverse-vol weight (no exposure multiplier)."""
    bears = [r for r in replays[book].rebalances if not r.is_bull and r.actual_buys]
    assert bears, f"{book}: no bear action day with entries"
    bad = [(str(r.exec_date.date()), r.expected_shares, r.actual_buys)
           for r in bears if r.expected_shares != r.actual_buys]
    assert bad == [], f"{book}: bear entrants are not at full inverse-vol size: {bad[:2]}"
    worst = 0.0
    for r in bears:
        for s, w in r.target_weights.items():
            if s in r.actual_buys:
                worst = max(worst, float(w))
    assert worst > 0.03, f"{book}: bear entry target weights peak at {worst:.4f} — they look scaled down"
    assert not np.isnan(worst)
