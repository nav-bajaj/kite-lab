"""Quant-driven watchlists for the Daily Quant Note + web dashboard.

Five named lists, each refreshed daily from the NSE 500 panel + Nifty 50
benchmark. Each list returns up to N stocks ranked by the relevant signal,
with enough context for commentary to call them out.

  breakouts        Stocks closing today above their trailing 20-day high.
                   Filter: must also be above 50-DMA (avoid false breakouts
                   in downtrends). Sorted by % above the breakout level.

  rs_leaders       Stocks with the strongest 126-day return vs Nifty 50.
                   Top N by RS score. Useful for "who's leading the
                   market" content.

  coiled_springs   Stocks in a tight consolidation near 50-DMA with low
                   realized vol AND above 200-DMA — the classic setup
                   before a breakout. Sorted by tightness (lower realized
                   vol = more coiled).

  stretched        Stocks more than 20% above their 200-DMA — extended
                   names that historically mean-revert. For "watch for
                   pullback" content.

  recent_breakdowns Stocks that closed below their 50-DMA for the first
                    time in the last 5 sessions — early warning signs.

All lists return list[WatchlistEntry], easily JSON-serialisable for the
API.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from app.insights import breadth as _breadth
from app.insights._freshness import file_signature
from app.insights._paths import indices_dir as _indices_dir
from app.insights.breadth import load_close_panel, load_universe


# Default list sizes
DEFAULT_LIMIT = 15


@dataclass
class WatchlistEntry:
    symbol: str
    close: float
    chg_today_pct: float | None     # daily % return
    score: float                     # list-specific score (higher = better-fit)
    note: str                        # short context string for display
    sectors: tuple[str, ...] = ()    # which sectors this stock belongs to

    def to_dict(self) -> dict:
        return asdict(self)


def _nifty_signature() -> tuple:
    return (file_signature(_indices_dir() / "NIFTY_50.csv"),)


def _nifty_close() -> pd.Series:
    return _nifty_close_cached(_nifty_signature())


@lru_cache(maxsize=2)
def _nifty_close_cached(signature) -> pd.Series:
    p = _indices_dir() / "NIFTY_50.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    return (pd.read_csv(p, parse_dates=["date"])
              .set_index("date")["close"]
              .sort_index())


_nifty_close.cache_clear = _nifty_close_cached.cache_clear


def _stock_panel() -> pd.DataFrame:
    # Same universe + price sources as breadth, so reuse its signature.
    return _stock_panel_cached(_breadth._signature())


@lru_cache(maxsize=2)
def _stock_panel_cached(signature) -> pd.DataFrame:
    return load_close_panel(load_universe())


_stock_panel.cache_clear = _stock_panel_cached.cache_clear


def _sectors_for(symbol: str) -> tuple[str, ...]:
    """Lazy import to avoid circular dep."""
    from app.insights.sector_constituents import get_sectors_for
    return get_sectors_for(symbol)


def _asof_index(panel: pd.DataFrame, asof: pd.Timestamp | None) -> pd.Timestamp:
    if asof is None:
        return panel.index.max()
    asof = pd.Timestamp(asof)
    valid = panel.index[panel.index <= asof]
    return valid.max() if not valid.empty else panel.index.max()


# ---------- individual list builders ----------

def get_breakouts(
    asof: pd.Timestamp | None = None,
    lookback_high: int = 20,
    limit: int = DEFAULT_LIMIT,
) -> list[WatchlistEntry]:
    """Stocks closing today above their trailing `lookback_high`-day high
    AND above their 50-DMA. Sorted by % above the breakout level."""
    panel = _stock_panel()
    asof = _asof_index(panel, asof)

    sub = panel.loc[:asof]
    close = sub.iloc[-1]
    prev_close = sub.iloc[-2] if len(sub) >= 2 else None
    chg = (close / prev_close - 1) if prev_close is not None else pd.Series(np.nan, index=close.index)

    # Trailing N-day high excluding today
    high_n = sub.iloc[-(lookback_high + 1):-1].max()
    sma_50 = sub.iloc[-50:].mean() if len(sub) >= 50 else pd.Series(np.nan, index=close.index)

    breakouts = (close > high_n) & (close > sma_50) & close.notna() & high_n.notna()
    pct_above_high = (close - high_n) / high_n
    candidates = pct_above_high[breakouts].sort_values(ascending=False).head(limit)

    out: list[WatchlistEntry] = []
    for sym, score in candidates.items():
        if pd.isna(score):
            continue
        out.append(WatchlistEntry(
            symbol=sym,
            close=float(close[sym]),
            chg_today_pct=float(chg[sym]) if pd.notna(chg[sym]) else None,
            score=float(score),
            note=f"{score*100:+.1f}% above {lookback_high}d high",
            sectors=_sectors_for(sym),
        ))
    return out


def get_rs_leaders(
    asof: pd.Timestamp | None = None,
    lookback: int = 126,
    limit: int = DEFAULT_LIMIT,
) -> list[WatchlistEntry]:
    """Stocks with strongest `lookback`-day return minus Nifty 50's
    return over the same window. Top `limit` by RS."""
    panel = _stock_panel()
    asof = _asof_index(panel, asof)
    sub = panel.loc[:asof]
    if len(sub) < lookback + 1:
        return []

    end_close = sub.iloc[-1]
    start_close = sub.iloc[-(lookback + 1)]
    stock_ret = (end_close / start_close) - 1.0

    nifty = _nifty_close()
    nifty_v = nifty.loc[:asof]
    if len(nifty_v) < lookback + 1:
        return []
    nifty_ret = nifty_v.iloc[-1] / nifty_v.iloc[-(lookback + 1)] - 1.0

    rs = stock_ret - nifty_ret
    chg_today = (end_close / sub.iloc[-2]) - 1 if len(sub) >= 2 else pd.Series(np.nan, index=end_close.index)
    candidates = rs.dropna().sort_values(ascending=False).head(limit)

    out: list[WatchlistEntry] = []
    for sym, score in candidates.items():
        out.append(WatchlistEntry(
            symbol=sym,
            close=float(end_close[sym]),
            chg_today_pct=float(chg_today[sym]) if pd.notna(chg_today.get(sym, np.nan)) else None,
            score=float(score),
            note=f"+{score*100:.1f}% vs Nifty over {lookback}d",
            sectors=_sectors_for(sym),
        ))
    return out


def get_coiled_springs(
    asof: pd.Timestamp | None = None,
    vol_window: int = 20,
    limit: int = DEFAULT_LIMIT,
) -> list[WatchlistEntry]:
    """Setup: above 200-DMA AND above 50-DMA AND realized vol over
    `vol_window` is in the bottom quartile of the stock's own history.
    The "compressed before the move" pattern."""
    panel = _stock_panel()
    asof = _asof_index(panel, asof)
    sub = panel.loc[:asof]
    if len(sub) < 252:
        return []

    close = sub.iloc[-1]
    sma_50 = sub.iloc[-50:].mean()
    sma_200 = sub.iloc[-200:].mean()
    daily_ret = sub.pct_change(fill_method=None)
    recent_vol = daily_ret.iloc[-vol_window:].std()
    historical_vol_q25 = daily_ret.rolling(vol_window).std().quantile(0.25)

    coiled = (
        (close > sma_50) & (close > sma_200)
        & (recent_vol < historical_vol_q25)
        & close.notna() & sma_50.notna() & sma_200.notna()
    )
    chg_today = (close / sub.iloc[-2]) - 1 if len(sub) >= 2 else pd.Series(np.nan, index=close.index)
    # Score: tighter (lower vol) = more coiled; we sort ascending by recent_vol
    candidates = recent_vol[coiled].sort_values(ascending=True).head(limit)

    out: list[WatchlistEntry] = []
    for sym, score in candidates.items():
        # Score for display is "vol percentile of its own history" (lower = tighter)
        own_pctile = (daily_ret[sym].rolling(vol_window).std()
                      .rank(pct=True).iloc[-1])
        out.append(WatchlistEntry(
            symbol=sym,
            close=float(close[sym]),
            chg_today_pct=float(chg_today[sym]) if pd.notna(chg_today.get(sym, np.nan)) else None,
            score=float(own_pctile if pd.notna(own_pctile) else 0.0),
            note=f"vol in own bottom {own_pctile*100:.0f}%; above 50+200 DMA",
            sectors=_sectors_for(sym),
        ))
    return out


def get_stretched(
    asof: pd.Timestamp | None = None,
    threshold: float = 0.20,
    limit: int = DEFAULT_LIMIT,
) -> list[WatchlistEntry]:
    """Stocks > threshold above their 200-DMA. Sorted by extension."""
    panel = _stock_panel()
    asof = _asof_index(panel, asof)
    sub = panel.loc[:asof]
    if len(sub) < 200:
        return []
    close = sub.iloc[-1]
    sma_200 = sub.iloc[-200:].mean()
    extension = (close / sma_200) - 1.0
    chg_today = (close / sub.iloc[-2]) - 1 if len(sub) >= 2 else pd.Series(np.nan, index=close.index)

    stretched = extension[(extension > threshold) & extension.notna()]
    candidates = stretched.sort_values(ascending=False).head(limit)

    out: list[WatchlistEntry] = []
    for sym, score in candidates.items():
        out.append(WatchlistEntry(
            symbol=sym,
            close=float(close[sym]),
            chg_today_pct=float(chg_today[sym]) if pd.notna(chg_today.get(sym, np.nan)) else None,
            score=float(score),
            note=f"+{score*100:.0f}% above 200-DMA",
            sectors=_sectors_for(sym),
        ))
    return out


def get_recent_breakdowns(
    asof: pd.Timestamp | None = None,
    crossover_lookback: int = 5,
    limit: int = DEFAULT_LIMIT,
) -> list[WatchlistEntry]:
    """Stocks that closed below their 50-DMA for the FIRST time in the
    last `crossover_lookback` sessions. Sorted by % below 50-DMA (deepest)."""
    panel = _stock_panel()
    asof = _asof_index(panel, asof)
    sub = panel.loc[:asof]
    if len(sub) < 55:
        return []

    # Compute rolling 50-DMA across history (we need recent values)
    sma_50 = sub.rolling(50, min_periods=50).mean()
    below = sub < sma_50

    today = below.iloc[-1]
    # Was BELOW only in last `crossover_lookback` days?
    recent_window = below.iloc[-crossover_lookback:]
    older_window = below.iloc[-(crossover_lookback + 50):-crossover_lookback]
    if older_window.empty:
        return []
    was_above_all_older = ~older_window.any(axis=0)
    fresh_breakdown = today & was_above_all_older & recent_window.any(axis=0)

    close = sub.iloc[-1]
    sma_today = sma_50.iloc[-1]
    pct_below = (close / sma_today) - 1.0
    chg_today = (close / sub.iloc[-2]) - 1 if len(sub) >= 2 else pd.Series(np.nan, index=close.index)

    candidates = pct_below[fresh_breakdown].sort_values(ascending=True).head(limit)

    out: list[WatchlistEntry] = []
    for sym, score in candidates.items():
        out.append(WatchlistEntry(
            symbol=sym,
            close=float(close[sym]),
            chg_today_pct=float(chg_today[sym]) if pd.notna(chg_today.get(sym, np.nan)) else None,
            score=float(score),
            note=f"{score*100:+.1f}% below 50-DMA (fresh breakdown)",
            sectors=_sectors_for(sym),
        ))
    return out


# ---------- Phase 4.2 candidate patterns ----------
#
# These detectors are wired into the validity-study harness in
# tasks/insight_engine/pattern_validity_study.py. Whether they end up in
# the live watchlist depends on their study findings — see
# tasks/insight_engine/PATTERN_VALIDITY/ for the per-pattern reports.

def get_multi_year_breakouts(
    asof: pd.Timestamp | None = None,
    lookback_days: int = 1260,  # ~5 trading years
    limit: int = DEFAULT_LIMIT,
) -> list[WatchlistEntry]:
    """Close today above the highest close of the prior `lookback_days`
    sessions (excluding today) AND above the 50-DMA. The 'no overhead
    supply for years' setup — historically the strongest variant of a
    breakout signal."""
    panel = _stock_panel()
    asof = _asof_index(panel, asof)
    sub = panel.loc[:asof]
    if len(sub) < lookback_days + 1:
        return []

    close = sub.iloc[-1]
    prev_close = sub.iloc[-2] if len(sub) >= 2 else None
    chg = (close / prev_close - 1) if prev_close is not None else pd.Series(np.nan, index=close.index)

    high_long = sub.iloc[-(lookback_days + 1):-1].max()
    sma_50 = sub.iloc[-50:].mean() if len(sub) >= 50 else pd.Series(np.nan, index=close.index)

    fires = (close > high_long) & (close > sma_50) & close.notna() & high_long.notna()
    pct_above = (close - high_long) / high_long
    candidates = pct_above[fires].sort_values(ascending=False).head(limit)

    out: list[WatchlistEntry] = []
    for sym, score in candidates.items():
        if pd.isna(score):
            continue
        out.append(WatchlistEntry(
            symbol=sym,
            close=float(close[sym]),
            chg_today_pct=float(chg[sym]) if pd.notna(chg[sym]) else None,
            score=float(score),
            note=f"{score*100:+.1f}% above {lookback_days // 252}y high",
            sectors=_sectors_for(sym),
        ))
    return out


def get_pullback_to_50dma(
    asof: pd.Timestamp | None = None,
    proximity_pct: float = 0.02,  # within 2% of the 50-DMA
    uptrend_lookback: int = 20,
    limit: int = DEFAULT_LIMIT,
) -> list[WatchlistEntry]:
    """Stock above 200-DMA AND has been above its 50-DMA at least once in
    the trailing `uptrend_lookback` sessions AND today's close is within
    `proximity_pct` of the 50-DMA. The classic 'reset to trend' setup
    within an established uptrend."""
    panel = _stock_panel()
    asof = _asof_index(panel, asof)
    sub = panel.loc[:asof]
    if len(sub) < 200:
        return []

    close = sub.iloc[-1]
    sma_50 = sub.iloc[-50:].mean()
    sma_200 = sub.iloc[-200:].mean()

    # Distance from 50-DMA today (signed). Negative = pulled back below.
    dist = (close / sma_50) - 1.0

    # Was the stock above its 50-DMA at any point in the prior window?
    # (Rolling 50-DMA needed across the lookback.)
    sma_50_rolling = sub.rolling(50, min_periods=50).mean()
    above_recent = (sub > sma_50_rolling).iloc[-uptrend_lookback:].any(axis=0)

    chg_today = (close / sub.iloc[-2]) - 1 if len(sub) >= 2 else pd.Series(np.nan, index=close.index)

    fires = (
        (close > sma_200)
        & above_recent
        & (dist.abs() < proximity_pct)
        & close.notna() & sma_50.notna() & sma_200.notna()
    )
    # Score by absolute distance — smaller = cleaner pullback to the line
    candidates = dist[fires].abs().sort_values(ascending=True).head(limit)

    out: list[WatchlistEntry] = []
    for sym, _abs_score in candidates.items():
        signed = float(dist[sym])
        out.append(WatchlistEntry(
            symbol=sym,
            close=float(close[sym]),
            chg_today_pct=float(chg_today[sym]) if pd.notna(chg_today.get(sym, np.nan)) else None,
            score=abs(signed),
            note=f"{signed*100:+.1f}% from 50-DMA; above 200-DMA",
            sectors=_sectors_for(sym),
        ))
    return out


def get_sustained_uptrend(
    asof: pd.Timestamp | None = None,
    min_252d_return: float = 0.20,
    max_60d_drawdown: float = 0.08,
    limit: int = DEFAULT_LIMIT,
) -> list[WatchlistEntry]:
    """Clean, durable uptrend: trailing 252-day return ≥ +20%, max drawdown
    over the last 60 days ≤ 8%, close above 200-DMA. Captures stocks in
    persistent uptrends without recent corrective episodes."""
    panel = _stock_panel()
    asof = _asof_index(panel, asof)
    sub = panel.loc[:asof]
    if len(sub) < 252:
        return []

    end_close = sub.iloc[-1]
    start_close = sub.iloc[-252]
    ret_252 = (end_close / start_close) - 1.0

    sma_200 = sub.iloc[-200:].mean()

    # 60-day max drawdown: peak-to-trough over the trailing 60 sessions
    last_60 = sub.iloc[-60:]
    rolling_max = last_60.cummax()
    drawdown_pct = (last_60 / rolling_max) - 1.0
    max_dd = drawdown_pct.min()  # negative number; -0.08 means 8% drawdown

    chg_today = (end_close / sub.iloc[-2]) - 1 if len(sub) >= 2 else pd.Series(np.nan, index=end_close.index)

    fires = (
        (ret_252 >= min_252d_return)
        & (max_dd >= -max_60d_drawdown)
        & (end_close > sma_200)
        & end_close.notna() & sma_200.notna() & max_dd.notna()
    )
    # Score: prefer cleanest trend (smallest drawdown ÷ largest return)
    cleanliness = ret_252 / (-max_dd).clip(lower=0.01)
    candidates = cleanliness[fires].sort_values(ascending=False).head(limit)

    out: list[WatchlistEntry] = []
    for sym, _score in candidates.items():
        out.append(WatchlistEntry(
            symbol=sym,
            close=float(end_close[sym]),
            chg_today_pct=float(chg_today[sym]) if pd.notna(chg_today.get(sym, np.nan)) else None,
            score=float(ret_252[sym]),
            note=f"+{ret_252[sym]*100:.0f}% over 1y; max-DD {max_dd[sym]*100:+.1f}% in 60d",
            sectors=_sectors_for(sym),
        ))
    return out


# ---------- bundled snapshot ----------

def get_all_watchlists(
    asof: pd.Timestamp | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, list[WatchlistEntry]]:
    """All 5 watchlists in one call. Convenience for the snapshot orchestrator."""
    return {
        "breakouts":          get_breakouts(asof, limit=limit),
        "rs_leaders":         get_rs_leaders(asof, limit=limit),
        "coiled_springs":     get_coiled_springs(asof, limit=limit),
        "stretched":          get_stretched(asof, limit=limit),
        "recent_breakdowns":  get_recent_breakdowns(asof, limit=limit),
        # Phase 4.2 — added after passing validity studies (see
        # tasks/insight_engine/PATTERN_VALIDITY/). pullback_to_50dma failed
        # its check and is intentionally not surfaced.
        "multi_year_breakouts": get_multi_year_breakouts(asof, limit=limit),
        "sustained_uptrend":    get_sustained_uptrend(asof, limit=limit),
    }


def clear_cache() -> None:
    _stock_panel_cached.cache_clear()
    _nifty_close_cached.cache_clear()
