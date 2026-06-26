"""Tests for the EOD engine-readout helpers.

The engine emits multiple trades on a single rebalance date with different
``reason`` codes (``rank``, ``entry``, ``regime_bear``, ``regime_topup``,
``atr_stop``, ``200dma``, ``donchian``, ``rank_weekly``). For the rebalance
*page* we surface **membership changes only** — a partial trim on a
continuing holding is not an action the subscriber should take. The pure
helpers under test here turn a trade ledger into entries / exits / continuing
by net-share transition (``0 -> held`` = entry, ``held -> 0`` = exit,
everything else = continuing, regardless of trim direction).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.engine_readout import (  # noqa: E402
    holdings_from_trades,
    partition_membership_by_date,
)


# ----- holdings_from_trades -----

def test_holdings_from_trades_simple_entry():
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
    ])
    assert holdings_from_trades(trades) == {"A": 100}


def test_holdings_from_trades_full_exit_drops_symbol():
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
        {"date": "2026-02-02", "symbol": "A", "side": "SELL", "shares": 100},
    ])
    assert holdings_from_trades(trades) == {}


def test_holdings_from_trades_partial_trim_keeps_residual():
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
        {"date": "2026-02-02", "symbol": "A", "side": "SELL", "shares": 40},
    ])
    assert holdings_from_trades(trades) == {"A": 60}


def test_holdings_from_trades_topup_adds():
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
        {"date": "2026-02-02", "symbol": "A", "side": "BUY", "shares": 30},
    ])
    assert holdings_from_trades(trades) == {"A": 130}


def test_holdings_from_trades_only_up_to_cutoff():
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
        {"date": "2026-02-02", "symbol": "A", "side": "SELL", "shares": 100},
    ])
    # Cutoff strictly before the SELL: A still held at 100.
    cutoff = pd.Timestamp("2026-02-01")
    assert holdings_from_trades(trades, up_to=cutoff) == {"A": 100}


def test_holdings_from_trades_handles_empty_ledger():
    assert holdings_from_trades(pd.DataFrame(columns=["date", "symbol", "side", "shares"])) == {}


# ----- partition_membership_by_date -----

def test_partition_full_exit_and_new_entry_on_same_date():
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
        {"date": "2026-01-02", "symbol": "B", "side": "BUY", "shares": 50},
        # 2-week rebalance:
        {"date": "2026-01-16", "symbol": "A", "side": "SELL", "shares": 100},
        {"date": "2026-01-16", "symbol": "C", "side": "BUY", "shares": 70},
    ])
    parts = partition_membership_by_date(trades, exec_date="2026-01-16")
    assert parts["exits"] == ["A"]
    assert parts["entries"] == ["C"]
    assert parts["continuing"] == ["B"]


def test_partition_trim_on_continuing_is_not_an_action():
    # Regime-bear emits a partial SELL on a continuing holding. The model
    # still holds the name (residual shares > 0), so membership-wise it is a
    # HOLD, not a SELL. This is the gotcha called out in PLAN.md.
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
        {"date": "2026-01-02", "symbol": "B", "side": "BUY", "shares": 50},
        # Regime-bear scale-down on the next rebalance:
        {"date": "2026-01-16", "symbol": "A", "side": "SELL",
         "shares": 40, "reason": "regime_bear"},
    ])
    parts = partition_membership_by_date(trades, exec_date="2026-01-16")
    assert parts["exits"] == []
    assert parts["entries"] == []
    assert parts["continuing"] == ["A", "B"]


def test_partition_topup_on_continuing_is_not_an_action():
    # Regime-topup emits an extra BUY on a continuing holding. Continuing.
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
        {"date": "2026-01-16", "symbol": "A", "side": "BUY",
         "shares": 30, "reason": "regime_topup"},
    ])
    parts = partition_membership_by_date(trades, exec_date="2026-01-16")
    assert parts["exits"] == []
    assert parts["entries"] == []
    assert parts["continuing"] == ["A"]


def test_partition_full_exit_via_repeated_sells_on_one_date():
    # If something exits via a partial SELL on the rebalance and a later
    # rank-exit on the same date (engine doesn't actually do this, but the
    # helper should be robust to it), it is still an exit when the net falls
    # to zero on the exec date.
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
        {"date": "2026-01-16", "symbol": "A", "side": "SELL", "shares": 40},
        {"date": "2026-01-16", "symbol": "A", "side": "SELL", "shares": 60},
    ])
    parts = partition_membership_by_date(trades, exec_date="2026-01-16")
    assert parts["exits"] == ["A"]
    assert parts["entries"] == []
    assert parts["continuing"] == []


def test_partition_no_trades_on_exec_date_means_no_actions():
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 100},
    ])
    parts = partition_membership_by_date(trades, exec_date="2026-01-16")
    assert parts["exits"] == []
    assert parts["entries"] == []
    assert parts["continuing"] == ["A"]


def test_partition_sorts_results_deterministically():
    trades = pd.DataFrame([
        {"date": "2026-01-02", "symbol": "C", "side": "BUY", "shares": 10},
        {"date": "2026-01-02", "symbol": "A", "side": "BUY", "shares": 10},
        {"date": "2026-01-16", "symbol": "C", "side": "SELL", "shares": 10},
        {"date": "2026-01-16", "symbol": "Z", "side": "BUY", "shares": 5},
        {"date": "2026-01-16", "symbol": "B", "side": "BUY", "shares": 5},
    ])
    parts = partition_membership_by_date(trades, exec_date="2026-01-16")
    assert parts["exits"] == ["C"]
    assert parts["entries"] == ["B", "Z"]
    assert parts["continuing"] == ["A"]


def test_partition_accepts_datetime_exec_date():
    trades = pd.DataFrame([
        {"date": pd.Timestamp("2026-01-02"), "symbol": "A", "side": "BUY", "shares": 100},
        {"date": pd.Timestamp("2026-01-16"), "symbol": "A", "side": "SELL", "shares": 100},
    ])
    parts = partition_membership_by_date(trades, exec_date=pd.Timestamp("2026-01-16"))
    assert parts["exits"] == ["A"]
