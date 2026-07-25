"""Tests for `app.insights.zerodha_sectors` — the per-stock Zerodha sector
loader over the map produced by `scripts/fetch_zerodha_sectors.py`
(`data/static/zerodha_sectors.csv`).

Two layers:
  - anchors against the real committed map (stable, high-cap classifications),
  - a hermetic parse + cache-invalidation check on a temp CSV.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.insights import zerodha_sectors


class TestRealMap:
    @pytest.fixture(autouse=True)
    def _clear(self):
        zerodha_sectors.clear_cache()

    def test_map_loads(self):
        m = zerodha_sectors.get_symbol_to_sector()
        assert len(m) >= 450, f"expected the full tracked map, got {len(m)}"

    def test_known_anchors(self):
        # Finer than NSE's macro Industry: Reliance is Energy (not "Oil Gas"),
        # TCS is Software Services (not the catch-all "Information Technology").
        assert zerodha_sectors.get_sector_for("RELIANCE") == "Energy"
        assert zerodha_sectors.get_sector_for("TCS") == "Software Services"
        assert zerodha_sectors.get_sector_for("HDFCBANK") == "Financial Services"

    def test_renamed_tickers_resolved_via_alias(self):
        # Universe keeps the canonical symbol; the fetch follows SYMBOL_ALIASES
        # (LTIM->LTM, AKZOINDIA->JSWDULUX) so these still carry a sector.
        assert zerodha_sectors.get_sector_for("LTIM") == "Software Services"
        assert zerodha_sectors.get_sector_for("AKZOINDIA") == "Building Materials"

    def test_unknown_symbol_returns_none(self):
        assert zerodha_sectors.get_sector_for("NOTASTOCK") is None

    def test_reverse_index(self):
        rev = zerodha_sectors.get_sector_to_symbols()
        assert "TCS" in rev["Software Services"]
        assert all(isinstance(v, tuple) for v in rev.values())

    def test_super_sector_rollup(self):
        # Fine sectors roll up into the coarser 15-bucket study layer.
        assert zerodha_sectors.get_super_sector_for("HDFCBANK") == "Financials"
        assert zerodha_sectors.get_super_sector_for("TCS") == "IT & Internet"
        # Media Entertainment (a thin 4-name fine sector) folds into IT & Internet.
        assert zerodha_sectors.get_super_sector_for("SUNTV") == "IT & Internet"

    def test_super_sector_reverse_index_is_coarser(self):
        fine = zerodha_sectors.get_sector_to_symbols()
        supers = zerodha_sectors.get_super_sector_to_symbols()
        assert len(supers) <= 15
        assert len(supers) < len(fine)  # strictly coarser than the fine level
        assert "TCS" in supers["IT & Internet"]

    def test_super_sectors_stay_within_known_15(self):
        # Guard against taxonomy drift: every super-sector in the live map must
        # be one of the 15 defined buckets (no silent fallback leakage).
        known = {
            "Financials", "Industrials & Capital Goods", "Healthcare",
            "IT & Internet", "Automobile & Ancillaries", "Energy",
            "FMCG / Staples", "Real Estate & Building", "Materials & Chemicals",
            "Consumer Discretionary", "Metals & Mining", "Transport & Logistics",
            "Telecom", "Tourism & Hospitality", "Diversified / Other",
        }
        got = set(zerodha_sectors.get_super_sector_to_symbols())
        assert got <= known, f"unexpected super-sectors: {got - known}"


class TestHermetic:
    def test_parse_and_cache_invalidation(self, tmp_path: Path, monkeypatch):
        csv_path = tmp_path / "zerodha_sectors.csv"
        monkeypatch.setattr(zerodha_sectors, "_path", lambda: csv_path)

        header = ("symbol,company,zerodha_sector,zerodha_sector_slug,"
                  "super_sector,source_exchange\n")
        csv_path.write_text(
            header
            + "AAA,Alpha Ltd.,Metals,metals,Metals & Mining,NSE\n"
            + "BBB,Beta Ltd.,,,,\n"  # unresolved: no sector -> skipped
        )
        zerodha_sectors.clear_cache()
        assert zerodha_sectors.get_sector_for("AAA") == "Metals"
        assert zerodha_sectors.get_super_sector_for("AAA") == "Metals & Mining"
        assert zerodha_sectors.get_sector_for("BBB") is None  # blank skipped

        # Rewriting the file changes its mtime signature -> cache self-busts,
        # no explicit clear_cache() needed.
        import os
        import time

        csv_path.write_text(
            header + "AAA,Alpha Ltd.,Chemicals,chemicals,Materials & Chemicals,NSE\n")
        future = time.time() + 5
        os.utime(csv_path, (future, future))
        assert zerodha_sectors.get_sector_for("AAA") == "Chemicals"
        assert zerodha_sectors.get_super_sector_for("AAA") == "Materials & Chemicals"

    def test_missing_file_raises(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(zerodha_sectors, "_path", lambda: tmp_path / "nope.csv")
        zerodha_sectors.clear_cache()
        with pytest.raises(FileNotFoundError):
            zerodha_sectors.get_symbol_to_sector()
