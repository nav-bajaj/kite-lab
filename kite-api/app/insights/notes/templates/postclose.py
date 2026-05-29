"""Post-close template — fires at 4:15 PM IST after market close.

Structure:
  • Opening: dated header
  • Headline (bold, single line)
  • Regime + stress paragraph (the "where are we" context)
  • Sector observation (which sectors led/lagged + narrow-vs-broad nuance)
  • Historical context (analog reference)
  • Watch tomorrow (specific stocks)
  • CTA + disclaimer
"""
from __future__ import annotations

from app.insights.notes.commentary import Commentary
from app.insights.reading import MarketReading

CTA = "Full dashboard: marketworks.in/insights"


def render(reading: MarketReading, commentary: Commentary) -> str:
    """Return the WhatsApp-ready text body for the post-close note."""
    date_str = reading.date.strftime("%a, %d %b %Y")

    parts = [
        f"*MARKETWORKS — Post-close note · {date_str}*",
        "",
        f"*{commentary.headline}*",
        "",
        commentary.regime,
        "",
        f"📊 *Sectors*",
        commentary.sector,
    ]
    if commentary.conditional:
        parts.extend(["", f"📈 *Historical base-rate*", commentary.conditional])
    parts.extend([
        "",
        f"👀 *Watch tomorrow*",
        commentary.watch,
    ])
    # Phase 5.C — learn_moment fires only when something is unusual today
    if commentary.learn_moment:
        parts.extend(["", f"💡 *Indicator spotlight*", commentary.learn_moment])
    parts.extend([
        "",
        f"_{CTA}_",
        "",
        f"_{commentary.disclaimer}_",
    ])
    return "\n".join(parts)
