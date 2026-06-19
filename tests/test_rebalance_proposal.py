"""Tests for the membership-only rebalance proposal builder."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.rebalance_proposal import (  # noqa: E402
    build_proposal,
    select_target_membership,
    propose_next_rebalance,
)


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


# ---------------------------------------------------------------------------
# select_target_membership — the engine's rank + exit-buffer rule
# ---------------------------------------------------------------------------

def test_entry_fills_to_top_n_keeping_held_in_buffer():
    # top_n=3, buffer=2 -> keep_zone = top 5. Hold S03 (in buffer) and S99 (out).
    ranked = ["S00", "S01", "S02", "S03", "S04"]  # +others irrelevant
    target, entries, exits, retained = select_target_membership(
        ranked, ["S03", "S99"], top_n=3, exit_buffer=2, is_entry=True,
    )
    assert exits == ["S99"]            # fell outside keep_zone
    assert retained == ["S03"]         # in buffer -> kept
    # fill to top_n=3: need 2 more from top_n (S00,S01,S02) not held
    assert entries == ["S00", "S01"]
    assert set(target) == {"S03", "S00", "S01"}


def test_held_in_buffer_is_not_exited():
    ranked = ["A", "B", "C", "D", "E"]  # top_n=3 -> keep_zone top5
    _, entries, exits, retained = select_target_membership(
        ranked, ["D"], top_n=3, exit_buffer=2, is_entry=True,
    )
    assert exits == []                 # D is rank 4, inside top_n+buffer(5)
    assert "D" in retained


def test_exit_only_week_adds_nothing():
    ranked = ["A", "B", "C", "D", "E"]
    target, entries, exits, retained = select_target_membership(
        ranked, ["Z", "A"], top_n=3, exit_buffer=2, is_entry=False,
    )
    assert entries == []
    assert exits == ["Z"]
    assert target == ["A"]


def test_bear_regime_skips_entries():
    ranked = ["A", "B", "C", "D", "E"]
    _, entries, exits, _ = select_target_membership(
        ranked, ["A"], top_n=3, exit_buffer=2, is_entry=True,
        is_bear=True, bear_skips_entries=True,
    )
    assert entries == []               # no new names in bear
    assert exits == []                 # A still in keep_zone


def test_propose_next_rebalance_respects_buffer_hysteresis():
    # A naive top-N diff would exit S03; the buffer rule keeps it.
    ranked = ["S00", "S01", "S02", "S03", "S04"]
    p = propose_next_rebalance(
        ranked, ["S03", "S99"], top_n=3, exit_buffer=2, is_entry=True,
        prices={"S00": 100.0, "S01": 50.0}, capital=300_000,
    )
    assert [o.symbol for o in p.sells] == ["S99"]
    assert [o.symbol for o in p.buys] == ["S00", "S01"]
    assert p.holds == ["S03"]
    # equal weight 1/3 of 300k = 100k; S00 @100 -> 1000 sh
    s00 = next(o for o in p.buys if o.symbol == "S00")
    assert s00.est_shares == 1000
