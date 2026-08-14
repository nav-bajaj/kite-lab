"""Smoke tests for the promoted insight engines.

`app.insights.breadth` and `app.insights.macro` were promoted from the
`tasks/nifty_trader/` research folder into the kite-api runtime so the
API routes (Phase 2) can import them. These tests verify the modules
load cleanly, produce the expected schema, and cache correctly.

Run from the kite-api dir: pytest tests/test_insights_breadth_macro.py
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import pytest

from app.config import get_settings
from app.insights import breadth, macro


EXPECTED_BREADTH_COLUMNS = {
    "pct_above_21dma", "pct_above_50dma", "pct_above_100dma",
    "pct_above_200dma", "avg_dist_from_200dma",
    "ad_diff_pct", "cumulative_ad", "mcclellan_osc", "mcclellan_sum",
    "new_52w_highs_pct", "new_52w_lows_pct", "net_new_highs_pct",
    "dispersion", "n_active",
}

EXPECTED_MACRO_COLUMNS = {
    "vix_close", "vix_zscore_60d", "vix_zscore_252d", "vix_roc_5d",
    "vix_above_20", "sector_pct_above_50dma", "sector_pct_above_200dma",
    "sector_breadth_st_lt", "sector_dispersion_20d",
}


@pytest.fixture(scope="module")
def breadth_panel() -> pd.DataFrame:
    breadth.clear_cache()
    return breadth.get_breadth_panel()


@pytest.fixture(scope="module")
def macro_panel() -> pd.DataFrame:
    macro.clear_cache()
    return macro.get_macro_panel()


# ---------- breadth ----------

class TestBreadthPanel:
    def test_panel_loads_with_expected_schema(self, breadth_panel):
        missing = EXPECTED_BREADTH_COLUMNS - set(breadth_panel.columns)
        assert not missing, f"missing breadth columns: {sorted(missing)}"

    def test_panel_has_meaningful_history(self, breadth_panel):
        # We need at least 10 years of breadth history for the analog finder
        # and conditional distribution engines to be useful.
        years = (breadth_panel.index.max() - breadth_panel.index.min()).days / 365.25
        assert years >= 10, f"breadth history is only {years:.1f} years; expected ≥10"

    def test_pct_above_dma_in_valid_range(self, breadth_panel):
        # Fractions must be in [0, 1]
        for col in ["pct_above_50dma", "pct_above_100dma", "pct_above_200dma"]:
            vals = breadth_panel[col].dropna()
            assert vals.min() >= 0, f"{col}: negative value {vals.min()}"
            assert vals.max() <= 1, f"{col}: value > 1 ({vals.max()})"

    def test_ad_diff_pct_in_valid_range(self, breadth_panel):
        # (advancers - decliners) / total ∈ [-1, +1]
        vals = breadth_panel["ad_diff_pct"].dropna()
        assert vals.min() >= -1.0001, f"ad_diff_pct min {vals.min()}"
        assert vals.max() <= 1.0001, f"ad_diff_pct max {vals.max()}"

    def test_n_active_is_positive(self, breadth_panel):
        assert (breadth_panel["n_active"] > 0).all()

    def test_cache_reload_is_fast(self):
        """Second call should hit the lru_cache and be near-instant."""
        # Prime: ensure cache is populated
        breadth.clear_cache()
        _ = breadth.get_breadth_panel()  # cold
        t0 = time.time()
        _ = breadth.get_breadth_panel()
        elapsed_ms = (time.time() - t0) * 1000
        assert elapsed_ms < 50, f"lru_cache hit took {elapsed_ms:.1f}ms (expected <50ms)"

    def test_cache_file_lands_in_expected_location(self):
        breadth.clear_cache()
        _ = breadth.get_breadth_panel()
        cache_path = get_settings().data_dir / "cache" / "insights" / "breadth_panel.pkl"
        assert cache_path.exists(), f"cache file not at {cache_path}"


# ---------- macro ----------

class TestMacroPanel:
    def test_panel_loads_with_expected_schema(self, macro_panel):
        missing = EXPECTED_MACRO_COLUMNS - set(macro_panel.columns)
        assert not missing, f"missing macro columns: {sorted(missing)}"

    def test_vix_reasonable_range(self, macro_panel):
        # India VIX has historically traded ~8 to ~90 over 16 years
        v = macro_panel["vix_close"].dropna()
        assert v.min() > 5, f"vix_close min {v.min()} — too low"
        assert v.max() < 100, f"vix_close max {v.max()} — too high"

    def test_vix_above_20_is_binary(self, macro_panel):
        vals = set(macro_panel["vix_above_20"].dropna().unique())
        assert vals.issubset({0.0, 1.0}), f"vix_above_20 has non-binary values: {vals}"

    def test_sector_pct_above_dma_in_valid_range(self, macro_panel):
        for col in ["sector_pct_above_50dma", "sector_pct_above_200dma"]:
            vals = macro_panel[col].dropna()
            assert vals.min() >= 0
            assert vals.max() <= 1


# ---------- combined: align breadth + macro ----------

class TestCombinedPanels:
    def test_overlapping_history_exists(self, breadth_panel, macro_panel):
        common = breadth_panel.index.intersection(macro_panel.index)
        assert len(common) > 1000, (
            f"breadth × macro common history is only {len(common)} days; "
            f"need at least 1000 for meaningful joint analysis"
        )

    def test_modules_use_same_repo_root(self):
        """Both modules resolve paths via the same settings — protects
        against the macro module accidentally pointing at a stale fork
        of the data dir."""
        # breadth uses `_repo_root()` internally; macro uses `get_settings().data_dir`
        # They should be identical.
        assert breadth._repo_root() == get_settings().data_dir


class TestAtlasColumnAdditions:
    """Spec for the three Breadth Atlas metrics promoted into the live
    engine (insights_dashboard_v2 Slice 2.5; empirical profile in
    tasks/breadth_atlas/REPORT.md): pct_above_21dma, avg_dist_from_200dma
    (the continuous, statistically stronger sibling of pct_above_200dma)
    and mcclellan_sum. Written spec-first per TDD_POLICY."""

    @staticmethod
    def _synthetic_panel() -> pd.DataFrame:
        dates = pd.date_range("2023-01-02", periods=260, freq="B")
        flat = pd.Series([100.0] * 260, index=dates)
        rising = pd.Series([100.0 + 0.5 * i for i in range(260)], index=dates)
        return breadth.compute_breadth_panel(pd.DataFrame({"FLAT": flat, "UP": rising}))

    def test_avg_dist_from_200dma_hand_computed(self):
        """FLAT sits exactly on its 200-DMA (dist 0); UP's last-day dist is
        229.5 / 179.75 - 1. The cross-sectional mean follows."""
        panel = self._synthetic_panel()
        expected_up = 229.5 / 179.75 - 1.0
        assert abs(panel["avg_dist_from_200dma"].iloc[-1] - expected_up / 2) < 1e-9

    def test_pct_above_21dma_strict_inequality(self):
        """FLAT == its 21-DMA (not above, matching the > convention of the
        other pct_above columns); UP is above. So the share is 0.5."""
        panel = self._synthetic_panel()
        assert abs(panel["pct_above_21dma"].iloc[-1] - 0.5) < 1e-9

    def test_pct_above_21dma_warmup(self):
        """Needs 21 observations — NaN before, populated after."""
        panel = self._synthetic_panel()
        assert panel["pct_above_21dma"].iloc[:20].isna().all()
        assert panel["pct_above_21dma"].iloc[20:].notna().all()

    def test_mcclellan_sum_is_cumsum_of_oscillator(self):
        """The summation index is by definition the running total of the
        oscillator (skipping its NaN warm-up)."""
        panel = self._synthetic_panel()
        expected = panel["mcclellan_osc"].cumsum()
        pd.testing.assert_series_equal(
            panel["mcclellan_sum"], expected, check_names=False
        )

    def test_avg_dist_and_pct_above_200_agree_on_real_data(self, breadth_panel):
        """Atlas finding: the continuous and binary forms are the same
        signal (Pearson 0.97). Pin a loose floor so a wiring mistake
        (wrong column, wrong sign) fails loudly."""
        sub = breadth_panel[["avg_dist_from_200dma", "pct_above_200dma"]].dropna()
        if len(sub) < 500:
            pytest.skip("not enough real history")
        corr = sub["avg_dist_from_200dma"].corr(sub["pct_above_200dma"])
        assert corr > 0.9


class TestUniverseScopedBreadth:
    """Spec for universe-scoped breadth panels (insights_dashboard_v2:
    the dashboard's universe selector — Nifty 500 default, plus
    nifty250 / nifty100 / nifty50 via the committed universe CSVs).
    Written spec-first per TDD_POLICY."""

    def test_smaller_universe_has_fewer_names(self):
        full = breadth.get_breadth_panel()
        n50 = breadth.get_breadth_panel("nifty50")
        assert n50["n_active"].iloc[-1] <= 55
        assert full["n_active"].iloc[-1] > 400
        assert set(n50.columns) == set(full.columns)

    def test_unknown_universe_rejected(self):
        with pytest.raises(ValueError):
            breadth.get_breadth_panel("nifty9000")

    def test_universe_caches_do_not_collide(self):
        assert breadth._cache_file() != breadth._cache_file("nifty50")
        # Legacy path is preserved for the default universe so existing
        # prod caches stay valid.
        assert breadth._cache_file().name == "breadth_panel.pkl"
