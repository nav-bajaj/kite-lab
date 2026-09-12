"""Group B of tasks/book_verification_2026/TESTS_BOOKS.md — rebalance timing.

Spec: "close of the first trading day of each month; orders at the next session's trade price";
"**one order day a month**; no weekly action".
"""
from __future__ import annotations

import pandas as pd
import pytest

from _harness import BOOKS
from data_pipeline.strategies.calendar import monthly_on_or_after

ALLOWED_REASONS = {"entry", "rank", "atr_stop"}


@pytest.mark.parametrize("book", BOOKS)
def test_b01_signal_dates_are_the_first_trading_day_of_each_month(runs, ctxs, book):
    """B-01: signal dates are exactly monthly_on_or_after(calendar, 1) over the run window."""
    ctx, run = ctxs[book], runs[book]
    got = pd.DatetimeIndex(sorted(run.signals.date.unique()))
    expected = pd.DatetimeIndex(monthly_on_or_after(ctx.panels.calendar, 1))
    expected = expected[(expected >= got[0]) & (expected <= got[-1])]
    assert list(got) == list(expected), f"{book}: signal-date set differs from the monthly calendar"
    cal = ctx.panels.calendar
    for sd in got:
        month = cal[(cal.year == sd.year) & (cal.month == sd.month)]
        assert sd == month[0], f"{book}: {sd.date()} is not the first session of its month"


@pytest.mark.parametrize("book", BOOKS)
def test_b02_trades_execute_on_the_next_session_only(runs, ctxs, book):
    """B-02: every trade lands on the session immediately after a signal date, and nowhere else."""
    ctx, run = ctxs[book], runs[book]
    cal = ctx.panels.calendar
    signal_dates = set(run.signals.date.unique())
    expected = set()
    for sd in signal_dates:
        i = cal.get_loc(sd)
        if i + 1 < len(cal):
            expected.add(cal[i + 1])
    actual = set(run.trades.date.unique())
    assert actual <= expected, f"{book}: trades outside the mapped exec dates: {sorted(actual - expected)[:5]}"
    assert not (actual & signal_dates), f"{book}: trades on a signal date (same-close execution)"


@pytest.mark.parametrize("book", BOOKS)
def test_b03_one_action_day_a_month_with_exits_and_entries_together(runs, book):
    """B-03: one order day a month; exits and entries share that day."""
    tr = runs[book].trades
    per_month = tr.groupby([tr.date.dt.year, tr.date.dt.month]).date.nunique()
    offenders = per_month[per_month > 1]
    assert offenders.empty, f"{book}: months with more than one action day: {offenders.to_dict()}"
    both = 0
    for _, g in tr.groupby("date"):
        if {"BUY", "SELL"} <= set(g.side):
            both += 1
    assert both > 0, f"{book}: no action day carries both sides — exits and entries are not being paired"


@pytest.mark.parametrize("book", BOOKS)
def test_b04_no_weekly_or_trim_machinery_is_active(runs, book):
    """B-04: reasons are only entry / rank / atr_stop — no rank_weekly, trim, regime_bear or topup."""
    reasons = set(runs[book].trades.reason.unique())
    assert reasons <= ALLOWED_REASONS, f"{book}: unexpected trade reasons {sorted(reasons - ALLOWED_REASONS)}"
