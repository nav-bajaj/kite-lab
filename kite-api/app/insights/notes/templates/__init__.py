"""Daily Quant Note text templates — one per delivery cadence.

Each template takes a Commentary + MarketReading and returns the
WhatsApp-ready message text. Templates are intentionally thin: they
ARRANGE prose, they don't compose it. The narrative engine
(commentary.py) produces the sentences; templates pick which sections
appear in which order, format the heading lines, and add CTAs.

WhatsApp formatting conventions used:
  *bold*      → bold text (single asterisks)
  _italic_    → italics (single underscores)
  blank line  → paragraph break
"""

from app.insights.notes.templates import postclose, premarket, weekly

__all__ = ["postclose", "premarket", "weekly"]
