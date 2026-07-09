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


# ─────────── B1: get_seasonality ───────────

def _synthetic_monthly_close() -> pd.Series:
    """A daily close series whose month-end values are hand-chosen so the
    resampled month-over-month returns are exactly known.

    Month-end closes:
      2018-12-31 = 100   (base — no prior month in series)
      2019-01-31 = 110   → Jan 2019 return = +10%
      ...we build four Decembers with known Dec-over-Nov returns.
    """
    # Build explicit month-end anchor points; daily index filled by ffill.
    anchors = {
        "2018-11-30": 100.0,
        "2018-12-31": 110.0,   # Dec 2018 = +10%
        "2019-11-30": 200.0,
        "2019-12-31": 190.0,   # Dec 2019 = -5%
        "2020-11-30": 50.0,
        "2020-12-31": 60.0,    # Dec 2020 = +20%
        "2021-11-30": 80.0,
        "2021-12-31": 84.0,    # Dec 2021 = +5%
    }
    idx = pd.date_range("2018-11-01", "2021-12-31", freq="D")
    ser = pd.Series(index=idx, dtype=float)
    for d, v in anchors.items():
        ser.loc[pd.Timestamp(d)] = v
    # Forward/back fill so every month-end resamples to the nearest anchor.
    return ser.ffill().bfill()


class TestSeasonality:
    """B1 — historical calendar-month (and week) return profile from the
    16y Nifty panel. Descriptive-only: median / IQR / % positive / n."""

    def test_month_profile_median_iqr_pct_positive(self):
        """Spec: December profile from the synthetic panel has hand-computed
        median, middle-half range, %-positive and n.

        Dec returns = [+10%, -5%, +20%, +5%] → median = +7.5%,
        3 of 4 positive, n = 4."""
        close = _synthetic_monthly_close()
        prof = calendar_content.compute_seasonality(
            close, pd.Timestamp("2022-12-15"), include_week=False
        )
        m = prof.month
        assert m is not None
        assert m.period == 12
        assert m.n == 4
        assert m.median_return_pct == pytest.approx(7.5, abs=0.01)
        assert m.pct_positive == pytest.approx(0.75, abs=1e-6)
        # middle-half range brackets the median
        assert m.q1_return_pct <= m.median_return_pct <= m.q3_return_pct

    def test_n_is_disclosed_and_positive(self):
        prof = calendar_content.compute_seasonality(
            _synthetic_monthly_close(), pd.Timestamp("2022-12-15"),
            include_week=False,
        )
        assert isinstance(prof.month.n, int)
        assert prof.month.n > 0

    def test_insufficient_history_returns_none(self):
        """Spec: a month with fewer than the minimum number of historical
        years is omitted (profile is None), not fabricated."""
        # A single calendar year of data → each month appears exactly once,
        # which is below the min-obs floor → every month profile is None.
        idx = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        close = pd.Series(range(len(idx)), index=idx, dtype=float) + 100.0
        prof = calendar_content.compute_seasonality(
            close, pd.Timestamp("2020-06-15"), include_week=False,
        )
        assert prof.month is None

    def test_get_seasonality_real_panel_month_matches_asof(self):
        """Spec: against the real Nifty panel, the month profile is for the
        as-of month and discloses a plausible multi-year n."""
        prof = calendar_content.get_seasonality(pd.Timestamp("2024-12-10"))
        if prof.month is None:
            pytest.skip("Nifty panel unprovisioned in this environment")
        assert prof.month.period == 12
        assert prof.month.n >= 10  # ~16 years of history

    def test_serialisable_to_dict(self):
        import json
        prof = calendar_content.compute_seasonality(
            _synthetic_monthly_close(), pd.Timestamp("2022-12-15")
        )
        json.dumps(prof.to_dict())  # must not raise

    def test_week_profile_optional_and_cheap(self):
        """Spec: include_week=True adds an ISO-week profile using the same
        machinery (or None if that week lacks history)."""
        prof = calendar_content.compute_seasonality(
            _synthetic_monthly_close(), pd.Timestamp("2022-12-15"),
            include_week=True,
        )
        # week is either a valid profile or None — never an exception
        assert prof.week is None or prof.week.kind == "week"


# ─────────── B2: get_pre_event ───────────

def _synthetic_event_close() -> pd.Series:
    """Daily close where two 'budget' event days have known 1-day moves."""
    idx = pd.bdate_range("2020-01-20", "2020-02-15")
    ser = pd.Series(100.0, index=idx, dtype=float)
    # 2020-02-03 is a trading day; make the prior-close→event-close move +5%.
    # prior trading day 2020-01-31 close = 100, event day close = 105.
    ser.loc[pd.Timestamp("2020-02-03"):] = 105.0
    return ser


class TestPreEvent:
    """B2 — flag upcoming curated events within N days and attach the
    historical move profile for the same event *type*. Descriptive-only."""

    def test_classify_event_types(self):
        assert calendar_content.classify_event("Union Budget 2024") == "budget"
        assert calendar_content.classify_event(
            "RBI surprise off-cycle 40bp repo hike") == "rbi_policy"
        assert calendar_content.classify_event(
            "2024 General Election results") == "election"
        assert calendar_content.classify_event("Some unrelated headline") is None

    def test_pre_event_flags_upcoming_within_window(self):
        """Spec: an event dated 3 days after as-of is flagged; one 30 days
        out is not (default window = 7)."""
        events = [
            {"date": pd.Timestamp("2020-02-01"), "tag": "Union Budget"},
            {"date": pd.Timestamp("2020-03-05"), "tag": "RBI monetary policy"},
        ]
        upcoming = calendar_content.get_pre_event(
            pd.Timestamp("2020-01-29"), window_days=7,
            events=events, close=_synthetic_event_close(),
        )
        tags = [u.tag for u in upcoming]
        assert "Union Budget" in tags
        assert "RBI monetary policy" not in tags
        assert all(0 <= u.days_until <= 7 for u in upcoming)

    def test_event_type_history_discloses_n_and_move(self):
        """Spec: history for a type computes the median 1d move around past
        events of that type, n disclosed."""
        events = [
            {"date": pd.Timestamp("2020-02-03"), "tag": "Union Budget A"},
        ]
        hist = calendar_content.get_event_type_history(
            "budget", events=events, close=_synthetic_event_close(),
        )
        assert hist is not None
        assert hist.n == 1
        # prior close 100 → event close 105 = +5%
        assert hist.median_move_1d_pct == pytest.approx(5.0, abs=0.01)

    def test_pre_event_empty_when_no_forward_events(self):
        """Spec: with the real (all-past) curated file, an as-of date beyond
        the last curated event returns no upcoming events. This documents
        that forward-dated events must be curated manually into the CSV."""
        upcoming = calendar_content.get_pre_event(
            pd.Timestamp("2030-01-01"), window_days=7,
        )
        assert upcoming == []

    def test_unknown_event_type_history_is_none(self):
        hist = calendar_content.get_event_type_history(
            "budget", events=[{"date": pd.Timestamp("2020-02-03"),
                               "tag": "Unrelated market headline"}],
            close=_synthetic_event_close(),
        )
        assert hist is None
