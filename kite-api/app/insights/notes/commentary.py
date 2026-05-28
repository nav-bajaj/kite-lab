"""Plain-English commentary engine.

Given a `MarketReading`, produces a structured `Commentary` object that
templates (postclose / premarket / weekly) compose into the Daily Quant
Note. Output style follows the editorial guidelines from PLAN.md:

  - Lead each section with a plain-English headline; no jargon
  - Translate every number into accessible language ("about 2 in 3"
    instead of "64%" when it improves readability; bare numbers for
    things readers parse natively like a stress score)
  - Anchor claims with historical context — "highest in 6 months",
    "last seen in March 2018" — never raw percentile speak
  - End each section with one concrete observation or thing to watch.
    Never a recommendation; always neutral framing
  - Specificity over abstraction — name actual stocks/sectors, not
    "select names"

Approach: deterministic rule-based templating with multiple sentence
variants per situation, picked by signal magnitude. No LLM dependency,
no regulatory surface around AI-generated investment content, fully
reproducible across channels.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from app.insights import regime as regime_mod
from app.insights.reading import MarketReading


DISCLAIMER = (
    "Educational commentary based on quantitative market data — not "
    "investment advice. Past patterns do not guarantee future outcomes."
)


@dataclass
class Commentary:
    """Structured narrative output. Templates pick which sections to render."""
    date: pd.Timestamp
    headline: str          # one-line, suitable as WhatsApp first line
    regime: str            # 1-2 sentences on today's regime + stress
    sector: str            # 1-2 sentences on sector rotation
    analog: str            # 1-2 sentences with a specific historical date
    conditional: str       # 1-2 sentences on historical-conditional outcomes
    watch: str             # 1-2 sentences naming specific stocks to watch
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


# ---------- translation helpers (the "no jargon" layer) ----------

def _pct_to_words(p: float) -> str:
    """Translate 0..1 fraction into a readable phrase.

    Avoids "X%" speak for things that read more naturally as ratios.
    Used for breadth-type metrics where the eye parses 'about 2 in 3'
    faster than '64%'.
    """
    if p is None:
        return "an unknown number of"
    if p >= 0.90: return "nearly all"
    if p >= 0.80: return "more than 4 in 5"
    if p >= 0.65: return "about 2 in 3"
    if p >= 0.55: return "more than half"
    if p >= 0.45: return "about half"
    if p >= 0.35: return "more than 1 in 3"
    if p >= 0.20: return "about 1 in 4"
    if p >= 0.10: return "1 in 10"
    return "very few"


def _vix_z_descriptor(z: float | None) -> str:
    if z is None:
        return "near typical levels"
    if z >= 1.5:  return "sharply elevated — markets are nervous"
    if z >= 0.75: return "running above average — caution showing through"
    if z >= -0.25 and z <= 0.25: return "near its typical range"
    if z <= -1.5: return "unusually compressed — complacency is high"
    if z <= -0.75: return "below average — calm conditions"
    return "near its typical range"


def _stress_band(score: float) -> str:
    if score >= 80: return "panic / capitulation territory"
    if score >= 60: return "elevated stress"
    if score >= 40: return "moderately elevated"
    if score >= 20: return "calm"
    return "very calm"


def _stress_pctile_descriptor(pctile: float | None) -> str:
    """Translate the 5y percentile into a non-jargony descriptor."""
    if pctile is None:
        return ""
    if pctile >= 90: return "the highest readings of the past five years"
    if pctile >= 75: return "the top quarter of readings over the past five years"
    if pctile >= 60: return "above average for the past five years"
    if pctile >= 40: return "around the middle of the past five years' range"
    if pctile >= 25: return "below average for recent years"
    return "the calmest readings of recent years"


def _regime_descriptor(name: str) -> str:
    """Plain-English name for each regime label."""
    return {
        regime_mod.TREND_BULL: "trend-bull mode — uptrend intact and participation broad",
        regime_mod.DRIFT:      "drift mode — neutral, neither trending nor under pressure",
        regime_mod.STRETCHED:  "stretched-and-complacent zone — market above trend with very low fear",
        regime_mod.STRESS:     "stress mode — markets under pressure, breadth deteriorating",
    }.get(name, name.lower())


def _drawdown_descriptor(dd: float | None) -> str:
    if dd is None or abs(dd) < 0.01:
        return "essentially at recent highs"
    pct = abs(dd) * 100
    if pct < 3:   return f"trading within {pct:.0f}% of recent highs"
    if pct < 8:   return f"{pct:.0f}% off the recent high — modest pullback"
    if pct < 15:  return f"{pct:.0f}% off the high — meaningful correction"
    if pct < 25:  return f"{pct:.0f}% off the high — significant drawdown"
    return f"more than {int(pct)}% off the high — severe drawdown"


# ---------- section builders ----------

def _headline(reading: MarketReading) -> str:
    """One-line summary readable without any chart. Front-of-WhatsApp content."""
    regime = reading.regime.regime
    stress = reading.stress.score

    # Branch by the headline-worthy signal
    if stress >= 80:
        return "Markets are in panic territory — sharp moves typical from here."
    if stress >= 60 and regime == regime_mod.STRESS:
        return "Markets remain under stress — breadth is weak and vol is elevated."
    if regime == regime_mod.STRETCHED:
        return "Markets are stretched and complacent — historically a pullback risk."
    if regime == regime_mod.TREND_BULL and stress < 30:
        return "Markets are in calm uptrend mode with broad participation."
    if regime == regime_mod.TREND_BULL:
        return "Uptrend intact, but stress reading is creeping up."
    if regime == regime_mod.DRIFT:
        return "Markets are in drift mode — neither trending strongly nor under pressure."
    return f"Markets reading: {_regime_descriptor(regime)}."


def _regime_paragraph(reading: MarketReading) -> str:
    """1-2 sentences on regime + stress, with persistence context."""
    r = reading.regime
    s = reading.stress

    regime_phrase = _regime_descriptor(r.regime)

    # Persistence: how long has this regime been active
    if r.persistence_days <= 3:
        persist = "just entered today" if r.persistence_days == 1 else f"only {r.persistence_days} days old"
    elif r.persistence_days <= 14:
        persist = f"in its second week ({r.persistence_days} days)"
    elif r.persistence_days <= 40:
        persist = f"a few weeks old ({r.persistence_days} trading days)"
    else:
        persist = f"persistent — running {r.persistence_days} trading days now"

    sentence1 = f"Markets are in {regime_phrase}; the current phase is {persist}."

    # Sentence 2: stress level with context
    stress_pctile = _stress_pctile_descriptor(s.score_percentile)
    stress_band = _stress_band(s.score)
    if stress_pctile:
        sentence2 = (
            f"Overall stress reading is {s.score:.0f}/100 ({stress_band}), "
            f"sitting in {stress_pctile}."
        )
    else:
        sentence2 = f"Overall stress reading is {s.score:.0f}/100 ({stress_band})."

    # If there was a recent transition, mention it
    if r.prev_regime and r.persistence_days <= 5 and r.prev_regime_lasted_days:
        prior_phrase = _regime_descriptor(r.prev_regime).split(" — ")[0]
        sentence1 += f" That follows {r.prev_regime_lasted_days} days in {prior_phrase}."

    return sentence1 + " " + sentence2


def _sector_paragraph(reading: MarketReading) -> str:
    """1-2 sentences on which sectors are leading + a narrow-vs-broad nuance."""
    board = reading.sector_leaderboard_60d
    if not board:
        return "Sector readings are unavailable today."

    # Pick top 1 (by 60d rank) and bottom 1
    top = board[0]
    bottom = board[-1]
    top_name = top.sector.replace("NIFTY_", "")
    bot_name = bottom.sector.replace("NIFTY_", "")
    top_rs = top.rs_60d * 100 if top.rs_60d is not None else 0
    bot_rs = bottom.rs_60d * 100 if bottom.rs_60d is not None else 0

    # Look for a notable WoW mover (climbed or fell ≥2 spots)
    movers = [s for s in board if s.rank_change_wow_60d is not None
              and abs(s.rank_change_wow_60d) >= 2]
    notable_mover_phrase = ""
    if movers:
        m = max(movers, key=lambda s: abs(s.rank_change_wow_60d))
        m_name = m.sector.replace("NIFTY_", "")
        direction = "climbed" if m.rank_change_wow_60d > 0 else "fell"
        notable_mover_phrase = (
            f" {m_name} {direction} {abs(m.rank_change_wow_60d)} spots this week — "
            "a notable rotation."
        )

    # Narrow-vs-broad nuance on the top sector
    top_breadth = (top.pct_above_200dma * 100) if top.pct_above_200dma is not None else None
    if top_breadth is not None and top_breadth >= 70:
        nuance = f"Leadership is broad — {_pct_to_words(top.pct_above_200dma)} of its stocks are in an uptrend."
    elif top_breadth is not None and top_breadth < 40:
        nuance = (
            f"But the rally there is narrow — only {_pct_to_words(top.pct_above_200dma)} "
            "of its stocks are in an uptrend, so a few names are doing the heavy lifting."
        )
    else:
        nuance = ""

    sentence1 = (
        f"{top_name} is leading sectors over the past three months "
        f"({top_rs:+.1f}% vs Nifty), with {bot_name} lagging ({bot_rs:+.1f}%)."
    )

    parts = [sentence1]
    if nuance:
        parts.append(nuance)
    if notable_mover_phrase:
        parts.append(notable_mover_phrase.strip())
    return " ".join(parts)


def _analog_paragraph(reading: MarketReading) -> str:
    """1-2 sentences naming the closest historical analog + what happened next."""
    if not reading.analogs:
        return "Historical analogs not available for today's reading."

    top = reading.analogs[0]
    match_date_str = top.match_date.strftime("%B %Y")
    # Forward-return outcome for the top match (prefer 20d, fall back to 60d)
    fwd = top.fwd_return_20d if top.fwd_return_20d is not None else top.fwd_return_60d
    horizon_label = "20 trading days" if top.fwd_return_20d is not None else "60 trading days"

    sentence1 = f"Today's market reading most closely resembles {match_date_str}."

    if fwd is not None:
        if fwd > 0.05:
            outcome = f"From that setup, Nifty added {fwd*100:.1f}% over the following {horizon_label}."
        elif fwd > 0.01:
            outcome = f"From that setup, Nifty drifted modestly higher (+{fwd*100:.1f}% over {horizon_label})."
        elif fwd > -0.01:
            outcome = f"From that setup, Nifty moved sideways over the following {horizon_label}."
        elif fwd > -0.05:
            outcome = f"From that setup, Nifty drifted lower ({fwd*100:.1f}% over {horizon_label})."
        else:
            outcome = f"From that setup, Nifty fell {abs(fwd)*100:.1f}% over the following {horizon_label}."
    else:
        outcome = ""

    # Widen the view: what's the median across the top 20 analogs?
    dist_20 = reading.analog_distribution.get(20)
    distribution_sentence = ""
    if dist_20 and dist_20.median is not None and dist_20.n_with_forward_return >= 10:
        med = dist_20.median * 100
        n = dist_20.n_with_forward_return
        # Spread context (p25 to p75 = middle half)
        if dist_20.p25 is not None and dist_20.p75 is not None:
            spread = f"{dist_20.p25*100:+.1f}% to {dist_20.p75*100:+.1f}%"
            distribution_sentence = (
                f"Across the {n} closest historical analogs, Nifty's median 20-day "
                f"return from these setups was {med:+.1f}%, with the middle half "
                f"of outcomes between {spread}."
            )

    parts = [sentence1]
    if outcome:
        parts.append(outcome)
    if distribution_sentence:
        parts.append(distribution_sentence)
    return " ".join(parts)


def _conditional_paragraph(reading: MarketReading) -> str:
    """1-2 sentences on what historically happened in this regime/stress combo."""
    cond = reading.conditional
    if not cond or not cond.get("by_regime"):
        return ""

    regime_name = cond.get("today_regime", "")
    by_r = cond["by_regime"]

    # Pick 20-day fwd as the headline horizon
    d20 = by_r.get(20) or by_r.get("20")
    if not d20 or d20.get("n", 0) < 30:
        return ""

    n = d20["n"]
    median = d20["median"]
    pct_pos = d20["pct_positive"]
    p25 = d20["p25"]
    p75 = d20["p75"]

    regime_phrase = _regime_descriptor(regime_name).split(" — ")[0]

    s = (
        f"Across {n} similar past days in {regime_phrase}, Nifty's median "
        f"forward 20-day return has been {median*100:+.2f}%, with "
        f"{pct_pos*100:.0f}% of historical observations finishing in positive "
        f"territory (middle half of outcomes: {p25*100:+.1f}% to {p75*100:+.1f}%)."
    )
    return s


def _watch_paragraph(reading: MarketReading) -> str:
    """1-2 sentences naming specific stocks to watch — drives engagement."""
    wl = reading.watchlists

    parts = []

    # 1) Fresh breakouts — most actionable
    breakouts = wl.get("breakouts", [])
    if breakouts:
        top_names = ", ".join(e.symbol for e in breakouts[:3])
        parts.append(f"Fresh breakouts to watch: {top_names}.")

    # 2) RS leaders — leadership names
    rs = wl.get("rs_leaders", [])
    if rs:
        top_names = ", ".join(e.symbol for e in rs[:3])
        parts.append(f"Strongest names over the past six months: {top_names}.")

    # 3) Recent breakdowns — early warnings (only if present)
    bd = wl.get("recent_breakdowns", [])
    if bd:
        names = ", ".join(e.symbol for e in bd[:3])
        parts.append(f"Worth watching for trend break: {names} just lost the 50-day average.")

    return " ".join(parts) if parts else "No notable single-stock signals firing today."


# ---------- composer ----------

def compose(reading: MarketReading) -> Commentary:
    """Compose the full Commentary object from a MarketReading."""
    return Commentary(
        date=reading.date,
        headline=_headline(reading),
        regime=_regime_paragraph(reading),
        sector=_sector_paragraph(reading),
        analog=_analog_paragraph(reading),
        conditional=_conditional_paragraph(reading),
        watch=_watch_paragraph(reading),
    )
