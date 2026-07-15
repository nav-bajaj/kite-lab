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


class TestHermetic:
    def test_parse_and_cache_invalidation(self, tmp_path: Path, monkeypatch):
        csv_path = tmp_path / "zerodha_sectors.csv"
        monkeypatch.setattr(zerodha_sectors, "_path", lambda: csv_path)

        header = "symbol,company,zerodha_sector,zerodha_sector_slug,source_exchange\n"
        csv_path.write_text(
            header
            + "AAA,Alpha Ltd.,Metals,metals,NSE\n"
            + "BBB,Beta Ltd.,,,\n"  # unresolved: no sector -> skipped
        )
        zerodha_sectors.clear_cache()
        assert zerodha_sectors.get_sector_for("AAA") == "Metals"
        assert zerodha_sectors.get_sector_for("BBB") is None  # blank skipped

        # Rewriting the file changes its mtime signature -> cache self-busts,
        # no explicit clear_cache() needed.
        import os
        import time

        csv_path.write_text(header + "AAA,Alpha Ltd.,Chemicals,chemicals,NSE\n")
        future = time.time() + 5
        os.utime(csv_path, (future, future))
        assert zerodha_sectors.get_sector_for("AAA") == "Chemicals"

    def test_missing_file_raises(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(zerodha_sectors, "_path", lambda: tmp_path / "nope.csv")
        zerodha_sectors.clear_cache()
        with pytest.raises(FileNotFoundError):
            zerodha_sectors.get_symbol_to_sector()
