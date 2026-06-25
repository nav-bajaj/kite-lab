"""Tests for the proposal reconciliation core."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reconcile_proposals import reconcile  # noqa: E402


def _buy(date, sym, sh=10):
    return {"date": date, "symbol": sym, "side": "BUY", "shares": sh}


def _sell(date, sym, sh=10):
    return {"date": date, "symbol": sym, "side": "SELL", "shares": sh}


def test_perfect_match_when_engine_follows_rank_rule():
    # top_n=3, buffer=2. First rebalance buys A,B,C from empty; second is a
    # no-change rebalance (holdings all stay in the keep-zone).
    signals = {
        "2026-01-02": ["A", "B", "C", "D", "E"],
        "2026-01-16": ["A", "B", "F", "C", "D"],
    }
    trades = [_buy("2026-01-02", s) for s in ["A", "B", "C"]]
    rep = reconcile(signals, trades, top_n=3, exit_buffer=2)
    assert rep["summary"]["rebalances"] == 2
    assert rep["summary"]["exact_match"] == 2
    assert rep["summary"]["match_rate"] == 1.0


def test_partial_trim_is_not_a_membership_change():
    # The regime de-risk trims a continuing holding (SELL part of A) — A stays
    # held, so it must NOT be read as a full exit (and not re-predicted as a buy).
    signals = {
        "2026-01-02": ["A", "B", "C", "D", "E"],
        "2026-01-16": ["A", "B", "C", "D", "E"],
    }
    trades = (
        [_buy("2026-01-02", s, 10) for s in ["A", "B", "C"]]
        + [_sell("2026-01-16", "A", 3)]   # trim only: A 10 -> 7, still held
    )
    rep = reconcile(signals, trades, top_n=3, exit_buffer=2)
    r2 = rep["results"][1]
    assert r2["buys_match"] and r2["sells_match"]   # no phantom exit/entry of A
    assert rep["summary"]["exact_match"] == 2


def test_detects_stop_exit_divergence():
    # Engine fully sells A (stop) and buys D — a real membership change the rank
    # rule (ranking unchanged) does not predict.
    signals = {
        "2026-01-02": ["A", "B", "C", "D", "E"],
        "2026-01-16": ["A", "B", "C", "D", "E"],
    }
    trades = (
        [_buy("2026-01-02", s) for s in ["A", "B", "C"]]
        + [_sell("2026-01-16", "A", 10), _buy("2026-01-16", "D", 10)]
    )
    rep = reconcile(signals, trades, top_n=3, exit_buffer=2)
    r2 = rep["results"][1]
    assert r2["sells_match"] is False
    assert r2["extra_actual_sells"] == ["A"]
    assert r2["extra_actual_buys"] == ["D"]
    assert rep["summary"]["exact_match"] == 1


def test_empty_signals_yields_empty_report():
    rep = reconcile({}, [], top_n=3, exit_buffer=2)
    assert rep["summary"]["rebalances"] == 0
    assert rep["summary"]["match_rate"] is None
