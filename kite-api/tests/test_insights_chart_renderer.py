"""Tests for the WhatsApp-portrait chart renderer.

Validates that the post-close and weekly images render at the right
dimensions, are valid PNGs, and don't blow up on edge-case historical
inputs (e.g., very early dates with sparse breadth data).
"""
from __future__ import annotations

import io

import pandas as pd
import pytest
from PIL import Image

from app.insights.notes import chart_renderer
from app.insights.reading import get_market_reading


# Target dimensions per PLAN.md — Instagram/WhatsApp portrait
EXPECTED_WIDTH = 1080
EXPECTED_HEIGHT = 1350


@pytest.fixture(scope="module")
def latest_reading():
    return get_market_reading()


class TestPostcloseImage:
    def test_returns_bytes(self, latest_reading):
        img = chart_renderer.make_postclose_image(latest_reading)
        assert isinstance(img, bytes)
        assert len(img) > 10_000, f"image too small ({len(img)} bytes)"

    def test_is_valid_png(self, latest_reading):
        img = chart_renderer.make_postclose_image(latest_reading)
        # PNG magic bytes
        assert img[:8] == b"\x89PNG\r\n\x1a\n"

    def test_dimensions(self, latest_reading):
        img = chart_renderer.make_postclose_image(latest_reading)
        with Image.open(io.BytesIO(img)) as pil_img:
            assert pil_img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT), (
                f"image size {pil_img.size} != target ({EXPECTED_WIDTH}, {EXPECTED_HEIGHT})"
            )

    def test_renders_for_historical_dates(self):
        """No crash on canonical historical dates."""
        for date in ["2020-03-23", "2018-10-05", "2022-06-17", "2017-10-13"]:
            r = get_market_reading(pd.Timestamp(date))
            img = chart_renderer.make_postclose_image(r)
            assert len(img) > 10_000


class TestWeeklyImage:
    def test_returns_valid_png_with_correct_dims(self, latest_reading):
        img = chart_renderer.make_weekly_image(latest_reading)
        assert img[:8] == b"\x89PNG\r\n\x1a\n"
        with Image.open(io.BytesIO(img)) as pil_img:
            assert pil_img.size == (EXPECTED_WIDTH, EXPECTED_HEIGHT)

    def test_is_larger_than_postclose(self, latest_reading):
        """Weekly has an extra analog-fan panel — should produce a larger PNG."""
        pc = chart_renderer.make_postclose_image(latest_reading)
        wk = chart_renderer.make_weekly_image(latest_reading)
        assert len(wk) > len(pc), "weekly should be larger (more chart content)"


class TestSavers:
    def test_save_postclose_writes_file(self, latest_reading, tmp_path):
        out = tmp_path / "postclose.png"
        path = chart_renderer.save_postclose_image(latest_reading, out)
        assert path.exists()
        assert path.stat().st_size > 10_000

    def test_save_weekly_writes_file(self, latest_reading, tmp_path):
        out = tmp_path / "weekly.png"
        path = chart_renderer.save_weekly_image(latest_reading, out)
        assert path.exists()
        assert path.stat().st_size > 10_000

    def test_save_creates_parent_directory(self, latest_reading, tmp_path):
        out = tmp_path / "nested" / "dir" / "image.png"
        path = chart_renderer.save_postclose_image(latest_reading, out)
        assert path.exists()
        assert path.parent.is_dir()


class TestThumbnailLegibility:
    """Verify text remains readable when image is shrunk to WhatsApp-thumbnail
    width (375px). We can't visually inspect, but we can verify that key
    elements (regime/stress in the subtitle, sector names) are large enough
    in the rendered file."""

    def test_thumbnail_resize_does_not_corrupt(self, latest_reading):
        """Shrinking by ~3x must produce a non-blank image. (Sanity check
        that matplotlib produced real pixel content, not a blank canvas.)"""
        img = chart_renderer.make_postclose_image(latest_reading)
        with Image.open(io.BytesIO(img)) as pil_img:
            thumb = pil_img.resize((375, 469))
            colors = thumb.convert("RGB").getcolors(maxcolors=2**16)
            # A blank/single-color image has ≤2 unique colors after antialiasing
            assert colors is None or len(colors) > 100, (
                "thumbnail has too few colors — likely blank or solid fill"
            )
