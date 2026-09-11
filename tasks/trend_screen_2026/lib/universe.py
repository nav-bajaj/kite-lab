"""Point-in-time tradeable universe for breakout_calls_2026.

The liquidity floor is turnover-scaled (TASKS.md §0, founder 2026-09-11):
Rs10cr in 2026 money, deflated by aggregate market turnover, so the universe
holds at roughly 500-700 names in every era instead of collapsing to 113 in
2006. The deflator is derived from the store's own aggregate daily turnover
and frozen; it is data, not a fitted parameter.
"""
from __future__ import annotations
import pandas as pd

STORE = "data/master/bhavcopy_eq.parquet"
FLOOR_2026_CR = 10.0
WINDOW = 63          # ~3 months of sessions for the rolling turnover median
DEFL_WINDOW = 252    # trailing year of sessions for the market-turnover deflator


def load_turnover(store: str = STORE) -> pd.DataFrame:
    """One row per symbol per session.

    The bhavcopy prints a symbol under more than one series on the same day
    (EQ alongside BE/BZ). Left in, a symbol gets two rows for one session and
    every rolling window below counts ROWS, not sessions — so the 63-session
    turnover median silently becomes a 63-row median over a shorter calendar
    span. EQ is preferred, then BE, then BZ, matching the spine's own export.
    """
    df = pd.read_parquet(store, columns=["date", "symbol", "series", "close", "volume"])
    df["pri"] = df.series.map({"EQ": 0, "BE": 1, "BZ": 2}).fillna(3)
    df = (df.sort_values(["symbol", "date", "pri"])
            .drop_duplicates(["symbol", "date"], keep="first")
            .drop(columns=["pri", "series"]))
    df["turn"] = df.close * df.volume / 1e7          # Rs crore
    return df.sort_values(["symbol", "date"])


def turnover_deflator(df: pd.DataFrame, window: int = DEFL_WINDOW) -> pd.Series:
    """Trailing-year market turnover per date, indexed so the last date == 1.0.

    Deliberately trailing rather than calendar-annual. A calendar-year
    deflator is itself look-ahead — standing in March 2020 you do not know
    what the whole of 2020 will trade — and this study cannot afford that
    anywhere. Using a mean over the window rather than a sum also keeps the
    final, incomplete year from distorting the anchor.
    """
    daily = df.groupby("date")["turn"].sum().sort_index()
    trailing = daily.rolling(window, min_periods=window // 2).mean().shift(1)
    trailing = trailing.bfill()
    return (trailing / trailing.iloc[-1]).rename("deflator")


def pit_liquidity(df: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Rolling median turnover per symbol per day, shifted one day.

    The shift is what makes it point-in-time: the floor applied on day T uses
    only turnover observed through T-1, so a name can never qualify on the
    strength of the very session we are about to trade.
    """
    g = df.groupby("symbol", sort=False)["turn"]
    df = df.copy()
    df["adv"] = g.transform(lambda s: s.rolling(window, min_periods=window // 2).median().shift(1))
    return df


def eligible(df: pd.DataFrame, deflator: pd.Series, floor_cr: float = FLOOR_2026_CR) -> pd.DataFrame:
    """Flag each (date, symbol) as inside the tradeable universe."""
    df = df.copy()
    df["floor_cr"] = df.date.map(deflator).astype(float) * floor_cr
    df["eligible"] = df.adv >= df.floor_cr
    return df
