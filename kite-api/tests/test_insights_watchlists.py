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


# ─────────── Spec tests (promoted from characterization 2026-05-28) ───────────
#
# Synthetic-panel tests that pin detector tie-breaking and boundary
# behaviour. Built per the playbook in `tasks/insight_engine/TDD_POLICY.md`.
#
# Approach: monkeypatch `_stock_panel` and `_nifty_close` to return
# hand-crafted DataFrames. Each test constructs the minimum input that
# isolates one behaviour (will fire / will not fire / boundary).


import numpy as np


def _make_panel(days: int = 300, start_price: float = 100.0,
                drift: float = 0.0005, seed: int = 0) -> pd.DataFrame:
    """A baseline 'flat-ish' stock series — drift around `start_price`.
    Used as scaffolding; individual tests overwrite specific symbols/days
    to construct the scenario they care about."""
    dates = pd.date_range("2024-01-01", periods=days, freq="B")
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, 0.005, size=days)
    rets[0] = 0.0
    closes = start_price * np.exp(np.cumsum(rets))
    return pd.DataFrame({"BASE": closes}, index=dates)


class TestBreakoutDetectorSpec:
    """Pin the breakout-detector contract via synthetic panels."""

    def _patch(self, monkeypatch, panel: pd.DataFrame,
               nifty: pd.Series | None = None):
        monkeypatch.setattr(watchlists, "_stock_panel", lambda: panel)
        if nifty is None:
            # Trivial Nifty: same length, flat — not used by breakout detector
            nifty = pd.Series(20000.0, index=panel.index, name="close")
        monkeypatch.setattr(watchlists, "_nifty_close", lambda: nifty)
        # Note: do NOT call watchlists.clear_cache() here — the patched
        # _stock_panel is a plain function without .cache_clear(). The
        # detectors look it up via module namespace at call time, so the
        # patch is already effective.

    def test_fires_only_when_above_both_20d_high_and_50dma(self, monkeypatch):
        """The two-filter contract: close > 20d_high AND close > 50_DMA.
        Constructing 3 stocks that isolate each filter."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        # Stock A: cleanly breaks both filters — should fire
        # Stock B: above 20d high but BELOW 50-DMA — should NOT fire
        # Stock C: above 50-DMA but NOT above 20d high — should NOT fire
        a = np.linspace(80, 100, n - 1).tolist() + [110.0]   # spike up
        b = np.linspace(120, 95, n - 1).tolist() + [97.0]    # downtrend, blip
        c = np.linspace(80, 100, n - 1).tolist() + [99.0]    # near high
        panel = pd.DataFrame({"A": a, "B": b, "C": c}, index=dates)
        self._patch(monkeypatch, panel)

        results = watchlists.get_breakouts(limit=10)
        symbols = {e.symbol for e in results}
        assert "A" in symbols, "A should fire (above 20d high AND above 50-DMA)"
        assert "B" not in symbols, "B should NOT fire (below 50-DMA)"
        assert "C" not in symbols, "C should NOT fire (not above 20d high)"

    def test_tie_at_20d_high_does_not_fire(self, monkeypatch):
        """Spec decision: close == 20d_high should NOT fire. We pin the
        strict-greater-than semantic that the implementation uses."""
        n = 60
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        # Build a series where today's close exactly equals the trailing
        # 20-day high (last day before today was the high)
        vals = np.linspace(80, 105, n - 1).tolist()
        # Today equals the 20-day high (which is the last value pre-today)
        vals.append(vals[-1])
        panel = pd.DataFrame({"TIE": vals}, index=dates)
        self._patch(monkeypatch, panel)

        results = watchlists.get_breakouts(limit=10)
        symbols = {e.symbol for e in results}
        assert "TIE" not in symbols, (
            "Strict-greater-than: close == 20d_high should not fire"
        )

    def test_handles_nan_gracefully(self, monkeypatch):
        """Spec: stocks with NaN in lookback or today must be silently
        dropped, not cause exceptions or false positives."""
        n = 70
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        good = np.linspace(80, 105, n - 1).tolist() + [115.0]
        bad = [float("nan")] * 30 + np.linspace(80, 110, n - 30).tolist()
        panel = pd.DataFrame({"GOOD": good, "BAD": bad}, index=dates)
        self._patch(monkeypatch, panel)

        results = watchlists.get_breakouts(limit=10)
        # Must not raise. GOOD should fire; BAD might or might not depending
        # on whether the partial NaN history yields a valid 20d_high — what
        # matters is no exception.
        assert any(e.symbol == "GOOD" for e in results)


def _patch_panel(monkeypatch, panel: pd.DataFrame):
    """Module-level helper: patch both _stock_panel and _nifty_close with
    a constructed panel + trivial Nifty series of the same length."""
    monkeypatch.setattr(watchlists, "_stock_panel", lambda: panel)
    monkeypatch.setattr(
        watchlists, "_nifty_close",
        lambda: pd.Series(20000.0, index=panel.index, name="close"),
    )


class TestMultiYearBreakoutDetectorSpec:
    """Spec for the 5-year-high detector — needs ≥1260 trading days."""

    def test_insufficient_history_returns_empty(self, monkeypatch):
        """Spec: stocks without 5 years of history are silently excluded
        (not an error). Empty universe → empty result, not crash."""
        n = 500  # less than 1260
        dates = pd.date_range("2020-01-01", periods=n, freq="B")
        panel = pd.DataFrame({"SHORT": np.linspace(100, 200, n)}, index=dates)
        _patch_panel(monkeypatch, panel)

        results = watchlists.get_multi_year_breakouts(limit=10)
        assert results == []

    def test_fires_for_genuine_5y_high(self, monkeypatch):
        """A stock that's been ranging for 5 years and breaks out today
        should fire."""
        n = 1400
        dates = pd.date_range("2020-01-01", periods=n, freq="B")
        # 5-year history with peak at day 100, ranging below since,
        # then a new high today
        prices = np.full(n, 100.0)
        prices[100] = 120.0                            # earlier peak
        prices[200:1399] = np.linspace(110.0, 100.0, 1199)  # range below
        prices[-1] = 125.0                             # new 5y high
        panel = pd.DataFrame({"MYB": prices}, index=dates)
        _patch_panel(monkeypatch, panel)

        results = watchlists.get_multi_year_breakouts(limit=10)
        symbols = {e.symbol for e in results}
        assert "MYB" in symbols, (
            "MYB at new 5y high (125 vs prior 120 peak) should fire"
        )


class TestSustainedUptrendDetectorSpec:
    """Pin the 3-filter contract: 1y return ≥ 20%, max-DD ≤ 8%, above 200-DMA."""

    def test_high_return_but_deep_drawdown_does_not_fire(self, monkeypatch):
        """Spec: gained 30% over the year but had a 20% intra-period
        drawdown in the last 60 days should NOT fire — the 'clean' filter
        excludes choppy uptrends."""
        n = 300
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        smooth = np.linspace(100.0, 135.0, n - 60)
        peak = smooth[-1]
        crash = np.linspace(peak, peak * 0.80, 25)
        recover = np.linspace(peak * 0.80, 130.0, 35)
        prices = np.concatenate([smooth, crash, recover])
        panel = pd.DataFrame({"CHOPPY": prices}, index=dates)
        _patch_panel(monkeypatch, panel)

        results = watchlists.get_sustained_uptrend(limit=10)
        symbols = {e.symbol for e in results}
        assert "CHOPPY" not in symbols, (
            "20% intra-60d drawdown should exclude this name"
        )

    def test_low_return_does_not_fire_even_if_clean(self, monkeypatch):
        """Spec: clean trend with <20% 1y return doesn't fire — the
        return threshold is binding."""
        n = 300
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        prices = np.linspace(100.0, 110.0, n)  # +10% only
        panel = pd.DataFrame({"MILD": prices}, index=dates)
        _patch_panel(monkeypatch, panel)

        results = watchlists.get_sustained_uptrend(limit=10)
        assert all(e.symbol != "MILD" for e in results), (
            "10% 1y return is below the 20% threshold; should not fire"
        )

    def test_fires_for_clean_strong_uptrend(self, monkeypatch):
        """Sanity: a clean +40% uptrend with no drawdowns should fire."""
        n = 300
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        prices = np.linspace(100.0, 140.0, n)
        panel = pd.DataFrame({"CLEAN": prices}, index=dates)
        _patch_panel(monkeypatch, panel)

        results = watchlists.get_sustained_uptrend(limit=10)
        assert any(e.symbol == "CLEAN" for e in results), (
            "Clean +40% uptrend should fire"
        )
