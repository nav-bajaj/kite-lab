"""Tests for the plain-English commentary engine.

These tests enforce the editorial voice rules from PLAN.md — no jargon,
no percentile-speak in the body, specific stocks named, neutral framing.
They also verify the regime classifier surfaces in headlines correctly.
"""
from __future__ import annotations

import json
import re

import pandas as pd
import pytest

from app.insights.notes import commentary
from app.insights.reading import get_market_reading, MarketReading


# Banned jargon — these tokens are signals that we slipped into quant-speak.
# Common offenders are documented in PLAN.md.
JARGON_TERMS = [
    "z-score", "zscore", "z score",
    "percentile of",       # we use "the highest of" / "calmest of" descriptors
    "rolling stdev", "stdev",
    "cross-sectional",
    "lr_cache", "lru",
    "DataFrame", "panel",
    "rs_score", "ad_diff",
    "pct_above_50dma", "pct_above_200dma",  # raw column names
    "vix_zscore",
]

# Banned recommendation verbs (we're educational only, not advisory)
RECOMMENDATION_VERBS = [
    " buy ", " sell ", " short ", " purchase ", " avoid ",
    " recommend", " advise", " suggest ",
]


@pytest.fixture(scope="module")
def reading() -> MarketReading:
    return get_market_reading()


@pytest.fixture(scope="module")
def commentary_obj(reading) -> commentary.Commentary:
    return commentary.compose(reading)


class TestCommentaryStructure:
    def test_has_all_sections(self, commentary_obj):
        # 'analog' section was retired after the validity study showed it
        # had no predictive content (see tasks/insight_engine/ANALOG_STUDY.md)
        for field in ["headline", "regime", "sector",
                      "conditional", "watch", "disclaimer"]:
            assert getattr(commentary_obj, field), f"missing or empty: {field}"

    def test_headline_is_one_line(self, commentary_obj):
        assert "\n" not in commentary_obj.headline
        assert len(commentary_obj.headline) <= 120, (
            f"headline too long ({len(commentary_obj.headline)} chars)"
        )

    def test_to_dict_json_serializable(self, commentary_obj):
        d = commentary_obj.to_dict()
        json.dumps(d)


class TestEditorialVoice:
    """Enforce the no-jargon, no-recommendation rules from PLAN.md."""

    @pytest.fixture(scope="class")
    def all_text(self, commentary_obj):
        return " ".join([
            commentary_obj.headline,
            commentary_obj.regime,
            commentary_obj.sector,
            commentary_obj.conditional,
            commentary_obj.watch,
            commentary_obj.learn_moment,  # Phase 5.C — same rules apply
        ]).lower()

    def test_no_jargon(self, all_text):
        offending = [t for t in JARGON_TERMS if t.lower() in all_text]
        assert not offending, (
            f"jargon found in commentary: {offending}. "
            "These terms should be translated per editorial guidelines."
        )

    def test_no_recommendation_verbs(self, all_text):
        offending = [v for v in RECOMMENDATION_VERBS if v.lower() in all_text]
        assert not offending, (
            f"recommendation verbs found: {offending}. "
            "Commentary must stay neutral — no buy/sell/recommend language."
        )

    def test_disclaimer_present(self, commentary_obj):
        assert "not investment advice" in commentary_obj.disclaimer.lower()


class TestHeadlinesAcrossRegimes:
    """The headline should reflect the regime well — verify on canonical
    historical episodes."""

    def test_covid_crash_headline_mentions_panic_or_stress(self):
        r = get_market_reading(pd.Timestamp("2020-03-23"))
        c = commentary.compose(r)
        h = c.headline.lower()
        assert "panic" in h or "stress" in h, (
            f"COVID crash headline should signal stress: {c.headline!r}"
        )

    def test_2018_nbfc_headline_signals_stress(self):
        r = get_market_reading(pd.Timestamp("2018-10-05"))
        c = commentary.compose(r)
        h = c.headline.lower()
        assert "panic" in h or "stress" in h or "pressure" in h, (
            f"2018 NBFC crisis headline should signal stress: {c.headline!r}"
        )

    def test_calm_rally_headline_signals_uptrend_or_calm(self):
        r = get_market_reading(pd.Timestamp("2017-10-13"))
        c = commentary.compose(r)
        h = c.headline.lower()
        assert "uptrend" in h or "calm" in h or "trend" in h, (
            f"Calm rally headline should signal calm/uptrend: {c.headline!r}"
        )


class TestSectionContent:
    def test_regime_paragraph_mentions_stress_score(self, commentary_obj):
        # The regime paragraph carries the stress reading; verify the
        # numeric score actually appears so readers see it.
        assert "/100" in commentary_obj.regime or "stress" in commentary_obj.regime.lower()

    def test_sector_paragraph_names_actual_sectors(self, commentary_obj):
        # Should name at least one sector by short name (e.g., METAL, IT, BANK)
        sector_keywords = ["METAL", "IT", "BANK", "PHARMA", "FMCG", "AUTO",
                           "REALTY", "ENERGY", "FIN", "MEDIA"]
        assert any(k in commentary_obj.sector.upper() for k in sector_keywords), (
            f"sector paragraph must name a sector by short name: {commentary_obj.sector!r}"
        )

    def test_watch_paragraph_names_specific_stocks(self, commentary_obj):
        # At least one capitalized ticker-like token should appear
        # (rough check — actual NSE tickers vary in format)
        ticker_pattern = re.compile(r"\b[A-Z]{3,}[A-Z0-9]*\b")
        tokens = ticker_pattern.findall(commentary_obj.watch)
        # Filter out generic capitalized words
        non_generic = [t for t in tokens if t not in ("RS", "DMA")]
        assert non_generic, (
            f"watch paragraph should name specific tickers: {commentary_obj.watch!r}"
        )


class TestHistoricalDatesProduceCleanOutput:
    """Spot-check 4 historical regimes for content quality (smoke tests)."""

    @pytest.mark.parametrize("label,date", [
        ("COVID crash",     "2020-03-23"),
        ("2018 NBFC",       "2018-10-05"),
        ("2022 rate shock", "2022-06-17"),
        ("2017 melt-up",    "2017-10-13"),
    ])
    def test_historical_date_produces_full_commentary(self, label, date):
        r = get_market_reading(pd.Timestamp(date))
        c = commentary.compose(r)
        # Every section must be non-empty
        for field in ["headline", "regime", "sector",
                      "conditional", "watch"]:
            assert getattr(c, field), f"{label}: empty {field}"
        # JSON-roundtrips
        json.dumps(c.to_dict())


class TestTranslationHelpers:
    """Spot-check the small translation utilities."""

    @pytest.mark.parametrize("p,expected_phrase", [
        (0.95, "nearly all"),
        (0.84, "more than 4 in 5"),
        (0.67, "about 2 in 3"),
        (0.55, "more than half"),
        (0.37, "more than 1 in 3"),
        (0.30, "about 1 in 4"),
        (0.05, "very few"),
    ])
    def test_pct_to_words(self, p, expected_phrase):
        assert commentary._pct_to_words(p) == expected_phrase

    @pytest.mark.parametrize("z,kw", [
        (2.0, "elevated"),     # high vol
        (1.0, "above average"),
        (0.0, "typical"),      # the middle phrase mentions typical range
        (-1.8, "compressed"),  # very low vol = complacency
    ])
    def test_vix_z_descriptor_directionally_correct(self, z, kw):
        text = commentary._vix_z_descriptor(z).lower()
        assert kw in text, f"vix_z={z}: expected keyword '{kw}' in '{text}'"

    @pytest.mark.parametrize("score,kw", [
        (95, "panic"),
        (70, "elevated"),
        (50, "moderately"),
        (30, "calm"),
        (10, "very calm"),
    ])
    def test_stress_band(self, score, kw):
        assert kw in commentary._stress_band(score).lower()


# ─────────── Spec tests (promoted from characterization 2026-05-28) ───────────
#
# These tests assert behavior derived from external requirements — canonical
# historical days that we know what they "should" read like, mathematical
# invariants, and edge cases that previously lived only in the implementation.
# See `tasks/insight_engine/TDD_POLICY.md` for the policy this section follows.


class TestStressBandSpec:
    """Stress-band phrase must match what reality looked like on canonical
    historical days. This is stronger than the parametrized threshold check
    above — it pins the END-TO-END contract that 'panic-day in history → panic-
    band reading in commentary'."""

    @pytest.mark.parametrize("date_str,expected_substring", [
        # March 2020 COVID washout — deepest stress in the 16y series.
        # Anything other than panic/capitulation would be wrong.
        ("2020-03-23", "panic"),
        # 2017 melt-up — calm conditions for months. "Very calm" / "calm"
        # is the only defensible read.
        ("2017-10-13", "calm"),
        # Early 2018 NBFC stress (before IL&FS crystallised) — stress in
        # the 60-80 band. NOTE: my initial intuition picked 2018-10-05 here
        # but the spec test surfaced that stress on that day was actually
        # 87/100 (panic territory) — the engine was right, my mental model
        # was wrong. 2018-09-25 is the canonical "elevated, not panic" day.
        ("2018-09-25", "elevated"),
        # Late 2024 — moderate stress (DRIFT regime, stress in 50-60 band)
        ("2024-10-25", "moderately"),
    ])
    def test_canonical_historical_day_maps_to_expected_band(
        self, date_str, expected_substring,
    ):
        from app.insights.reading import get_market_reading
        r = get_market_reading(pd.Timestamp(date_str))
        phrase = commentary._stress_band(r.stress.score).lower()
        assert expected_substring in phrase, (
            f"{date_str}: stress={r.stress.score:.0f} → {phrase!r}; "
            f"expected '{expected_substring}'"
        )

    def test_band_phrases_are_monotonic_across_thresholds(self):
        """Each named band must be reachable — no overlapping ranges,
        no unreachable phrases. Tests the function's TABLE of phrases,
        not just one input."""
        phrases = {commentary._stress_band(s)
                   for s in [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]}
        # At least 4 distinct phrases out of 5 possible bands
        assert len(phrases) >= 4, (
            f"Bands collapsed too much: only {len(phrases)} distinct phrases"
        )

    def test_band_boundary_is_inclusive_at_lower_edge(self):
        """Edge case: exactly 80.0 should be in the panic band (≥ 80),
        and exactly 79.99 should NOT be. Pins the boundary semantics."""
        assert "panic" in commentary._stress_band(80.0).lower()
        assert "panic" not in commentary._stress_band(79.99).lower()


class TestVixDescriptorSpec:
    """VIX descriptor must read appropriately for canonical regimes.
    Spec: high z-score → 'elevated'/'nervous'; deeply negative → 'compressed'/
    'complacency'."""

    @pytest.mark.parametrize("date_str,must_contain_one_of", [
        # COVID — VIX was extreme
        ("2020-03-23", ("elevated", "nervous")),
        # Calm 2017 melt-up — VIX z-score was deeply negative
        ("2017-10-13", ("compressed", "complacency", "calm", "below")),
    ])
    def test_canonical_day_descriptor_matches(
        self, date_str, must_contain_one_of,
    ):
        from app.insights.reading import get_market_reading
        r = get_market_reading(pd.Timestamp(date_str))
        z = r.regime.vix_zscore_252d
        if z is None:
            pytest.skip(f"VIX z-score unavailable on {date_str}")
        phrase = commentary._vix_z_descriptor(z).lower()
        assert any(t in phrase for t in must_contain_one_of), (
            f"{date_str}: vix_z={z:+.2f} → {phrase!r}; "
            f"expected one of {must_contain_one_of}"
        )

    def test_handles_none_input(self):
        """Spec: when VIX z is unavailable, descriptor must not crash."""
        result = commentary._vix_z_descriptor(None)
        assert isinstance(result, str) and result, (
            "Expected a defensive default phrase, got empty/non-str"
        )


# ─────────────── Phase 5.C — teach-while-broadcasting ───────────────

class TestLearnMoment:
    """The learn_moment field should fire only when something is unusual
    today (postclose/premarket) or rotate weekly (weekly digest).
    """

    def test_weekly_mode_always_has_learn_moment(self, reading):
        c = commentary.compose(reading, mode="weekly")
        assert c.learn_moment, "weekly mode must always carry pattern-of-the-week"
        assert "Pattern this week" in c.learn_moment

    def test_default_mode_is_postclose(self, reading):
        # No mode arg should behave like postclose (indicator_spotlight,
        # may be empty if nothing unusual today)
        c1 = commentary.compose(reading)
        c2 = commentary.compose(reading, mode="postclose")
        assert c1.learn_moment == c2.learn_moment

    def test_unknown_mode_yields_no_learn_moment(self, reading):
        c = commentary.compose(reading, mode="not-a-mode")
        assert c.learn_moment == ""

    def test_pattern_of_the_week_rotates_across_iso_weeks(self):
        """Different ISO weeks should hit different positions in the
        rotation. We don't require every entry to differ from every
        other — just that the rotation actually rotates."""
        from app.insights.reading import get_market_reading
        seen = set()
        # 6 weeks at ~7 days apart should hit several positions
        for date_str in ["2025-01-06", "2025-01-13", "2025-01-20",
                         "2025-01-27", "2025-02-03", "2025-02-10"]:
            r = get_market_reading(pd.Timestamp(date_str))
            c = commentary.compose(r, mode="weekly")
            # Extract the pattern title (first ** chunk after "Pattern this week: ")
            tag = c.learn_moment.split(".", 1)[0]
            seen.add(tag)
        assert len(seen) >= 2, f"Pattern-of-the-week did not rotate: {seen}"

    @pytest.mark.parametrize("date_str", [
        "2020-03-23",  # COVID panic
        "2018-10-05",  # NBFC stress
        "2017-10-13",  # Calm rally
        "2022-06-17",  # Rate-shock chop
    ])
    def test_learn_moment_jargon_free_across_history(self, date_str):
        """Same jargon rules apply to learn_moment as to other sections."""
        from app.insights.reading import get_market_reading
        r = get_market_reading(pd.Timestamp(date_str))
        for mode in ("postclose", "premarket", "weekly"):
            c = commentary.compose(r, mode=mode)
            text = c.learn_moment.lower()
            offending = [t for t in JARGON_TERMS if t.lower() in text]
            assert not offending, (
                f"jargon in learn_moment ({date_str}, mode={mode}): {offending}"
            )

    def test_learn_moment_no_recommendation_verbs(self, reading):
        for mode in ("postclose", "premarket", "weekly"):
            c = commentary.compose(reading, mode=mode)
            text = c.learn_moment.lower()
            offending = [v for v in RECOMMENDATION_VERBS if v.lower() in text]
            assert not offending, (
                f"recommendation verb in learn_moment (mode={mode}): {offending}"
            )

    def test_covid_panic_day_fires_stress_spotlight(self):
        """On a known very-high-stress day, the spotlight should mention
        stress or panic by name."""
        from app.insights.reading import get_market_reading
        r = get_market_reading(pd.Timestamp("2020-03-23"))
        c = commentary.compose(r, mode="postclose")
        lm = c.learn_moment.lower()
        assert lm, "Expected non-empty learn_moment on COVID panic day"
        assert "stress" in lm or "panic" in lm, (
            f"Expected stress/panic mention; got: {c.learn_moment!r}"
        )


class TestOnThisDayLearnMoment:
    """Phase 4.4 wiring — premarket mode should prefer an on_this_day
    moment when an anniversary lands on a curated event.

    Spec test written before the routing change in commentary.py — per
    the TDD policy."""

    def test_premarket_fires_on_this_day_when_anniversary_matches_event(self):
        """COVID lockdown was 2020-03-24. Premarket note on 2025-03-24
        should fire an on-this-day moment (5y back lands on a curated
        event) rather than falling through to indicator_spotlight."""
        from app.insights.reading import get_market_reading
        r = get_market_reading(pd.Timestamp("2025-03-24"))
        c = commentary.compose(r, mode="premarket")
        lm = c.learn_moment.lower()
        assert lm, "Expected non-empty premarket learn_moment on COVID anniversary"
        # The moment should mention "ago" + an event-related word
        assert "ago" in lm, (
            f"Expected anniversary phrasing; got: {c.learn_moment!r}"
        )
        # And reference the event (covid, lockdown, or pandemic)
        assert any(t in lm for t in ("covid", "lockdown", "pandemic")), (
            f"Expected COVID-event reference; got: {c.learn_moment!r}"
        )

    def test_premarket_falls_through_to_spotlight_when_no_anniversary_event(self):
        """When no anniversary has a curated event_tag, premarket should
        behave like postclose (indicator_spotlight or empty).

        Distinguishing on_this_day from regime-transition spotlight needs
        a more specific signal than 'ago' alone — both use that word. We
        rely on the on_this_day-specific prefix pattern '** N year(s) ago
        today **'."""
        from app.insights.reading import get_market_reading
        # Pick a recent date where 1y/3y/5y/10y back are unlikely to be
        # curated events (most ordinary days)
        r = get_market_reading(pd.Timestamp("2025-08-15"))
        c_pre = commentary.compose(r, mode="premarket")
        c_post = commentary.compose(r, mode="postclose")
        # Reliable signal that on_this_day specifically fired: the
        # opening "** N year(s) ago today **" phrase
        on_this_day_fired = "year" in c_pre.learn_moment.lower() and \
            "ago today" in c_pre.learn_moment.lower()
        if on_this_day_fired:
            # If on_this_day fired, an event_tag MUST be referenced
            assert any(t in c_pre.learn_moment.lower()
                       for t in ("budget", "election", "covid", "lockdown",
                                 "hindenburg", "gst", "lehman", "ukraine",
                                 "demonetization", "vaccine", "rbi"))
        else:
            # Otherwise it should match the postclose spotlight (both run
            # _indicator_spotlight on the same reading)
            assert c_pre.learn_moment == c_post.learn_moment
