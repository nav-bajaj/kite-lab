"""Spec: insight-engine in-memory caches self-invalidate when data changes.

The production bug these tests pin: the cached loaders keyed their
``@lru_cache`` on a static flag, so once a uvicorn worker held a panel in
memory it never re-checked the on-disk freshness and served frozen data until
a redeploy. The fix keys each cache on an mtime-based *signature* of the
sources the loader reads, so the next request after the daily pipeline rewrites
the files rebuilds automatically.

Authored test-first per ``tasks/insight_engine/TDD_POLICY.md``. Two cache
shapes are covered: the no-arg panel loader (``breadth.get_breadth_panel``,
lru-on-static) and a date-keyed dict loader (``stock_metrics.get_stock_metrics``,
whose per-date ``_MEM_CACHE`` must also fold in the source signature so a
same-date re-request after adjusted closes reloads).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from app.insights import _freshness, breadth, reading, stock_metrics


# ─────────────────────────── synthetic data helpers ───────────────────────────

def _bdates(n: int, end: str = "2026-06-30") -> pd.DatetimeIndex:
    return pd.bdate_range(end=end, periods=n)


def _write_prices(prices_dir, symbols, dates, bump: float = 0.0) -> None:
    """Write one ``<SYM>_day.csv`` per symbol (OHLCV) into ``prices_dir``.

    ``bump`` shifts the whole close series so a rewrite is observable.
    """
    prices_dir.mkdir(parents=True, exist_ok=True)
    for i, sym in enumerate(symbols):
        close = 100.0 + i + np.arange(len(dates), dtype=float) + bump
        df = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1_000_000.0,
        })
        df.to_csv(prices_dir / f"{sym}_day.csv", index=False)


def _write_universe(path, symbols) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"Symbol": symbols}).to_csv(path, index=False)


def _touch_future(*paths, seconds: int = 20) -> None:
    """Force mtimes to clearly the future so freshness checks see a change
    regardless of filesystem mtime granularity."""
    import time
    future = time.time() + seconds
    for p in paths:
        os.utime(p, (future, future))


SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]


@pytest.fixture
def breadth_env(tmp_path, monkeypatch):
    """Point breadth at an isolated synthetic data dir and clear caches."""
    prices = tmp_path / "nse500_data_merged"
    universe = tmp_path / "data" / "static" / "nse500_universe.csv"
    cache = tmp_path / "cache" / "insights" / "breadth_panel.pkl"

    dates = _bdates(40)
    _write_prices(prices, SYMBOLS, dates)
    _write_universe(universe, SYMBOLS)

    monkeypatch.setattr(breadth, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(breadth, "_prices_dir", lambda: prices)
    monkeypatch.setattr(breadth, "_universe_file", lambda u="nse500": universe)
    monkeypatch.setattr(breadth, "_cache_file", lambda u="nse500": cache)

    breadth.clear_cache()
    yield {"prices": prices, "universe": universe, "cache": cache, "dates": dates}
    breadth.clear_cache()


# ─────────────────────────── signature helper spec ───────────────────────────

class TestFreshnessHelper:
    def test_missing_file_is_stable_sentinel(self, tmp_path):
        assert _freshness.file_signature(tmp_path / "nope.csv") == 0.0

    def test_signature_changes_when_file_appears_later(self, tmp_path):
        p = tmp_path / "later.csv"
        before = _freshness.file_signature(p)   # missing → 0.0
        p.write_text("hello")
        after = _freshness.file_signature(p)
        assert before == 0.0
        assert after != before and after > 0.0

    def test_dir_signature_missing_sentinel_is_sentinel(self, tmp_path):
        assert _freshness.dir_signature(tmp_path, sentinel="RELIANCE_day.csv") == 0.0

    def test_dir_signature_tracks_sentinel_mtime(self, tmp_path):
        sent = tmp_path / "RELIANCE_day.csv"
        sent.write_text("1")
        before = _freshness.dir_signature(tmp_path, sentinel="RELIANCE_day.csv")
        _touch_future(sent)
        after = _freshness.dir_signature(tmp_path, sentinel="RELIANCE_day.csv")
        assert after != before


# ─────────────── breadth: no-arg panel loader (lru-on-static shape) ───────────

class TestBreadthSelfInvalidation:
    def test_reloads_after_source_changes_without_explicit_clear(self, breadth_env):
        """THE regression that caught prod: update a source file, then call the
        loader again with NO explicit clear — it must return the NEW data."""
        panel1 = breadth.get_breadth_panel()
        last1 = panel1.index.max()

        # Pipeline appends a fresh trading day and rewrites the panel.
        new_dates = _bdates(41, end="2026-07-01")
        _write_prices(breadth_env["prices"], SYMBOLS, new_dates)
        _write_universe(breadth_env["universe"], SYMBOLS)
        _touch_future(
            breadth_env["prices"] / "RELIANCE_day.csv",
            breadth_env["universe"],
        )

        panel2 = breadth.get_breadth_panel()  # no clear_cache() call
        assert panel2.index.max() > last1, (
            "loader served frozen in-memory panel after the source advanced"
        )

    def test_unchanged_data_does_not_rebuild(self, breadth_env, monkeypatch):
        """Identical signature → cache hit → the loader body (freshness check +
        rebuild/reload) must not run again, keeping the hot path fast."""
        calls = {"n": 0}
        orig = breadth._cache_is_fresh

        def spy(path, universe="nse500"):
            calls["n"] += 1
            return orig(path, universe)

        monkeypatch.setattr(breadth, "_cache_is_fresh", spy)

        breadth.get_breadth_panel()          # cold: body runs
        n_cold = calls["n"]
        assert n_cold >= 1
        breadth.get_breadth_panel()          # warm: pure lru hit, body skipped
        assert calls["n"] == n_cold

    def test_clear_cache_forces_rebuild(self, breadth_env, monkeypatch):
        calls = {"n": 0}
        orig = breadth.compute_breadth_panel

        def spy(close_panel):
            calls["n"] += 1
            return orig(close_panel)

        monkeypatch.setattr(breadth, "compute_breadth_panel", spy)

        breadth.get_breadth_panel()
        assert calls["n"] == 1
        breadth.clear_cache()
        breadth.get_breadth_panel()
        assert calls["n"] == 2, "clear_cache() must force a rebuild"

    def test_clear_all_caches_forces_breadth_rebuild(self, breadth_env, monkeypatch):
        calls = {"n": 0}
        orig = breadth.compute_breadth_panel

        def spy(close_panel):
            calls["n"] += 1
            return orig(close_panel)

        monkeypatch.setattr(breadth, "compute_breadth_panel", spy)

        breadth.get_breadth_panel()
        assert calls["n"] == 1
        reading.clear_all_caches()           # must not raise; clears every module
        breadth.get_breadth_panel()
        assert calls["n"] == 2


# ─────────────── stock_metrics: date-keyed _MEM_CACHE shape ───────────────

@pytest.fixture
def stock_metrics_env(tmp_path, monkeypatch):
    prices = tmp_path / "nse500_data_merged"
    indices = tmp_path / "indices"
    universe = tmp_path / "data" / "static" / "nse500_universe.csv"
    cache_dir = tmp_path / "cache" / "insights"
    cache_dir.mkdir(parents=True, exist_ok=True)

    dates = _bdates(30)
    _write_prices(prices, SYMBOLS, dates)
    _write_universe(universe, SYMBOLS)
    # Nifty 50 index for beta / nifty loader.
    nifty_close = 20000.0 + np.arange(len(dates), dtype=float)
    pd.DataFrame({"date": dates, "close": nifty_close}).to_csv(
        (indices.mkdir(parents=True, exist_ok=True) or indices) / "NIFTY_50.csv",
        index=False,
    )

    monkeypatch.setattr(stock_metrics, "_prices_dir", lambda: prices)
    monkeypatch.setattr(stock_metrics, "_indices_dir", lambda: indices)
    monkeypatch.setattr(breadth, "_universe_file", lambda u="nse500": universe)
    monkeypatch.setattr(
        stock_metrics, "_cache_file",
        lambda key: cache_dir / f"stock_metrics_{key}.pkl",
    )

    stock_metrics.clear_cache()
    yield {"prices": prices, "dates": dates, "universe": universe}
    stock_metrics.clear_cache()


class TestStockMetricsSelfInvalidation:
    def test_same_date_adjusted_close_reloads(self, stock_metrics_env):
        """Date-keyed cache must fold in the source signature: after an
        adjusted close on the SAME resolved date, a re-request reloads."""
        env = stock_metrics_env
        asof = env["dates"].max()

        m1 = stock_metrics.get_stock_metrics(asof)
        assert m1, "expected a non-empty metrics frame"
        close1 = m1["RELIANCE"].close

        # Corporate-action adjustment: same dates, shifted closes, newer mtime.
        _write_prices(env["prices"], SYMBOLS, env["dates"], bump=50.0)
        _touch_future(env["prices"] / "RELIANCE_day.csv", env["universe"])

        m2 = stock_metrics.get_stock_metrics(asof)   # no explicit clear
        close2 = m2["RELIANCE"].close
        assert close2 is not None and close1 is not None
        assert close2 != close1, (
            "date-keyed cache served a stale record after a same-date "
            "adjusted-close update"
        )

    def test_unchanged_data_is_cache_hit(self, stock_metrics_env, monkeypatch):
        calls = {"n": 0}
        orig = stock_metrics.compute_stock_metrics

        def spy(asof, panels, nifty_close=None):
            calls["n"] += 1
            return orig(asof, panels, nifty_close=nifty_close)

        monkeypatch.setattr(stock_metrics, "compute_stock_metrics", spy)

        asof = stock_metrics_env["dates"].max()
        stock_metrics.get_stock_metrics(asof)
        n_cold = calls["n"]
        assert n_cold == 1
        stock_metrics.get_stock_metrics(asof)
        assert calls["n"] == n_cold, "identical inputs must not recompute"


class TestSchemaGuard:
    """A disk cache that is fresh by mtime but written by an OLDER code
    version (missing newer columns) must be rebuilt, not served — the
    mtime check can't see code changes (insights_dashboard_v2 Slice 2.5,
    where avg_dist_from_200dma/mcclellan_sum/pct_above_21dma were added)."""

    def test_stale_schema_pickle_triggers_rebuild(self, breadth_env):
        # Build once (writes a current-schema pickle), then strip the new
        # columns and touch the file so it stays mtime-fresh.
        panel = breadth.get_breadth_panel()
        old_schema = panel.drop(
            columns=["avg_dist_from_200dma", "mcclellan_sum", "pct_above_21dma"]
        )
        old_schema.to_pickle(breadth_env["cache"])
        # Simulate a worker restart after a deploy: in-memory cache gone,
        # stale-schema pickle still on disk (clear_cache would delete it,
        # which is precisely what does NOT happen on a redeploy).
        breadth._get_breadth_panel_cached.cache_clear()

        reloaded = breadth.get_breadth_panel()
        for col in ("avg_dist_from_200dma", "mcclellan_sum", "pct_above_21dma"):
            assert col in reloaded.columns, f"stale-schema cache served: {col} missing"
