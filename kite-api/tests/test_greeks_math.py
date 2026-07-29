"""Stage-1 spec: Black-Scholes pricing, IV inversion, first-order Greeks.

TDD spec written BEFORE app/microstructure/greeks.py exists. Known values
computed independently (standard BS closed forms). Assumption set under
test: spot underlying, flat r, q=0 — see tasks/microstructure_engine/PLAN.md.
"""
import math
from datetime import date, datetime

import numpy as np
import pytest

from app.microstructure import greeks as G


S, K, T, R, SIG = 24000.0, 24000.0, 7 / 365, 0.065, 0.12


class TestPricing:
    def test_atm_call_known_value(self):
        # Independently computed with the plain closed form (math.erf), not
        # via the module under test: d1=0.04836, c=174.409.
        px = G.bs_price(S, K, T, R, SIG, "CE")
        assert px == pytest.approx(174.409, abs=0.05)

    def test_put_call_parity(self):
        c = G.bs_price(S, K, T, R, SIG, "CE")
        p = G.bs_price(S, K, T, R, SIG, "PE")
        assert c - p == pytest.approx(S - K * math.exp(-R * T), abs=1e-6)

    def test_deep_itm_call_approaches_forward_intrinsic(self):
        px = G.bs_price(S, 20000, T, R, 0.10, "CE")
        assert px == pytest.approx(S - 20000 * math.exp(-R * T), abs=0.5)

    def test_zero_time_is_intrinsic(self):
        assert G.bs_price(S, 23800, 0.0, R, SIG, "CE") == pytest.approx(200.0)
        assert G.bs_price(S, 24200, 0.0, R, SIG, "PE") == pytest.approx(200.0)


class TestImpliedVol:
    def test_round_trip_scalar(self):
        px = G.bs_price(S, K, T, R, 0.147, "CE")
        iv = G.implied_vol(np.array([px]), np.array([S]), np.array([K]),
                           np.array([T]), R, np.array(["CE"]))[0]
        assert iv == pytest.approx(0.147, abs=1e-4)

    def test_round_trip_vectorized_smile(self):
        strikes = np.array([23000, 23500, 24000, 24500, 25000], dtype=float)
        sigmas = np.array([0.18, 0.15, 0.12, 0.13, 0.16])
        kinds = np.array(["PE", "PE", "CE", "CE", "CE"])
        prices = np.array([G.bs_price(S, k, T, R, s, kd) for k, s, kd in zip(strikes, sigmas, kinds)])
        ivs = G.implied_vol(prices, np.full(5, S), strikes, np.full(5, T), R, kinds)
        np.testing.assert_allclose(ivs, sigmas, atol=1e-4)

    def test_below_intrinsic_returns_nan(self):
        ivs = G.implied_vol(np.array([100.0]), np.array([S]), np.array([23000.0]),
                            np.array([T]), R, np.array(["CE"]))  # intrinsic ~1000
        assert np.isnan(ivs[0])

    def test_expired_returns_nan(self):
        ivs = G.implied_vol(np.array([50.0]), np.array([S]), np.array([K]),
                            np.array([0.0]), R, np.array(["CE"]))
        assert np.isnan(ivs[0])


class TestGreeks:
    def test_call_minus_put_delta_is_one(self):
        g_c = G.greeks(np.array([S]), np.array([K]), np.array([T]), R,
                       np.array([SIG]), np.array(["CE"]))
        g_p = G.greeks(np.array([S]), np.array([K]), np.array([T]), R,
                       np.array([SIG]), np.array(["PE"]))
        assert g_c["delta"][0] - g_p["delta"][0] == pytest.approx(1.0, abs=1e-9)

    def test_gamma_vega_same_for_ce_pe(self):
        g_c = G.greeks(np.array([S]), np.array([K]), np.array([T]), R,
                       np.array([SIG]), np.array(["CE"]))
        g_p = G.greeks(np.array([S]), np.array([K]), np.array([T]), R,
                       np.array([SIG]), np.array(["PE"]))
        assert g_c["gamma"][0] == pytest.approx(g_p["gamma"][0], rel=1e-12)
        assert g_c["vega"][0] == pytest.approx(g_p["vega"][0], rel=1e-12)

    def test_atm_call_delta_near_half(self):
        g = G.greeks(np.array([S]), np.array([K]), np.array([T]), R,
                     np.array([SIG]), np.array(["CE"]))
        assert 0.5 < g["delta"][0] < 0.56  # slightly above .5 with positive carry

    def test_gamma_peaks_at_atm(self):
        ks = np.array([23000.0, 24000.0, 25000.0])
        g = G.greeks(np.full(3, S), ks, np.full(3, T), R, np.full(3, SIG),
                     np.array(["CE", "CE", "CE"]))
        assert g["gamma"][1] > g["gamma"][0] and g["gamma"][1] > g["gamma"][2]

    def test_theta_negative_for_long_options(self):
        g = G.greeks(np.array([S]), np.array([K]), np.array([T]), R,
                     np.array([SIG]), np.array(["CE"]))
        assert g["theta"][0] < 0


class TestTimeToExpiry:
    def test_t_years_before_and_after_cutoff(self):
        expiry = date(2026, 8, 4)
        t1 = G.t_years(datetime.fromisoformat("2026-07-28T15:30:00+05:30"), expiry)
        assert t1 == pytest.approx(7 / 365, rel=1e-6)
        t2 = G.t_years(datetime.fromisoformat("2026-08-04T15:30:00+05:30"), expiry)
        assert t2 == 0.0
        t3 = G.t_years(datetime.fromisoformat("2026-08-05T10:00:00+05:30"), expiry)
        assert t3 == 0.0


class TestMaterializer:
    def test_roundtrip_on_sqlite(self, tmp_path):
        from app.workers.options.bar_store import BarStore
        from app.microstructure import materialize as M
        from sqlalchemy import create_engine, text as sqltext

        url = f"sqlite:///{tmp_path}/mat.db"
        store = BarStore(database_url=url)
        minute = datetime.fromisoformat("2026-07-29T10:00:00+05:30")
        base = dict(minute=minute, oi_open=0, oi_high=0, oi_low=0, oi_close=0,
                    volume=0, bid_close=None, ask_close=None, bid_qty_close=None,
                    ask_qty_close=None, avg_spread=None, avg_depth_imbalance=None,
                    tick_count=1, open=0, high=0, low=0)
        exp = date(2026, 8, 4)
        store.insert_bars([
            {**base, "contract_id": "NIFTY_SPOT", "kind": "SPOT", "expiry": None,
             "strike": None, "close": 24000.0},
            {**base, "contract_id": "NIFTY_20260804_24000_CE", "kind": "CE",
             "expiry": exp, "strike": 24000.0, "close": 180.0},
            {**base, "contract_id": "NIFTY_20260804_25000_CE", "kind": "CE",
             "expiry": exp, "strike": 25000.0, "close": 26000.0},  # a call can never exceed S — unattainable
        ])
        n = M.run(days=["2026-07-29"], database_url=url)
        assert n == 2  # spot excluded; both CE rows written
        e = create_engine(url)
        with e.connect() as c:
            rows = {r[0]: r for r in c.execute(sqltext(
                "select contract_id, iv, delta, gamma from option_greeks_minute"))}
        e.dispose()
        atm = rows["NIFTY_20260804_24000_CE"]
        assert atm[1] is not None and 0.05 < atm[1] < 0.5
        assert 0.4 < atm[2] < 0.65
        assert rows["NIFTY_20260804_25000_CE"][1] is None  # not computable -> NULL, row present

        # idempotent re-run replaces, not duplicates
        n2 = M.run(days=["2026-07-29"], database_url=url)
        assert n2 == 2
