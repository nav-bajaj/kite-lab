"""Stage 2b — per-minute gamma profile.

The 3-snapshot profile made the concentration SLOPE a two-point estimate
across three hours, which is what stalled the gamma-positioning study
(tasks/options_data/research/RESULTS_2026-08-18_gamma_positioning.md).
option_greeks_minute already carries gamma and IV per minute per
contract, so the profile is computable at 1-minute resolution from data
already stored.

The load-bearing requirement is that the per-minute path and the
3-snapshot path cannot drift: one shared pure core, so a concentration
read at 13:00 means the same thing in gamma_profile_daily,
gamma_profile_minute, the daily report and the day-plan.
"""
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import (
    Column, DateTime, Float, MetaData, String, Table, create_engine, text,
)

from app.microstructure import gamma_profile as GP


def _greeks_frame(rows):
    """rows: (hm, strike, kind, gamma, iv, oi, underlying)"""
    return pd.DataFrame(
        [{"minute": f"2026-08-18 {hm}", "strike": k, "kind": kind, "gamma": g,
          "iv": iv, "oi_close": oi, "underlying": u}
         for hm, k, kind, g, iv, oi, u in rows])


class TestProfileSeries:
    def test_one_minute_one_strike_totals_the_gex(self):
        # gex_cr = gamma * oi * F^2 * 0.01 / 1e7
        df = _greeks_frame([("10:00", 24000.0, "CE", 0.0002, 0.11, 50000, 24000.0)])
        out = GP.profile_series(df)
        assert len(out) == 1
        expected = 0.0002 * 50000 * 24000.0 ** 2 * 0.01 / GP.CR
        assert out.total_gex_cr.iloc[0] == pytest.approx(expected)
        assert out.max_gamma_strike.iloc[0] == 24000.0
        assert out.concentration.iloc[0] == pytest.approx(1.0)

    def test_ce_and_pe_at_the_same_strike_aggregate(self):
        df = _greeks_frame([
            ("10:00", 24000.0, "CE", 0.0002, 0.11, 50000, 24000.0),
            ("10:00", 24000.0, "PE", 0.0002, 0.11, 50000, 24000.0)])
        out = GP.profile_series(df)
        assert out.concentration.iloc[0] == pytest.approx(1.0)
        one = 0.0002 * 50000 * 24000.0 ** 2 * 0.01 / GP.CR
        assert out.total_gex_cr.iloc[0] == pytest.approx(2 * one)

    def test_concentration_is_the_max_strikes_share(self):
        df = _greeks_frame([
            ("10:00", 24000.0, "CE", 0.0003, 0.11, 50000, 24000.0),   # 3 parts
            ("10:00", 24100.0, "CE", 0.0001, 0.11, 50000, 24000.0)])  # 1 part
        out = GP.profile_series(df)
        assert out.max_gamma_strike.iloc[0] == 24000.0
        assert out.concentration.iloc[0] == pytest.approx(0.75)

    def test_each_minute_gets_its_own_row_and_its_own_forward(self):
        df = _greeks_frame([
            ("10:00", 24000.0, "CE", 0.0002, 0.11, 50000, 24000.0),
            ("10:01", 24000.0, "CE", 0.0002, 0.12, 50000, 24050.0)])
        out = GP.profile_series(df).sort_values("minute").reset_index(drop=True)
        assert len(out) == 2
        assert out.forward.tolist() == [24000.0, 24050.0]
        assert out.atm_iv.tolist() == [pytest.approx(0.11), pytest.approx(0.12)]

    def test_atm_iv_uses_the_strike_nearest_the_forward(self):
        df = _greeks_frame([
            ("10:00", 24000.0, "CE", 0.0002, 0.10, 50000, 24040.0),   # nearest
            ("10:00", 24200.0, "CE", 0.0002, 0.30, 50000, 24040.0)])
        assert GP.profile_series(df).atm_iv.iloc[0] == pytest.approx(0.10)

    def test_atm_iv_averages_the_pair_at_the_atm_strike(self):
        df = _greeks_frame([
            ("10:00", 24000.0, "CE", 0.0002, 0.10, 50000, 24000.0),
            ("10:00", 24000.0, "PE", 0.0002, 0.14, 50000, 24000.0)])
        assert GP.profile_series(df).atm_iv.iloc[0] == pytest.approx(0.12)

    def test_rows_with_null_gamma_are_dropped_not_zeroed(self):
        # a non-computable greek must not pull concentration toward a strike
        df = _greeks_frame([
            ("10:00", 24000.0, "CE", 0.0002, 0.11, 50000, 24000.0),
            ("10:00", 24100.0, "CE", np.nan, np.nan, 50000, 24000.0)])
        out = GP.profile_series(df)
        assert out.concentration.iloc[0] == pytest.approx(1.0)
        assert out.max_gamma_strike.iloc[0] == 24000.0

    def test_minute_with_zero_total_gex_yields_null_concentration(self):
        df = _greeks_frame([("10:00", 24000.0, "CE", 0.0, 0.11, 50000, 24000.0)])
        out = GP.profile_series(df)
        assert out.total_gex_cr.iloc[0] == pytest.approx(0.0)
        assert pd.isna(out.concentration.iloc[0])

    def test_empty_input_returns_an_empty_frame_with_the_right_columns(self):
        out = GP.profile_series(_greeks_frame([]).reindex(
            columns=["minute", "strike", "kind", "gamma", "iv", "oi_close", "underlying"]))
        assert out.empty
        for c in ("minute", "forward", "total_gex_cr", "max_gamma_strike",
                  "concentration", "atm_iv"):
            assert c in out.columns

    def test_regime_labels_agree_with_the_shared_cutoffs(self):
        # the per-minute path must not introduce a second set of thresholds
        assert GP.regime_from_concentration(GP.CONC_PIN + 0.01) == "PIN-GRAVITY"
        assert GP.regime_from_concentration(GP.CONC_DIFFUSE - 0.01) == "DIFFUSE"
        assert GP.regime_from_concentration(
            (GP.CONC_PIN + GP.CONC_DIFFUSE) / 2) == "MIXED"


def _seed_greeks(url, day="2026-08-18"):
    """Two minutes x two strikes, near expiry + a decoy far expiry."""
    engine = create_engine(url)
    GP._metadata.create_all(engine, checkfirst=True)
    from app.microstructure.materialize import option_greeks_minute, _metadata as MM
    MM.create_all(engine, checkfirst=True)
    near, far = date(2026, 8, 18), date(2026, 8, 25)
    rows = []
    for hm, u in (("10:00", 24000.0), ("10:01", 24050.0)):
        h, m = map(int, hm.split(":"))
        minute = datetime(2026, 8, 18, h, m) - timedelta(hours=5, minutes=30)
        for k, g, exp in ((24000.0, 0.0003, near), (24100.0, 0.0001, near),
                          (24000.0, 0.0009, far)):   # decoy: far expiry, huge gamma
            rows.append(dict(contract_id=f"{k:.0f}{exp}{hm}", minute=minute,
                             expiry=exp, strike=k, kind="CE", underlying=u,
                             underlying_src="parity", iv=0.11, delta=0.5,
                             gamma=g, vega=1.0, theta_day=-1.0, r=0.065,
                             engine_version="test", computed_at=datetime.now(timezone.utc)))
    # OI lives on the bars, joined by (contract_id, minute) — declare the
    # join columns through SQLAlchemy so the datetime rendering matches the
    # greeks table exactly (a raw-SQL insert writes a different string).
    md = MetaData()
    bars = Table("option_minute_bars", md,
                 Column("contract_id", String(40), primary_key=True),
                 Column("minute", DateTime(timezone=True), primary_key=True),
                 Column("oi_close", Float))
    md.create_all(engine, checkfirst=True)
    with engine.begin() as c:
        c.execute(option_greeks_minute.insert(), rows)
        c.execute(bars.insert(), [
            dict(contract_id=r["contract_id"], minute=r["minute"], oi_close=50000.0)
            for r in rows])
    engine.dispose()


class TestStoreIntraday:
    def test_writes_one_row_per_minute(self, tmp_path):
        url = f"sqlite:///{tmp_path}/g.db"
        _seed_greeks(url)
        n = GP.store_intraday("2026-08-18", database_url=url)
        assert n == 2
        engine = create_engine(url)
        with engine.connect() as c:
            got = pd.read_sql(text(
                "select * from gamma_profile_minute order by minute"), c)
        engine.dispose()
        assert len(got) == 2
        assert got.concentration.iloc[0] == pytest.approx(0.75)
        assert got.max_gamma_strike.iloc[0] == 24000.0

    def test_only_the_near_expiry_contributes(self, tmp_path):
        # the far-expiry decoy carries 3x the gamma; if it leaked in,
        # concentration would not be 0.75
        url = f"sqlite:///{tmp_path}/g2.db"
        _seed_greeks(url)
        GP.store_intraday("2026-08-18", database_url=url)
        engine = create_engine(url)
        with engine.connect() as c:
            conc = c.execute(text(
                "select concentration from gamma_profile_minute order by minute")).scalar()
        engine.dispose()
        assert conc == pytest.approx(0.75)

    def test_rerun_replaces_rather_than_duplicates(self, tmp_path):
        url = f"sqlite:///{tmp_path}/g3.db"
        _seed_greeks(url)
        GP.store_intraday("2026-08-18", database_url=url)
        GP.store_intraday("2026-08-18", database_url=url)
        engine = create_engine(url)
        with engine.connect() as c:
            n = c.execute(text("select count(*) from gamma_profile_minute")).scalar()
        engine.dispose()
        assert n == 2

    def test_step_minutes_thins_the_grid(self, tmp_path):
        url = f"sqlite:///{tmp_path}/g4.db"
        _seed_greeks(url)
        # 10:00 and 10:01; a 15-min grid keeps only the :00
        assert GP.store_intraday("2026-08-18", database_url=url, step_minutes=15) == 1

    def test_day_with_no_greeks_stores_nothing_and_does_not_raise(self, tmp_path):
        url = f"sqlite:///{tmp_path}/g5.db"
        _seed_greeks(url)
        assert GP.store_intraday("2026-01-01", database_url=url) == 0
