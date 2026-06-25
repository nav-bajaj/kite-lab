"""Tests for the proposal reconciliation core."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reconcile_proposals import reconcile  # noqa: E402


def test_perfect_match_when_engine_follows_rank_rule():
    # top_n=3, buffer=2. First rebalance buys A,B,C from empty.
    signals = {
        "2026-01-02": ["A", "B", "C", "D", "E"],
        # 2 weeks later: F enters top3, E falls out of keep-zone(top5).
        "2026-01-16": ["A", "B", "F", "C", "D"],
    }
    trades = [
        {"date": "2026-01-02", "symbol": s, "side": "BUY"} for s in ["A", "B", "C"]
    ] + [
        # rebalance 2: C drops to rank4 (still in buffer -> kept); slots full -> no buys.
        # Actually with holdings {A,B,C} all in keep-zone, no change.
    ]
    rep = reconcile(signals, trades, top_n=3, exit_buffer=2)
    # Both rebalances reconcile: first = buy A,B,C; second = no change.
    assert rep["summary"]["rebalances"] == 2
    assert rep["summary"]["exact_match"] == 2
    assert rep["summary"]["match_rate"] == 1.0


def test_detects_stop_exit_divergence():
    # Engine sells X on the rebalance day for a reason the rank rule can't see
    # (e.g. trailing stop) — flagged as an extra_actual_sell, not an exact match.
    signals = {
        "2026-01-02": ["A", "B", "C", "D", "E"],
        "2026-01-16": ["A", "B", "C", "D", "E"],  # ranking unchanged
    }
    trades = (
        [{"date": "2026-01-02", "symbol": s, "side": "BUY"} for s in ["A", "B", "C"]]
        # rebalance 2: engine sells A (stop) and buys D to refill — rank rule
        # would have held A and added nothing.
        + [{"date": "2026-01-16", "symbol": "A", "side": "SELL"},
           {"date": "2026-01-16", "symbol": "D", "side": "BUY"}]
    )
    rep = reconcile(signals, trades, top_n=3, exit_buffer=2)
    r2 = rep["results"][1]
    assert r2["sells_match"] is False
    assert r2["extra_actual_sells"] == ["A"]      # the stop exit the rule missed
    assert rep["summary"]["exact_match"] == 1     # only rebalance 1 matched


def test_empty_signals_yields_empty_report():
    rep = reconcile({}, [], top_n=3, exit_buffer=2)
    assert rep["summary"]["rebalances"] == 0
    assert rep["summary"]["match_rate"] is None
