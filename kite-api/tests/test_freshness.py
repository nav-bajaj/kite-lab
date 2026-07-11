"""Spec tests for the data-freshness / staleness monitor.

Authored test-first per tasks/insight_engine/TDD_POLICY.md. The monitor is
threshold/classifier logic (it decides fresh/stale/critical/missing per
source), so the expected outputs are derived from the external requirement
(the canonical VIX-froze-while-everything-advanced incident and the
documented tier boundaries), not from reading the implementation.

The motivating incident: INDIA_VIX.csv silently froze at 2026-05-08 while
every other index panel advanced to 2026-07-10. The reading date looked
current but the VIX input was ~2 months stale. These tests pin that the
monitor would have flagged it critical.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from app.services import freshness_service as fs


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _write_index_csv(directory: Path, name: str, dates, close: float = 100.0) -> Path:
    """Write a minimal OHLCV index CSV (date,open,high,low,close,volume)."""
    directory.mkdir(parents=True, exist_ok=True)
    rows = [
        {"date": pd.Timestamp(d).date().isoformat(),
         "open": close, "high": close, "low": close, "close": close, "volume": 0}
        for d in dates
    ]
    path = directory / f"{name}.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _write_stock_day_csv(directory: Path, symbol: str, dates, close: float = 100.0) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    rows = [
        {"date": pd.Timestamp(d).date().isoformat(),
         "open": close, "high": close, "low": close, "close": close, "volume": 0}
        for d in dates
    ]
    path = directory / f"{symbol}_day.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


@pytest.fixture
def trading_dates():
    """~120 business days ending on a fixed reference Friday."""
    idx = pd.bdate_range(end="2026-07-10", periods=120)
    return [d.date() for d in idx]


# ---------------------------------------------------------------------------
# trading_day_lag — reference-based calendar math (the core design)
# ---------------------------------------------------------------------------

def test_trading_day_lag_zero_when_equal(trading_dates):
    ref = trading_dates[-1]
    assert fs.trading_day_lag(trading_dates, ref, ref) == 0


def test_trading_day_lag_one_step_behind(trading_dates):
    ref = trading_dates[-1]
    prev = trading_dates[-2]
    assert fs.trading_day_lag(trading_dates, prev, ref) == 1


def test_trading_day_lag_counts_actual_dates(trading_dates):
    ref = trading_dates[-1]
    behind = trading_dates[-6]  # 5 trading dates back
    assert fs.trading_day_lag(trading_dates, behind, ref) == 5


def test_trading_day_lag_skips_weekend(trading_dates):
    """Friday data evaluated against the following Wednesday must count the
    intervening trading dates (Mon/Tue/Wed) = 3, not the 5 wall-clock days."""
    # Find a Friday and the Wednesday 3 trading-days later in the calendar.
    fridays = [d for d in trading_dates if d.weekday() == 4]
    friday = fridays[-2]
    i = trading_dates.index(friday)
    wednesday = trading_dates[i + 3]
    assert wednesday.weekday() == 2  # sanity: it is a Wednesday
    assert (wednesday - friday).days == 5  # sanity: weekend spanned
    assert fs.trading_day_lag(trading_dates, friday, wednesday) == 3


def test_trading_day_lag_clamps_when_ahead(trading_dates):
    ref = trading_dates[-3]
    ahead = trading_dates[-1]
    assert fs.trading_day_lag(trading_dates, ahead, ref) == 0


# ---------------------------------------------------------------------------
# classify_daily — status tiers (transparent operational thresholds)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lag,expected", [
    (0, "fresh"),
    (1, "fresh"),
    (2, "stale"),
    (5, "stale"),
    (6, "critical"),
    (40, "critical"),
])
def test_classify_daily_lag_tiers(lag, expected):
    # small wall-clock age so the age override does not fire
    assert fs.classify_daily(lag, age_days=lag + 1) == expected


def test_classify_daily_wall_clock_override():
    """Even at lag 0, a >10-day wall-clock gap is critical (guards against the
    reference index itself being frozen, so lag reads 0 for everything)."""
    assert fs.classify_daily(0, age_days=11) == "critical"
    assert fs.classify_daily(1, age_days=10) == "fresh"


# ---------------------------------------------------------------------------
# classify_monthly — wall-clock tiers for slow-moving snapshots
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("age,expected", [
    (10, "fresh"),
    (39, "fresh"),
    (40, "stale"),
    (70, "stale"),
    (71, "critical"),
])
def test_classify_monthly_tiers(age, expected):
    assert fs.classify_monthly(age) == expected


# ---------------------------------------------------------------------------
# classify_token — session-cadence expiry logic
# ---------------------------------------------------------------------------

def test_classify_token_fresh_when_valid_and_far_from_expiry():
    assert fs.classify_token(valid=True, hours_to_expiry=5.0, file_missing=False) == "fresh"


def test_classify_token_stale_near_expiry():
    assert fs.classify_token(valid=True, hours_to_expiry=1.0, file_missing=False) == "stale"


def test_classify_token_critical_when_expired():
    assert fs.classify_token(valid=False, hours_to_expiry=None, file_missing=False) == "critical"


def test_classify_token_missing_when_no_file():
    assert fs.classify_token(valid=False, hours_to_expiry=None, file_missing=True) == "missing"


# ---------------------------------------------------------------------------
# last_csv_date — cheap last-row date read
# ---------------------------------------------------------------------------

def test_last_csv_date(tmp_path, trading_dates):
    path = _write_index_csv(tmp_path, "NIFTY_50", trading_dates)
    assert fs.last_csv_date(path) == trading_dates[-1]


def test_last_csv_date_missing_file(tmp_path):
    assert fs.last_csv_date(tmp_path / "nope.csv") is None


def test_last_csv_date_header_only(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("date,open,high,low,close,volume\n")
    assert fs.last_csv_date(path) is None


# ---------------------------------------------------------------------------
# build_daily_source — one row end-to-end
# ---------------------------------------------------------------------------

def test_build_daily_source_fresh(trading_dates):
    ref = trading_dates[-1]
    row = fs.build_daily_source(
        name="Nifty 50", kind="index", last_date=ref,
        trading_dates=trading_dates, reference_date=ref, today=ref,
    )
    assert row.status == "fresh"
    assert row.lag_trading_days == 0
    assert row.last_date == ref.isoformat()


def test_build_daily_source_stale(trading_dates):
    ref = trading_dates[-1]
    behind = trading_dates[-4]  # 3 trading days back
    row = fs.build_daily_source(
        name="X", kind="index", last_date=behind,
        trading_dates=trading_dates, reference_date=ref, today=ref,
    )
    assert row.status == "stale"
    assert row.lag_trading_days == 3


def test_build_daily_source_critical(trading_dates):
    ref = trading_dates[-1]
    behind = trading_dates[-31]  # 30 trading days back
    row = fs.build_daily_source(
        name="X", kind="index", last_date=behind,
        trading_dates=trading_dates, reference_date=ref, today=ref,
    )
    assert row.status == "critical"
    assert row.lag_trading_days == 30


def test_build_daily_source_missing():
    row = fs.build_daily_source(
        name="X", kind="index", last_date=None,
        trading_dates=[], reference_date=None, today=date(2026, 7, 10),
    )
    assert row.status == "missing"
    assert row.last_date is None


# ---------------------------------------------------------------------------
# The canonical VIX incident — full report
# ---------------------------------------------------------------------------

def test_vix_stale_incident_flagged_critical(tmp_path, trading_dates):
    """Indices at 2026-07-10, VIX frozen at ~40 trading days back. The VIX row
    must be critical and the overall report status must be critical."""
    indices = tmp_path / "indices"
    ref = trading_dates[-1]
    vix_date = trading_dates[-41]

    _write_index_csv(indices, "NIFTY_50", trading_dates)
    _write_index_csv(indices, "NIFTY_100", trading_dates)
    _write_index_csv(indices, "NIFTY_500", trading_dates)
    _write_index_csv(indices, "NIFTY_BANK", trading_dates)
    _write_index_csv(indices, "NIFTY_IT", trading_dates)
    _write_index_csv(indices, "INDIA_VIX", trading_dates[:-40])  # last = trading_dates[-41]

    report = fs.get_freshness_report(
        today=ref,
        indices_directory=indices,
        stock_panel_dir=tmp_path / "no_panel",
        cross_asset_dir=indices,
        sector_constituents_root=tmp_path / "no_sectors",
        index_weights_root=tmp_path / "no_weights",
        include_db=False,
        include_token=False,
    )

    assert report["generated_for_reference_date"] == ref.isoformat()
    vix_rows = [s for s in report["sources"]
                if s["kind"] == "index" and "VIX" in s["name"]]
    assert len(vix_rows) == 1
    vix = vix_rows[0]
    assert vix["status"] == "critical"
    assert vix["last_date"] == vix_date.isoformat()
    assert vix["lag_trading_days"] == 40
    assert report["overall_status"] == "critical"


def test_core_indices_fresh(tmp_path, trading_dates):
    indices = tmp_path / "indices"
    ref = trading_dates[-1]
    for name in ("NIFTY_50", "NIFTY_100", "NIFTY_500"):
        _write_index_csv(indices, name, trading_dates)

    report = fs.get_freshness_report(
        today=ref,
        indices_directory=indices,
        stock_panel_dir=tmp_path / "no_panel",
        cross_asset_dir=indices,
        sector_constituents_root=tmp_path / "no_sectors",
        index_weights_root=tmp_path / "no_weights",
        include_db=False,
        include_token=False,
    )
    core = [s for s in report["sources"]
            if s["kind"] == "index" and s["name"] in
            ("Nifty 50", "Nifty 100", "Nifty 500")]
    assert core
    assert all(s["status"] == "fresh" for s in core)


# ---------------------------------------------------------------------------
# Stock panel aggregate + worst-laggards
# ---------------------------------------------------------------------------

def test_stock_panel_surfaces_worst_laggards(tmp_path, trading_dates):
    indices = tmp_path / "indices"
    panel = tmp_path / "panel"
    ref = trading_dates[-1]
    _write_index_csv(indices, "NIFTY_50", trading_dates)
    _write_index_csv(indices, "NIFTY_100", trading_dates)

    # 8 fresh symbols, 1 badly stale
    for i in range(8):
        _write_stock_day_csv(panel, f"FRESH{i}", trading_dates)
    _write_stock_day_csv(panel, "STALEONE", trading_dates[:-30])  # 30 trading days behind

    report = fs.get_freshness_report(
        today=ref,
        indices_directory=indices,
        stock_panel_dir=panel,
        cross_asset_dir=indices,
        sector_constituents_root=tmp_path / "no_sectors",
        index_weights_root=tmp_path / "no_weights",
        include_db=False,
        include_token=False,
    )
    panel_rows = [s for s in report["sources"] if s["kind"] == "stock_panel"]
    assert len(panel_rows) == 1
    prow = panel_rows[0]
    assert prow["status"] == "critical"
    assert "STALEONE" in prow["detail"]


# ---------------------------------------------------------------------------
# Monthly sources
# ---------------------------------------------------------------------------

def test_sector_constituents_monthly_fresh(tmp_path, trading_dates):
    indices = tmp_path / "indices"
    _write_index_csv(indices, "NIFTY_50", trading_dates)
    _write_index_csv(indices, "NIFTY_100", trading_dates)
    ref = trading_dates[-1]

    # snapshot dated the same month as the reference -> fresh
    sc_root = tmp_path / "sector_constituents"
    (sc_root / ref.strftime("%Y-%m")).mkdir(parents=True)
    (sc_root / ref.strftime("%Y-%m") / "NIFTY_BANK.csv").write_text("Symbol\nHDFCBANK\n")

    report = fs.get_freshness_report(
        today=ref,
        indices_directory=indices,
        stock_panel_dir=tmp_path / "no_panel",
        cross_asset_dir=indices,
        sector_constituents_root=sc_root,
        index_weights_root=tmp_path / "no_weights",
        include_db=False,
        include_token=False,
    )
    rows = [s for s in report["sources"] if s["kind"] == "sector_constituents"]
    assert len(rows) == 1
    assert rows[0]["status"] == "fresh"
    assert rows[0]["expected_cadence"] == "monthly"


def test_index_weights_monthly_critical_when_old(tmp_path, trading_dates):
    indices = tmp_path / "indices"
    _write_index_csv(indices, "NIFTY_50", trading_dates)
    _write_index_csv(indices, "NIFTY_100", trading_dates)
    ref = trading_dates[-1]

    weights_root = tmp_path / "index_weights"
    old = (ref - timedelta(days=120))
    (weights_root / "NIFTY_50").mkdir(parents=True)
    (weights_root / "NIFTY_50" / f"{old.isoformat()}.csv").write_text("symbol,weight_pct\nX,1.0\n")

    report = fs.get_freshness_report(
        today=ref,
        indices_directory=indices,
        stock_panel_dir=tmp_path / "no_panel",
        cross_asset_dir=indices,
        sector_constituents_root=tmp_path / "no_sectors",
        index_weights_root=weights_root,
        include_db=False,
        include_token=False,
    )
    rows = [s for s in report["sources"] if s["kind"] == "index_weights"]
    assert len(rows) == 1
    assert rows[0]["status"] == "critical"


# ---------------------------------------------------------------------------
# Graceful degradation + serializability
# ---------------------------------------------------------------------------

def test_missing_dirs_degrade_to_missing_not_raise(tmp_path):
    """A report must build even when every source directory is absent."""
    report = fs.get_freshness_report(
        today=date(2026, 7, 10),
        indices_directory=tmp_path / "nope_indices",
        stock_panel_dir=tmp_path / "nope_panel",
        cross_asset_dir=tmp_path / "nope_cross",
        sector_constituents_root=tmp_path / "nope_sectors",
        index_weights_root=tmp_path / "nope_weights",
        include_db=False,
        include_token=False,
    )
    assert "sources" in report
    stock = [s for s in report["sources"] if s["kind"] == "stock_panel"]
    assert stock and stock[0]["status"] == "missing"


def test_report_is_json_serializable(tmp_path, trading_dates):
    indices = tmp_path / "indices"
    _write_index_csv(indices, "NIFTY_50", trading_dates)
    _write_index_csv(indices, "NIFTY_100", trading_dates)
    ref = trading_dates[-1]
    report = fs.get_freshness_report(
        today=ref,
        indices_directory=indices,
        stock_panel_dir=tmp_path / "no_panel",
        cross_asset_dir=indices,
        sector_constituents_root=tmp_path / "no_sectors",
        index_weights_root=tmp_path / "no_weights",
        include_db=False,
        include_token=False,
    )
    # Must not raise
    encoded = json.dumps(report)
    assert isinstance(encoded, str)
    # Every source row carries the locked field set
    for s in report["sources"]:
        assert set(s.keys()) == {
            "name", "kind", "last_date", "age_days", "lag_trading_days",
            "status", "detail", "expected_cadence",
        }


def test_default_report_builds_against_real_layout():
    """Smoke test: with no overrides the report builds off the real data
    locations (or degrades gracefully) and never raises."""
    report = fs.get_freshness_report(include_db=False, include_token=False)
    assert report["overall_status"] in ("fresh", "stale", "critical", "missing")
    assert isinstance(report["sources"], list)
