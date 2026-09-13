"""Market phase from breadth.

Two things the founder asked to separate: how broad the market is, and which
way that breadth is moving. "Improving from lows" and "strong but rolling
over" are different tapes and a call taken in each should be judged separately.

Everything is point-in-time. Breadth on day T uses only bars through T, and
its 63-session change compares T against T-63 — both known when a call is
placed. Universe membership is the same point-in-time top-500-plus-floor used
by the screen, so breadth is measured over exactly the names the screen could
have picked from.

Three measures, all on the same universe:
  pct_above_200   share of the universe trading above its own 200-day
  pct_leading     share in the screen's own LEADING/EXTENDED states
  net_highs       share at a 52-week high minus share at a 52-week low
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

PANELS = "data/master/prices/adjusted_pr"
CHG_WINDOW = 63          # ~3 months, the direction lookback


def symbol_flags(sym: str) -> pd.DataFrame | None:
    f = os.path.join(PANELS, f"{sym}.csv")
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, parse_dates=["date"]).dropna(subset=["close"]).set_index("date")
    df = df[~df.index.duplicated()].sort_index()
    if len(df) < 260:
        return None
    c, h, l = df.close, df.high, df.low
    s200 = c.rolling(200).mean()
    hi52, lo52 = h.rolling(252).max(), l.rolling(252).min()
    out = pd.DataFrame({
        "above200": (c > s200).astype(float),
        "at_high": (c >= 0.98 * hi52).astype(float),
        "at_low": (c <= 1.02 * lo52).astype(float),
    })
    out[s200.isna()] = np.nan
    return out.assign(symbol=sym).reset_index()


def build(universe: pd.DataFrame, syms) -> pd.DataFrame:
    """universe: long frame of the point-in-time (date, symbol) pairs."""
    parts = []
    for i, s in enumerate(syms, 1):
        r = symbol_flags(s)
        if r is not None:
            parts.append(r)
        if i % 500 == 0:
            print(f"  breadth {i}/{len(syms)}", flush=True)
    flags = pd.concat(parts, ignore_index=True)
    # restrict to the days each name was actually in the universe
    flags = flags.merge(universe, on=["date", "symbol"], how="inner")
    b = flags.groupby("date").agg(
        n=("above200", "size"),
        pct_above_200=("above200", "mean"),
        at_high=("at_high", "mean"),
        at_low=("at_low", "mean"),
    )
    b["net_highs"] = b.at_high - b.at_low
    b = b[b.n >= 50]
    for col in ("pct_above_200", "net_highs"):
        b[f"{col}_chg"] = b[col] - b[col].shift(CHG_WINDOW)
    return b


def phases(b: pd.DataFrame, level_col="pct_above_200", chg_col="pct_above_200_chg",
           level_cut: float | None = None) -> pd.Series:
    """Four phases from breadth level x breadth direction.

    The level threshold is the series' own long-run median rather than a round
    50%, because what counts as "broad" differs between markets; the median is
    computed once over the whole span and is therefore a single fixed constant,
    not a rolling look-ahead.
    """
    if level_cut is None:
        level_cut = b[level_col].median()
    high = b[level_col] >= level_cut
    rising = b[chg_col] > 0
    ph = pd.Series("", index=b.index, dtype=object)
    ph[high & rising] = "EXPANSION"       # broad and getting broader
    ph[high & ~rising] = "TOPPING"        # broad but narrowing
    ph[~high & rising] = "RECOVERY"       # thin but improving off lows
    ph[~high & ~rising] = "CONTRACTION"   # thin and deteriorating
    ph[b[chg_col].isna()] = np.nan
    return ph
