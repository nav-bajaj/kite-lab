"""Regression test for the latest.json run-dir pointer.

Guards the bug where the daily sync (and every dashboard read that shares the
pointer) kept serving a stale run dir because nothing advanced latest.json to
each day's new run. Symptom in production: holdings frozen, no new trades.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import sync_service


def _make_run(parent_dir, name: str):
    """Create a timestamped run dir with the holdings CSV sync_service looks for."""
    run_dir = parent_dir / "data" / "om25_v3_portfolios" / name
    baseline = run_dir / "backtests" / "baseline"
    baseline.mkdir(parents=True)
    (baseline / "momentum_holdings.csv").write_text("symbol,shares\nTCS,10\n")
    return run_dir


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_service, "settings", SimpleNamespace(data_dir=tmp_path))
    return tmp_path


def test_pointer_goes_stale_without_refresh(data_root):
    """Documents the failure mode: a cached pointer ignores newer runs."""
    old = _make_run(data_root, "om25_v3_portfolio_20260601_070000")

    # First read caches the pointer at the only run that exists.
    assert sync_service.get_latest_experiment_dir("om25_v3") == old

    # The daily pipeline produces a newer run...
    _make_run(data_root, "om25_v3_portfolio_20260616_070000")

    # ...but the cached pointer still resolves to the old one.
    assert sync_service.get_latest_experiment_dir("om25_v3") == old


def test_refresh_advances_pointer_to_newest_run(data_root):
    """The fix: refresh_latest_pointer re-points at the newest valid run."""
    _make_run(data_root, "om25_v3_portfolio_20260601_070000")
    sync_service.get_latest_experiment_dir("om25_v3")  # cache stale pointer

    newest = _make_run(data_root, "om25_v3_portfolio_20260616_070000")

    assert sync_service.refresh_latest_pointer("om25_v3") == newest
    # Subsequent shared reads now see the fresh run.
    assert sync_service.get_latest_experiment_dir("om25_v3") == newest


def test_refresh_ignores_runs_without_holdings(data_root):
    """A half-written run dir (no holdings CSV) must not become 'latest'."""
    good = _make_run(data_root, "om25_v3_portfolio_20260601_070000")

    # Newer dir by name, but missing the holdings CSV — must be skipped.
    incomplete = data_root / "data" / "om25_v3_portfolios" / "om25_v3_portfolio_20260616_070000"
    (incomplete / "backtests" / "baseline").mkdir(parents=True)

    assert sync_service.refresh_latest_pointer("om25_v3") == good
