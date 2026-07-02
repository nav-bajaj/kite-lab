"""Unit tests for the 16:00 IST EOD producer scheduler task.

The gate ``_is_eod_signal_day`` decides per-strategy whether the cron
should dispatch a job. It sources the cadence anchor from the DB Trade
table (most recent BUY exec_date), then asks
``rebalance_service.project_next_signal`` to project the next entry-cadence
date. Compares to ``today``.

The old implementation read the anchor from a per-strategy signals CSV in
the latest run dir; that broke for l6_v2 (weekly Thu-Fri) which never
writes a signals CSV. This test file exercises the new DB-backed path
and covers the l6_v2 gap.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.models import EquityCurve, OpenPosition, Trade
from app.scheduler import tasks
from app.services import market_service


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[Trade.__table__, EquityCurve.__table__, OpenPosition.__table__],
    )
    return sessionmaker(bind=engine, autoflush=False)()


@pytest.fixture
def install_session(monkeypatch):
    """Patch tasks._is_eod_signal_day's session factory to yield our sqlite."""
    def install(session):
        from app.models import database as db_module
        monkeypatch.setattr(db_module, "get_session_local",
                             lambda: (lambda: session))
    return install


def _stub_trading_day(monkeypatch, return_value=True):
    monkeypatch.setattr(market_service, "is_trading_day",
                         lambda _d: return_value)


def _add_buy(session, universe, trade_date):
    session.add(Trade(
        universe=universe, trade_date=trade_date, symbol="ANCHOR",
        side="BUY", shares=Decimal(1), price=Decimal(100),
        notional=Decimal(100),
    ))
    session.commit()


# ============================================================
# Biweekly strategies (om25_v3, tl25_v3) — cadence parity from Trade table
# ============================================================

def test_biweekly_true_on_next_expected_friday(
    db_session, install_session, monkeypatch,
):
    # Anchor entry-bearing trade: 2026-05-04 (Mon exec for Thu 04-30 signal,
    # because Fri 5/1 was Labour Day). Next biweekly signal in the week-
    # bucket domain lands on Fri 2026-05-15 → exec Mon 2026-05-18.
    # Today = signal day (Fri 2026-05-15) → gate must return True.
    _add_buy(db_session, "om25_v3", date(2026, 5, 4))
    install_session(db_session)
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("om25_v3", date(2026, 5, 15)) is True


def test_biweekly_false_on_off_week_friday(
    db_session, install_session, monkeypatch,
):
    # Off-week Friday between biweekly anchors — no entry cadence.
    _add_buy(db_session, "om25_v3", date(2026, 5, 4))
    install_session(db_session)
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("om25_v3", date(2026, 5, 8)) is False


def test_biweekly_false_on_thursday_when_cadence_is_friday(
    db_session, install_session, monkeypatch,
):
    _add_buy(db_session, "tl25_v3", date(2026, 5, 4))
    install_session(db_session)
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("tl25_v3", date(2026, 5, 14)) is False


# ============================================================
# Weekly Thu-Fri strategies (l6_v2) — this was the bug
# ============================================================

def test_l6_v2_true_on_signal_thursday(
    db_session, install_session, monkeypatch,
):
    # l6_v2 signal on Thu, exec on Fri. Anchor exec Fri 2026-05-01 → anchor
    # signal Thu 2026-04-30. Next signal one week later = Thu 2026-05-07.
    _add_buy(db_session, "l6_v2", date(2026, 5, 1))
    install_session(db_session)
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("l6_v2", date(2026, 5, 7)) is True


def test_l6_v2_true_on_today_2026_07_02(
    db_session, install_session, monkeypatch,
):
    # Regression test for the user's report — Thu 2026-07-02 with a fresh
    # anchor should fire for l6_v2.
    _add_buy(db_session, "l6_v2", date(2026, 6, 26))  # last week's Fri exec
    install_session(db_session)
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("l6_v2", date(2026, 7, 2)) is True


def test_l6_v2_false_on_wednesday(
    db_session, install_session, monkeypatch,
):
    _add_buy(db_session, "l6_v2", date(2026, 5, 1))
    install_session(db_session)
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("l6_v2", date(2026, 5, 6)) is False


# ============================================================
# Shared skip conditions
# ============================================================

def test_skip_on_nse_holiday(
    db_session, install_session, monkeypatch,
):
    _add_buy(db_session, "tl25_v3", date(2026, 5, 4))
    install_session(db_session)
    _stub_trading_day(monkeypatch, False)

    assert tasks._is_eod_signal_day("tl25_v3", date(2026, 5, 15)) is False


def test_skip_when_no_buy_trades_in_db(
    db_session, install_session, monkeypatch,
):
    # New strategy with no historical trades yet — nothing to anchor on.
    install_session(db_session)
    _stub_trading_day(monkeypatch, True)

    assert tasks._is_eod_signal_day("om25_v3", date(2026, 5, 15)) is False


def test_sell_only_trades_are_ignored_as_anchor(
    db_session, install_session, monkeypatch,
):
    # A weekly-exit-only SELL trade shouldn't set the cadence anchor for
    # biweekly parity — only entry-bearing (BUY) trades do.
    db_session.add(Trade(
        universe="om25_v3", trade_date=date(2026, 5, 8),
        symbol="EXIT", side="SELL", shares=Decimal(1), price=Decimal(100),
        notional=Decimal(100),
    ))
    db_session.commit()
    install_session(db_session)
    _stub_trading_day(monkeypatch, True)

    # No BUY anchor → gate returns False.
    assert tasks._is_eod_signal_day("om25_v3", date(2026, 5, 15)) is False
