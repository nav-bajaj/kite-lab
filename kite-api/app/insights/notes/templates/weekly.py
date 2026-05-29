"""Weekly digest template — fires Sunday 8 PM IST.

Long-form, multi-section. Includes BOTH the analog reference (specific
historical date) AND the conditional-distribution stats (aggregate
historical context). Reads more like a Sunday market column than the
daily ticker-style notes.

Structure:
  • Opening: week-ending header
  • Headline
  • Regime + stress paragraph (full)
  • Sector deep-dive
  • Historical analog (specific date + outcome)
  • Conditional stats (the aggregate "buy panic / fade complacency" type stat)
  • Watch next week
  • Closing CTA + disclaimer
"""
from __future__ import annotations

from app.insights.notes.commentary import Commentary
from app.insights.reading import MarketReading

CTA = "Read the full week's data: marketworks.in/insights"


def render(reading: MarketReading, commentary: Commentary) -> str:
    """Return the WhatsApp-ready text body for the Sunday weekly digest."""
    week_end = reading.date.strftime("%a, %d %b %Y")

    parts = [
        f"*MARKETWORKS — Weekly digest · week ending {week_end}*",
        "",
        f"*{commentary.headline}*",
        "",
        f"📐 *Market state*",
        commentary.regime,
        "",
        f"📊 *Sector rotation*",
        commentary.sector,
    ]

    # Conditional base-rate stats only render if we have enough data
    if commentary.conditional:
        parts.extend([
            "",
            f"📈 *Historical base-rate*",
            commentary.conditional,
        ])

    parts.extend([
        "",
        f"👀 *Watch next week*",
        commentary.watch,
    ])
    # Phase 5.C — weekly digest always carries a pattern-of-the-week
    if commentary.learn_moment:
        parts.extend(["", f"💡 *Pattern of the week*", commentary.learn_moment])
    parts.extend([
        "",
        f"_{CTA}_",
        "",
        f"_{commentary.disclaimer}_",
    ])
    return "\n".join(parts)
