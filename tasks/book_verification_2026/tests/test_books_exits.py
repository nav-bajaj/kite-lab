"""Group C of tasks/book_verification_2026/TESTS_BOOKS.md — exits.

Spec: "a holding exits at the monthly review if its rank falls below 45 (25 + buffer 20)"; bear
"exits at rank 35"; "20% trailing from the position's peak, checked at the monthly signal, executed
next session; a stopped name is sold and replaced by the next-ranked name — it is not rebought on
the same action day (founder, 2026-09-12; §23)".
"""
from __future__ import annotations

import numpy as np
import pytest

from _harness import BOOKS


@pytest.mark.parametrize("book", BOOKS)
def test_c01_exit_reasons_and_one_sell_per_exit(runs, book):
    """C-01: exits are only rank / atr_stop, and pair one-to-one with SELL trades."""
    run = runs[book]
    assert set(run.exits.reason.unique()) == {"rank", "atr_stop"}, \
        f"{book}: unexpected exit reasons {sorted(set(run.exits.reason.unique()))}"
    assert len(run.exits) == len(run.sells), \
        f"{book}: {len(run.exits)} exit rows vs {len(run.sells)} SELL trades"
    left = run.exits.groupby([run.exits.exit_date, run.exits.symbol]).size()
    right = run.sells.groupby([run.sells.date, run.sells.symbol]).size()
    assert left.to_dict() == right.to_dict(), f"{book}: exits and SELL trades do not pair up"


@pytest.mark.parametrize("book", BOOKS)
def test_c02_rank_exits_are_the_holdings_below_the_buffer(replays, book):
    """C-02: rank exits are exactly the holdings outside the top 45 (35 in a bear), less that day's stops."""
    bad = [(str(r.exec_date.date()), sorted(r.actual_rank_exits - r.expected_rank_exits),
            sorted(r.expected_rank_exits - r.actual_rank_exits))
           for r in replays[book].rebalances if r.actual_rank_exits != r.expected_rank_exits]
    assert bad == [], f"{book}: rank-exit mismatches on {len(bad)} action days: {bad[:3]}"


@pytest.mark.parametrize("book", BOOKS)
def test_c03_stop_exits_are_the_twenty_percent_breaches_at_the_signal_close(replays, book):
    """C-03: stop exits are exactly the holdings whose signal-date close is >20% below their peak."""
    bad = [(str(r.exec_date.date()), sorted(r.actual_stops - r.expected_stops_engine),
            sorted(r.expected_stops_engine - r.actual_stops))
           for r in replays[book].rebalances if r.actual_stops != r.expected_stops_engine]
    assert bad == [], f"{book}: stop mismatches on {len(bad)} action days: {bad[:3]}"


@pytest.mark.parametrize("book", BOOKS)
def test_c04_peak_is_the_running_peak_of_closes_since_entry(replays, book):
    """C-04: the peak read literally — entry trade price and every close from the entry session on.

    The engine's peak update (scripts/_clean_engine.py:344-349) runs before the entry block, so the
    entry session's own close is folded in only on the following session. Where that one-day gap
    changes a stop decision this test fails: it is a rule question for the founder, not a silent fix,
    because the locked figures were produced with the engine's convention.
    """
    bad = [(str(r.exec_date.date()), sorted(r.actual_stops - r.expected_stops_literal),
            sorted(r.expected_stops_literal - r.actual_stops))
           for r in replays[book].rebalances if r.actual_stops != r.expected_stops_literal]
    assert bad == [], (
        f"{book}: the peak excludes the entry-session close on {len(bad)} action days "
        f"(engine convention vs the literal rule): {bad[:3]}")


@pytest.mark.parametrize("book", BOOKS)
def test_c05_the_stop_never_fires_between_signal_dates(replays, runs, ctxs, book):
    """C-05: the stop is checked at the monthly signal only — daily breaches must not trade."""
    rp = replays[book]
    assert rp.breach_days_without_trade > 100, (
        f"{book}: only {rp.breach_days_without_trade} non-action days carried a live >20% breach — "
        "the check is vacuous, investigate the peak tracking rather than trusting this pass")
    action_dates = set(runs[book].trades.date.unique())
    cal = ctxs[book].panels.calendar
    assert not (action_dates - set(cal)), f"{book}: trade dates off the session calendar"


@pytest.mark.parametrize("book", BOOKS)
def test_c06_stop_exits_execute_next_session_at_the_trade_panel_price(runs, ctxs, book):
    """C-06: a stop decided at the signal close is filled on the next session at OHLC/4."""
    ctx, run = ctxs[book], runs[book]
    cal = ctx.panels.calendar
    signal_dates = set(run.signals.date.unique())
    stops = run.trades[(run.trades.side == "SELL") & (run.trades.reason == "atr_stop")]
    assert len(stops) > 0, f"{book}: no stop exits at all — the stop is not wired in"
    for _, r in stops.iterrows():
        i = cal.get_loc(r.date)
        assert i >= 1 and cal[i - 1] in signal_dates, f"{book}: stop on {r.date.date()} is not a next-session fill"
        px = ctx.panels.trade.loc[r.date, r.symbol]
        assert np.isclose(px, r.price, rtol=1e-9), f"{book}: {r.symbol} stop filled off-panel on {r.date.date()}"


@pytest.mark.parametrize("book", BOOKS)
def test_c07_a_stopped_name_is_never_rebought_the_same_day(replays, runs, book):
    """C-07: §23 / stop_reentry_block=1 — sold and replaced, never sold and rebought."""
    assert replays[book].same_day_both_sides == 0, \
        f"{book}: {replays[book].same_day_both_sides} (date, symbol) pairs carry both a BUY and a SELL"
    run = runs[book]
    stopped = run.exits[run.exits.reason == "atr_stop"]
    buys = {(d, s) for d, s in zip(run.buys.date, run.buys.symbol)}
    clashes = [(str(d.date()), s) for d, s in zip(stopped.exit_date, stopped.symbol) if (d, s) in buys]
    assert clashes == [], f"{book}: stopped names bought back on the same action day: {clashes[:5]}"


@pytest.mark.parametrize("book", BOOKS)
def test_c08_the_reentry_block_lasts_exactly_one_entry_date(replays, runs, book):
    """C-08: stop_reentry_block=1 — a stopped name may return at the following action day.

    The replay that reconciles in A-01 / D-01 applies a one-date block; here we also show the block
    is not longer, by finding a name stopped at one action day and re-entered at the next.
    """
    run = runs[book]
    dates = sorted(run.trades.date.unique())
    nxt = {d: dates[i + 1] for i, d in enumerate(dates[:-1])}
    stopped = run.exits[run.exits.reason == "atr_stop"]
    buys = {(d, s) for d, s in zip(run.buys.date, run.buys.symbol)}
    revivals = sum(1 for d, s in zip(stopped.exit_date, stopped.symbol)
                   if d in nxt and (nxt[d], s) in buys)
    assert revivals > 0, f"{book}: no stopped name ever returns at the next action day — block looks longer than 1"
