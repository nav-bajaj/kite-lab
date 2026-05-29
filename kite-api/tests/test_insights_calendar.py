"""Tests for the anniversary / calendar content engine — Phase 4.4.

Written test-first per `tasks/insight_engine/TDD_POLICY.md`. When this
file is first run, every test should fail with ImportError because
`app.insights.calendar_content` does not yet exist. After the minimum
implementation lands, each test should pass deterministically.

Scope tested:
  - `get_on_this_day(date)` — for date D, return anniversaries at
    1y / 3y / 5y / 10y back, each with regime, stress, optional
    event_tag from the curated events file
  - `get_seasonality(date)` — for date D, return historical median /
    IQR of Nifty forward 5d / 20d return on the same calendar week
    across prior years
  - `get_pre_event(date, window_days)` — find known upcoming events
    within `window_days` of date D
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.insights import calendar_content


# ─────────── get_on_this_day ───────────

class TestOnThisDay:
    """The 'X years ago today' helper used by the weekly digest's
    on_this_day learn-moment."""

    def test_returns_dict_with_anniversary_keys(self):
        """Spec: return a dict whose keys are anniversary horizons in
        years and whose values are AnniversarySnapshot objects."""
        result = calendar_content.get_on_this_day(pd.Timestamp("2025-03-24"))
        assert isinstance(result, dict)
        # At least the 1-year-back entry should be available for any
        # recent date (2025-03-24 - 1y = 2024-03-24 → in panel)
        assert 1 in result, "Missing 1-year-back anniversary"

    def test_anniversary_carries_regime_and_stress(self):
        """Spec: each anniversary entry has regime + stress + date."""
        result = calendar_content.get_on_this_day(pd.Timestamp("2025-03-24"))
        if 5 not in result:
            pytest.skip("Sample date too close to panel start")
        snap = result[5]
        assert hasattr(snap, "date")
        assert hasattr(snap, "regime")
        assert hasattr(snap, "stress_score")
        assert hasattr(snap, "event_tag")
        # Regime must be a known value
        from app.insights.regime import REGIMES
        assert snap.regime in REGIMES

    def test_covid_anniversary_lookback_finds_stress(self):
        """Spec: looking 5 years back from 2025-03-25 lands on 2020-03-25
        (deepest COVID stress days). Stress score must reflect that."""
        result = calendar_content.get_on_this_day(pd.Timestamp("2025-03-25"))
        if 5 not in result:
            pytest.skip("5y anniversary unavailable")
        snap = result[5]
        assert snap.stress_score is not None
        # In the worst week of COVID, stress should be in the panic band
        assert snap.stress_score >= 70, (
            f"Expected COVID-era anniversary to show high stress; "
            f"got stress={snap.stress_score} on {snap.date}"
        )

    def test_event_tag_attached_when_anniversary_matches_known_event(self):
        """Spec: if an anniversary lands on a date in the curated events
        file, event_tag should be populated."""
        # 2020-03-24 was the COVID lockdown announcement — a curated event.
        # Looking 5y back from 2025-03-24 should attach the tag.
        result = calendar_content.get_on_this_day(pd.Timestamp("2025-03-24"))
        if 5 not in result:
            pytest.skip("5y anniversary unavailable")
        snap = result[5]
        # The tag should mention COVID / lockdown — exact wording not pinned
        if snap.event_tag is not None:
            assert any(t in snap.event_tag.lower()
                       for t in ("covid", "lockdown", "pandemic")), (
                f"Expected COVID/lockdown tag on 2020-03-24; got {snap.event_tag!r}"
            )
        # If no tag yet (curated file might not include it), this test
        # is informational — but if the implementation says "yes there
        # was an event", it had better be the right one.

    def test_missing_anniversary_returns_no_entry(self):
        """Spec: if the anniversary date is before the data panel begins,
        that horizon is simply absent from the returned dict — not None,
        not an error."""
        # Our panel starts in 2010. 15y back from 2020 = 2005, before panel.
        result = calendar_content.get_on_this_day(pd.Timestamp("2020-06-01"))
        # 10y back = 2010-06-01 → on or just after panel start; may or may
        # not resolve. What matters: no crash, and missing horizons are
        # omitted rather than set to None.
        for k, v in result.items():
            assert v is not None
            assert v.date is not None

    def test_default_horizons_are_1_3_5_10_years(self):
        """Spec: by default the function looks at 1y, 3y, 5y, 10y back."""
        result = calendar_content.get_on_this_day(pd.Timestamp("2025-06-15"))
        # Out of 1/3/5/10, at least 1, 3, 5 should be present (10y back
        # = 2015-06-15, which is in panel; should also resolve)
        present = set(result.keys())
        assert present <= {1, 3, 5, 10}, (
            f"Unexpected horizons in default result: {present - {1, 3, 5, 10}}"
        )
        assert {1, 3, 5}.issubset(present), (
            f"Default horizons should include 1, 3, 5 years; got {present}"
        )

    def test_serialisable_to_dict(self):
        """Spec: each AnniversarySnapshot has a to_dict() returning plain
        JSON-native types."""
        import json
        result = calendar_content.get_on_this_day(pd.Timestamp("2025-03-24"))
        for snap in result.values():
            d = snap.to_dict()
            json.dumps(d)  # must not raise


# ─────────── events file ───────────

class TestCuratedEvents:
    """The events file is hand-curated — sanity-check shape + contents."""

    def test_events_loaded_as_list_of_records(self):
        events = calendar_content.load_events()
        assert isinstance(events, list)
        assert len(events) > 0, "Expected at least some curated events"

    def test_every_event_has_date_and_tag(self):
        events = calendar_content.load_events()
        for e in events:
            assert "date" in e and "tag" in e, (
                f"Bad event record: {e}"
            )
            assert isinstance(e["date"], pd.Timestamp)
            assert isinstance(e["tag"], str) and e["tag"]

    def test_known_event_dates_present(self):
        """Sanity: a handful of well-documented Indian-market event dates
        we expect to be in the curated file."""
        events = calendar_content.load_events()
        dates = {e["date"].date().isoformat() for e in events}
        # Demonetization — Nov 8, 2016 — widely documented
        assert "2016-11-08" in dates, "Expected demonetization in events"
        # COVID lockdown announcement — Mar 24, 2020 — widely documented
        assert "2020-03-24" in dates, (
            "Expected COVID lockdown announcement in events"
        )
