"""Group H of tasks/book_verification_2026/TESTS_BOOKS.md — outputs and bookkeeping.

The runner's own files plus the DB-facing `backtests/baseline/momentum_*.csv` set that
`kite-api/app/services/sync_service.py` loads into Postgres.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from _harness import BOOKS, REFERENCE
from scripts.rebuilt_books import LOCKED


@pytest.mark.parametrize("book", BOOKS)
def test_h01_metrics_json_carries_the_locked_config(runs, book):
    """H-01: the run is the locked book — config equals scripts.rebuilt_books.LOCKED[book]."""
    cfg = runs[book].metrics["config"]
    assert cfg == LOCKED[book], f"{book}: config drift {set(cfg.items()) ^ set(LOCKED[book].items())}"
    assert cfg["lock_date"] == "2026-09-12" and cfg["stop_reentry_block"] == 1


@pytest.mark.parametrize("book", BOOKS)
def test_h02_metrics_json_tail_matches_the_run(runs, ctxs, book):
    """H-02: holdings, cash share and regime_today are the run's last session, not decoration."""
    run, ctx = runs[book], ctxs[book]
    last = run.equity.iloc[-1]
    assert run.metrics["holdings"] == int(last.holdings)
    assert abs(run.metrics["cash_pct"] - float(last.cash_pct)) < 1e-12
    expected = "bull" if bool(ctx.regime.loc[ctx.panels.calendar[-1]]) else "bear"
    assert run.metrics["regime_today"] == expected
    result = run.metrics["result"]
    assert pd.Timestamp(result["start"]) == run.equity.date.iloc[0]
    assert pd.Timestamp(result["end"]) == run.equity.date.iloc[-1]


@pytest.mark.parametrize("book", BOOKS)
def test_h03_db_facing_trades_reconcile(runs, book):
    """H-03: momentum_trades.csv is the runner's trade log."""
    run = runs[book]
    dash = pd.read_csv(run.dashboard / "momentum_trades.csv", parse_dates=["date"])
    cols = ["date", "symbol", "side", "shares", "price", "notional", "slippage"]
    assert list(dash.columns) == cols, f"{book}: momentum_trades schema {list(dash.columns)}"
    left = dash.sort_values(cols).reset_index(drop=True)
    right = run.trades[cols].sort_values(cols).reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right, obj=f"{book} momentum_trades vs runner trades")


@pytest.mark.parametrize("book", BOOKS)
def test_h04_db_facing_equity_reconciles(runs, book):
    """H-04: momentum_equity.csv carries the same curve, and a drawdown consistent with it."""
    run = runs[book]
    dash = pd.read_csv(run.dashboard / "momentum_equity.csv", parse_dates=["date"])
    assert list(dash.date) == list(run.equity.date)
    assert np.allclose(dash.portfolio_value.values, run.equity.pv.values, rtol=1e-12)
    expected_dd = dash.portfolio_value / dash.portfolio_value.cummax() - 1.0
    assert np.allclose(dash.drawdown.values, expected_dd.values, atol=1e-12)
    assert np.allclose(dash.benchmark.values, run.equity.benchmark.values, equal_nan=True)


@pytest.mark.parametrize("book", BOOKS)
def test_h05_db_facing_holdings_reconcile(runs, replays, book):
    """H-05: momentum_holdings.csv is the book left open after replaying every trade."""
    dash = pd.read_csv(runs[book].dashboard / "momentum_holdings.csv")
    got = {r.symbol: int(r.shares) for r in dash.itertuples()}
    assert got == replays[book].final_holdings, \
        f"{book}: holdings file disagrees with the replay: {set(got.items()) ^ set(replays[book].final_holdings.items())}"


@pytest.mark.parametrize("book", BOOKS)
def test_h06_db_facing_metrics_reconcile(runs, book):
    """H-06: momentum_metrics.csv equals metrics.json's result block."""
    run = runs[book]
    dash = pd.read_csv(run.dashboard / "momentum_metrics.csv")
    assert len(dash) == 1
    row = dash.iloc[0]
    for key, value in run.metrics["result"].items():
        if key not in dash.columns:
            continue
        try:
            assert abs(float(row[key]) - float(value)) < 1e-9, f"{book}: {key} {row[key]} vs {value}"
        except (TypeError, ValueError):
            assert str(row[key]) == str(value), f"{book}: {key} {row[key]} vs {value}"


@pytest.mark.parametrize("book", BOOKS)
def test_h07_run_reproduces_the_reference_figures(runs, ctxs, master, book):
    """H-07: the regression anchor — mm_rebuild RESULTS.md §23 decision line, runner convention."""
    run = runs[book]
    cagr, mdd = REFERENCE[book]
    got_cagr = float(run.metrics["result"]["cagr"])
    got_mdd = float(run.metrics["result"]["max_drawdown"])
    assert abs(got_cagr - cagr) < 0.0015, f"{book}: CAGR {got_cagr:.4f} vs reference {cagr}"
    assert abs(got_mdd - mdd) < 0.0015, f"{book}: max drawdown {got_mdd:.4f} vs reference {mdd}"

    ctx = ctxs[book]
    cal = ctx.panels.calendar
    assert list(run.equity.date) == list(cal[cal >= run.equity.date.iloc[0]]), \
        f"{book}: the equity calendar has gaps"
    bench = ctx.benchmark.reindex(run.equity.date).values
    assert np.allclose(run.equity.benchmark.values, bench, equal_nan=True), \
        f"{book}: the benchmark column is not {ctx.cfg['regime_index']}_bench"


@pytest.mark.parametrize("book", BOOKS)
def test_h08_per_trade_pnl_is_net_of_both_slippage_legs(runs, ctxs, book):
    """H-08: exits.pnl_pct must use effective prices on both sides (founder's standing P&L rule)."""
    run, slip = runs[book], ctxs[book].cfg["slippage"]
    shares: dict = {}
    basis: dict = {}
    rows = []
    for dt, g in run.trades.groupby("date"):
        for r in g[g.side == "SELL"].itertuples():
            sh = shares.get(r.symbol, 0)
            avg = basis.get(r.symbol, 0.0) / sh if sh else 0.0
            rows.append({"symbol": r.symbol, "exit_date": dt,
                         "net": (r.price * (1 - slip)) / avg - 1 if avg > 0 else np.nan,
                         "gross": r.price / avg - 1 if avg > 0 else np.nan})
            shares[r.symbol] = sh - r.shares
            if shares[r.symbol] <= 0:
                shares.pop(r.symbol, None)
                basis.pop(r.symbol, None)
        for r in g[g.side == "BUY"].itertuples():
            shares[r.symbol] = shares.get(r.symbol, 0) + r.shares
            basis[r.symbol] = basis.get(r.symbol, 0.0) + r.shares * r.price * (1 + slip)
    rec = pd.DataFrame(rows)
    merged = run.exits.merge(rec, on=["symbol", "exit_date"], how="left")
    assert merged.net.notna().all(), f"{book}: could not price every exit from the trade log"
    assert np.allclose(merged.pnl_pct.values, merged.net.values, atol=1e-9), (
        f"{book}: exits.pnl_pct is gross of the sell-side slippage leg "
        f"(matches the gross form: {np.allclose(merged.pnl_pct.values, merged.gross.values, atol=1e-9)}); "
        "scripts/_clean_engine.py:531-533 computes exec_price / avg_cost - 1")
