"""Unit tests for sync_service.sync_proposed_rebalance.

The producer (``data_pipeline/eod_proposal.py``) writes
``proposed_regime.json`` into ``<run-dir>/backtests/baseline/``. This sync
reads it and upserts a ProposedRebalance row keyed by ``(universe,
exec_date)``. We don't spin up a live DB here (JSONB isn't sqlite-friendly);
we stub the Session and capture the row that would be persisted.

Covered:
- Happy path: JSON → row with expected scalars + JSON lists
- Missing JSON → soft-skip (no row, no error) so strategies without an EOD
  producer don't break ``sync_all``
- No experiment dir → soft-skip (same reason)
- Malformed JSON → returns an error dict but doesn't raise
- Idempotent re-sync: a same-day re-run replaces, not duplicates
"""
from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

import pytest

from app.services import sync_service


# --------- fakes ------------------------------------------------------------

class _FakeQuery:
    def __init__(self, store):
        self._store = store
        self._universe = None
        self._exec_date = None

    def filter(self, *exprs):
        # We only care about the (universe, exec_date) filter pattern used in
        # sync_proposed_rebalance. Pull the literal values out of the
        # BinaryExpression rights so the test stays independent of the
        # specific class attribute strings.
        for expr in exprs:
            right = getattr(expr, "right", None)
            val = getattr(right, "value", None) if right is not None else None
            if isinstance(val, str):
                self._universe = val
            elif isinstance(val, date):
                self._exec_date = val
        return self

    def delete(self):
        key = (self._universe, self._exec_date)
        before = len(self._store)
        self._store[:] = [r for r in self._store
                          if (r.universe, r.exec_date) != key]
        return before - len(self._store)


class _FakeSession:
    """Captures .add() calls into a list; .commit() is a no-op."""

    def __init__(self):
        self.rows = []
        self.commits = 0

    def query(self, _model):
        return _FakeQuery(self.rows)

    def add(self, row):
        self.rows.append(row)

    def commit(self):
        self.commits += 1


def _write_run_with_json(parent, run_name, payload):
    baseline = parent / "data" / "om25_v3_portfolios" / run_name / "backtests" / "baseline"
    baseline.mkdir(parents=True)
    # _holdings_present needs this so get_latest_experiment_dir returns the run
    (baseline / "momentum_holdings.csv").write_text("symbol,shares\nTCS,10\n")
    if payload is not None:
        (baseline / "proposed_regime.json").write_text(json.dumps(payload))
    return baseline.parents[1]


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_service, "settings",
                         SimpleNamespace(data_dir=tmp_path))
    # Reset any cached latest.json from earlier tests in this module.
    return tmp_path


def _sample_payload():
    return {
        "strategy": "om25_v3",
        "signal_date": "2026-05-22",
        "exec_date": "2026-05-25",
        "data_as_of": "2026-05-22",
        "sell_count": 2,
        "buy_count": 3,
        "hold_count": 20,
        "sells": ["ALPHA", "BETA"],
        "buys": [
            {"symbol": "DELTA", "target_weight": 0.04,
             "est_notional": 40000.0, "est_shares": 100},
            {"symbol": "EPSILON", "target_weight": 0.035,
             "est_notional": 35000.0, "est_shares": 50},
            {"symbol": "GAMMA", "target_weight": 0.038,
             "est_notional": 38000.0, "est_shares": 75},
        ],
        "holds": ["HOLD1", "HOLD2"],
        "drawdown_from_peak": -0.07,
        "final_pv": 1_140_000.0,
        "initial_capital": 1_000_000.0,
        "regime": "bear",
    }


# --------- tests ------------------------------------------------------------

def test_happy_path_inserts_row_with_expected_fields(data_root):
    _write_run_with_json(data_root,
                          "om25_v3_portfolio_20260518_201514",
                          _sample_payload())

    db = _FakeSession()
    result = sync_service.sync_proposed_rebalance(db, "om25_v3")

    assert result["count"] == 1
    assert result["exec_date"] == "2026-05-25"
    assert len(db.rows) == 1
    row = db.rows[0]
    assert row.universe == "om25_v3"
    assert row.exec_date == date(2026, 5, 25)
    assert row.signal_date == date(2026, 5, 22)
    assert row.data_as_of == date(2026, 5, 22)
    assert row.sell_count == 2
    assert row.buy_count == 3
    assert row.hold_count == 20
    assert row.sells == ["ALPHA", "BETA"]
    assert row.buys[0]["symbol"] == "DELTA"
    assert row.buys[0]["target_weight"] == 0.04
    assert row.holds == ["HOLD1", "HOLD2"]
    assert row.regime == "bear"
    assert float(row.drawdown_from_peak) == pytest.approx(-0.07)
    assert float(row.final_pv) == 1_140_000.0
    assert float(row.initial_capital) == 1_000_000.0


def test_missing_json_is_soft_skip(data_root):
    # Run dir exists but no proposed_regime.json — strategies without an EOD
    # producer yet (l6_v2, combo_defensive) take this path. Must not raise.
    _write_run_with_json(data_root,
                          "om25_v3_portfolio_20260518_201514",
                          payload=None)

    db = _FakeSession()
    result = sync_service.sync_proposed_rebalance(db, "om25_v3")

    assert result["count"] == 0
    assert "no proposed_regime.json" in result["skipped"]
    assert db.rows == []


def test_missing_experiment_dir_is_soft_skip(data_root):
    db = _FakeSession()
    result = sync_service.sync_proposed_rebalance(db, "om25_v3")

    assert result["count"] == 0
    assert "no experiment dir" in result["skipped"]
    assert db.rows == []


def test_malformed_json_returns_error_without_raising(data_root):
    baseline = (data_root / "data/om25_v3_portfolios"
                / "om25_v3_portfolio_20260518_201514"
                / "backtests/baseline")
    baseline.mkdir(parents=True)
    (baseline / "momentum_holdings.csv").write_text("symbol,shares\nTCS,10\n")
    (baseline / "proposed_regime.json").write_text("{not json,")

    db = _FakeSession()
    result = sync_service.sync_proposed_rebalance(db, "om25_v3")

    assert result["count"] == 0
    assert "error" in result
    assert db.rows == []


def test_resync_replaces_existing_row_for_same_exec_date(data_root):
    _write_run_with_json(data_root,
                          "om25_v3_portfolio_20260518_201514",
                          _sample_payload())

    db = _FakeSession()
    sync_service.sync_proposed_rebalance(db, "om25_v3")
    assert len(db.rows) == 1

    # Re-sync (e.g. producer was re-run after a data correction) on the same
    # exec date: the delete() before insert removes the prior row.
    sync_service.sync_proposed_rebalance(db, "om25_v3")
    assert len(db.rows) == 1


def test_unknown_universe_is_soft_skip(data_root):
    db = _FakeSession()
    result = sync_service.sync_proposed_rebalance(db, "nope_v0")

    assert result["count"] == 0
    assert db.rows == []
