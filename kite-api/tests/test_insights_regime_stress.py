"""Tests for the regime classifier and stress composite.

Both modules are foundational — the Daily Quant Note leads with these
("REGIME: Trend Bull · STRESS 42/100"). Verifying they classify known
historical episodes correctly is critical before any commentary builds
on top.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.insights import breadth, macro, regime, stress


# ---------- regime ----------

class TestRegimeClassifier:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        regime.clear_cache()
        breadth.clear_cache()
        macro.clear_cache()

    @pytest.fixture(scope="class")
    def panel(self):
        return regime.compute_regime_panel()

    def test_panel_builds(self, panel):
        assert not panel.empty
        for col in ["raw_regime", "regime", "persistence_days",
                     "nifty100_above_100dma", "pct_above_200dma", "vix_zscore_252d"]:
            assert col in panel.columns

    def test_all_regimes_are_valid_labels(self, panel):
        valid = {*regime.REGIMES, ""}  # raw_regime can be empty pre-data
        assert set(panel["regime"].unique()).issubset(set(regime.REGIMES))

    def test_persistence_resets_on_transition(self, panel):
        """When regime changes, persistence should drop to 1; while it
        stays the same, it should monotonically increase."""
        prev_reg = None
        prev_pers = 0
        for _, row in panel.head(500).iterrows():  # sample to keep test fast
            reg = row["regime"]
            pers = row["persistence_days"]
            if reg == prev_reg:
                assert pers == prev_pers + 1, (
                    f"persistence didn't increment for {reg}: {prev_pers} → {pers}"
                )
            else:
                assert pers == 1, f"transition to {reg} should reset to 1, got {pers}"
            prev_reg = reg
            prev_pers = pers

    def test_covid_crash_classified_as_stress(self):
        """March 2020 COVID crash should be STRESS."""
        snap = regime.get_regime_snapshot(pd.Timestamp("2020-03-23"))
        assert snap is not None
        assert snap.regime == regime.STRESS, (
            f"COVID crash classified as {snap.regime}, not STRESS"
        )

    def test_post_covid_rally_classified_as_trend_bull(self):
        snap = regime.get_regime_snapshot(pd.Timestamp("2021-10-14"))
        assert snap is not None
        assert snap.regime == regime.TREND_BULL

    def test_2018_nbfc_crisis_classified_as_stress(self):
        snap = regime.get_regime_snapshot(pd.Timestamp("2018-10-05"))
        assert snap is not None
        assert snap.regime == regime.STRESS

    def test_snapshot_to_dict_is_json_serializable(self):
        snap = regime.get_regime_snapshot()
        assert snap is not None
        json.dumps(snap.to_dict())

    def test_regime_history_episodes(self):
        h = regime.get_regime_history()
        assert not h.empty
        for _, ep in h.iterrows():
            assert ep["regime"] in regime.REGIMES
            assert ep["start"] <= ep["end"]
            assert ep["days"] >= 1


# ---------- stress ----------

class TestStressComposite:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        stress.clear_cache()
        breadth.clear_cache()
        macro.clear_cache()

    @pytest.fixture(scope="class")
    def panel(self):
        return stress.compute_stress_panel()

    def test_panel_builds(self, panel):
        assert not panel.empty
        for col in ["score", "score_percentile",
                     "vix_pctile_component", "drawdown_component",
                     "below_200dma_component", "dispersion_component"]:
            assert col in panel.columns

    def test_score_in_0_100_range(self, panel):
        s = panel["score"].dropna()
        assert s.min() >= 0
        assert s.max() <= 100

    def test_components_in_0_100_range(self, panel):
        for col in ["vix_pctile_component", "drawdown_component",
                     "below_200dma_component", "dispersion_component"]:
            v = panel[col].dropna()
            assert v.min() >= 0, f"{col} min {v.min()}"
            assert v.max() <= 100, f"{col} max {v.max()}"

    def test_covid_crash_has_very_high_stress(self):
        snap = stress.get_stress_snapshot(pd.Timestamp("2020-03-23"))
        assert snap is not None
        assert snap.score >= 90, (
            f"COVID crash stress {snap.score} should be ≥90"
        )

    def test_calm_period_has_low_stress(self):
        """A known calm point (post-COVID rally peak, low VIX, high breadth)
        should give low stress."""
        snap = stress.get_stress_snapshot(pd.Timestamp("2021-10-14"))
        assert snap is not None
        assert snap.score <= 30, (
            f"Calm 2021-10 stress {snap.score} should be ≤30"
        )

    def test_2018_nbfc_high_stress(self):
        snap = stress.get_stress_snapshot(pd.Timestamp("2018-10-05"))
        assert snap is not None
        assert snap.score >= 70

    def test_weights_normalised(self):
        assert abs(sum(stress.WEIGHTS.values()) - 1.0) < 1e-9

    def test_snapshot_to_dict_is_json_serializable(self):
        snap = stress.get_stress_snapshot()
        assert snap is not None
        json.dumps(snap.to_dict())

    def test_score_reconciles_with_components(self):
        """Spot-check: score = weighted sum of components, on a recent day."""
        snap = stress.get_stress_snapshot()
        assert snap is not None
        expected = (
            stress.WEIGHTS["vix_pctile"]   * (snap.vix_pctile_component or 0)
            + stress.WEIGHTS["drawdown"]   * (snap.drawdown_component or 0)
            + stress.WEIGHTS["below_200dma"] * (snap.below_200dma_component or 0)
            + stress.WEIGHTS["dispersion"] * (snap.dispersion_component or 0)
        )
        assert abs(snap.score - expected) < 0.5, (
            f"score {snap.score} != weighted components {expected}"
        )
