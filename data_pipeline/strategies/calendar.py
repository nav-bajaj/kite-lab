"""Signal-date builders: monthly on-or-after a calendar day; stop-check dates by cadence."""
from __future__ import annotations
import pandas as pd
from scripts._clean_engine import fridays, biweekly_fridays, monthly_first_trading_day


def monthly_on_or_after(cal: pd.DatetimeIndex, day: int = 1) -> pd.DatetimeIndex:
    """First trading day of each month on or after calendar day `day` (day=1 reproduces monthly_first_trading_day)."""
    if day == 1:
        return pd.DatetimeIndex(monthly_first_trading_day(cal))
    out = []
    for (_, _), grp in pd.Series(cal, index=cal).groupby([cal.year, cal.month]):
        hit = grp[grp.index.day >= day]
        if len(hit):
            out.append(hit.index[0])
    return pd.DatetimeIndex(out)


def signal_dates(cal: pd.DatetimeIndex, cadence: str, day: int = 1) -> pd.DatetimeIndex:
    """Entry (and, when used as weekly_signal_dates, stop-check) dates for a cadence: weekly | biweekly | monthly."""
    if cadence == "weekly":
        return pd.DatetimeIndex(fridays(cal))
    if cadence == "biweekly":
        return pd.DatetimeIndex(biweekly_fridays(cal))
    if cadence == "monthly":
        return monthly_on_or_after(cal, day)
    raise ValueError(cadence)
