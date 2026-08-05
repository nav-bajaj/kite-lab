"""MAE ledger + live gamma profile (Stage 2)."""
import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pytest
from sqlalchemy import create_engine, text

from app.microstructure import gamma_profile as GP
from app.microstructure import paper_straddle as PS
from app.microstructure.greeks import IST, b76_price
from app.workers.options.bar_store import BarStore


def seed_bars(url, day="2026-07-30"):
    """Synthetic session: ATM straddle decays 240 -> 220 with a -20 dip at 11:00."""
    store = BarStore(database_url=url)
    exp = date(2026, 8, 4)
    rows = []
    hms = [(9, 20), (10, 0), (11, 0), (12, 0), (15, 15)]
    ce_closes = [120.0, 118.0, 132.0, 115.0, 110.0]  # dip at 11:00 (price up = short loses)
    pe_closes = [120.0, 118.0, 128.0, 113.0, 110.0]
    for (h, m), ce, pe in zip(hms, ce_closes, pe_closes):
        # sqlite drops tzinfo -> store the UTC-naive equivalent of IST h:m
        minute = datetime(2026, 7, 30, h, m) - timedelta(hours=5, minutes=30)
        base = dict(minute=minute, open=0, high=0, low=0, volume=0,
                    oi_open=0, oi_high=0, oi_low=0, oi_close=50000,
                    bid_qty_close=None, ask_qty_close=None, avg_spread=None,
                    avg_depth_imbalance=None, tick_count=1)
        rows += [
            {**base, "contract_id": "S", "kind": "SPOT", "expiry": None, "strike": None,
             "close": 24000.0, "bid_close": None, "ask_close": None},
            {**base, "contract_id": "C", "kind": "CE", "expiry": exp, "strike": 24000.0,
             "close": ce, "bid_close": ce - 0.5, "ask_close": ce + 0.5},
            {**base, "contract_id": "P", "kind": "PE", "expiry": exp, "strike": 24000.0,
             "close": pe, "bid_close": pe - 0.5, "ask_close": pe + 0.5},
        ]
    # NIFTY_SPOT contract_id matters for the spot query
    for r in rows:
        if r["contract_id"] == "S":
            r["contract_id"] = "NIFTY_SPOT"
    store.insert_bars(rows)
    store.dispose()


class TestPaperStraddle:
    def test_mae_ledger_row(self, tmp_path):
        url = f"sqlite:///{tmp_path}/ps.db"
        seed_bars(url)
        row = PS.store_day("2026-07-30", database_url=url)
        assert row is not None
        assert row["strike"] == 24000.0
        assert row["entry_credit"] == pytest.approx(239.0)  # bids: 119.5 + 119.5
        # MAE at 11:00: credit 239 - (132+128)=260 -> -21
        assert row["mae"] == pytest.approx(-21.0)
        assert row["mae_time"] == "11:00"
        # 2 underwater minutes: the entry minute itself (bid-entry marks -1
        # vs closes — the spread is a real instant cost) and the 11:00 dip
        assert row["underwater_minutes"] == 2
        # exit at asks 110.5*2=221 -> +18
        assert row["final_pnl"] == pytest.approx(18.0)
        # idempotent
        row2 = PS.store_day("2026-07-30", database_url=url)
        e = create_engine(url)
        with e.connect() as c:
            assert c.execute(text("select count(*) from paper_straddle_ledger")).scalar() == 1
        e.dispose()


class TestLiveGammaProfile:
    def test_compute_from_snapshot(self):
        # build a synthetic but arbitrage-consistent chain at F=24000
        F, T, r, sig = 24000.0, 5 / 365, 0.065, 0.12
        contracts = {}
        for k in range(23500, 24550, 100):
            for kind in ("CE", "PE"):
                px = b76_price(F, float(k), T, r, sig, kind)
                contracts[f"NIFTY_20260804_{k}_{kind}"] = {
                    "kind": kind, "expiry": "2026-08-04", "strike": float(k),
                    "ltp": round(px, 2), "oi": 100000, "volume": 0,
                    "bid": px - 0.5, "ask": px + 0.5, "bid_qty": 0, "ask_qty": 0,
                }
        now = datetime(2026, 7, 30, 11, 0, tzinfo=IST).replace(
            tzinfo=timezone(timedelta(hours=5, minutes=30)))
        # T in compute comes from clock -> expiry; pick now so T ~ 5/365
        now = datetime(2026, 7, 30, 15, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        out = GP.compute_from_snapshot({"spot": 24000.0, "contracts": contracts}, now)
        assert out is not None
        assert out["forward"] == pytest.approx(F, abs=2.0)   # parity recovers F
        assert out["atm_iv"] == pytest.approx(sig, abs=0.01)  # IV recovers sigma
        assert out["max_gamma_strike"] == pytest.approx(24000.0)  # gamma peaks ATM
        assert out["regime"] in ("PIN-GRAVITY", "MIXED", "DIFFUSE")
        assert out["total_gex_cr"] > 0
        # spot == forward here -> no divergence, no flag
        assert out["divergence"] == pytest.approx(0.0, abs=2.0)
        assert out["divergence_flag"] is False

    def test_compute_from_snapshot_divergence_flag(self):
        # same arbitrage-consistent chain at F=24000, but the index spot prints
        # 200 pts above where the chain trades -> dislocation flag fires.
        F, T, r, sig = 24000.0, 5 / 365, 0.065, 0.12
        contracts = {}
        for k in range(23500, 24550, 100):
            for kind in ("CE", "PE"):
                px = b76_price(F, float(k), T, r, sig, kind)
                contracts[f"NIFTY_20260804_{k}_{kind}"] = {
                    "kind": kind, "expiry": "2026-08-04", "strike": float(k),
                    "ltp": round(px, 2), "oi": 100000, "volume": 0,
                    "bid": px - 0.5, "ask": px + 0.5, "bid_qty": 0, "ask_qty": 0,
                }
        now = datetime(2026, 7, 30, 15, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        out = GP.compute_from_snapshot({"spot": 24200.0, "contracts": contracts}, now)
        assert out is not None
        assert out["divergence"] == pytest.approx(200.0, abs=3.0)
        assert out["divergence_flag"] is True

    def test_snapshot_without_pairs_returns_none(self):
        contracts = {"X": {"kind": "CE", "expiry": "2026-08-04", "strike": 24000.0,
                           "ltp": 100.0, "oi": 1}}
        now = datetime(2026, 7, 30, 12, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        assert GP.compute_from_snapshot({"contracts": contracts}, now) is None


class TestDivergenceSection:
    """EOD spot-vs-parity-forward dislocation (daily_report._divergence_section)."""

    def _seed(self, url, day="2026-08-03"):
        from app.microstructure.materialize import _ensure_schema, option_greeks_minute

        exp = date(2026, 8, 4)
        # forward (chain-implied underlying) flat at 24400; spot flat at 24400
        # until a +180 close print at 15:29 -> the new-timings dislocation.
        minutes = [(10, 0, 24400.0), (13, 0, 24400.0), (15, 20, 24400.0), (15, 29, 24580.0)]
        store = BarStore(database_url=url)
        spot_rows = []
        for h, m, px in minutes:
            minute = datetime(2026, 8, 3, h, m) - timedelta(hours=5, minutes=30)
            spot_rows.append(dict(
                contract_id="NIFTY_SPOT", kind="SPOT", expiry=None, strike=None, minute=minute,
                open=0, high=0, low=0, close=px, volume=0, oi_open=0, oi_high=0, oi_low=0,
                oi_close=0, bid_close=None, ask_close=None, bid_qty_close=None,
                ask_qty_close=None, avg_spread=None, avg_depth_imbalance=None, tick_count=1))
        store.insert_bars(spot_rows)
        store.dispose()

        e = create_engine(url)
        _ensure_schema(e)
        now = datetime.now(timezone.utc)
        recs = [dict(
            contract_id="NIFTY_20260804_24400_CE", minute=datetime(2026, 8, 3, h, m) - timedelta(hours=5, minutes=30),
            expiry=exp, strike=24400.0, kind="CE", underlying=24400.0, underlying_src="parity",
            iv=0.12, delta=0.5, gamma=0.0001, vega=1.0, theta_day=-1.0, r=0.065,
            engine_version="test", computed_at=now) for h, m, _ in minutes]
        with e.begin() as c:
            c.execute(option_greeks_minute.insert(), recs)
        e.dispose()

    def test_close_print_dislocation_flags(self, tmp_path):
        from app.microstructure import daily_report as DR

        url = f"sqlite:///{tmp_path}/dv.db"
        self._seed(url)
        e = create_engine(url)
        out = []
        with e.connect() as conn:
            res = DR._divergence_section(conn, "2026-08-03", {"close": 24580.0}, out)
        e.dispose()
        assert res is not None
        assert res["baseline_gap"] == pytest.approx(0.0, abs=1.0)  # spot==forward normally
        assert res["max_dev"] == pytest.approx(180.0, abs=1.0)     # the close print
        assert res["max_dev_hm"] == "15:29"
        assert any("DIVERGENCE FLAG" in line for line in out)
