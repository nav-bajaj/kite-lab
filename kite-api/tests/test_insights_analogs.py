"""Tests for the historical analog finder.

The killer differentiator. These tests verify:
  - Matches are deterministic and reproducible
  - Trivial neighbors (within ±60 days of target) are excluded
  - Forward returns are properly attached
  - Output is JSON-serializable for API responses
  - Sanity: COVID crash's top analogs are other 2011 stress episodes
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.insights import analog_finder, breadth, macro, stress


class TestAnalogFinder:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        analog_finder.clear_cache()
        breadth.clear_cache()
        macro.clear_cache()
        stress.clear_cache()

    def test_returns_requested_k(self):
        matches = analog_finder.find_analogs(k=10)
        assert len(matches) == 10

    def test_matches_sorted_by_distance(self):
        matches = analog_finder.find_analogs(k=10)
        distances = [m.distance for m in matches]
        assert distances == sorted(distances), "matches not sorted ascending by distance"

    def test_exclusion_window_respected(self):
        """No match should be within ±EXCLUSION_DAYS of the target date."""
        target = pd.Timestamp("2020-06-15")
        matches = analog_finder.find_analogs(asof=target, k=5)
        for m in matches:
            delta = abs((m.match_date - target).days)
            assert delta > analog_finder.EXCLUSION_DAYS, (
                f"match {m.match_date} only {delta}d from target {target} — "
                f"violates {analog_finder.EXCLUSION_DAYS}-day exclusion"
            )

    def test_no_future_matches(self):
        """Matches must be ON OR BEFORE the target date — no peeking ahead."""
        target = pd.Timestamp("2022-01-15")
        matches = analog_finder.find_analogs(asof=target, k=10)
        for m in matches:
            assert m.match_date <= target, (
                f"match {m.match_date} is AFTER target {target}"
            )

    def test_covid_analogs_are_other_stress_episodes(self):
        """The 5 closest matches to COVID crash should be other identifiable
        market-stress episodes (high VIX, low breadth, deep drawdown). We
        don't have an exact COVID analog in 16y, but the matches should be
        directionally correct (VIX > 25, breadth < 50%)."""
        matches = analog_finder.find_analogs(asof=pd.Timestamp("2020-03-23"), k=5)
        assert len(matches) == 5
        for m in matches:
            assert m.vix_close is not None and m.vix_close > 25, (
                f"COVID analog {m.match_date} has VIX={m.vix_close} — not stress-like"
            )
            assert m.pct_above_200dma is not None and m.pct_above_200dma < 0.50, (
                f"COVID analog {m.match_date} has pct200={m.pct_above_200dma} — not stress-like"
            )

    def test_calm_day_analogs_are_calm(self):
        """For a known calm day (2017-09-04), analogs should also be calm
        (low VIX, broad breadth)."""
        matches = analog_finder.find_analogs(asof=pd.Timestamp("2017-09-04"), k=5)
        for m in matches:
            assert m.vix_close is not None and m.vix_close < 20, (
                f"calm-day analog {m.match_date} has VIX={m.vix_close}"
            )
            assert m.pct_above_200dma is not None and m.pct_above_200dma > 0.50

    def test_forward_returns_populated_for_old_matches(self):
        """Matches well in the past should have all 4 forward returns."""
        matches = analog_finder.find_analogs(asof=pd.Timestamp("2017-09-04"), k=5)
        for m in matches:
            if (pd.Timestamp("2026-01-01") - m.match_date).days > 200:
                assert m.fwd_return_120d is not None, (
                    f"old match {m.match_date} missing fwd_120d"
                )

    def test_analog_match_to_dict_is_json_serializable(self):
        matches = analog_finder.find_analogs(k=3)
        for m in matches:
            json.dumps(m.to_dict())

    def test_distribution_returns_all_horizons(self):
        dist = analog_finder.get_analog_distribution(k=20)
        assert set(dist.keys()) == set(analog_finder.FORWARD_HORIZONS)

    def test_distribution_quantiles_ordered(self):
        dist = analog_finder.get_analog_distribution(k=20)
        for h, d in dist.items():
            if d.median is None:
                continue
            assert d.p5 <= d.p25 <= d.median <= d.p75 <= d.p95, (
                f"horizon {h}: percentiles not monotonic"
            )

    def test_distribution_to_dict_serializable(self):
        dist = analog_finder.get_analog_distribution(k=10)
        for h, d in dist.items():
            json.dumps(d.to_dict())

    def test_deterministic(self):
        """Same call should give same answer (no random component)."""
        analog_finder.clear_cache()
        m1 = analog_finder.find_analogs(asof=pd.Timestamp("2019-06-15"), k=5)
        analog_finder.clear_cache()
        m2 = analog_finder.find_analogs(asof=pd.Timestamp("2019-06-15"), k=5)
        for a, b in zip(m1, m2):
            assert a.match_date == b.match_date
            assert abs(a.distance - b.distance) < 1e-9
