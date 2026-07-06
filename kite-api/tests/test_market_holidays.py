"""Tests for the NSE holiday table + its staleness guardrail.

Guards two correctness risks called out in the rebalance-page audit (L1):
  1. The 2026 calendar must match the official NSE list exactly — a wrong entry
     closes the market on a real trading day (or vice-versa).
  2. An uncovered year must be caught loudly (tripwire), not silently treated as
     a year with no holidays.
"""
from __future__ import annotations

from datetime import date, datetime

from app.services import market_service as ms


# The authoritative 2026 NSE Capital-Market weekday holiday set (16 days),
# cross-checked against Zerodha + ClearTax calendars and NSE circular reporting.
# Includes the ad-hoc 15 Jan 2026 municipal-election closure. Weekend-falling
# holidays (Mahashivratri 15 Feb, Id-ul-Fitr 21 Mar, Independence Day 15 Aug,
# Diwali 08 Nov) are intentionally excluded.
EXPECTED_2026 = {
    (1, 15),   # Maharashtra civic elections (special)
    (1, 26),   # Republic Day
    (3, 3),    # Holi
    (3, 26),   # Shri Ram Navami
    (3, 31),   # Mahavir Jayanti
    (4, 3),    # Good Friday
    (4, 14),   # Ambedkar Jayanti
    (5, 1),    # Maharashtra Day
    (5, 28),   # Bakri Id
    (6, 26),   # Muharram
    (9, 14),   # Ganesh Chaturthi
    (10, 2),   # Gandhi Jayanti
    (10, 20),  # Dussehra
    (11, 10),  # Diwali Balipratipada
    (11, 24),  # Guru Nanak Jayanti
    (12, 25),  # Christmas
}


class TestHolidayTable2026:
    def test_matches_official_2026_set_exactly(self):
        assert set(ms.NSE_HOLIDAYS[2026]) == EXPECTED_2026

    def test_jan_15_2026_election_holiday_present(self):
        # Regression: the ad-hoc 15 Jan 2026 CM closure was previously missing.
        assert ms.is_nse_holiday(datetime(2026, 1, 15)) is True
        assert ms.is_trading_day(date(2026, 1, 15)) is False

    def test_known_trading_days_are_not_holidays(self):
        # Adjacent weekdays that ARE open (guards against false holidays, the
        # "market open but platform showed closed" symptom).
        assert ms.is_nse_holiday(datetime(2026, 1, 14)) is False  # Wed before
        assert ms.is_nse_holiday(datetime(2026, 1, 16)) is False  # Fri after
        assert ms.is_nse_holiday(datetime(2026, 4, 2)) is False   # Thu before Good Fri

    def test_all_listed_days_are_weekdays(self):
        for month, day in ms.NSE_HOLIDAYS[2026]:
            assert date(2026, month, day).weekday() < 5, (month, day)


class TestHolidayCoverageGuardrail:
    def test_current_year_is_covered(self):
        # Tripwire: fails once the calendar year rolls past the last populated
        # year, forcing an annual refresh from the NSE circular.
        assert ms.is_holiday_year_covered(date.today().year), (
            "NSE_HOLIDAYS has no entry for the current year — update it from the "
            "official NSE circular before trusting any holiday-dependent logic."
        )

    def test_stale_check_flags_uncovered_next_year_near_year_end(self, monkeypatch):
        # With only 2026 loaded, a date in mid-December 2026 must warn about 2027.
        monkeypatch.setattr(ms, "NSE_HOLIDAYS", {2026: [(1, 26)]})
        assert ms.warn_if_holiday_table_stale(date(2026, 12, 15)) == [2027]

    def test_stale_check_quiet_mid_year_when_current_year_covered(self, monkeypatch):
        monkeypatch.setattr(ms, "NSE_HOLIDAYS", {2026: [(1, 26)]})
        assert ms.warn_if_holiday_table_stale(date(2026, 7, 5)) == []

    def test_stale_check_flags_uncovered_current_year(self, monkeypatch):
        monkeypatch.setattr(ms, "NSE_HOLIDAYS", {2026: [(1, 26)]})
        assert ms.warn_if_holiday_table_stale(date(2027, 3, 1)) == [2027]
