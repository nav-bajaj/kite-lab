"""Tests for the cadence-aware rebalance history + summary.

The Trade-table-derived history used to **silently drop** cycles where the
engine fired zero trades (rotations stayed inside the exit buffer, so no
rank-out SELL and no new BUY entries). Same for the summary's "Previous
rebalance" card — it anchored on the latest *trade* date, missing any
no-action cycle that fired afterwards.

We don't want a real DB here (JSONB columns aren't sqlite-friendly and
spinning Postgres up per test is overkill). Instead we patch
``get_session_local`` so the service code calls into a tiny in-memory
fake that we control. Same pattern as ``test_sync_proposed_rebalance``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from typing import Optional

import pytest

from app.services import rebalance_service as rs


# ---------- helper: stepping helper itself ---------------------------------

class TestExpectedCadenceHistory:
    """``expected_cadence_history`` walks the engine's parity backwards +
    forwards from a known entry-bearing exec date."""

    def test_biweekly_steps_back_14_days(self):
        # Anchor: Mon 2026-05-04 (exec for Thu 2026-04-30, Friday 2026-05-01
        # was Labour Day so the signal rolled to Thursday).
        pairs = rs.expected_cadence_history(
            today=date(2026, 5, 18),
            anchor_exec=date(2026, 5, 4),
            cadence_key="biweekly_fri",
            lookback_count=3,
        )
        exec_dates = [p[1] for p in pairs]
        # Most recent at or before today should be the 05-18 cycle (signal
        # Fri 2026-05-15 → exec Mon 2026-05-18). Then 05-04, then ~04-20.
        assert exec_dates[0] == date(2026, 5, 18)
        assert exec_dates[1] == date(2026, 5, 4)

    def test_forward_step_includes_today_if_exec_lands_today(self):
        # Signal Thu 2026-06-25 (Fri 2026-06-26 is Muharram), exec Mon 06-29.
        # Anchor at 2026-06-15. today=2026-06-29 should pull the 06-29 cycle in
        # via the forward walk, even though no trade has been logged for it
        # (the whole point — surface no-action cycles after the anchor).
        pairs = rs.expected_cadence_history(
            today=date(2026, 6, 29),
            anchor_exec=date(2026, 6, 15),
            cadence_key="biweekly_fri",
            lookback_count=2,
        )
        exec_dates = [p[1] for p in pairs]
        assert date(2026, 6, 29) in exec_dates
        assert date(2026, 6, 15) in exec_dates

    def test_does_not_yield_future_exec_dates(self):
        # No cycle whose exec > today should be returned.
        pairs = rs.expected_cadence_history(
            today=date(2026, 5, 4),
            anchor_exec=date(2026, 5, 4),
            cadence_key="biweekly_fri",
            lookback_count=5,
        )
        for _sig, exec_d in pairs:
            assert exec_d <= date(2026, 5, 4)

    def test_dedup_anchors_correctly(self):
        # The anchor itself should appear exactly once.
        pairs = rs.expected_cadence_history(
            today=date(2026, 5, 4),
            anchor_exec=date(2026, 5, 4),
            cadence_key="biweekly_fri",
            lookback_count=3,
        )
        execs = [p[1] for p in pairs]
        assert execs.count(date(2026, 5, 4)) == 1


# ---------- helper: real sqlite DB for the service to query ----------------

# Trade / EquityCurve / OpenPosition / Holding don't use JSONB so they're
# happy on sqlite. Spin one up per test, populate it, and patch the service's
# session factory so its production code path runs unchanged.
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.models import EquityCurve, OpenPosition, ProposedRebalance, Trade


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Trade.__table__, EquityCurve.__table__, OpenPosition.__table__,
        ],
    )
    # ProposedRebalance carries JSONB columns sqlite can't DDL-compile, but
    # the history path only reads its date + count columns — a hand-rolled
    # table (JSON columns stay null in tests) is enough.
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE proposed_rebalances ("
            "id INTEGER PRIMARY KEY, universe VARCHAR(20), exec_date DATE, "
            "signal_date DATE, data_as_of DATE, sell_count INTEGER, "
            "buy_count INTEGER, hold_count INTEGER, sells TEXT, buys TEXT, "
            "holds TEXT, regime VARCHAR(10), drawdown_from_peak NUMERIC, "
            "final_pv NUMERIC, initial_capital NUMERIC, created_at DATETIME)"
        ))
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    return SessionLocal()


@pytest.fixture
def patched_today(monkeypatch):
    """Pin ``date.today()`` inside rebalance_service to a fixed value.

    ``rebalance_service`` only uses ``date`` via ``date.today()`` at module
    scope (everywhere else it relies on ``timedelta`` arithmetic + the
    already-imported ``snap_back_to_trading_day`` / ``next_trading_day_after``
    helpers). So replacing the module's ``date`` symbol with a shim whose
    only role is ``today()`` is enough.
    """

    def install(d: date):
        monkeypatch.setattr(rs, "date", SimpleNamespace(today=lambda: d))
    return install


def _make_trade(*, universe, trade_date, symbol, side, notional, shares=1,
                price=100):
    return Trade(
        universe=universe, trade_date=trade_date, symbol=symbol, side=side,
        shares=Decimal(shares), price=Decimal(price),
        notional=Decimal(notional),
    )


@pytest.fixture
def install_session(monkeypatch):
    def install(session):
        monkeypatch.setattr(rs, "get_session_local",
                             lambda: (lambda: session))
    return install


# ---------- end-to-end behaviour --------------------------------------------

class TestGetRebalanceHistoryNoAction:
    def test_no_action_cycle_appears_between_traded_cycles(
        self, db_session, install_session, patched_today,
    ):
        # Production om25_v3 pattern: 04-06 traded, 04-20 no-action, 05-04 traded.
        db_session.add_all([
            _make_trade(universe="om25_v3", trade_date=date(2026, 4, 6),
                        symbol="OIL", side="BUY", notional=250000),
            _make_trade(universe="om25_v3", trade_date=date(2026, 4, 6),
                        symbol="CANBK", side="SELL", notional=230000),
            _make_trade(universe="om25_v3", trade_date=date(2026, 5, 4),
                        symbol="HINDALCO", side="BUY", notional=250000),
            _make_trade(universe="om25_v3", trade_date=date(2026, 5, 4),
                        symbol="UNIONBANK", side="SELL", notional=230000),
            EquityCurve(universe="om25_v3", date=date(2026, 4, 6),
                        portfolio_value=Decimal("10000000")),
            EquityCurve(universe="om25_v3", date=date(2026, 5, 4),
                        portfolio_value=Decimal("10000000")),
        ])
        db_session.commit()
        install_session(db_session)
        patched_today(date(2026, 5, 4))

        result = rs.get_rebalance_history("om25_v3", limit=5)

        rows = [(h["date"], h["no_action"]) for h in result["history"]]
        assert ("2026-04-20", True) in rows
        assert ("2026-05-04", False) in rows
        assert ("2026-04-06", False) in rows

    def test_empty_db_returns_empty_history(
        self, db_session, install_session, patched_today,
    ):
        install_session(db_session)
        patched_today(date(2026, 5, 4))
        assert rs.get_rebalance_history("om25_v3", limit=10) == {
            "universe": "om25_v3", "history": [], "count": 0,
        }

    def test_zero_trade_weekly_check_surfaces_from_proposal(
        self, db_session, install_session, patched_today,
    ):
        # Production 2026-07-17 pattern: last entry exec Mon 07-13, then the
        # off-week Friday exit check (signal 07-17, exec Mon 07-20) sold
        # nothing. It leaves no Trade rows and 07-20 is not on the entry
        # grid, so only the recorded ProposedRebalance can surface it.
        db_session.add_all([
            _make_trade(universe="om25_v3", trade_date=date(2026, 7, 13),
                        symbol="BSE", side="BUY", notional=250000),
            _make_trade(universe="om25_v3", trade_date=date(2026, 7, 13),
                        symbol="ENRIN", side="SELL", notional=230000),
            ProposedRebalance(
                universe="om25_v3", exec_date=date(2026, 7, 20),
                signal_date=date(2026, 7, 17), data_as_of=date(2026, 7, 17),
                sell_count=0, buy_count=0, hold_count=25,
            ),
        ])
        db_session.commit()
        install_session(db_session)
        patched_today(date(2026, 7, 21))

        rows = {h["date"]: h for h in
                rs.get_rebalance_history("om25_v3", limit=6)["history"]}
        assert rows["2026-07-20"]["no_action"] is True
        assert rows["2026-07-20"]["kind"] == "no_action"
        assert rows["2026-07-13"]["no_action"] is False

    def test_proposal_with_trades_does_not_add_no_action_row(
        self, db_session, install_session, patched_today,
    ):
        # A live proposal that HAS moves (not yet executed/synced) must not
        # masquerade as a completed no-action cycle.
        db_session.add_all([
            _make_trade(universe="om25_v3", trade_date=date(2026, 7, 13),
                        symbol="BSE", side="BUY", notional=250000),
            ProposedRebalance(
                universe="om25_v3", exec_date=date(2026, 7, 20),
                signal_date=date(2026, 7, 17), data_as_of=date(2026, 7, 17),
                sell_count=2, buy_count=3, hold_count=20,
            ),
        ])
        db_session.commit()
        install_session(db_session)
        patched_today(date(2026, 7, 21))

        dates = [h["date"] for h in
                 rs.get_rebalance_history("om25_v3", limit=6)["history"]]
        assert "2026-07-20" not in dates


class TestGetRebalanceSummaryNoAction:
    def test_previous_anchors_on_latest_cadence_when_no_action(
        self, db_session, install_session, patched_today,
    ):
        # Latest BUY trade: 2026-06-15. Today: 2026-06-29 (a biweekly exec
        # day, Muharram-rolled from Fri 06-26). Card must anchor on 06-29
        # no_action — NOT fall back to 06-15.
        db_session.add_all([
            _make_trade(universe="om25_v3", trade_date=date(2026, 6, 15),
                        symbol="TCS", side="BUY", notional=250000),
            _make_trade(universe="om25_v3", trade_date=date(2026, 6, 15),
                        symbol="INFY", side="SELL", notional=230000),
            EquityCurve(universe="om25_v3", date=date(2026, 6, 15),
                        portfolio_value=Decimal("10000000")),
        ])
        db_session.commit()
        install_session(db_session)
        patched_today(date(2026, 6, 29))

        prev = rs.get_rebalance_summary("om25_v3")["previous"]
        assert prev["date"] == "2026-06-29"
        assert prev["no_action"] is True
        assert prev["kind"] == "no_action"
        assert prev["buy_count"] == 0 and prev["sell_count"] == 0

    def test_previous_reflects_trade_when_today_is_trade_day(
        self, db_session, install_session, patched_today,
    ):
        db_session.add_all([
            _make_trade(universe="om25_v3", trade_date=date(2026, 6, 29),
                        symbol="TCS", side="BUY", notional=250000),
            _make_trade(universe="om25_v3", trade_date=date(2026, 6, 29),
                        symbol="INFY", side="SELL", notional=230000),
            EquityCurve(universe="om25_v3", date=date(2026, 6, 29),
                        portfolio_value=Decimal("10000000")),
        ])
        db_session.commit()
        install_session(db_session)
        patched_today(date(2026, 6, 29))

        prev = rs.get_rebalance_summary("om25_v3")["previous"]
        assert prev["date"] == "2026-06-29"
        assert prev["no_action"] is False
        assert prev["kind"] == "entry"
        assert "TCS" in prev["added"]

    def test_next_projects_from_signal_parity_not_exec_date(
        self, db_session, install_session, patched_today,
    ):
        # Regression: the "next" anchor passed the BUY *exec* date (Mon
        # 07-13) straight into project_next_signal, which rolled it onto its
        # own week's Friday (07-17) and reported the next entry a week late
        # (07-31). Anchored on the true signal (Fri 07-10), the next entry
        # is Fri 07-24 — and 07-31 is merely the off-week exit check.
        db_session.add_all([
            _make_trade(universe="om25_v3", trade_date=date(2026, 7, 13),
                        symbol="BSE", side="BUY", notional=250000),
            EquityCurve(universe="om25_v3", date=date(2026, 7, 13),
                        portfolio_value=Decimal("10000000")),
        ])
        db_session.commit()
        install_session(db_session)
        patched_today(date(2026, 7, 20))

        nxt = rs.get_rebalance_summary("om25_v3")["next"]
        assert nxt["signal_date"] == "2026-07-24"
        assert nxt["exec_date"] == "2026-07-27"

    def test_summary_survives_universe_with_zero_buy_trades(
        self, db_session, install_session, patched_today,
    ):
        # Regression (audit L1/L2): the "next" anchor used an undefined
        # ``last_date``, so ``get_rebalance_summary`` raised NameError for any
        # universe whose BUY query returned None (SELL-only / pre-first-entry).
        # It must instead fall back to the latest trade of any side.
        db_session.add_all([
            _make_trade(universe="om25_v3", trade_date=date(2026, 6, 15),
                        symbol="INFY", side="SELL", notional=230000),
            EquityCurve(universe="om25_v3", date=date(2026, 6, 15),
                        portfolio_value=Decimal("10000000")),
        ])
        db_session.commit()
        install_session(db_session)
        patched_today(date(2026, 6, 16))

        summary = rs.get_rebalance_summary("om25_v3")  # must not raise
        assert summary["next"] is not None
        assert summary["previous"]["kind"] == "weekly_exit"
        assert summary["previous"]["removed"] == ["INFY"]
