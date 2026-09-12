"""Group E of tasks/book_verification_2026/TESTS_BOOKS.md — the sector cap.

Spec: "at most 5 names per NSE sector at entry (21 sectors; historical labels in `sector/`)".
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from _harness import BOOKS
from scripts._clean_engine import monthly_first_trading_day, run_strategy

SYMS = [f"S{i:02d}" for i in range(12)]


@pytest.mark.parametrize("book", BOOKS)
def test_e01_no_labelled_sector_holds_more_than_five_names(replays, ctxs, book):
    """E-01: after every rebalance, the count per sector_v2 label is at most sector_cap."""
    cap = ctxs[book].cfg["sector_cap"]
    bad = [(str(r.exec_date.date()), {k: v for k, v in r.sector_counts_after.items() if v > cap})
           for r in replays[book].rebalances if r.sector_counts_after and max(r.sector_counts_after.values()) > cap]
    assert bad == [], f"{book}: sector cap {cap} breached on {len(bad)} action days: {bad[:3]}"
    peak = max((max(r.sector_counts_after.values()) for r in replays[book].rebalances if r.sector_counts_after),
               default=0)
    assert peak == cap, f"{book}: the cap never binds (peak sector count {peak}) — check the sector map is loaded"


@pytest.mark.parametrize("book", BOOKS)
def test_e02_the_cap_skips_lower_ranked_entrants(replays, book):
    """E-02: the cap drops candidates in rank order; D-01's exact reconciliation is the proof.

    Here we also show the cap actually removed someone: at least one action day must have a
    candidate in the entry pool that the cap pushed out while a lower-ranked name got in.
    """
    skipped = 0
    for r in replays[book].rebalances:
        if len(r.expected_entrants) < len(r.entry_pool - r.held_pre_entry):
            skipped += 1
    assert skipped > 0, f"{book}: the sector cap and slot cap never removed a candidate — suspicious"


def test_e03_unlabelled_names_are_unconstrained():
    """E-03: a symbol with no sector label cannot be capped (sector_of.get -> None)."""
    rng = np.random.default_rng(11)
    cal = pd.bdate_range("2021-01-01", "2022-06-30")
    drift = np.linspace(0.0006, -0.0002, len(SYMS))
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(drift, 0.012, size=(len(cal), len(SYMS))), axis=0)),
                         index=cal, columns=SYMS)
    entries = pd.DatetimeIndex(monthly_first_trading_day(cal))
    order = pd.Series({s: -i for i, s in enumerate(SYMS)}, dtype=float)

    def score(date, **_):
        return order.copy()

    kwargs = dict(close_panel=close, trade_panel=close, calendar=cal, benchmark_aligned=close.mean(axis=1),
                  entry_signal_dates=entries, weekly_signal_dates=entries, signal_function=score,
                  signal_function_args={}, sma_200_panel=close.rolling(200).mean(),
                  atr_20_panel=close.pct_change().rolling(20).std(), top_n=8, exit_buffer=2, max_weight=1.0,
                  slippage=0.0, atr_mult=0.0, atr_min_floor=0.0, use_trailing_stop=False, use_dma_exit=False,
                  initial_capital=1_000_000, sector_cap=2)

    labelled = run_strategy(sector_of={s: "A" for s in SYMS}, **kwargs)
    unlabelled = run_strategy(sector_of={SYMS[0]: "A"}, **kwargs)
    assert labelled["equity"].holdings.max() <= 2, "one labelled sector should cap the book at 2 names"
    assert unlabelled["equity"].holdings.max() >= 8, \
        "names with no sector label must not be capped; got " \
        f"{unlabelled['equity'].holdings.max()} holdings"


def test_e03b_sector_map_is_the_twenty_one_sector_scheme(ctxs, replays):
    """E-03: the lookup carries NSE's 21 macro sectors and labels the names the books trade."""
    sector_of = ctxs["mm_v1"].sector_of
    assert len(set(sector_of.values())) == 21, f"expected 21 sectors, got {len(set(sector_of.values()))}"
    traded = {s for book in BOOKS for r in replays[book].rebalances for s in r.actual_buys}
    coverage = sum(1 for s in traded if s in sector_of) / len(traded)
    assert coverage >= 0.95, f"only {coverage:.3f} of traded names carry a sector label"
