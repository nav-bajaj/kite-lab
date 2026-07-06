"""
Market status service.

Provides market hours detection for NSE (National Stock Exchange of India).
"""
from datetime import datetime, date, time, timedelta
from typing import Optional
import logging
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
#   - Id-ul-Fitr (Ramzan) Sat 21 Mar 2026
#   - Independence Day   Sat 15 Aug 2026
#   - Diwali Laxmi Pujan Sun 08 Nov 2026 (special Muhurat session, not a full
#     trading day; not modelled here)
#
# NOTE ON AD-HOC CLOSURES: NSE also declares special one-off holidays outside
# the annual circular (elections, days of mourning). These MUST be backfilled
# here too — e.g. 15 Jan 2026 was declared a full CM trading holiday on 12 Jan
# 2026 for the Maharashtra municipal-corporation elections (NSE/BSE closed).
# Verified against Zerodha + ClearTax calendars and NSE circular reporting
# (2026 total = 16 weekday CM holidays).
#
# Format: {year: [(month, day), ...]}
NSE_HOLIDAYS = {
    2026: [
        (1, 15),   # Maharashtra civic elections (special, declared 12 Jan) (Thu)
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


def is_holiday_year_covered(year: int) -> bool:
    """True if ``NSE_HOLIDAYS`` has an explicit entry for ``year``.

    An uncovered year is dangerous: ``is_nse_holiday`` returns False for every
    date in it, so date/schedule logic silently treats that year's exchange
    holidays as trading days. Callers use this as a staleness tripwire.
    """
    return year in NSE_HOLIDAYS


def warn_if_holiday_table_stale(today: Optional[date] = None) -> list:
    """Log a warning for any near-term year missing from ``NSE_HOLIDAYS``.

    Checks the current year, and — once within the final 45 days of it — next
    year too (NSE publishes the next calendar in December). The table MUST be
    refreshed from the official NSE circular before an uncovered year begins.
    Returns the list of uncovered years (also used by the coverage test).
    """
    if today is None:
        today = datetime.now(IST).date()
    years_to_check = [today.year]
    if (date(today.year, 12, 31) - today).days <= 45:
        years_to_check.append(today.year + 1)
    missing = [y for y in years_to_check if not is_holiday_year_covered(y)]
    if missing:
        logging.getLogger(__name__).warning(
            "NSE_HOLIDAYS is missing entries for year(s) %s — holiday-dependent "
            "scheduling will treat those years' exchange holidays as trading "
            "days. Update market_service.NSE_HOLIDAYS from the official NSE "
            "circular (nseindia.com/resources/exchange-communication-holidays).",
            ", ".join(str(y) for y in missing),
        )
    return missing


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


# ---------------------------------------------------------------------------
# Trading-day helpers (date-based) — used by the rebalance schedule module to
# project rebalance dates onto the NSE calendar. Pure functions over the
# holiday table above; no Kite/network access.
# ---------------------------------------------------------------------------

def is_trading_day(d: date) -> bool:
    """True if `d` is a weekday and not an NSE holiday."""
    return d.weekday() < 5 and not is_nse_holiday(datetime(d.year, d.month, d.day))


def snap_back_to_trading_day(d: date) -> date:
    """Return `d` if it's a trading day, else the nearest trading day before it.

    Mirrors the engine's ``resample('W-FRI').last()`` behaviour: a rebalance
    nominally on a Friday that is a holiday falls back to that week's prior
    trading day (Thursday, etc.).
    """
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def next_trading_day_after(d: date) -> date:
    """Return the first trading day strictly after `d`."""
    d += timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d


def trading_days_between(start: date, end: date) -> int:
    """Count trading days in the half-open interval (start, end]."""
    if end <= start:
        return 0
    count = 0
    d = start + timedelta(days=1)
    while d <= end:
        if is_trading_day(d):
            count += 1
        d += timedelta(days=1)
    return count
