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
    """Structured narrative output. Templates pick which sections to render.

    Note: an `analog` section was dropped after the validity study
    (`tasks/insight_engine/ANALOG_STUDY.md`) showed the analog forward-return
    content has no actionable signal beyond Nifty's unconditional drift.
    Conditional-distribution content (`conditional`) survives because that
    engine uses hundreds-to-thousands of observations per bucket and does
    carry real signal at the regime level.
    """
    date: pd.Timestamp
    headline: str          # one-line, suitable as WhatsApp first line
    regime: str            # 1-2 sentences on today's regime + stress
    sector: str            # 1-2 sentences on sector rotation
    conditional: str       # 1-2 sentences on historical-conditional outcomes
    watch: str             # 1-2 sentences naming specific stocks to watch
    learn_moment: str = ""  # Phase 5.C teach-while-broadcasting micro-moment;
                            # empty if nothing notable enough to teach today
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


def _conditional_paragraph(reading: MarketReading) -> str:
    """1-2 sentences on what historically happened in this regime/stress combo.

    Copy framing is matched to the regime's empirical strength, per the
    validity protocol audit (tasks/insight_engine/VALIDITY_PROTOCOL.md):
      - DRIFT: lead with explicit 'no clear edge vs baseline' framing,
        since DRIFT's 20d median is basically Nifty's unconditional drift
      - STRETCHED (n<200): include a 'limited history' caveat so
        readers don't over-weight the stat
      - STRESS / TREND_BULL: keep the original descriptive framing,
        since their excess vs baseline is real and well-sampled
    """
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

    # DRIFT — lead with the 'no clear edge' frame because the empirical
    # median is essentially unconditional Nifty drift
    if regime_name == "DRIFT":
        return (
            f"Across {n} similar past days in {regime_phrase}, Nifty has "
            f"shown no clear edge vs typical drift — the 20-day median is "
            f"{median*100:+.2f}% (close to baseline) and "
            f"{pct_pos*100:.0f}% of historical observations finished positive. "
            f"Middle half of outcomes: {p25*100:+.1f}% to {p75*100:+.1f}%."
        )

    # Small-sample caveat — STRETCHED or any other slice with n<200
    small_sample_suffix = (
        " — limited history, treat this stat as directional only."
        if n < 200 else ""
    )

    s = (
        f"Across {n} similar past days in {regime_phrase}, Nifty's median "
        f"forward 20-day return has been {median*100:+.2f}%, with "
        f"{pct_pos*100:.0f}% of historical observations finishing in positive "
        f"territory (middle half of outcomes: {p25*100:+.1f}% to "
        f"{p75*100:+.1f}%){small_sample_suffix}."
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


# ---------- Phase 5.C: teach-while-broadcasting ----------
#
# Each generator returns a short teaching micro-moment (≤ ~200 chars,
# 1-2 sentences) that fires only when something in today's reading
# actually triggers it. Returning "" means "nothing notable enough to
# teach today — templates should skip the section". Avoids ritualised
# filler that subscribers stop reading.

# Pattern-of-the-week rotation. Indexed by ISO week number mod len.
# Pulled from our published Learn explainers so the tone matches.
_PATTERN_OF_THE_WEEK: list[tuple[str, str]] = [
    (
        "Multi-year breakout",
        "A stock closing above its 5-year high is one of the cleanest setups: "
        "no overhead supply for years means no trapped sellers above price. "
        "Our validity study found these names beat the NSE 500 baseline by "
        "roughly +1pp at 20d and +6pp at 120d in 14 years of data — small but "
        "real.",
    ),
    (
        "Coiled spring",
        "Tight ranges in trending stocks usually release energy in one "
        "direction or the other. The 'coiled spring' setup — above 50+200 DMA "
        "with volatility in the stock's own bottom quartile — flags compression "
        "points before the move. The broader regime is usually the tiebreaker "
        "on direction.",
    ),
    (
        "RS leader",
        "Stocks that have beaten Nifty over the trailing 6 months show "
        "persistent momentum. The top-25 are the conceptual cousin of what our "
        "Quality Momentum portfolio screens for. Persistent leaders (months in "
        "the top-25) are often higher-quality compounders than fresh entrants.",
    ),
    (
        "Sustained uptrend",
        "1-year return above 20% with shallow drawdowns. Quiet compounders. "
        "Validity-tested but the baseline-excess is modest (+0.75pp at 20d), so "
        "we publish the names without forward-return claims. The pattern "
        "selects 'clean' over 'fast'.",
    ),
    (
        "20-day breakout",
        "The simplest variant of trend continuation: close above the prior "
        "20-day high AND above the 50-DMA. Follow-through rates depend strongly "
        "on the regime — TREND_BULL breakouts have meaningfully higher 20-day "
        "follow-through than the same signal in STRESS or DRIFT.",
    ),
    (
        "Stretched",
        "More than 20% above a 200-DMA is the historical mean-reversion zone — "
        "not a guaranteed reversal, but a context where forward returns thin "
        "out. Stretched names that keep going have usually had an earnings "
        "inflection or a structural re-rating.",
    ),
]


_MACRO_ASSET_PHRASES: dict[str, tuple[str, str, str]] = {
    # asset_id -> (display label, high-side phrase, low-side phrase)
    "usdinr": (
        "USDINR",
        "the rupee is near its weakest level of the trailing year (high USDINR percentile)",
        "the rupee is near its strongest level of the trailing year (low USDINR percentile)",
    ),
    "gold":      ("Gold",       "gold is elevated", "gold is depressed"),
    "crude":     ("Crude",      "crude oil is elevated", "crude oil is depressed"),
    "india_10y": ("India 10y",  "Indian 10-year yields are elevated", "Indian 10-year yields are depressed"),
}


def _macro_spotlight(reading: MarketReading) -> str:
    """Surface a cross-asset macro move when one of the tracked assets is
    at extreme z_252d or pctile_252d. Empty string when nothing is
    extreme — caller falls through the cascade."""
    cross = getattr(reading, "cross_asset", None)
    if not cross:
        return ""

    # Score each available asset by how unusual it is; pick the most
    # unusual non-deferred entry to spotlight.
    best_asset_id: str | None = None
    best_magnitude: float = 0.0
    best_direction: str = ""  # "high" or "low"
    best_z: float | None = None
    best_pctile: float | None = None
    for aid, entry in cross.items():
        if aid not in _MACRO_ASSET_PHRASES:
            continue
        if not getattr(entry, "data_available", False):
            continue
        feats = entry.features
        z = feats.z_252d
        pctile = feats.pctile_252d
        magnitude = 0.0
        direction = ""
        if z is not None and abs(z) >= 2.0:
            magnitude = abs(z)
            direction = "high" if z >= 0 else "low"
        if pctile is not None:
            if pctile >= 0.95 and magnitude < (pctile - 0.5):
                magnitude = pctile - 0.5
                direction = "high"
            elif pctile <= 0.05 and magnitude < (0.5 - pctile):
                magnitude = 0.5 - pctile
                direction = "low"
        if magnitude > best_magnitude and direction:
            best_magnitude = magnitude
            best_asset_id = aid
            best_direction = direction
            best_z = z
            best_pctile = pctile

    if best_asset_id is None:
        return ""

    label, high_phrase, low_phrase = _MACRO_ASSET_PHRASES[best_asset_id]
    direction_phrase = high_phrase if best_direction == "high" else low_phrase

    head = f"Cross-asset note: {direction_phrase}"
    if best_pctile is not None:
        head += f" ({best_pctile*100:.0f}th percentile within its trailing year)"
    elif best_z is not None:
        sign = "+" if best_z >= 0 else ""
        head += f" (z = {sign}{best_z:.2f} over 252 days)"
    tail = (
        "Indian equities don't move in isolation — currency, gold, and "
        "rates shape risk premia and sector flows. When one of them is at "
        "an extreme, it's a context to watch, not a directional call."
    )
    return f"{head}. {tail}"


def _indicator_spotlight(reading: MarketReading) -> str:
    """Pick the most unusual single indicator in today's reading and teach it.

    Returns "" if nothing is unusual enough to be worth spotlighting. The
    order of checks reflects what's most worth teaching when it fires —
    extreme stress / panic days get priority over routine breadth chatter.
    """
    stress = reading.stress
    regime = reading.regime
    conc = reading.concentration

    # 1. Stress in panic / very-calm territory
    if stress.score >= 80:
        return (
            f"Today's stress reading is {stress.score:.0f}/100 — panic / "
            "capitulation zone. In 16 years of history, the highest stress "
            "readings have produced the strongest 20-day forward returns "
            "— uncomfortable but a documented pattern. The stress score "
            "blends VIX, drawdown, breadth and dispersion."
        )
    if stress.score <= 15 and stress.score_percentile is not None and stress.score_percentile <= 10:
        return (
            f"Stress is unusually compressed today ({stress.score:.0f}/100, "
            "around the calmest 10% of the trailing year). Very calm "
            "readings have historically preceded volatility expansion more "
            "often than continued calm. Complacency is itself a risk."
        )

    # 2. Concentration extremes (only meaningful if Nifty moved meaningfully)
    if abs(conc.nifty_return_pct) >= 0.3 and conc.top_3_share_of_move is not None:
        share = abs(conc.top_3_share_of_move)
        if share >= 0.85:
            return (
                f"Today's Nifty move ({conc.nifty_return_pct:+.2f}%) was almost "
                f"entirely driven by {', '.join(conc.top_3_symbols)} — "
                f"{share*100:.0f}% of the move came from those three names. A "
                "tape this narrow is fragile: a single mega-cap reversing can "
                "unwind the headline quickly."
            )
        if share <= 0.25:
            return (
                f"Today's Nifty move ({conc.nifty_return_pct:+.2f}%) was "
                "unusually broad — no single name dominated. Top-3 share was "
                f"just {share*100:.0f}%. Broad participation in a move is "
                "structurally stronger than narrow leadership."
            )

    # 3. VIX-driven moments
    vix_z = regime.vix_zscore_252d
    if vix_z is not None:
        if vix_z >= 2.0:
            return (
                "VIX is unusually elevated today — running more than 2 standard "
                "deviations above its trailing-year average. High VIX means "
                "option markets are pricing wide ranges in both directions. "
                "Historically aligns with mid-to-late stress regimes."
            )
        if vix_z <= -1.5:
            return (
                "VIX is unusually compressed — more than 1.5 standard "
                "deviations below its trailing-year average. Long stretches "
                "of low VIX can persist, but very low readings have also "
                "preceded volatility expansion. A condition, not a forecast."
            )

    # 4. Cross-asset macro — surface USDINR / gold / crude / India 10y
    # when one is at extreme z-score or percentile. Skip US 10y (deferred).
    macro_msg = _macro_spotlight(reading)
    if macro_msg:
        return macro_msg

    # 5. Regime persistence — a teaching moment around context
    if regime.persistence_days <= 5 and regime.prev_regime:
        return (
            f"Markets shifted into {regime.regime} {regime.persistence_days} "
            f"day(s) ago from {regime.prev_regime} (which lasted "
            f"{regime.prev_regime_lasted_days} days). Regime transitions are "
            "often more informative than the steady state — and we apply a "
            "3-day confirmation smoothing, so the change has held for at "
            "least that long."
        )

    # 6. Notable sibling-subgroup spread
    big_spreads = [
        sp for sp in reading.sibling_spreads
        if sp.spread_60d_pp is not None and abs(sp.spread_60d_pp) >= 7.0
    ]
    if big_spreads:
        sp = max(big_spreads, key=lambda s: abs(s.spread_60d_pp))
        a_label, b_label = sp.label.split(" vs ")
        if sp.spread_60d_pp > 0:
            leader, laggard, mag = a_label, b_label, sp.spread_60d_pp
        else:
            leader, laggard, mag = b_label, a_label, -sp.spread_60d_pp
        return (
            f"Inside their parent sectors, {leader} have outpaced "
            f"{laggard} by {mag:.1f}pp over 60 days — a meaningful split. "
            "Sector headlines can hide subgroup divergences like this. "
            "When sibling subgroups disagree, the sector index is less "
            "informative than either side."
        )

    # 7. Multi-year breakout cluster
    mybs = reading.watchlists.get("multi_year_breakouts", [])
    if len(mybs) >= 3:
        names = ", ".join(e.symbol for e in mybs[:3])
        return (
            f"{len(mybs)} stocks broke out above their 5-year highs today, "
            f"including {names}. Multi-year breakouts are the strongest variant "
            "of the breakout signal — our validity study found these names "
            "outpace the NSE 500 baseline by roughly +1pp at 20d and +6pp at "
            "120d historically."
        )

    return ""


def _on_this_day(reading: MarketReading) -> str:
    """Anniversary learn-moment for the premarket note.

    Looks at 1/3/5/10 years back from today's date and returns a teaching
    moment if any of those anniversaries lands on a curated historical
    event. Returns "" if no anniversary has a tag, so callers can fall
    through to indicator_spotlight.
    """
    from app.insights import calendar_content as _cal
    anniversaries = _cal.get_on_this_day(reading.date)
    tagged = [
        (years, snap) for years, snap in anniversaries.items()
        if snap.event_tag
    ]
    if not tagged:
        return ""
    # Prefer the longest meaningful horizon (10y > 5y > 3y > 1y) — older
    # anniversaries usually carry the most teaching value.
    tagged.sort(key=lambda kv: -kv[0])
    years, snap = tagged[0]
    horizon_phrase = f"{years} year{'s' if years > 1 else ''} ago today"
    return (
        f"**{horizon_phrase}** ({snap.date.strftime('%d %b %Y')}): "
        f"{snap.event_tag}. The regime that day was {snap.regime} with "
        f"stress at {snap.stress_score:.0f}/100. Useful context for "
        "today's reading."
    )


def _seasonality_note(profile) -> str:
    """One descriptive sentence about the as-of month's historical Nifty
    returns. Descriptive-only per VALIDITY_PROTOCOL.md — with ~16 years per
    month the sample can never clear the n>=100 forward-return bar, so the
    copy reports central tendency and explicitly disclaims prediction, and
    always discloses n. Returns "" when history is too thin to report."""
    m = getattr(profile, "month", None)
    if m is None or m.median_return_pct is None:
        return ""
    n_positive = round(m.pct_positive * m.n)
    return (
        f"Seasonal context: over the last {m.n} years, {m.label} has posted "
        f"a median Nifty return of {m.median_return_pct:+.1f}% "
        f"(middle-half range {m.q1_return_pct:+.1f}% to "
        f"{m.q3_return_pct:+.1f}%), finishing positive in {n_positive} of "
        f"{m.n}. A historical tendency across a small sample, not a forecast."
    )


def _seasonality_moment(reading: MarketReading) -> str:
    """Seasonality learn-moment for the premarket note — the quiet-day
    fallback when nothing in the tape is unusual enough to spotlight."""
    from app.insights import calendar_content as _cal
    try:
        profile = _cal.get_seasonality(reading.date, include_week=False)
    except Exception:
        return ""
    return _seasonality_note(profile)


def _pattern_of_the_week(reading: MarketReading) -> str:
    """Rotate through pattern explainers, one per ISO week.

    Used by the Sunday weekly digest. Same pattern week-to-week within
    a calendar week so the broadcast feels coherent across subscribers.
    """
    iso_week = reading.date.isocalendar().week
    title, body = _PATTERN_OF_THE_WEEK[iso_week % len(_PATTERN_OF_THE_WEEK)]
    return f"**Pattern this week: {title}.** {body}"


# ---------- composer ----------

def compose(reading: MarketReading, mode: str = "postclose") -> Commentary:
    """Compose the full Commentary object from a MarketReading.

    `mode` controls which learn_moment generator fires:
      - postclose / premarket: indicator_spotlight (fires only when
        something is actually unusual)
      - weekly: pattern_of_the_week (always non-empty — rotating)
    """
    if mode == "weekly":
        learn = _pattern_of_the_week(reading)
    elif mode == "premarket":
        # Premarket prefers on_this_day when an anniversary matches a
        # curated event; otherwise falls through to indicator_spotlight,
        # and finally to a descriptive seasonality note on quiet days.
        learn = (_on_this_day(reading)
                 or _indicator_spotlight(reading)
                 or _seasonality_moment(reading))
    elif mode == "postclose":
        learn = _indicator_spotlight(reading)
    else:
        learn = ""

    return Commentary(
        date=reading.date,
        headline=_headline(reading),
        regime=_regime_paragraph(reading),
        sector=_sector_paragraph(reading),
        conditional=_conditional_paragraph(reading),
        watch=_watch_paragraph(reading),
        learn_moment=learn,
    )
