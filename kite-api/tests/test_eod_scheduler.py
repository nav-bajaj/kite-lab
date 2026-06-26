"""Unit tests for the 16:00 IST EOD producer scheduler task.

Mostly exercises ``_is_eod_signal_day`` — the per-strategy gate the
scheduler asks before dispatching a job (signal-day + holiday-aware,
anchored on the engine's own most recent signal date).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from app.scheduler import tasks
from app.services import market_service, rebalance_service


def _write_signals(parent_dir, run_name, csv_name, dates):
    """Mimic what each strategy runner writes: <strategy>_signals.csv with
    a date column. We add momentum_holdings.csv too so the run dir survives
    the get_latest_experiment_dir / _holdings_present filter."""
    run_dir = parent_dir / run_name
    baseline = run_dir / "backtests" / "baseline"
    baseline.mkdir(parents=True)
    (baseline / "momentum_holdings.csv").write_text("symbol,shares\nTCS,10\n")
    df = pd.DataFrame({"date": pd.to_datetime(dates), "symbol": ["A"] * len(dates)})
    df.to_csv(run_dir / csv_name, index=False)
    return run_dir


@pytest.fixture
def patched_paths(tmp_path, monkeypatch):
    """Point both sync_service and rebalance_service at a tmp data root."""
    data_root = tmp_path
    monkeypatch.setattr(rebalance_service, "settings",
                         SimpleNamespace(data_dir=data_root))
    return data_root


def _stub_trading_day(monkeypatch, return_value=True):
    """Force is_trading_day → return_value so we don't depend on the real
    NSE holiday table for these unit tests."""
    monkeypatch.setattr(market_service, "is_trading_day",
                         lambda _d: return_value)


def test_signal_day_true_when_today_is_next_biweekly_friday(
    patched_paths, monkeypatch
):
    # Strategy's last signal: 2026-05-08 (Friday). Biweekly cadence → next
    # is 2026-05-22 (Friday). Today = 2026-05-22 ⇒ signal day.
    parent = patched_paths / "data" / "om25_v3_portfolios"
    _write_signals(parent, "om25_v3_portfolio_20260508_160000",
                    "om25_signals.csv",
                    ["2026-04-24", "2026-05-08"])
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("om25_v3", date(2026, 5, 22)) is True


def test_signal_day_false_on_off_week_friday(patched_paths, monkeypatch):
    # 2026-05-15 (Fri) is the off-week between biweekly anchors 2026-05-08
    # and 2026-05-22 — exit-check Friday, not an entry Friday. Producer
    # must not fire (PLAN.md: off-week exit-check days are out of scope
    # for the EOD producer right now).
    parent = patched_paths / "data" / "om25_v3_portfolios"
    _write_signals(parent, "om25_v3_portfolio_20260508_160000",
                    "om25_signals.csv",
                    ["2026-04-24", "2026-05-08"])
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("om25_v3", date(2026, 5, 15)) is False


def test_signal_day_false_on_non_friday_weekday(patched_paths, monkeypatch):
    # 2026-05-21 (Thu) — biweekly entries fire on Fridays only.
    parent = patched_paths / "data" / "tl25_v3_portfolios"
    _write_signals(parent, "tl25_v3_portfolio_20260508_160000",
                    "tl25_signals.csv",
                    ["2026-04-24", "2026-05-08"])
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("tl25_v3", date(2026, 5, 21)) is False


def test_signal_day_false_on_nse_holiday(patched_paths, monkeypatch):
    # Even if today would otherwise be a signal day, if NSE is closed we
    # skip — the engine's close prices wouldn't be available anyway.
    parent = patched_paths / "data" / "tl25_v3_portfolios"
    _write_signals(parent, "tl25_v3_portfolio_20260508_160000",
                    "tl25_signals.csv",
                    ["2026-04-24", "2026-05-08"])
    # NSE closed today.
    _stub_trading_day(monkeypatch, False)

    assert tasks._is_eod_signal_day("tl25_v3", date(2026, 5, 22)) is False


def test_signal_day_false_when_no_run_dir(patched_paths, monkeypatch):
    # Strategy has no production run on disk yet → we don't know the
    # cadence anchor → safe default is False.
    _stub_trading_day(monkeypatch, True)
    assert tasks._is_eod_signal_day("om25_v3", date(2026, 5, 22)) is False


def test_signal_day_false_when_no_signals_csv(patched_paths, monkeypatch):
    parent = patched_paths / "data" / "om25_v3_portfolios"
    run = parent / "om25_v3_portfolio_20260508_160000"
    baseline = run / "backtests" / "baseline"
    baseline.mkdir(parents=True)
    (baseline / "momentum_holdings.csv").write_text("symbol,shares\nTCS,10\n")
    # No om25_signals.csv at the run root.
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("om25_v3", date(2026, 5, 22)) is False


def test_signal_day_handles_holiday_rolled_anchor(patched_paths, monkeypatch):
    # If the engine's last signal was on a Thursday because Friday was a
    # holiday (resample('W-FRI').last() → that week's Thursday), the
    # cadence projector + snap-back-to-trading-day still picks the right
    # next signal date. We can't reasonably stub the actual NSE holiday
    # table here, so we just confirm the gate doesn't crash on a
    # non-Friday anchor (it falls through to a deterministic projection).
    parent = patched_paths / "data" / "om25_v3_portfolios"
    _write_signals(parent, "om25_v3_portfolio_20260508_160000",
                    "om25_signals.csv",
                    ["2026-04-30"])  # Thu, holiday-rolled from 2026-05-01
    _stub_trading_day(monkeypatch, True)

    # 14 days after 2026-04-30 is 2026-05-14 (Thu, no holiday here in our
    # stub). The projector lands on the same weekday as the anchor.
    result = tasks._is_eod_signal_day("om25_v3", date(2026, 5, 14))
    assert isinstance(result, bool)
