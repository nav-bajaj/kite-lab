"""Tests for the cross-asset feature engine — Phase 4.5.

Written test-first per `tasks/insight_engine/TDD_POLICY.md`. The engine
takes per-asset OHLC dataframes and produces standardized features
(z-scores, ROCs, distance-from-200DMA) that downstream consumers can
read uniformly.

Scope tested:
  - `compute_asset_features(close_series)` — z-scores at 60d/252d,
    ROCs at 5d/20d/60d, distance-from-200DMA, percentile-rank-of-close
  - `get_cross_asset_snapshot()` — for each registered asset, returns
    the latest feature row; missing-history assets produce None values
  - Spec invariants: percentile in [0, 1]; z-scores have plausible
    range; distance-from-200DMA None when history < 200 days
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.insights import cross_asset


# ─────────── per-series feature engine ───────────

class TestAssetFeatureSpec:
    """Spec for `compute_asset_features(close_series)`."""

    def test_returns_dataclass_with_expected_fields(self):
        # Build a long, plausibly-behaved synthetic series
        idx = pd.date_range("2018-01-01", periods=1500, freq="B")
        rng = np.random.default_rng(0)
        rets = rng.normal(0.0003, 0.01, size=1500)
        closes = 100.0 * np.exp(np.cumsum(rets))
        series = pd.Series(closes, index=idx, name="X")

        feat = cross_asset.compute_asset_features(series)
        for field in (
            "close", "z_60d", "z_252d", "roc_5d", "roc_20d", "roc_60d",
            "dist_from_200dma", "pctile_252d",
        ):
            assert hasattr(feat, field), f"missing field {field}"

    def test_zscore_in_plausible_range(self):
        idx = pd.date_range("2018-01-01", periods=1500, freq="B")
        rng = np.random.default_rng(1)
        closes = 100.0 + np.cumsum(rng.normal(0, 0.5, 1500))
        series = pd.Series(closes, index=idx)
        feat = cross_asset.compute_asset_features(series)
        # For an essentially-stationary series, z-score values shouldn't
        # be wildly outside ±5 — that would indicate a bug in the rolling
        # window calculation
        for z in (feat.z_60d, feat.z_252d):
            if z is not None:
                assert -5.0 < z < 5.0, f"implausible z-score: {z}"

    def test_percentile_in_unit_interval(self):
        idx = pd.date_range("2018-01-01", periods=1500, freq="B")
        rng = np.random.default_rng(2)
        closes = 100.0 + np.cumsum(rng.normal(0, 0.3, 1500))
        series = pd.Series(closes, index=idx)
        feat = cross_asset.compute_asset_features(series)
        if feat.pctile_252d is not None:
            assert 0.0 <= feat.pctile_252d <= 1.0

    def test_dist_from_200dma_none_when_history_too_short(self):
        """Spec: less than 200 days of history → dist_from_200dma is
        None rather than misleading."""
        idx = pd.date_range("2025-01-01", periods=100, freq="B")
        series = pd.Series(np.linspace(100, 110, 100), index=idx)
        feat = cross_asset.compute_asset_features(series)
        assert feat.dist_from_200dma is None

    def test_dist_from_200dma_positive_when_close_above_200dma(self):
        """Spec sanity: smoothly-rising series, today's close above the
        trailing-200 average should produce positive distance."""
        idx = pd.date_range("2018-01-01", periods=400, freq="B")
        closes = np.linspace(100.0, 200.0, 400)
        series = pd.Series(closes, index=idx)
        feat = cross_asset.compute_asset_features(series)
        assert feat.dist_from_200dma is not None
        assert feat.dist_from_200dma > 0, (
            f"Rising series: today's close should be above 200-DMA; "
            f"got dist={feat.dist_from_200dma}"
        )

    def test_roc_5d_pct_change_correct(self):
        """Spec: roc_5d is the percent change over the last 5 sessions
        — pin the arithmetic with a known input."""
        # Build a series where last value is 110 and value 5 sessions ago
        # was 100 → roc_5d should be 0.10
        idx = pd.date_range("2018-01-01", periods=300, freq="B")
        closes = np.full(300, 100.0)
        closes[-1] = 110.0
        series = pd.Series(closes, index=idx)
        feat = cross_asset.compute_asset_features(series)
        assert feat.roc_5d is not None
        assert abs(feat.roc_5d - 0.10) < 1e-6, (
            f"roc_5d should be exactly 0.10 in this fixture; got {feat.roc_5d}"
        )

    def test_handles_too_short_series_without_crash(self):
        """Spec: ≤5 days of data → most features None, no exception."""
        idx = pd.date_range("2025-05-01", periods=3, freq="B")
        series = pd.Series([100.0, 101.0, 102.0], index=idx)
        feat = cross_asset.compute_asset_features(series)
        # close must be populated even when other features can't be
        assert feat.close == 102.0
        assert feat.z_60d is None
        assert feat.z_252d is None
        assert feat.dist_from_200dma is None


# ─────────── multi-asset snapshot ───────────

class TestCrossAssetSnapshot:
    """Spec for `get_cross_asset_snapshot()` — the public function the
    Pulse page (when wired) and commentary read from."""

    def test_returns_dict_keyed_by_asset_id(self):
        snap = cross_asset.get_cross_asset_snapshot()
        assert isinstance(snap, dict)
        # We expect at least one registered asset
        assert len(snap) >= 1

    def test_every_entry_has_label_and_features(self):
        snap = cross_asset.get_cross_asset_snapshot()
        for asset_id, entry in snap.items():
            assert hasattr(entry, "asset_id")
            assert hasattr(entry, "label")
            assert hasattr(entry, "features")
            assert entry.asset_id == asset_id
            assert entry.label, f"{asset_id} missing label"

    def test_serializable_to_dict(self):
        snap = cross_asset.get_cross_asset_snapshot()
        for entry in snap.values():
            d = entry.to_dict()
            json.dumps(d)  # must not raise

    def test_assets_with_no_data_marked_unavailable(self):
        """Spec: when a registered asset has no CSV available, the entry
        is included but with `data_available=False` and feature fields
        all None. Pins the contract: UI consumer can iterate the dict
        and find every registered asset, gracefully handling missing
        data."""
        snap = cross_asset.get_cross_asset_snapshot()
        # Look at the documented assets that are deferred (we don't have
        # USDINR / crude / US 10y CSVs yet) — they should appear in the
        # snapshot but with data_available=False
        deferred_assets = [a for a in snap.values()
                           if a.data_available is False]
        # Either none are deferred (all available), or those that are
        # deferred have None features cleanly
        for entry in deferred_assets:
            for fname in ("z_60d", "z_252d", "roc_5d", "roc_20d",
                          "roc_60d", "dist_from_200dma", "pctile_252d"):
                assert getattr(entry.features, fname) is None, (
                    f"{entry.asset_id}: data_available=False but "
                    f"{fname} is not None"
                )


# ─────────── integration on real available data ───────────

class TestRealDataIntegration:
    """Integration check: at least one cross-asset series with real long
    history must produce a non-trivial feature row."""

    def test_at_least_one_asset_has_full_features(self):
        snap = cross_asset.get_cross_asset_snapshot()
        full = [e for e in snap.values() if e.data_available
                and e.features.dist_from_200dma is not None]
        assert len(full) >= 1, (
            "Expected at least one cross-asset series with >200 days of "
            "history to be available. Current state: "
            f"{[(a, e.data_available) for a, e in snap.items()]}"
        )
