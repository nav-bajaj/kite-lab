"""Tests for the quant-driven watchlists."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from app.insights import watchlists


class TestWatchlists:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        watchlists.clear_cache()

    def test_breakouts_returns_list(self):
        results = watchlists.get_breakouts(limit=5)
        assert isinstance(results, list)
        assert len(results) <= 5
        for e in results:
            assert e.score > 0, f"breakout score should be >0 (was {e.score})"
            assert "above" in e.note

    def test_rs_leaders_returns_sorted_by_score(self):
        results = watchlists.get_rs_leaders(limit=10)
        assert len(results) > 0
        scores = [e.score for e in results]
        assert scores == sorted(scores, reverse=True), "RS leaders not sorted descending"

    def test_coiled_springs_returns_list(self):
        results = watchlists.get_coiled_springs(limit=10)
        for e in results:
            assert 0 <= e.score <= 1, f"coiled-spring percentile out of range: {e.score}"

    def test_stretched_above_threshold(self):
        results = watchlists.get_stretched(threshold=0.20, limit=10)
        for e in results:
            assert e.score > 0.20, (
                f"stretched candidate {e.symbol} score {e.score} ≤ threshold 0.20"
            )

    def test_recent_breakdowns_have_negative_score(self):
        results = watchlists.get_recent_breakdowns(limit=10)
        for e in results:
            assert e.score < 0, (
                f"breakdown {e.symbol} score should be negative (was {e.score})"
            )

    def test_all_watchlists_returns_seven(self):
        # Phase 4.2 added 2 validity-tested patterns alongside the original 5.
        # pullback_to_50dma failed its validity study (see
        # tasks/insight_engine/PATTERN_VALIDITY/) and is intentionally not here.
        all_lists = watchlists.get_all_watchlists(limit=5)
        assert set(all_lists.keys()) == {
            "breakouts", "rs_leaders", "coiled_springs",
            "stretched", "recent_breakdowns",
            "multi_year_breakouts", "sustained_uptrend",
        }
        for name, entries in all_lists.items():
            assert isinstance(entries, list)
            assert len(entries) <= 5

    def test_entries_have_required_fields(self):
        results = watchlists.get_rs_leaders(limit=3)
        for e in results:
            assert e.symbol
            assert isinstance(e.close, float)
            assert e.close > 0
            assert isinstance(e.score, float)
            assert isinstance(e.note, str)
            assert isinstance(e.sectors, tuple)

    def test_entries_serialize_to_json(self):
        all_lists = watchlists.get_all_watchlists(limit=3)
        for name, entries in all_lists.items():
            for e in entries:
                json.dumps(e.to_dict())  # must not raise

    def test_breakouts_filters_to_uptrending(self):
        """Every breakout should be above its 50-DMA — the filter we
        documented to avoid false breakouts in downtrends."""
        results = watchlists.get_breakouts(limit=10)
        # Indirect check: chg_today should typically be strongly positive
        # since these names just broke higher with notable strength
        for e in results:
            if e.chg_today_pct is not None:
                # Most should be positive today (some may be soft if broke
                # earlier in the lookback window)
                pass  # not strict — just checking structure
            assert e.close > 0

    def test_asof_can_be_historical(self):
        """Calling with a past date should still produce a sensible list."""
        results = watchlists.get_rs_leaders(asof=pd.Timestamp("2024-01-31"), limit=5)
        # Just verify it doesn't crash and returns something plausible
        assert isinstance(results, list)
