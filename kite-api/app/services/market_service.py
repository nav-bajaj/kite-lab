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

# NSE Holidays 2026 (approximate - should be updated annually)
# Format: (month, day)
NSE_HOLIDAYS_2026 = [
    (1, 26),   # Republic Day
    (3, 17),   # Holi
    (4, 10),   # Good Friday
    (4, 14),   # Ambedkar Jayanti
    (4, 21),   # Ram Navami
    (5, 1),    # May Day
    (5, 12),   # Buddha Purnima
    (6, 17),   # Eid ul-Fitr (approx)
    (7, 17),   # Muharram
    (8, 15),   # Independence Day
    (8, 27),   # Janmashtami
    (10, 2),   # Gandhi Jayanti
    (10, 21),  # Dussehra
    (10, 22),  # Dussehra
    (11, 3),   # Diwali (Laxmi Puja)
    (11, 4),   # Diwali (Balipratipada)
    (11, 15),  # Guru Nanak Jayanti
    (12, 25),  # Christmas
]


def is_nse_holiday(dt: datetime) -> bool:
    """Check if given date is an NSE holiday."""
    for month, day in NSE_HOLIDAYS_2026:
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
