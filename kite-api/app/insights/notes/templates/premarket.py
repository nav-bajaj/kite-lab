"""Pre-market template — fires at 8:30 AM IST before market open.

Shorter and more forward-looking than post-close. Uses yesterday's close
as the most recent reading (markets haven't opened yet).

Structure:
  • Opening: dated header indicating pre-market
  • Headline (where things stand entering today)
  • Quick regime/stress recap (1 short line)
  • Yesterday's sector takeaway (1 line)
  • Things to watch today (specific names)
  • CTA + disclaimer
"""
from __future__ import annotations

from app.insights.notes.commentary import Commentary
from app.insights.reading import MarketReading

CTA = "Full dashboard: marketworks.in/insights"


def render(reading: MarketReading, commentary: Commentary) -> str:
    """Return the WhatsApp-ready text body for the pre-market note."""
    # Note uses YESTERDAY's close (which is what reading.date represents
    # if called pre-market; data is end-of-prior-day in either case)
    asof_str = reading.date.strftime("%a, %d %b")
    regime_short = commentary.regime.split(".")[0] + "."  # first sentence

    parts = [
        f"*MARKETWORKS — Pre-market note*",
        f"_Entering {asof_str} session · based on prior close_",
        "",
        f"*{commentary.headline}*",
        "",
        regime_short,
        "",
        f"📊 *Sectors*",
        commentary.sector,
        "",
        f"👀 *Watch today*",
        commentary.watch,
        "",
        f"_{CTA}_",
        "",
        f"_{commentary.disclaimer}_",
    ]
    return "\n".join(parts)
