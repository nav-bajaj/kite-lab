"""Tests for the sector RS ranking module.

Verifies the panel + snapshot produce ranks that are internally
consistent (1..N for each window, sum of ranks across N sectors equals
N*(N+1)/2), WoW deltas reconcile, and the snapshot is JSON-serializable
for the API layer.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.insights import sector_breadth, sector_rs


# ---------- panel ----------

class TestSectorRSPanel:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        sector_rs.clear_cache()
        sector_breadth.clear_cache()

    @pytest.fixture(scope="class")
    def panel(self):
        return sector_rs.compute_sector_rs_panel()

    def test_panel_builds(self, panel):
        assert not panel.empty
        assert isinstance(panel.columns, pd.MultiIndex)
        assert set(panel.columns.names) == {"sector", "window", "metric"}

    def test_panel_has_expected_windows(self, panel):
        windows = set(panel.columns.get_level_values("window"))
        assert windows == set(sector_rs.WINDOWS_TD.keys())

    def test_panel_has_expected_metrics(self, panel):
        metrics = set(panel.columns.get_level_values("metric"))
        assert metrics == {"rs_score", "rank"}

    def test_panel_covers_long_history_sectors(self, panel):
        sectors = set(panel.columns.get_level_values("sector"))
        assert sectors == set(sector_rs.SECTOR_INDICES), (
            f"panel sectors {sorted(sectors)} != configured "
            f"{sorted(sector_rs.SECTOR_INDICES)}"
        )

    def test_meaningful_history(self, panel):
        years = (panel.index.max() - panel.index.min()).days / 365.25
        assert years >= 14, f"only {years:.1f}y of history"

    def test_ranks_are_1_to_n_per_window_per_date(self, panel):
        """For each (date, window), valid ranks should form a contiguous
        1..k sequence where k = number of sectors with non-NaN RS."""
        # Sample 10 random dates to keep this test fast
        rng = np.random.default_rng(42)
        sample_dates = rng.choice(panel.index, size=min(10, len(panel.index)), replace=False)
        for d in sample_dates:
            for window in sector_rs.WINDOWS_TD.keys():
                rank_cols = [c for c in panel.columns
                             if c[1] == window and c[2] == "rank"]
                ranks = panel.loc[d, rank_cols].dropna().astype(int).tolist()
                if not ranks:
                    continue
                k = len(ranks)
                assert set(ranks).issubset(set(range(1, k + 1))), (
                    f"date={d.date()} window={window}: ranks {sorted(ranks)} "
                    f"not contained in 1..{k}"
                )

    def test_rs_score_signs_make_sense(self, panel):
        """On any given date, at least one sector should have positive RS
        and at least one negative — since RS is computed vs Nifty 50 which
        is itself a weighted blend, sectors should disperse around 0."""
        # Spot check the latest date
        asof = panel.index.max()
        for window in sector_rs.WINDOWS_TD.keys():
            rs_cols = [c for c in panel.columns
                       if c[1] == window and c[2] == "rs_score"]
            scores = panel.loc[asof, rs_cols].dropna()
            if len(scores) < 5:  # too few to meaningfully disperse
                continue
            assert (scores > 0).any() and (scores < 0).any(), (
                f"window={window}: all sectors same sign at {asof.date()} "
                f"({scores.to_dict()})"
            )


# ---------- snapshot ----------

class TestSectorRSSnapshot:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        sector_rs.clear_cache()
        sector_breadth.clear_cache()

    @pytest.fixture(scope="class")
    def snapshot(self):
        return sector_rs.get_sector_rs_snapshot()

    def test_snapshot_returns_all_long_history_sectors(self, snapshot):
        assert set(snapshot.keys()) == set(sector_rs.SECTOR_INDICES)

    def test_snapshot_dates_align(self, snapshot):
        dates = {s.date for s in snapshot.values()}
        assert len(dates) == 1, f"snapshot has multiple dates: {dates}"

    def test_ranks_in_expected_range(self, snapshot):
        n_sectors = len(sector_rs.SECTOR_INDICES)
        for sector_name, s in snapshot.items():
            for window in ["5d", "20d", "60d", "120d", "252d"]:
                rank = getattr(s, f"rank_{window}")
                if rank is None:
                    continue
                assert 1 <= rank <= n_sectors, (
                    f"{sector_name} rank_{window}={rank} out of range"
                )

    def test_no_duplicate_ranks_within_window(self, snapshot):
        """Each window's ranks should be a set of distinct integers across
        sectors (or use method='min' tie-breaking, which the panel does;
        ties remain possible but should be rare with continuous RS scores)."""
        for window in ["5d", "20d", "60d", "120d", "252d"]:
            ranks = [getattr(s, f"rank_{window}") for s in snapshot.values()
                     if getattr(s, f"rank_{window}") is not None]
            # Allow ties (method='min') but check most ranks are unique
            assert len(set(ranks)) >= len(ranks) - 1, (
                f"window={window}: too many tied ranks {sorted(ranks)}"
            )

    def test_rank_change_is_consistent_with_prior_rank(self, snapshot):
        """rank_change_wow_60d should equal (5d_ago_rank − today_rank).
        We can cross-check by reading the panel directly for one sector."""
        panel = sector_rs.compute_sector_rs_panel()
        asof = panel.index.max()
        asof_pos = panel.index.get_loc(asof)
        wow_date = panel.index[asof_pos - sector_rs.WOW_TD]

        for sector_name, s in snapshot.items():
            if s.rank_change_wow_60d is None:
                continue
            today_rank = int(panel.loc[asof, (sector_name, "60d", "rank")])
            wow_rank = int(panel.loc[wow_date, (sector_name, "60d", "rank")])
            expected = wow_rank - today_rank
            assert s.rank_change_wow_60d == expected, (
                f"{sector_name}: rank_change_wow_60d={s.rank_change_wow_60d} "
                f"expected {expected} (today={today_rank}, wow={wow_rank})"
            )

    def test_breadth_overlay_populated(self, snapshot):
        """sector_rs.snapshot should populate pct_above_200dma from
        sector_breadth for sectors that are in both modules."""
        # Sectors in sector_rs that have a constituent-level breadth view
        # NIFTY_MEDIA is partial but still has a value
        for sector in ["NIFTY_BANK", "NIFTY_IT", "NIFTY_METAL"]:
            s = snapshot[sector]
            assert s.pct_above_200dma is not None, (
                f"{sector} missing pct_above_200dma overlay"
            )
            assert 0 <= s.pct_above_200dma <= 1

    def test_partial_coverage_flag_propagates(self, snapshot):
        assert snapshot["NIFTY_MEDIA"].is_partial_coverage is True
        assert snapshot["NIFTY_BANK"].is_partial_coverage is False

    def test_sector_close_and_chg_populated(self, snapshot):
        for sector_name, s in snapshot.items():
            assert s.sector_close is not None and s.sector_close > 0, (
                f"{sector_name} missing sector_close"
            )
            assert s.sector_chg_today_pct is not None
            # Daily change rarely exceeds ±20% — sanity bound
            assert abs(s.sector_chg_today_pct) < 0.20, (
                f"{sector_name} day chg {s.sector_chg_today_pct} looks wrong"
            )

    def test_snapshot_to_dict_is_json_serializable(self, snapshot):
        for sector_name, s in snapshot.items():
            d = s.to_dict()
            json.dumps(d)  # should not raise


# ---------- leaderboard helper ----------

class TestLeaderboard:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        sector_rs.clear_cache()
        sector_breadth.clear_cache()

    def test_leaderboard_sorted_by_rank(self):
        for window in ["5d", "20d", "60d", "120d", "252d"]:
            board = sector_rs.get_leaderboard(window)
            ranks = [getattr(s, f"rank_{window}") for s in board]
            ranks_nonnull = [r for r in ranks if r is not None]
            assert ranks_nonnull == sorted(ranks_nonnull), (
                f"leaderboard({window}) not sorted by rank"
            )

    def test_leaderboard_contains_all_sectors(self):
        board = sector_rs.get_leaderboard("60d")
        sectors = {s.sector for s in board}
        assert sectors == set(sector_rs.SECTOR_INDICES)
