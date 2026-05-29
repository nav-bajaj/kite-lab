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


# ─────────── Spec tests (promoted from characterization 2026-05-28) ───────────
#
# Synthetic-input tests on the regime smoother + stress component
# arithmetic. See `tasks/insight_engine/TDD_POLICY.md`.


class TestRegimeSmoothingSpec:
    """Spec: the smoother must NOT flip on a 1-day border crossing but
    MUST flip on a `min_consecutive`-day persistent crossing."""

    def test_single_day_anomaly_does_not_flip_regime(self):
        """Spec: 1 anomalous day in the middle of a stable regime must not
        change the smoothed series."""
        idx = pd.date_range("2024-01-01", periods=20, freq="B")
        raw = pd.Series(["TREND_BULL"] * 20, index=idx)
        raw.iloc[10] = "DRIFT"

        smoothed = regime._apply_smoothing(raw, min_consecutive=3)
        assert smoothed.iloc[10] == "TREND_BULL", (
            "Single-day border crossing must not flip the smoothed regime"
        )

    def test_two_day_anomaly_does_not_flip_regime(self):
        """Spec: 2 consecutive anomalous days still below the 3-day
        threshold — must not flip."""
        idx = pd.date_range("2024-01-01", periods=20, freq="B")
        raw = pd.Series(["TREND_BULL"] * 20, index=idx)
        raw.iloc[10:12] = "DRIFT"

        smoothed = regime._apply_smoothing(raw, min_consecutive=3)
        assert smoothed.iloc[10] == "TREND_BULL"
        assert smoothed.iloc[11] == "TREND_BULL"

    def test_three_day_persistence_flips_regime(self):
        """Spec: when 3 consecutive new-state days have accumulated, the
        regime flips on the 3rd day and remains in the new state."""
        idx = pd.date_range("2024-01-01", periods=20, freq="B")
        raw = pd.Series(["TREND_BULL"] * 20, index=idx)
        raw.iloc[10:15] = "DRIFT"  # 5 consecutive DRIFT days

        smoothed = regime._apply_smoothing(raw, min_consecutive=3)
        # The smoother flips once the candidate has held for min_consecutive
        # days. Once flipped, subsequent days in that state stay flipped.
        assert smoothed.iloc[14] == "DRIFT", (
            f"Day 14 (5 consecutive DRIFT) should be DRIFT; got {smoothed.iloc[14]}"
        )
        # The transition into DRIFT must have happened — not still all TREND_BULL
        unique_after_10 = set(smoothed.iloc[10:15].unique())
        assert "DRIFT" in unique_after_10, (
            "After 5 DRIFT days, smoothed series must contain DRIFT"
        )

    def test_empty_input_returns_empty(self):
        """Spec: empty series in → empty series out, no crash."""
        empty = pd.Series([], dtype=str)
        out = regime._apply_smoothing(empty, min_consecutive=3)
        assert out.empty

    def test_first_day_takes_raw_value_directly(self):
        """Spec: the very first day has nothing prior to smooth against,
        so its smoothed value equals the raw value."""
        idx = pd.date_range("2024-01-01", periods=5, freq="B")
        raw = pd.Series(["STRESS", "STRESS", "STRESS", "STRESS", "STRESS"],
                        index=idx)
        out = regime._apply_smoothing(raw, min_consecutive=3)
        assert out.iloc[0] == "STRESS"


class TestStressBoundarySpec:
    """Spec for stress panel boundary cases — missing components, weights."""

    def test_all_four_components_have_weights(self):
        """Spec: every component referenced in the score formula must
        have a defined weight."""
        required = {"vix_pctile", "drawdown", "below_200dma", "dispersion"}
        assert set(stress.WEIGHTS.keys()) >= required

    def test_score_is_in_0_to_100_range(self):
        """Spec: the composite is 0-100 by construction. Pin it."""
        snap = stress.get_stress_snapshot()
        assert snap is not None
        assert 0.0 <= snap.score <= 100.0, (
            f"Score {snap.score} outside [0, 100]"
        )

    def test_panel_indexed_by_date(self):
        """Spec: the panel must be a DataFrame with DatetimeIndex —
        downstream code (commentary, charts) depends on this."""
        panel = stress.compute_stress_panel()
        assert isinstance(panel, pd.DataFrame)
        assert isinstance(panel.index, pd.DatetimeIndex)
