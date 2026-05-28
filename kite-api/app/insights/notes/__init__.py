"""Daily Quant Note generation — Phase 1 of the Insight Engine.

Reads a MarketReading from `app.insights.reading` and produces the
plain-English narrative + chart bundle delivered to WhatsApp / email /
web each market day.

Submodules:
  commentary    — narrative engine (no jargon, lightly actionable)
  chart_renderer — matplotlib → branded WhatsApp-portrait PNG
  templates/    — premarket / postclose / weekly templates
  note_assembler — packages text + image for delivery
"""
