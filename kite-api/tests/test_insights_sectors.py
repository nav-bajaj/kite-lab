"""Tests for the sector-level insight modules:
  - `app.insights.sector_constituents` — loader for the dated snapshots
  - `app.insights.sector_breadth` — constituent-level breadth panel + snapshot

These verify the runtime-promoted modules work against the snapshot
that `scripts/fetch_sector_constituents.py` produces and the NSE 500
price panel at `nse500_data_merged/`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.insights import sector_breadth, sector_constituents


# ---------- sector_constituents ----------

class TestSectorConstituents:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        sector_constituents.clear_cache()

    def test_all_sectors_load(self):
        sectors = sector_constituents.get_all_sectors()
        assert len(sectors) >= 11, f"expected ≥11 sectors, got {len(sectors)}"
        assert "NIFTY_BANK" in sectors
        assert "NIFTY_IT" in sectors

    def test_sector_has_expected_structure(self):
        bank = sector_constituents.get_sector("NIFTY_BANK")
        assert bank.name == "NIFTY_BANK"
        assert bank.n >= 10
        assert "HDFCBANK" in bank.symbols
        assert "ICICIBANK" in bank.symbols
        assert bank.company_names["HDFCBANK"].startswith("HDFC Bank")
        assert bank.is_partial_coverage is False

    def test_partial_coverage_flag_set(self):
        media = sector_constituents.get_sector("NIFTY_MEDIA")
        assert media.is_partial_coverage is True, (
            "NIFTY_MEDIA should be flagged as partial coverage"
        )

    def test_symbol_to_sectors_reverse_mapping(self):
        # HDFCBANK is in multiple sectors: NIFTY_BANK, NIFTY_FIN_SERVICE,
        # NIFTY_CONSUMPTION (broad consumer-services index includes it)
        sectors_for = sector_constituents.get_sectors_for("HDFCBANK")
        assert "NIFTY_BANK" in sectors_for
        assert "NIFTY_FIN_SERVICE" in sectors_for
        assert len(sectors_for) >= 2

    def test_unknown_symbol_returns_empty(self):
        assert sector_constituents.get_sectors_for("NOTASTOCK") == ()

    def test_unknown_sector_raises(self):
        with pytest.raises(KeyError):
            sector_constituents.get_sector("NIFTY_DOES_NOT_EXIST")


# ---------- sector_breadth ----------

class TestSectorBreadthPanel:
    @pytest.fixture(scope="class", autouse=True)
    def _clear_cache(self):
        sector_breadth.clear_cache()
        sector_constituents.clear_cache()

    def test_panel_builds(self):
        panel = sector_breadth.compute_sector_breadth_panel()
        assert not panel.empty
        assert isinstance(panel.columns, pd.MultiIndex)
        assert "sector" in panel.columns.names
        assert "metric" in panel.columns.names

    def test_panel_covers_all_sectors(self):
        panel = sector_breadth.compute_sector_breadth_panel()
        sectors_in_panel = set(panel.columns.get_level_values("sector"))
        all_sectors = set(sector_constituents.get_all_sectors().keys())
        # Allow up to 1 sector missing (e.g., if all constituents had no price files)
        missing = all_sectors - sectors_in_panel
        assert len(missing) <= 1, f"too many sectors absent from panel: {missing}"

    def test_panel_has_expected_metrics(self):
        panel = sector_breadth.compute_sector_breadth_panel()
        metrics = set(panel.columns.get_level_values("metric"))
        expected = {
            "pct_above_50dma", "pct_above_100dma", "pct_above_200dma",
            "pct_advancing", "dispersion_20d", "median_ret_20d",
            "n_covered", "n_constituents", "thrust_day",
        }
        missing = expected - metrics
        assert not missing, f"missing metrics: {missing}"

    def test_panel_has_meaningful_history(self):
        panel = sector_breadth.compute_sector_breadth_panel()
        years = (panel.index.max() - panel.index.min()).days / 365.25
        assert years >= 10, f"only {years:.1f}y of history; need ≥10"

    def test_pct_above_dma_in_valid_range(self):
        panel = sector_breadth.compute_sector_breadth_panel()
        for sector in panel.columns.get_level_values("sector").unique():
            for col in ["pct_above_50dma", "pct_above_100dma", "pct_above_200dma"]:
                vals = panel[(sector, col)].dropna()
                if vals.empty:
                    continue
                assert vals.min() >= 0
                assert vals.max() <= 1.0001


class TestSectorBreadthSnapshot:
    @pytest.fixture(scope="class")
    def snapshot(self):
        return sector_breadth.get_sector_breadth_snapshot()

    def test_snapshot_returns_all_sectors(self, snapshot):
        all_sectors = set(sector_constituents.get_all_sectors().keys())
        snap_sectors = set(snapshot.keys())
        missing = all_sectors - snap_sectors
        assert len(missing) <= 1, f"sectors missing from snapshot: {missing}"

    def test_snapshot_dates_align(self, snapshot):
        dates = {s.date for s in snapshot.values()}
        assert len(dates) == 1, f"snapshot has multiple dates: {dates}"

    def test_partial_coverage_flag_propagates(self, snapshot):
        assert snapshot["NIFTY_MEDIA"].is_partial_coverage is True
        assert snapshot["NIFTY_BANK"].is_partial_coverage is False

    def test_leaders_laggards_disjoint(self, snapshot):
        """Even on partial-coverage sectors, leaders and laggards must not
        share symbols (the original NIFTY_MEDIA n=4 bug)."""
        for sector_name, s in snapshot.items():
            leader_syms = {sym for sym, _ in s.rs_leaders}
            laggard_syms = {sym for sym, _ in s.rs_laggards}
            overlap = leader_syms & laggard_syms
            assert not overlap, (
                f"{sector_name}: leaders and laggards share symbols {overlap}"
            )

    def test_leaders_sorted_descending(self, snapshot):
        for sector_name, s in snapshot.items():
            scores = [score for _, score in s.rs_leaders]
            assert scores == sorted(scores, reverse=True), (
                f"{sector_name} leaders not sorted descending: {s.rs_leaders}"
            )

    def test_laggards_sorted_ascending(self, snapshot):
        for sector_name, s in snapshot.items():
            scores = [score for _, score in s.rs_laggards]
            assert scores == sorted(scores), (
                f"{sector_name} laggards not sorted ascending: {s.rs_laggards}"
            )

    def test_coverage_field_matches_constituent_count(self, snapshot):
        for sector_name, s in snapshot.items():
            if s.n_constituents > 0:
                expected = s.n_covered / s.n_constituents
                assert abs(s.coverage - expected) < 1e-9

    def test_snapshot_to_dict_is_json_serializable(self, snapshot):
        """The snapshot needs to be serializable for the API response."""
        import json
        for sector_name, s in snapshot.items():
            d = s.to_dict()
            json.dumps(d)  # should not raise
