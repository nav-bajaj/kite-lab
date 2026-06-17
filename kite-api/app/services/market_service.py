"""
Market status service.

Provides market hours detection for NSE (National Stock Exchange of India).
"""
from datetime import datetime, time, timedelta
from typing import Optional
import pytz

from app.schemas.positions import MarketStatus


# Indian Standard Time
IST = pytz.timezone("Asia/Kolkata")

# NSE Market Hours
MARKET_OPEN = time(9, 15)   # 9:15 AM IST
MARKET_CLOSE = time(15, 30)  # 3:30 PM IST

# NSE trading holidays — equity segment.
#
# This list MUST be updated annually from the official NSE circular
# ("Holidays" under nseindia.com/resources/exchange-communication-holidays).
# It is keyed by year because most entries are lunar festivals whose dates
# shift year to year — applying one year's dates to another silently flags
# the wrong days (the previous version did exactly that, hard-coding 2025-era
# approximations that wrongly closed the market on real trading days).
#
# Weekend-falling 2026 holidays are intentionally omitted (the market is
# already closed Sat/Sun and get_market_status handles that separately):
#   - Mahashivratri      Sun 15 Feb 2026
#   - Independence Day   Sat 15 Aug 2026
#   - Diwali Laxmi Pujan Sun 08 Nov 2026 (special Muhurat session, not a full
#     trading day; not modelled here)
#
# Format: {year: [(month, day), ...]}
NSE_HOLIDAYS = {
    2026: [
        (1, 26),   # Republic Day               (Mon)
        (3, 3),    # Holi                        (Tue)
        (3, 26),   # Shri Ram Navami             (Thu)
        (3, 31),   # Mahavir Jayanti             (Tue)
        (4, 3),    # Good Friday                 (Fri)
        (4, 14),   # Dr. Ambedkar Jayanti        (Tue)
        (5, 1),    # Maharashtra Day / Buddha Purnima (Fri)
        (5, 28),   # Bakri Id (Id-ul-Adha)       (Thu)
        (6, 26),   # Muharram                    (Fri)
        (9, 14),   # Ganesh Chaturthi            (Mon)
        (10, 2),   # Mahatma Gandhi Jayanti      (Fri)
        (10, 20),  # Dussehra (Vijaya Dashami)   (Tue)
        (11, 10),  # Diwali Balipratipada        (Tue)
        (11, 24),  # Guru Nanak Jayanti          (Tue)
        (12, 25),  # Christmas                   (Fri)
    ],
}


def is_nse_holiday(dt: datetime) -> bool:
    """Check if given date is an NSE holiday.

    Only returns True for years explicitly listed in ``NSE_HOLIDAYS``. For an
    unlisted year we return False rather than reuse a stale year's dates — see
    the note on ``NSE_HOLIDAYS`` for why the list is year-keyed.
    """
    for month, day in NSE_HOLIDAYS.get(dt.year, []):
        if dt.month == month and dt.day == day:
            return True
    return False


def get_next_trading_day_open(from_dt: Optional[datetime] = None) -> datetime:
    """Get the next trading day's market open time."""
    if from_dt is None:
        from_dt = datetime.now(IST)

    # Start from tomorrow
    next_day = from_dt + timedelta(days=1)
    next_day = next_day.replace(hour=9, minute=15, second=0, microsecond=0)

    # Skip weekends and holidays
    max_iterations = 10  # Safety limit
    for _ in range(max_iterations):
        if next_day.weekday() < 5 and not is_nse_holiday(next_day):
            return next_day
        next_day += timedelta(days=1)

    return next_day


def get_market_status() -> MarketStatus:
    """
    Get current NSE market status.

    Returns:
        MarketStatus with is_open, status, message, and timestamps
    """
    now = datetime.now(IST)
    current_time = now.time()
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    # Check weekend
    if weekday >= 5:
        day_name = "Saturday" if weekday == 5 else "Sunday"
        return MarketStatus(
            is_open=False,
            status="closed",
            message=f"Market closed ({day_name})",
            next_open=get_next_trading_day_open(now),
            last_updated=now
        )

    # Check holiday
    if is_nse_holiday(now):
        return MarketStatus(
            is_open=False,
            status="closed",
            message="Market closed (Holiday)",
            next_open=get_next_trading_day_open(now),
            last_updated=now
        )

    # Pre-market (before 9:15 AM)
    if current_time < MARKET_OPEN:
        open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
        return MarketStatus(
            is_open=False,
            status="pre_open",
            message="Market opens at 9:15 AM IST",
            next_open=open_time,
            last_updated=now
        )

    # Market hours (9:15 AM - 3:30 PM)
    if MARKET_OPEN <= current_time <= MARKET_CLOSE:
        return MarketStatus(
            is_open=True,
            status="open",
            message="Market is open",
            next_open=None,
            last_updated=now
        )

    # After hours (after 3:30 PM)
    return MarketStatus(
        is_open=False,
        status="closed",
        message="Market closed at 3:30 PM IST",
        next_open=get_next_trading_day_open(now),
        last_updated=now
    )


def is_market_open() -> bool:
    """Quick check if market is currently open."""
    return get_market_status().is_open
