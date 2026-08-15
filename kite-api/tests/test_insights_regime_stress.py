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


class TestUniverseScopedRegimeSpec:
    """Spec: the regime is defined per universe — a Nifty 500 TREND_BULL
    reads the NIFTY 500's own trend and the NSE 500's own breadth, not the
    NIFTY 100's (founder, 2026-08-15).

    The no-argument call keeps the legacy market-wide definition (NIFTY 100
    trend + NSE 500 breadth, 2010+) because the note generator, conditional
    distributions and calendar lookbacks depend on its depth — the NIFTY 500
    price series only starts in 2015.
    """

    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        regime.clear_cache()
        breadth.clear_cache()
        macro.clear_cache()

    def test_universes_match_the_breadth_universes(self):
        assert regime.REGIME_UNIVERSES == breadth.BREADTH_UNIVERSES

    def test_each_universe_names_its_own_index(self):
        assert regime.regime_index_label("nse500") == "Nifty 500"
        assert regime.regime_index_label("nifty250") == "Nifty 250"
        assert regime.regime_index_label("nifty100") == "Nifty 100"
        assert regime.regime_index_label("nifty50") == "Nifty 50"

    def test_unknown_universe_rejected(self):
        with pytest.raises(ValueError):
            regime.compute_regime_panel("nifty42")

    @pytest.mark.parametrize("universe", ["nse500", "nifty250", "nifty100", "nifty50"])
    def test_panel_builds_for_every_universe(self, universe):
        panel = regime.compute_regime_panel(universe)
        assert not panel.empty
        for col in ["raw_regime", "regime", "persistence_days",
                    "index_above_trend_ma", "participation_pct", "vix_zscore_252d"]:
            assert col in panel.columns, f"{universe} panel missing {col}"
        assert set(panel["regime"].unique()).issubset(set(regime.REGIMES))

    def test_trend_filter_differs_between_universes(self):
        """Spec: the trend input is the universe's OWN index. Nifty 50 and
        Nifty 500 do not sit above their 100-DMA on exactly the same days."""
        small = regime.compute_regime_panel("nifty50")["index_above_trend_ma"]
        broad = regime.compute_regime_panel("nse500")["index_above_trend_ma"]
        common = small.index.intersection(broad.index)
        assert len(common) > 500
        assert not small.loc[common].equals(broad.loc[common]), (
            "Nifty 50 and Nifty 500 trend filters are identical — the "
            "universe's own index is not being used"
        )

    def test_breadth_input_is_the_universes_own_breadth(self):
        """Spec: participation is measured over the same universe, not
        always the NSE 500."""
        panel = regime.compute_regime_panel("nifty50")
        own = breadth.get_breadth_panel("nifty50")["pct_above_50dma"]
        common = panel.index.intersection(own.index)
        assert len(common) > 500
        pd.testing.assert_series_equal(
            panel.loc[common, "participation_pct"],
            own.loc[common],
            check_names=False,
        )

    def test_scoped_rules_run_on_the_50_day_windows(self):
        """Spec (founder, 2026-08-15): the scoped regime reads the index
        against its 50-day average and participation as the share of the
        universe above their own 50-day averages — not 100/200."""
        assert regime.TREND_MA_DAYS == 50
        assert regime.PARTICIPATION_MA_DAYS == 50

        panel = regime.compute_regime_panel("nifty50")
        closes = regime.regime_index_close("nifty50")
        expected = closes > closes.rolling(50, min_periods=50).mean()
        common = panel.index.intersection(expected[expected.notna()].index)
        assert len(common) > 500
        pd.testing.assert_series_equal(
            panel.loc[common, "index_above_trend_ma"].astype(bool),
            expected.loc[common].astype(bool),
            check_names=False,
        )

    def test_legacy_panel_keeps_the_100_200_windows(self):
        """Regression guard: the market-wide panel the note generator uses
        is untouched by the dashboard's redefinition."""
        panel = regime.compute_regime_panel()
        own = breadth.get_breadth_panel()["pct_above_200dma"]
        common = panel.index.intersection(own.index)
        pd.testing.assert_series_equal(
            panel.loc[common, "participation_pct"],
            own.loc[common],
            check_names=False,
        )

    def test_snapshot_reports_the_windows_that_drove_it(self):
        """Spec: the UI states the rule, so the snapshot must carry the
        windows actually used rather than the UI hardcoding them."""
        scoped = regime.get_regime_snapshot(universe="nifty50")
        assert scoped is not None
        assert scoped.trend_ma_days == 50
        assert scoped.participation_ma_days == 50
        assert scoped.participation_pct is not None

        legacy = regime.get_regime_snapshot()
        assert legacy is not None
        assert legacy.trend_ma_days == 100
        assert legacy.participation_ma_days == 200

    def test_panel_starts_where_that_index_has_data(self):
        """Spec: each universe's regime starts from the point its own index
        series begins (plus the 100-day average warm-up), never before."""
        # NIFTY 500 history starts 2015-01-01; LARGEMID250 starts 2020-01-01.
        assert regime.compute_regime_panel("nse500").index.min() >= pd.Timestamp("2015-01-01")
        assert regime.compute_regime_panel("nifty250").index.min() >= pd.Timestamp("2020-01-01")
        # ...and each must actually start soon after warm-up, not years later.
        assert regime.compute_regime_panel("nse500").index.min() <= pd.Timestamp("2015-12-31")

    def test_legacy_market_wide_panel_is_unchanged(self):
        """Regression guard: the no-argument call keeps its 2010 depth and
        its NIFTY 100 trend column for the note generator."""
        panel = regime.compute_regime_panel()
        assert "nifty100_above_100dma" in panel.columns
        assert panel.index.min() <= pd.Timestamp("2010-12-31")

    def test_snapshot_carries_its_scope(self):
        snap = regime.get_regime_snapshot(universe="nifty50")
        assert snap is not None
        assert snap.universe == "nifty50"
        assert snap.index_label == "Nifty 50"
        json.dumps(snap.to_dict())

    def test_covid_crash_is_stress_in_every_universe(self):
        """Sanity across definitions: March 2020 was stress everywhere the
        data reaches (LARGEMID250 starts 2020-01, so it warms up later)."""
        for universe in ["nse500", "nifty100", "nifty50"]:
            snap = regime.get_regime_snapshot(pd.Timestamp("2020-03-23"), universe=universe)
            assert snap is not None, universe
            assert snap.regime == regime.STRESS, f"{universe} → {snap.regime}"

    def test_history_episodes_carry_the_index_move(self):
        """Spec: each episode reports what the universe's index did over the
        spell, so the UI can say what the market actually returned."""
        h = regime.get_regime_history("nse500")
        assert not h.empty
        assert "index_return_pct" in h.columns
        for _, ep in h.iterrows():
            assert ep["regime"] in regime.REGIMES
            assert ep["start"] <= ep["end"]
            assert ep["days"] >= 1
            if ep["index_return_pct"] is not None and not pd.isna(ep["index_return_pct"]):
                assert -0.95 < float(ep["index_return_pct"]) < 3.0

    def test_episode_index_return_matches_the_index_series(self):
        """Spec: the reported move is close-to-close across the spell."""
        h = regime.get_regime_history("nifty50")
        closes = regime.regime_index_close("nifty50")
        ep = h.iloc[len(h) // 2]
        window = closes.loc[ep["start"]:ep["end"]]
        expected = float(window.iloc[-1]) / float(window.iloc[0]) - 1.0
        assert abs(float(ep["index_return_pct"]) - expected) < 1e-9


class TestStressCoverageSpec:
    """Spec: the composite must not present a guess as a reading.

    Two defects found in the 2026-08-15 audit: a missing percentile was
    served as 0.0 (rendering as a confident "p0"), and a missing component
    contributed 0 to the weighted sum — i.e. "no data" scored as "maximum
    calm", understating early-2010 dates by up to 18 points.
    """

    def test_missing_percentile_is_none_not_zero(self):
        """Spec: before the percentile window has enough data, the field is
        None. `rank(pct=True)` can never legitimately return 0, so a 0.0
        here could only ever be a stand-in for missing.

        The date is derived from the panel rather than hardcoded — these
        boundaries move whenever a lookback window is retuned.
        """
        panel = stress.compute_stress_panel()
        missing = panel.index[panel["score_percentile"].isna()]
        assert len(missing) > 0, "expected some warm-up rows"
        snap = stress.get_stress_snapshot(missing.max())
        assert snap is not None
        assert snap.score_percentile is None, (
            "an unavailable percentile must be None, not 0.0"
        )

    def test_percentile_is_never_zero_when_present(self):
        panel = stress.compute_stress_panel()
        present = panel["score_percentile"].dropna()
        assert present.min() > 0.0

    def test_score_renormalises_over_available_components(self):
        """Spec: with only some components available, the score is the
        weighted mean of those present — not a sum that treats absent
        inputs as 0."""
        snap = stress.get_stress_snapshot(pd.Timestamp("2010-01-15"))
        assert snap is not None
        present = {
            "vix_pctile": snap.vix_pctile_component,
            "drawdown": snap.drawdown_component,
            "below_200dma": snap.below_200dma_component,
            "dispersion": snap.dispersion_component,
        }
        available = {k: v for k, v in present.items() if v is not None}
        assert 0 < len(available) < 4, "fixture date should be partially covered"
        total_weight = sum(stress.WEIGHTS[k] for k in available)
        expected = sum(stress.WEIGHTS[k] * v for k, v in available.items()) / total_weight
        assert abs(snap.score - expected) < 0.5, (
            f"score {snap.score} should renormalise to {expected}"
        )

    def test_score_is_none_when_no_component_is_available(self):
        panel = stress.compute_stress_panel()
        comp_cols = ["vix_pctile_component", "drawdown_component",
                     "below_200dma_component", "dispersion_component"]
        empty = panel[panel[comp_cols].isna().all(axis=1)]
        assert empty["score"].isna().all(), (
            "a day with no inputs at all must not carry a score"
        )

    def test_fully_covered_days_are_unchanged(self):
        """Regression guard: renormalisation must be a no-op once all four
        components are present — weights already sum to 1."""
        snap = stress.get_stress_snapshot()
        assert snap is not None
        expected = (
            stress.WEIGHTS["vix_pctile"] * (snap.vix_pctile_component or 0)
            + stress.WEIGHTS["drawdown"] * (snap.drawdown_component or 0)
            + stress.WEIGHTS["below_200dma"] * (snap.below_200dma_component or 0)
            + stress.WEIGHTS["dispersion"] * (snap.dispersion_component or 0)
        )
        assert abs(snap.score - expected) < 1e-9

    def test_snapshot_reports_how_much_history_backs_the_percentile(self):
        """Spec: the UI says "vs the last 5 years", so it needs to know when
        the window is not actually five years deep yet."""
        snap = stress.get_stress_snapshot()
        assert snap is not None
        assert snap.score_percentile_obs == stress.SCORE_PERCENTILE_WINDOW

        # The first day the percentile exists is by construction backed by
        # fewer observations than the nominal window.
        panel = stress.compute_stress_panel()
        first = panel.index[panel["score_percentile"].notna()].min()
        early = stress.get_stress_snapshot(first)
        assert early is not None
        assert early.score_percentile_obs is not None
        assert early.score_percentile_obs < stress.SCORE_PERCENTILE_WINDOW


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
