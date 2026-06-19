"""Tests for the membership-only rebalance proposal builder."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.rebalance_proposal import build_proposal  # noqa: E402


def test_membership_diff():
    p = build_proposal(
        current_symbols=["A", "B", "C"],
        target_weights={"B": 0.33, "C": 0.33, "D": 0.34},
    )
    assert [o.symbol for o in p.sells] == ["A"]
    assert [o.symbol for o in p.buys] == ["D"]
    assert p.holds == ["B", "C"]


def test_sells_are_full_exits_weight_zero():
    p = build_proposal(["A"], {"B": 1.0})
    assert p.sells[0].side == "SELL"
    assert p.sells[0].target_weight == 0.0


def test_buys_carry_target_weight():
    p = build_proposal([], {"D": 0.042})
    assert p.buys[0].side == "BUY"
    assert p.buys[0].target_weight == 0.042


def test_rupee_sizing_with_capital_and_price():
    p = build_proposal(
        current_symbols=[],
        target_weights={"D": 0.042},
        prices={"D": 200.0},
        capital=1_000_000,
    )
    buy = p.buys[0]
    assert buy.est_notional == 42_000.0
    assert buy.est_shares == 210  # round(42000 / 200)


def test_no_capital_means_no_sizing():
    p = build_proposal([], {"D": 0.042})
    assert p.buys[0].est_notional is None
    assert p.buys[0].est_shares is None


def test_capital_but_missing_price_sizes_notional_only():
    p = build_proposal([], {"D": 0.042}, prices={}, capital=1_000_000)
    assert p.buys[0].est_notional == 42_000.0
    assert p.buys[0].est_shares is None


def test_continuing_holdings_are_hold_even_if_weight_drifts():
    # Membership-only: a weight change on a continuing name is NOT an action.
    p = build_proposal(["A"], {"A": 0.03})
    assert p.holds == ["A"]
    assert p.sells == [] and p.buys == []


def test_empty_target_exits_everything():
    # Bear-regime all-cash: every holding becomes a full exit, no buys.
    p = build_proposal(["A", "B"], {})
    assert [o.symbol for o in p.sells] == ["A", "B"]
    assert p.buys == []
    assert p.has_actions is True


def test_zero_weight_target_is_not_a_holding():
    # A name present at weight 0 should be treated as not held / exited.
    p = build_proposal(["A"], {"A": 0.0})
    assert [o.symbol for o in p.sells] == ["A"]
    assert p.holds == []


def test_to_rows_sells_first_then_buys():
    p = build_proposal(["A"], {"D": 0.5, "E": 0.5})
    rows = p.to_rows()
    assert [r["side"] for r in rows] == ["SELL", "BUY", "BUY"]
    assert rows[0]["symbol"] == "A"


def test_deterministic_sorted_order():
    p = build_proposal(["C", "A", "B"], {"Z": 0.5, "Y": 0.5})
    assert [o.symbol for o in p.sells] == ["A", "B", "C"]
    assert [o.symbol for o in p.buys] == ["Y", "Z"]
