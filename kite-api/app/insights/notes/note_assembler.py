"""Note assembler — packages text + image into a single delivery bundle.

One entry point — `assemble(mode, reading)` — handles all three modes
(premarket / postclose / weekly) and returns a `NoteBundle` ready for
broadcast or file persistence.

Phase 1 ships with manual-broadcast workflow: the CLI script writes the
bundle to disk and opens a preview; the admin copies image + text into
WhatsApp Web. Phase 3 replaces the manual step with the WhatsApp
Business API call.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from app.insights.notes import chart_renderer, commentary as commentary_mod
from app.insights.notes.templates import postclose, premarket, weekly
from app.insights.reading import MarketReading

Mode = Literal["premarket", "postclose", "weekly"]
VALID_MODES = ("premarket", "postclose", "weekly")


@dataclass
class NoteBundle:
    """A complete note ready for broadcast."""
    mode: Mode
    date: pd.Timestamp
    text: str
    image_bytes: bytes
    # Metadata for tracking / API responses
    regime: str
    stress_score: float
    headline: str

    def save_to(self, out_dir: Path) -> tuple[Path, Path]:
        """Write text + image to a dated directory. Returns (text_path, image_path)."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = f"{self.date.strftime('%Y-%m-%d')}_{self.mode}"
        text_path = out_dir / f"{slug}.txt"
        image_path = out_dir / f"{slug}.png"
        text_path.write_text(self.text)
        image_path.write_bytes(self.image_bytes)
        return text_path, image_path


def assemble(mode: Mode, reading: MarketReading) -> NoteBundle:
    """Build the full NoteBundle for `mode`.

    `mode` ∈ {"premarket", "postclose", "weekly"}. Picks the matching
    template + chart variant. Returns text + PNG bytes packaged with
    metadata for the API / tracking layer.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"Unknown mode {mode!r}. Expected one of {VALID_MODES}")

    commentary = commentary_mod.compose(reading, mode=mode)

    # Text (per-mode template)
    if mode == "premarket":
        text = premarket.render(reading, commentary)
    elif mode == "postclose":
        text = postclose.render(reading, commentary)
    else:  # weekly
        text = weekly.render(reading, commentary)

    # Image (weekly gets the 3-panel variant with the analog fan)
    if mode == "weekly":
        image_bytes = chart_renderer.make_weekly_image(reading)
    else:
        image_bytes = chart_renderer.make_postclose_image(reading)

    return NoteBundle(
        mode=mode,
        date=reading.date,
        text=text,
        image_bytes=image_bytes,
        regime=reading.regime.regime,
        stress_score=reading.stress.score,
        headline=commentary.headline,
    )
