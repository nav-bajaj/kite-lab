"""Unit tests for the rebalance schedule projection and trading-day helpers.

Pure date logic over the NSE holiday calendar — no DB needed.
"""
from __future__ import annotations

from datetime import date

from app.services import market_service as ms
from app.services.rebalance_service import project_next_signal


class TestTradingDayHelpers:
    def test_weekend_and_holiday_not_trading_days(self):
        assert ms.is_trading_day(date(2026, 6, 19)) is True   # Friday
        assert ms.is_trading_day(date(2026, 6, 20)) is False  # Saturday
        assert ms.is_trading_day(date(2026, 6, 26)) is False  # Muharram holiday

    def test_snap_back_rolls_off_good_friday(self):
        # Good Friday 2026-04-03 is a holiday -> snap back to Thu 04-02.
        assert ms.snap_back_to_trading_day(date(2026, 4, 3)) == date(2026, 4, 2)
        # A normal trading day snaps to itself.
        assert ms.snap_back_to_trading_day(date(2026, 6, 19)) == date(2026, 6, 19)

    def test_next_trading_day_skips_holiday_and_weekend(self):
        # After Muharram Fri 06-26 -> skip Sat/Sun -> Mon 06-29.
        assert ms.next_trading_day_after(date(2026, 6, 26)) == date(2026, 6, 29)

    def test_trading_days_between_excludes_weekends_holidays(self):
        # 06-18 (Thu) -> 06-19 (Fri): one trading day.
        assert ms.trading_days_between(date(2026, 6, 18), date(2026, 6, 19)) == 1
        assert ms.trading_days_between(date(2026, 6, 19), date(2026, 6, 18)) == 0


class TestProjectNextSignal:
    def test_biweekly_friday(self):
        nxt = project_next_signal(date(2026, 6, 5), "biweekly_fri", date(2026, 6, 18))
        assert nxt == date(2026, 6, 19)

    def test_on_the_day_projects_to_next_cycle(self):
        # If today is the candidate date, "next" is the following fortnight.
        nxt = project_next_signal(date(2026, 6, 5), "biweekly_fri", date(2026, 6, 19))
        assert nxt == date(2026, 7, 3)

    def test_weekly_thursday(self):
        nxt = project_next_signal(date(2026, 6, 11), "weekly_thu_fri", date(2026, 6, 18))
        assert nxt == date(2026, 6, 25)

    def test_projection_snaps_off_holiday(self):
        # The biweekly Friday lands on Good Friday (04-03) -> Thu 04-02.
        nxt = project_next_signal(date(2026, 3, 20), "biweekly_fri", date(2026, 3, 30))
        assert nxt == date(2026, 4, 2)

    def test_anchor_in_the_past_advances_to_future(self):
        # A stale anchor still projects forward to a strictly-future date.
        today = date(2026, 6, 18)
        nxt = project_next_signal(date(2026, 1, 9), "biweekly_fri", today)
        assert nxt > today
        assert nxt.weekday() <= 4  # a weekday
