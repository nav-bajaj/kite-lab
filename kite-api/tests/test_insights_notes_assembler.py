"""Tests for the Daily Quant Note assembler + templates.

End-to-end check that each delivery mode produces a complete bundle
with WhatsApp-friendly text + valid PNG image.
"""
from __future__ import annotations

import pandas as pd
import pytest
from PIL import Image
import io

from app.insights.notes.note_assembler import (
    NoteBundle, VALID_MODES, assemble,
)
from app.insights.reading import get_market_reading


@pytest.fixture(scope="module")
def latest_reading():
    return get_market_reading()


# ---------- mode validity ----------

class TestModeValidity:
    def test_unknown_mode_raises(self, latest_reading):
        with pytest.raises(ValueError):
            assemble("not-a-mode", latest_reading)

    def test_three_valid_modes(self):
        assert set(VALID_MODES) == {"premarket", "postclose", "weekly"}


# ---------- structure ----------

class TestBundleStructure:
    @pytest.mark.parametrize("mode", VALID_MODES)
    def test_bundle_fields_populated(self, mode, latest_reading):
        b = assemble(mode, latest_reading)
        assert isinstance(b, NoteBundle)
        assert b.mode == mode
        assert isinstance(b.date, pd.Timestamp)
        assert b.text and len(b.text) > 100
        assert b.image_bytes and len(b.image_bytes) > 10_000
        assert b.regime
        assert 0 <= b.stress_score <= 100
        assert b.headline

    @pytest.mark.parametrize("mode", VALID_MODES)
    def test_image_is_valid_png(self, mode, latest_reading):
        b = assemble(mode, latest_reading)
        assert b.image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        with Image.open(io.BytesIO(b.image_bytes)) as img:
            assert img.size == (1080, 1350)


# ---------- text content per mode ----------

class TestTextContent:
    def test_postclose_has_section_headings(self, latest_reading):
        b = assemble("postclose", latest_reading)
        # 'Historical' (analog) section retired — see ANALOG_STUDY.md
        for heading in ("Post-close", "*Sectors*", "*Watch tomorrow*"):
            assert heading in b.text, f"missing heading: {heading!r}"

    def test_premarket_has_section_headings(self, latest_reading):
        b = assemble("premarket", latest_reading)
        for heading in ("Pre-market", "*Sectors*", "*Watch today*"):
            assert heading in b.text, f"missing heading: {heading!r}"

    def test_weekly_includes_conditional_section(self, latest_reading):
        b = assemble("weekly", latest_reading)
        # 'Historical analog' section retired — see ANALOG_STUDY.md
        for heading in ("Weekly digest", "*Market state*",
                        "*Sector rotation*",
                        "*Watch next week*"):
            assert heading in b.text, f"missing heading: {heading!r}"

    def test_weekly_always_has_pattern_of_the_week(self, latest_reading):
        # Phase 5.C — weekly digest always carries a pattern-of-the-week
        b = assemble("weekly", latest_reading)
        assert "*Pattern of the week*" in b.text

    def test_postclose_spotlight_when_unusual(self):
        # COVID panic day — stress in panic zone — spotlight must fire
        from app.insights.reading import get_market_reading
        r = get_market_reading(pd.Timestamp("2020-03-23"))
        b = assemble("postclose", r)
        assert "*Indicator spotlight*" in b.text, (
            "Expected indicator spotlight on COVID panic day; "
            f"text was: {b.text[:500]!r}"
        )

    def test_weekly_is_longer_than_premarket(self, latest_reading):
        pre = assemble("premarket", latest_reading)
        wk = assemble("weekly", latest_reading)
        assert len(wk.text) > len(pre.text), (
            "weekly should be the longest format"
        )

    def test_all_modes_include_disclaimer(self, latest_reading):
        for mode in VALID_MODES:
            b = assemble(mode, latest_reading)
            assert "not investment advice" in b.text.lower()

    def test_all_modes_include_cta(self, latest_reading):
        for mode in VALID_MODES:
            b = assemble(mode, latest_reading)
            assert "marketworks.in/insights" in b.text


# ---------- persistence ----------

class TestSavingBundle:
    @pytest.mark.parametrize("mode", VALID_MODES)
    def test_save_to_creates_files(self, mode, latest_reading, tmp_path):
        b = assemble(mode, latest_reading)
        text_path, image_path = b.save_to(tmp_path)
        assert text_path.exists() and text_path.stat().st_size > 100
        assert image_path.exists() and image_path.stat().st_size > 10_000
        # Filename convention: YYYY-MM-DD_<mode>.{txt,png}
        assert mode in text_path.stem
        assert mode in image_path.stem
        assert text_path.suffix == ".txt"
        assert image_path.suffix == ".png"


# ---------- historical-date robustness ----------

class TestHistoricalDates:
    @pytest.mark.parametrize("mode", VALID_MODES)
    @pytest.mark.parametrize("date", [
        "2020-03-23",  # COVID crash
        "2018-10-05",  # NBFC crisis
        "2022-06-17",  # rate shock
        "2017-10-13",  # melt-up
    ])
    def test_renders_for_historical_date(self, mode, date):
        """Each mode should produce a complete bundle for any historical date
        with enough data — no crashes, no empty text."""
        r = get_market_reading(pd.Timestamp(date))
        b = assemble(mode, r)
        assert len(b.text) > 100
        assert len(b.image_bytes) > 10_000
        assert b.regime
        assert b.headline
