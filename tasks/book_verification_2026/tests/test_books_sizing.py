"""Group D of tasks/book_verification_2026/TESTS_BOOKS.md — sizing, cash and bookkeeping.

Spec: "inverse-volatility across the intended book (63-day vol), capped at 10%; positions drift,
never resized"; "no position is ever trimmed to make room"; "net of 20 bps slippage each way".
"""
from __future__ import annotations

import numpy as np
import pytest

from _harness import BOOKS
from data_pipeline.strategies.sizing import make_inverse_vol_weights


@pytest.mark.parametrize("book", BOOKS)
def test_d01_entrants_and_share_counts_reproduce_exactly(replays, book):
    """D-01: golden replay — the whole entry path re-derived from the store matches the engine.

    Covers the buffer draw, membership, the stop re-entry block, the sector cap, the slot cap, the
    inverse-vol target, the 10% cap and the two-pass allocation, at every action day.
    """
    bad = [(str(r.exec_date.date()), r.expected_shares, r.actual_buys)
           for r in replays[book].rebalances if r.expected_shares != r.actual_buys]
    assert bad == [], f"{book}: entrant/share mismatch on {len(bad)} action days: {bad[:2]}"


@pytest.mark.parametrize("book", BOOKS)
def test_d02_no_entry_weight_exceeds_ten_percent(replays, runs, book):
    """D-02: inverse-vol weights capped at 10% of the book."""
    run = runs[book]
    notional = run.buys.groupby(["date", "symbol"]).notional.sum()
    worst = 0.0
    worst_at = None
    for r in replays[book].rebalances:
        for s in r.actual_buys:
            w = float(notional[(r.exec_date, s)]) / r.book_value
            if w > worst:
                worst, worst_at = w, (str(r.exec_date.date()), s)
    assert worst <= 0.105, f"{book}: entry weight {worst:.4f} at {worst_at} above the 10% cap"


@pytest.mark.parametrize("book", BOOKS)
def test_d03_entry_weights_are_inverse_volatility(replays, book):
    """D-03: target weights rank inversely to 63-day vol, and the weight map sums to 1."""
    checked = 0
    for r in replays[book].rebalances:
        if not r.target_weights:
            continue
        assert abs(sum(r.target_weights.values()) - 1.0) < 1e-9, \
            f"{book} {r.exec_date.date()}: weight map sums to {sum(r.target_weights.values())}"
        pairs = [(r.vol63[s], r.target_weights[s]) for s in r.expected_entrants
                 if s in r.vol63 and s in r.target_weights]
        uncapped = [(v, w) for v, w in pairs if w < 0.10 - 1e-12]
        if len(uncapped) < 2:
            continue
        checked += 1
        vols = [v for v, _ in uncapped]
        weights = [w for _, w in uncapped]
        order = np.argsort(vols)
        ranked = [weights[i] for i in order]
        assert all(a >= b - 1e-12 for a, b in zip(ranked, ranked[1:])), \
            f"{book} {r.exec_date.date()}: weights are not monotonically decreasing in vol"
    assert checked > 20, f"{book}: only {checked} rebalances had two uncapped entrants to compare"


@pytest.mark.parametrize("book", BOOKS)
def test_d04_sizing_uses_no_data_after_the_signal_date(ctxs, book):
    """D-04: the weight map at t is identical when the returns panel is truncated at t."""
    ctx = ctxs[book]
    for sd in list(ctx.entries)[::53]:
        syms = [s for s in ctx.returns.columns[:60]]
        full = make_inverse_vol_weights(ctx.returns, ctx.cfg["iv_window"], ctx.cfg["max_weight"])(sd, syms)
        cut = make_inverse_vol_weights(ctx.returns[ctx.returns.index <= sd], ctx.cfg["iv_window"],
                                      ctx.cfg["max_weight"])(sd, syms)
        assert (full is None) == (cut is None)
        if full is None:
            continue
        assert {k: round(v, 12) for k, v in full.items()} == {k: round(v, 12) for k, v in cut.items()}, \
            f"{book}: weights at {sd.date()} move when later returns are removed"


@pytest.mark.parametrize("book", BOOKS)
def test_d05_cash_is_never_negative_and_small_in_a_full_bull_book(runs, book):
    """D-05: no leverage; a 25-name book is close to fully invested."""
    eq = runs[book].equity
    assert (eq.cash >= 0).all(), f"{book}: negative cash on {(eq.cash < 0).sum()} sessions"
    full = eq[eq.holdings == ctx_top_n(runs[book])]
    assert len(full) > 200, f"{book}: only {len(full)} sessions with a full book"
    assert full.cash_pct.median() < 0.02, f"{book}: median cash share {full.cash_pct.median():.4f} with a full book"
    assert full.cash_pct.max() < 0.15, f"{book}: cash share peaks at {full.cash_pct.max():.4f} with a full book"


def ctx_top_n(run) -> int:
    return int(run.metrics["config"]["top_n"])


@pytest.mark.parametrize("book", BOOKS)
def test_d06_equity_equals_cash_plus_marked_holdings(replays, book):
    """D-06: pv = cash + sum(shares * close) on every session; holdings count matches too."""
    rp = replays[book]
    assert rp.equity_error < 1e-6, f"{book}: max |cash + mtm - pv| = {rp.equity_error}"
    assert rp.holdings_mismatch_days == 0, f"{book}: holdings count disagrees on {rp.holdings_mismatch_days} sessions"


@pytest.mark.parametrize("book", BOOKS)
def test_d07_no_partial_sells_and_no_trims(replays, runs, book):
    """D-07: every SELL clears the whole position; trimming is off (§19)."""
    assert replays[book].partial_sells == 0, f"{book}: {replays[book].partial_sells} partial sells"
    assert (runs[book].trades.reason == "trim").sum() == 0, f"{book}: trim trades present"


@pytest.mark.parametrize("book", BOOKS)
def test_d08_no_held_position_is_topped_up(replays, book):
    """D-08: positions drift, never resized — no BUY into a name already held that day."""
    assert replays[book].held_topups == 0, f"{book}: {replays[book].held_topups} top-ups of held positions"


@pytest.mark.parametrize("book", BOOKS)
def test_d09_costs_prices_and_starting_capital(runs, ctxs, book):
    """D-09: 20 bps each way, fills at the trade panel (OHLC/4), Rs 10,00,000 of starting cash."""
    ctx, run = ctxs[book], runs[book]
    slip = ctx.cfg["slippage"]
    assert slip == 0.002
    assert np.allclose(run.trades.slippage, run.trades.notional * slip), f"{book}: slippage is not {slip} of notional"
    assert np.allclose(run.trades.notional, run.trades.shares * run.trades.price), f"{book}: notional != shares * price"
    panel = ctx.panels.trade
    got = np.array([panel.loc[d, s] for d, s in zip(run.trades.date, run.trades.symbol)])
    assert np.allclose(got, run.trades.price.values, rtol=1e-9), f"{book}: fills are not the trade-panel price"
    first = run.equity.iloc[0]
    assert float(first.cash) == float(ctx.cfg["initial_capital"]) == float(first.pv), \
        f"{book}: the book does not start flat at {ctx.cfg['initial_capital']}"
