"""Morning day-plan generator (Judgment-layer prototype)."""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text

from app.microstructure import day_plan as DP
from app.microstructure.gamma_profile import gamma_profile_daily
from app.microstructure.paper_straddle import paper_straddle_ledger
from app.workers.options.bar_store import BarStore


class TestRecommendStructure:
    """The pure decision core — the regime->structure logic."""

    def test_pin_healthy_credit_sells_straddle(self):
        r = DP.recommend_structure("PIN-GRAVITY", 0.5, credit_thin=False,
                                   is_expiry=False, max_gamma_strike=24000.0)
        assert r["structure"] == "SHORT_STRADDLE"
        assert r["center_strike"] == 24000.0

    def test_pin_thin_expiry_credit_goes_defined_risk(self):
        r = DP.recommend_structure("PIN-GRAVITY", 0.4, credit_thin=True,
                                   is_expiry=True, max_gamma_strike=24600.0)
        assert r["structure"] == "IRON_FLY"
        # the Aug-04 lesson must be explicit
        assert any("naked straddle" in c.lower() for c in r["caveats"])

    def test_diffuse_low_iv_prefers_directional_or_aside(self):
        r = DP.recommend_structure("DIFFUSE", 0.3, credit_thin=False,
                                   is_expiry=False, max_gamma_strike=24400.0)
        assert r["structure"] == "DIRECTIONAL_DEBIT_SPREAD"
        # the up-drift-only sample caveat must be present (no assumed symmetry)
        assert any("down-diffuse" in c.lower() or "up-drift" in c.lower() for c in r["caveats"])

    def test_diffuse_rich_iv_uses_wings(self):
        r = DP.recommend_structure("DIFFUSE", 0.85, credit_thin=False,
                                   is_expiry=False, max_gamma_strike=24400.0)
        assert r["structure"] == "DEFINED_RISK_SHORT"

    def test_mixed_reduces_size(self):
        r = DP.recommend_structure("MIXED", 0.5, credit_thin=False,
                                   is_expiry=False, max_gamma_strike=24500.0)
        assert r["structure"] == "REDUCED_SIZE"

    def test_unknown_stands_aside(self):
        r = DP.recommend_structure("UNKNOWN", None, credit_thin=False,
                                   is_expiry=False, max_gamma_strike=None)
        assert r["structure"] == "STAND_ASIDE"


def _seed_state(url, day="2026-08-04", conc=0.30, expiry="2026-08-04",
                atm_iv=0.18, credit_ce=46.0, credit_pe=47.0):
    """A gamma_profile_daily @10:00 + ATM bars @10:00 + a few ledger rows."""
    store = BarStore(database_url=url)
    exp = date.fromisoformat(expiry)
    minute = datetime.fromisoformat(day + "T10:00") - timedelta(hours=5, minutes=30)
    base = dict(minute=minute, open=0, high=0, low=0, volume=0, oi_open=0, oi_high=0,
                oi_low=0, oi_close=50000, bid_qty_close=None, ask_qty_close=None,
                avg_spread=None, avg_depth_imbalance=None, tick_count=1)
    rows = [
        {**base, "contract_id": "NIFTY_SPOT", "kind": "SPOT", "expiry": None, "strike": None,
         "close": 24600.0, "bid_close": None, "ask_close": None},
        {**base, "contract_id": "C", "kind": "CE", "expiry": exp, "strike": 24600.0,
         "close": credit_ce, "bid_close": credit_ce - 0.5, "ask_close": credit_ce + 0.5},
        {**base, "contract_id": "P", "kind": "PE", "expiry": exp, "strike": 24600.0,
         "close": credit_pe, "bid_close": credit_pe - 0.5, "ask_close": credit_pe + 0.5},
    ]
    store.insert_bars(rows)
    store.dispose()

    e = create_engine(url)
    gamma_profile_daily.metadata.create_all(e, checkfirst=True)
    paper_straddle_ledger.metadata.create_all(e, checkfirst=True)
    now = datetime.now(timezone.utc)
    with e.begin() as c:
        c.execute(gamma_profile_daily.insert().values(
            session_date=date.fromisoformat(day), snap_time="10:00", expiry=exp,
            forward=24600.0, total_gex_cr=100000.0, max_gamma_strike=24600.0,
            concentration=conc, atm_iv=atm_iv, computed_at=now))
        # prior winning sessions with fatter credits -> today's is 'thin'
        for i, (cr, pnl, mae) in enumerate([(239.0, 16.2, -13.3), (272.7, 7.8, -11.6),
                                            (195.2, 18.4, -12.2)]):
            c.execute(paper_straddle_ledger.insert().values(
                session_date=date(2026, 7, 28 + i), strike=24000.0, entry_credit=cr,
                final_pnl=pnl, mae=mae, mae_time="10:00", underwater_minutes=20,
                last_underwater="10:20", detail="{}", computed_at=now))
    e.dispose()


class TestBuildPlan:
    def test_thin_expiry_credit_end_to_end(self, tmp_path):
        url = f"sqlite:///{tmp_path}/dp.db"
        # conc 0.30 -> MIXED... use 0.40 for PIN + expiry + thin credit (93 pts)
        _seed_state(url, conc=0.40, credit_ce=46.0, credit_pe=47.0)
        e = create_engine(url)
        with e.connect() as conn:
            plan = DP.build_plan(conn, "2026-08-04", as_of="10:00")
        e.dispose()
        assert plan is not None
        assert plan["regime"] == "PIN-GRAVITY"
        assert plan["is_expiry"] is True
        assert plan["atm_credit"] == pytest.approx(93.0, abs=1.0)
        assert plan["credit_thin"] is True   # 93 < min winning credit 195.2
        assert plan["recommendation"]["structure"] == "IRON_FLY"
        # render must not raise and must carry the advisory framing
        md = "\n".join(DP.render_plan(plan))
        assert "ADVISORY" in md
        assert "IRON_FLY" in md

    def test_missing_state_returns_none(self, tmp_path):
        url = f"sqlite:///{tmp_path}/dp2.db"
        gamma_profile_daily.metadata.create_all(create_engine(url), checkfirst=True)
        e = create_engine(url)
        with e.connect() as conn:
            assert DP.build_plan(conn, "2099-01-01", as_of="10:00") is None
        e.dispose()
