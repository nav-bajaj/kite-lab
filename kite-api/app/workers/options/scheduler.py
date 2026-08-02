"""Market-clock phase machine for the options worker.

Pure function of an IST datetime — the worker loop feeds it the clock, and
tests feed it fixed datetimes. Holiday truth comes from market_service so
the worker and the web app can never disagree on trading days.
"""
from __future__ import annotations

from datetime import datetime, time
from enum import Enum

from app.services.market_service import IST, is_nse_holiday

PRE_MARKET_START = time(8, 30)   # instrument master download window
SELECTION_TIME = time(8, 45)     # contract selection
CONNECT_TIME = time(9, 0)        # websocket connect + subscribe
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
EOD_FLUSH_END = time(16, 0)      # flush + stats budget after close


class Phase(str, Enum):
    IDLE = "idle"              # non-trading day, or outside the session window
    PRE_MARKET = "pre_market"  # 08:30-09:15: load instruments, select, connect
    CAPTURE = "capture"        # 09:15-15:30: recording
    EOD_FLUSH = "eod_flush"    # 15:30-16:00: flush, stats, compress


def is_trading_day(dt: datetime) -> bool:
    return dt.weekday() < 5 and not is_nse_holiday(dt)


def market_phase(now: datetime, capture_close: time = MARKET_CLOSE) -> Phase:
    """capture_close overrides the 15:30 default for special sessions
    (exchange circulars extending F&O hours). The EOD window follows the
    actual close; its end stays anchored at EOD_FLUSH_END."""
    if now.tzinfo is None:
        now = IST.localize(now)
    now = now.astimezone(IST)
    if not is_trading_day(now):
        return Phase.IDLE
    t = now.time()
    if PRE_MARKET_START <= t < MARKET_OPEN:
        return Phase.PRE_MARKET
    if MARKET_OPEN <= t < capture_close:
        return Phase.CAPTURE
    if capture_close <= t < EOD_FLUSH_END:
        return Phase.EOD_FLUSH
    return Phase.IDLE


def now_ist() -> datetime:
    return datetime.now(IST)
