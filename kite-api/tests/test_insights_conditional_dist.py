"""Tests for the conditional distribution module."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.insights import conditional_dist as cd
from app.insights import regime


class TestConditionalDistByRegime:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        cd.clear_cache()

    @pytest.fixture(scope="class")
    def by_regime(self):
        return cd.by_regime()

    def test_returns_all_regimes(self, by_regime):
        assert set(by_regime.keys()) == set(regime.REGIMES)

    def test_returns_all_horizons(self, by_regime):
        for r, by_h in by_regime.items():
            assert set(by_h.keys()) == set(cd.FORWARD_HORIZONS)

    def test_n_is_positive_for_major_regimes(self, by_regime):
        for r in (regime.TREND_BULL, regime.DRIFT, regime.STRESS):
            d = by_regime[r][20]
            assert d.n > 50, f"{r} bucket only has n={d.n}"

    def test_quantiles_are_ordered(self, by_regime):
        for r, by_h in by_regime.items():
            for h, d in by_h.items():
                if d.n == 0:
                    continue
                assert d.p5 <= d.p25 <= d.median <= d.p75 <= d.p95, (
                    f"{r} fwd_{h}d: quantiles not monotonic"
                )

    def test_pct_positive_in_unit_range(self, by_regime):
        for r, by_h in by_regime.items():
            for h, d in by_h.items():
                if d.n == 0:
                    continue
                assert 0 <= d.pct_positive <= 1

    def test_stress_regime_has_strong_forward_bias(self, by_regime):
        """The 'buy panic' pattern: STRESS regime should historically have
        BETTER forward 20d returns than DRIFT regime (with positive median).
        If this fails, something is wrong with how we're aggregating."""
        stress_d = by_regime[regime.STRESS][20]
        drift_d = by_regime[regime.DRIFT][20]
        if stress_d.n > 50 and drift_d.n > 50:
            assert stress_d.median > drift_d.median, (
                f"STRESS median {stress_d.median} should beat DRIFT {drift_d.median}"
            )


class TestConditionalDistByStress:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        cd.clear_cache()

    @pytest.fixture(scope="class")
    def by_q(self):
        return cd.by_stress_quintile()

    def test_returns_all_quintiles(self, by_q):
        assert set(by_q.keys()) == set(range(cd.N_STRESS_QUINTILES))

    def test_quintile_n_approximately_balanced(self, by_q):
        """Each quintile should have roughly equal n. Some imbalance is
        expected because the early NaN window (before stress score can be
        computed) drops disproportionately into the lowest quintile when
        we eventually rank — we tolerate up to 30% imbalance."""
        ns = [by_q[q][20].n for q in range(cd.N_STRESS_QUINTILES)]
        mx, mn = max(ns), min(ns)
        assert (mx - mn) / max(ns) < 0.30, f"quintiles too imbalanced: {ns}"


class TestTodayConditional:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        cd.clear_cache()

    @pytest.fixture(scope="class")
    def today(self):
        return cd.get_today_conditional()

    def test_today_returns_expected_keys(self, today):
        for k in ("date", "today_regime", "today_stress_quintile",
                   "today_stress_score", "by_regime",
                   "by_stress_quintile", "by_regime_x_stress"):
            assert k in today

    def test_today_regime_is_valid(self, today):
        assert today["today_regime"] in regime.REGIMES

    def test_today_stress_quintile_in_range(self, today):
        q = today["today_stress_quintile"]
        if q is not None:
            assert 0 <= q < cd.N_STRESS_QUINTILES

    def test_today_is_json_serializable(self, today):
        json.dumps(today)

    def test_by_regime_has_horizons(self, today):
        # We expect entries for each forward horizon
        for h in cd.FORWARD_HORIZONS:
            assert h in today["by_regime"]
