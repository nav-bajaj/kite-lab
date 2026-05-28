"""Smoke + integration tests for the unified MarketReading orchestrator.

The orchestrator is the single object Phase 1 (Daily Quant Note generator)
will depend on. These tests verify it composes all subsystems correctly
and produces a fully JSON-serializable output for the API layer.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from app.insights import reading, regime as regime_mod


@pytest.fixture(scope="module", autouse=True)
def _clear_caches():
    reading.clear_all_caches()


@pytest.fixture(scope="module")
def market_reading():
    return reading.get_market_reading()


class TestMarketReading:
    def test_orchestrator_returns_reading_object(self, market_reading):
        assert isinstance(market_reading, reading.MarketReading)

    def test_date_is_timestamp(self, market_reading):
        assert isinstance(market_reading.date, pd.Timestamp)

    def test_regime_populated(self, market_reading):
        r = market_reading.regime
        assert r.regime in regime_mod.REGIMES
        assert r.persistence_days >= 1

    def test_stress_populated(self, market_reading):
        s = market_reading.stress
        assert 0 <= s.score <= 100
        assert 0 <= s.score_percentile <= 100

    def test_sector_breadth_has_all_sectors(self, market_reading):
        assert len(market_reading.sector_breadth) >= 11

    def test_sector_rs_has_long_history_sectors(self, market_reading):
        from app.insights.sector_rs import SECTOR_INDICES
        assert set(market_reading.sector_rs.keys()) == set(SECTOR_INDICES)

    def test_leaderboard_sorted_by_rank(self, market_reading):
        board = market_reading.sector_leaderboard_60d
        ranks = [s.rank_60d for s in board if s.rank_60d is not None]
        assert ranks == sorted(ranks)

    def test_analogs_present(self, market_reading):
        # Default k=5
        assert len(market_reading.analogs) == 5
        # Sorted by distance ascending
        dists = [m.distance for m in market_reading.analogs]
        assert dists == sorted(dists)

    def test_analog_distribution_has_all_horizons(self, market_reading):
        from app.insights.analog_finder import FORWARD_HORIZONS
        assert set(market_reading.analog_distribution.keys()) == set(FORWARD_HORIZONS)

    def test_watchlists_has_five_lists(self, market_reading):
        expected = {"breakouts", "rs_leaders", "coiled_springs",
                     "stretched", "recent_breakdowns"}
        assert set(market_reading.watchlists.keys()) == expected

    def test_conditional_dict_well_formed(self, market_reading):
        c = market_reading.conditional
        assert "today_regime" in c
        assert c["today_regime"] in regime_mod.REGIMES
        assert "by_regime" in c

    def test_breadth_dict_has_expected_keys(self, market_reading):
        b = market_reading.breadth
        for key in ["pct_above_50dma", "pct_above_200dma", "ad_diff_pct"]:
            assert key in b

    def test_macro_dict_has_vix(self, market_reading):
        assert "vix_close" in market_reading.macro

    def test_to_dict_is_json_serializable(self, market_reading):
        d = market_reading.to_dict()
        # Should not raise
        js = json.dumps(d)
        assert len(js) > 1000  # non-trivially sized output

    def test_to_dict_has_all_top_level_keys(self, market_reading):
        d = market_reading.to_dict()
        expected_keys = {
            "date", "regime", "stress", "breadth", "macro",
            "sector_breadth", "sector_rs", "sector_leaderboard_60d",
            "analogs", "analog_distribution", "conditional", "watchlists",
            "concentration",
        }
        assert set(d.keys()) == expected_keys

    def test_call_with_historical_asof(self):
        """Should be able to compute the reading for a past date."""
        r = reading.get_market_reading(pd.Timestamp("2020-04-15"))
        assert r.date <= pd.Timestamp("2020-04-15")
        assert r.regime.regime in regime_mod.REGIMES
        # April 2020 was post-COVID-crash bounce — should be elevated stress
        assert r.stress.score > 40

    def test_orchestrator_is_idempotent(self):
        """Two calls should produce equivalent dicts (uses caching)."""
        r1 = reading.get_market_reading().to_dict()
        r2 = reading.get_market_reading().to_dict()
        assert r1["date"] == r2["date"]
        assert r1["regime"]["regime"] == r2["regime"]["regime"]
        assert abs(r1["stress"]["score"] - r2["stress"]["score"]) < 1e-9
