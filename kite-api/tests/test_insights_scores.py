"""Spec tests for the composite 0-100 scores + insight tags (`scores.py`).

Authored FIRST per TDD_POLICY.md. Because the four scores are pure
functions of a StockMetrics record (+ RS percentile + coiled/inflection
flags), we test them by constructing StockMetrics directly — no panel
needed. Coverage:
  - monotonicity invariants (improving a driver never lowers its score)
  - band-boundary semantics (inclusive lower edge)
  - exact insight-tag strings (compliance-critical)
  - JSON serializability
"""
from __future__ import annotations

import json

import pytest

from app.insights import scores as sc
from app.insights.rs_rank import RSEntry
from app.insights.stock_metrics import StockMetrics


def _mk_metrics(**over) -> StockMetrics:
    """A neutral-ish StockMetrics; override specific fields per test."""
    base = dict(
        symbol="T", date="2024-01-01", close=100.0,
        ret_1d=0.0, ret_1w=0.0, ret_1m=0.05, ret_3m=0.10,
        ret_6m=0.15, ret_12m=0.20,
        sma_20=98.0, sma_50=95.0, sma_100=92.0, sma_200=90.0,
        above_20dma=True, above_50dma=True, above_100dma=True, above_200dma=True,
        dist_20dma_pct=0.02, dist_50dma_pct=0.05,
        dist_100dma_pct=0.08, dist_200dma_pct=0.11,
        slope_50dma_20d=0.02, slope_200dma_20d=0.01, dma_50_above_200=True,
        dist_52w_high_pct=-0.05, dist_52w_low_pct=0.40,
        days_since_52w_high=10, drawdown_from_peak_pct=-0.05,
        fresh_52w_high=False,
        atr_14=2.0, atr_pct=0.02,
        vol_20d_annualized=0.25, vol_60d_annualized=0.25,
        vol_percentile_1y=0.50, beta_60d=1.0,
        max_drawdown_1y_pct=-0.15, max_drawdown_6m_pct=-0.08,
        rsi_14=55.0, ret_5d_pctile_1y=0.50, pct_positive_weeks_6m=0.60,
        vol_ratio=1.2, vol_ratio_5d=1.1, avg_turnover_20d_cr=25.0,
        updown_vol_ratio_20d=1.3, liquidity_tier="Good",
    )
    base.update(over)
    return StockMetrics(**base)


# ───────────────────────────── band helpers ─────────────────────────────

class TestBandBoundaries:
    @pytest.mark.parametrize("score,band", [
        (24.9, "Low"), (25.0, "Moderate"), (49.9, "Moderate"),
        (50.0, "High"), (74.9, "High"), (75.0, "Very high"), (100.0, "Very high"),
    ])
    def test_extension_band_inclusive_lower_edge(self, score, band):
        assert sc.extension_band(score) == band

    @pytest.mark.parametrize("score,band", [
        (0.0, "Weak"), (32.9, "Weak"), (33.0, "Neutral"),
        (65.9, "Neutral"), (66.0, "Strong"), (100.0, "Strong"),
    ])
    def test_volume_band_inclusive_lower_edge(self, score, band):
        assert sc.volume_band(score) == band


# ───────────────────────────── monotonicity ─────────────────────────────

class TestMonotonicity:
    def test_trend_score_rises_with_more_dmas_above(self):
        below = _mk_metrics(above_50dma=False, above_100dma=False,
                            above_200dma=False, dma_50_above_200=False,
                            dist_50dma_pct=-0.05, dist_100dma_pct=-0.08,
                            dist_200dma_pct=-0.11)
        above = _mk_metrics()  # all above
        s_below = sc.compute_scores(below).trend_score
        s_above = sc.compute_scores(above).trend_score
        assert s_above > s_below

    def test_trend_score_never_falls_when_drawdown_shrinks(self):
        worse = _mk_metrics(max_drawdown_1y_pct=-0.45)
        better = _mk_metrics(max_drawdown_1y_pct=-0.05)
        assert (sc.compute_scores(better).trend_score
                >= sc.compute_scores(worse).trend_score)

    def test_extension_risk_rises_with_extension(self):
        calm = _mk_metrics(close=100.0, sma_20=100.0, sma_50=100.0,
                           atr_14=2.0, rsi_14=50.0, ret_5d_pctile_1y=0.30)
        hot = _mk_metrics(close=112.0, sma_20=100.0, sma_50=98.0,
                          atr_14=2.0, rsi_14=80.0, ret_5d_pctile_1y=0.95)
        assert (sc.compute_scores(hot).extension_risk
                > sc.compute_scores(calm).extension_risk)

    def test_volume_confirmation_rises_with_volume(self):
        quiet = _mk_metrics(vol_ratio=0.8, vol_ratio_5d=0.9,
                            updown_vol_ratio_20d=0.8)
        loud = _mk_metrics(vol_ratio=3.0, vol_ratio_5d=2.5,
                           updown_vol_ratio_20d=3.0)
        assert (sc.compute_scores(loud).volume_confirmation
                > sc.compute_scores(quiet).volume_confirmation)

    def test_consistency_rises_with_more_positive_weeks(self):
        choppy = _mk_metrics(pct_positive_weeks_6m=0.30)
        smooth = _mk_metrics(pct_positive_weeks_6m=0.90)
        assert (sc.compute_scores(smooth).momentum_consistency
                > sc.compute_scores(choppy).momentum_consistency)

    def test_all_scores_in_unit_range(self):
        for m in [_mk_metrics(), _mk_metrics(vol_ratio=10.0, rsi_14=95.0,
                                             close=200.0, sma_20=100.0)]:
            s = sc.compute_scores(m)
            for v in [s.trend_score, s.extension_risk,
                      s.volume_confirmation, s.momentum_consistency]:
                assert v is None or 0.0 <= v <= 100.0


# ───────────────────────────── insight tags ─────────────────────────────

class TestTags:
    def test_momentum_leader_from_top_decile_rs(self):
        rs = RSEntry(symbol="T", rs_score=0.95, rank=5, percentile=95.0,
                     sector_rank=1, sector_size=10, rank_21d_ago=8,
                     rank_delta_21d=3)
        tags = sc.compute_scores(_mk_metrics(), rs=rs).tags
        assert "Momentum leader" in tags

    def test_near_and_fresh_52w_high_tags(self):
        near = sc.compute_scores(_mk_metrics(dist_52w_high_pct=-0.02,
                                             fresh_52w_high=False)).tags
        assert "Near 52-week high" in near
        assert "Fresh 52-week high" not in near
        fresh = sc.compute_scores(_mk_metrics(dist_52w_high_pct=0.0,
                                              fresh_52w_high=True)).tags
        assert "Fresh 52-week high" in fresh

    def test_volume_expansion_tag_at_2x(self):
        assert "Volume expansion" in sc.compute_scores(
            _mk_metrics(vol_ratio=2.4)).tags
        assert "Volume expansion" not in sc.compute_scores(
            _mk_metrics(vol_ratio=1.5)).tags

    def test_extended_tag_tracks_band(self):
        hot = _mk_metrics(close=130.0, sma_20=100.0, sma_50=98.0,
                          atr_14=2.0, rsi_14=90.0, ret_5d_pctile_1y=0.99)
        s = sc.compute_scores(hot)
        if s.extension_band in ("High", "Very high"):
            assert "Extended" in s.tags

    def test_coiled_and_new_momentum_flags(self):
        s = sc.compute_scores(_mk_metrics(), is_coiled=True,
                              is_inflection_top25=True)
        assert "Coiled" in s.tags
        assert "New momentum" in s.tags

    def test_quiet_tag_requires_low_vol_and_above_200dma(self):
        q = sc.compute_scores(_mk_metrics(vol_percentile_1y=0.20,
                                          above_200dma=True)).tags
        assert "Quiet" in q
        not_q = sc.compute_scores(_mk_metrics(vol_percentile_1y=0.20,
                                              above_200dma=False)).tags
        assert "Quiet" not in not_q


# ───────────────────────────── serialization ─────────────────────────────

class TestSerialization:
    def test_to_dict_json_serializable(self):
        s = sc.compute_scores(_mk_metrics())
        json.dumps(s.to_dict())

    def test_tags_are_list_in_dict(self):
        d = sc.compute_scores(_mk_metrics(), is_coiled=True).to_dict()
        assert isinstance(d["tags"], list)
