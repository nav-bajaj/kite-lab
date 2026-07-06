"""``get_upcoming_rebalance`` must flag a proposal whose exec_date has passed
(audit L4).

A failed/missed producer run leaves the previous proposal as the latest row.
Once its exec_date < today the rebalance it describes has already executed, so
the endpoint returns it with ``stale: true`` rather than presenting an executed
trade as upcoming. We stub the Session (JSONB rows aren't sqlite-friendly).
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.services import rebalance_service as rs


def _row(exec_date: date):
    return SimpleNamespace(
        exec_date=exec_date,
        signal_date=exec_date - timedelta(days=1),
        data_as_of=exec_date - timedelta(days=1),
        sells=["AAA"], buys=[], holds=["BBB"],
        sell_count=1, buy_count=0, hold_count=1,
        regime="bull", drawdown_from_peak=-0.1,
        final_pv=1_000_000, initial_capital=1_000_000,
    )


class _FakeQuery:
    def __init__(self, row):
        self._row = row

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def first(self):
        return self._row


class _FakeSession:
    def __init__(self, row):
        self._row = row

    def query(self, _model):
        return _FakeQuery(self._row)

    def close(self):
        pass


@pytest.fixture
def install_row(monkeypatch):
    def install(row):
        monkeypatch.setattr(rs, "get_session_local",
                            lambda: (lambda: _FakeSession(row)))
    return install


@pytest.fixture
def pin_today(monkeypatch):
    def install(d: date):
        monkeypatch.setattr(rs, "date", SimpleNamespace(today=lambda: d))
    return install


def test_future_exec_date_is_not_stale(install_row, pin_today):
    pin_today(date(2026, 6, 19))
    install_row(_row(date(2026, 6, 26)))
    out = rs.get_upcoming_rebalance("tl25_v3")
    assert out["available"] is True
    assert out["stale"] is False


def test_today_exec_date_is_not_stale(install_row, pin_today):
    pin_today(date(2026, 6, 19))
    install_row(_row(date(2026, 6, 19)))
    assert rs.get_upcoming_rebalance("tl25_v3")["stale"] is False


def test_past_exec_date_is_stale(install_row, pin_today):
    pin_today(date(2026, 6, 22))
    install_row(_row(date(2026, 6, 19)))
    out = rs.get_upcoming_rebalance("tl25_v3")
    assert out["available"] is True
    assert out["stale"] is True


def test_no_proposal_is_not_stale(install_row, pin_today):
    pin_today(date(2026, 6, 22))
    install_row(None)
    out = rs.get_upcoming_rebalance("tl25_v3")
    assert out["available"] is False
    assert out["stale"] is False
