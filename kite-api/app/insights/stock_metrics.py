"""Per-stock, per-date feature engine over the NSE 500 OHLCV panel.

This is the C1 layer of insights_v2 — the raw quantitative features that
`rs_rank.py` (C2) and `scores.py` (C3) build on, and that the screener /
stock-detail API (C4) will serialize. One `StockMetrics` record per symbol
for a requested as-of date.

Design choices (transparent cutoffs, NOT researched thresholds — these are
quoted verbatim in the Learn explainers so they must stay auditable):

  - Liquidity tier from 20-session average turnover: Good ≥ ₹10 Cr,
    Moderate ≥ ₹1 Cr, else Low. Round, transparent buckets.
  - `vol_ratio` = today's volume ÷ average volume of the *prior* 20
    sessions (today excluded) so a "2x" reading means today is genuinely
    double the recent norm.
  - `vol_ratio_5d` = mean(last 5 sessions) ÷ mean(last 20 sessions).
  - RSI(14) is the simple-average variant (SMA of gains / SMA of losses
    over 14 sessions), chosen over Wilder smoothing because it is
    hand-checkable and the difference is immaterial at this horizon.
  - ATR(14) is the simple mean of True Range over 14 sessions.
  - Realized vol is daily-return stdev × √252 (annualized).
  - Beta is 60-session ordinary cov/var vs Nifty 50 daily returns.

Insufficient history yields `None` for the affected field (never a
propagated NaN). Serialization via `to_dict()` is pure JSON scalars.

Caching mirrors breadth.py: an in-memory dict keyed by resolved trading
date plus a pkl under cache/insights/, invalidated by `clear_cache()`
(wired into reading.clear_all_caches).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.insights._paths import indices_dir as _indices_dir
from app.insights.breadth import load_universe

# Trading-day horizons
TD_1W, TD_1M, TD_3M, TD_6M, TD_12M = 5, 21, 63, 126, 252
LEVEL_MIN_HISTORY = 100      # min sessions before 52w-level metrics are meaningful
CRORE = 1e7                  # ₹1 Cr = 10^7

# Liquidity tier cutoffs (₹ Cr, 20-session average turnover) — design choices.
LIQ_GOOD_CR = 10.0
LIQ_MODERATE_CR = 1.0
# User-facing tier labels — covered by the closed-lexicon compliance test.
LIQUIDITY_TIERS: tuple[str, ...] = ("Good", "Moderate", "Low")


@dataclass
class StockMetrics:
    symbol: str
    date: str
    close: float | None

    # Returns
    ret_1d: float | None
    ret_1w: float | None
    ret_1m: float | None
    ret_3m: float | None
    ret_6m: float | None
    ret_12m: float | None

    # Trend structure
    sma_20: float | None
    sma_50: float | None
    sma_100: float | None
    sma_200: float | None
    above_20dma: bool | None
    above_50dma: bool | None
    above_100dma: bool | None
    above_200dma: bool | None
    dist_20dma_pct: float | None
    dist_50dma_pct: float | None
    dist_100dma_pct: float | None
    dist_200dma_pct: float | None
    slope_50dma_20d: float | None
    slope_200dma_20d: float | None
    dma_50_above_200: bool | None

    # Levels
    dist_52w_high_pct: float | None
    dist_52w_low_pct: float | None
    days_since_52w_high: int | None
    drawdown_from_peak_pct: float | None
    fresh_52w_high: bool | None

    # Risk
    atr_14: float | None
    atr_pct: float | None
    vol_20d_annualized: float | None
    vol_60d_annualized: float | None
    vol_percentile_1y: float | None
    beta_60d: float | None
    max_drawdown_1y_pct: float | None
    max_drawdown_6m_pct: float | None
    rsi_14: float | None
    ret_5d_pctile_1y: float | None
    pct_positive_weeks_6m: float | None

    # Volume
    vol_ratio: float | None
    vol_ratio_5d: float | None
    avg_turnover_20d_cr: float | None
    updown_vol_ratio_20d: float | None
    liquidity_tier: str | None

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────── panel loaders ───────────────────────────

def _prices_dir() -> Path:
    return get_settings().data_dir / "nse500_data_merged"


@lru_cache(maxsize=1)
def load_ohlcv_panels() -> dict[str, pd.DataFrame]:
    """Wide panels (rows=date, cols=symbol) for close/high/low/volume.

    Uses the same 16y split-adjusted merged panel breadth.py reads.
    Symbols without a CSV are skipped (recent IPOs / non-NSE500 names).
    """
    prices_dir = _prices_dir()
    frames = {"close": [], "high": [], "low": [], "volume": []}
    for sym in load_universe():
        p = prices_dir / f"{sym}_day.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
        for col in frames:
            if col in df.columns:
                frames[col].append(df[col].rename(sym))
    if not frames["close"]:
        return {}
    out = {col: pd.concat(series, axis=1).sort_index()
           for col, series in frames.items()}
    return out


@lru_cache(maxsize=1)
def _nifty_close() -> pd.Series:
    p = _indices_dir() / "NIFTY_50.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    return (pd.read_csv(p, parse_dates=["date"])
            .set_index("date")["close"].sort_index())


# ─────────────────────────── computation ───────────────────────────

def _f(x) -> float | None:
    """NaN/inf/None → None; else native float."""
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(xf):
        return None
    return xf


def compute_stock_metrics(
    asof: pd.Timestamp,
    panels: dict[str, pd.DataFrame],
    nifty_close: pd.Series | None = None,
) -> dict[str, StockMetrics]:
    """Compute the full feature set for every symbol as of `asof`.

    `panels` is a dict with keys close/high/low/volume (wide frames). This
    is the pure computational core — `get_stock_metrics` wraps it with
    data loading + caching. Injecting `panels` keeps it unit-testable.
    """
    asof = pd.Timestamp(asof)
    close = panels["close"].loc[:asof].ffill(limit=5)
    high = panels["high"].loc[:asof].ffill(limit=5)
    low = panels["low"].loc[:asof].ffill(limit=5)
    vol = panels["volume"].loc[:asof].ffill(limit=5)
    if close.empty:
        return {}

    cols = close.columns
    n = len(close)
    last = close.iloc[-1]
    daily_ret = close.pct_change(fill_method=None)

    def back(k: int) -> pd.Series:
        return close.iloc[-(k + 1)] if n >= k + 1 else pd.Series(np.nan, index=cols)

    ret = {
        "1d": last / back(1) - 1,
        "1w": last / back(TD_1W) - 1,
        "1m": last / back(TD_1M) - 1,
        "3m": last / back(TD_3M) - 1,
        "6m": last / back(TD_6M) - 1,
        "12m": last / back(TD_12M) - 1,
    }

    def sma(w: int) -> pd.Series:
        return close.rolling(w, min_periods=w).mean().iloc[-1]

    def sma_series(w: int) -> pd.DataFrame:
        return close.rolling(w, min_periods=w).mean()

    sma20, sma50, sma100, sma200 = sma(20), sma(50), sma(100), sma(200)
    s50s, s200s = sma_series(50), sma_series(200)
    slope50 = (s50s.iloc[-1] / s50s.iloc[-1 - 20] - 1) if n >= 71 \
        else pd.Series(np.nan, index=cols)
    slope200 = (s200s.iloc[-1] / s200s.iloc[-1 - 20] - 1) if n >= 221 \
        else pd.Series(np.nan, index=cols)

    # 52w levels
    win252 = close.iloc[-TD_12M:]
    have_level = n >= LEVEL_MIN_HISTORY
    high52 = win252.max()
    low52 = win252.min()
    dist_high = last / high52 - 1
    dist_low = last / low52 - 1
    dd_peak = last / win252.cummax().iloc[-1] - 1
    # days since 52w high (position of max within the window)
    wv = win252.values
    filled = np.where(np.isnan(wv), -np.inf, wv)
    # Most-recent occurrence of the high: reverse-argmax finds the last row.
    pos_from_end = filled[::-1].argmax(axis=0)
    allnan = np.isnan(wv).all(axis=0)
    days_since = pos_from_end

    # Risk
    prev_close = close.shift(1)
    tr = np.maximum.reduce([
        (high - low).values,
        (high - prev_close).abs().values,
        (low - prev_close).abs().values,
    ])
    tr_df = pd.DataFrame(tr, index=close.index, columns=cols)
    atr = tr_df.rolling(14, min_periods=14).mean().iloc[-1]
    atr_pct = atr / last

    roll20 = daily_ret.rolling(20, min_periods=20).std()
    roll60 = daily_ret.rolling(60, min_periods=60).std()
    vol20 = roll20.iloc[-1] * np.sqrt(252)
    vol60 = roll60.iloc[-1] * np.sqrt(252)

    rs20_win = roll20.iloc[-TD_12M:]
    cur20 = rs20_win.iloc[-1]
    vp_count = rs20_win.notna().sum()
    vol_pctile = (rs20_win.le(cur20, axis=1).sum() / vp_count).where(vp_count > 0)

    r5 = close.pct_change(TD_1W, fill_method=None)
    r5_win = r5.iloc[-TD_12M:]
    cur5 = r5_win.iloc[-1]
    r5_count = r5_win.notna().sum()
    r5_pctile = (r5_win.le(cur5, axis=1).sum() / r5_count).where(r5_count > 0)

    # RSI(14), simple-average variant
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean().iloc[-1]
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean().iloc[-1]
    rsi = pd.Series(np.nan, index=cols)
    valid_rsi = gain.notna() & loss.notna()
    # loss == 0 → RSI 100; else 100 - 100/(1+gain/loss)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs_ratio = gain / loss
    rsi_vals = 100 - 100 / (1 + rs_ratio)
    rsi_vals = rsi_vals.where(loss != 0, 100.0)
    rsi = rsi_vals.where(valid_rsi)

    # Drawdowns
    dd_1y = (win252 / win252.cummax() - 1).min()
    win126 = close.iloc[-TD_6M:]
    dd_6m = (win126 / win126.cummax() - 1).min() if n >= TD_6M \
        else pd.Series(np.nan, index=cols)

    # Positive-week fraction over ~6M
    weekly = close.resample("W-FRI").last()
    wk_ret = weekly.pct_change(fill_method=None).iloc[-26:]
    wk_count = wk_ret.notna().sum()
    pos_weeks = ((wk_ret > 0).sum() / wk_count).where(wk_count >= 10)

    # Volume
    if n >= 21:
        avg_prior20 = vol.iloc[-21:-1].mean()
        vol_ratio = vol.iloc[-1] / avg_prior20.where(avg_prior20 > 0)
    else:
        vol_ratio = pd.Series(np.nan, index=cols)
    if n >= 20:
        vr5_num = vol.iloc[-5:].mean()
        vr5_den = vol.iloc[-20:].mean()
        vol_ratio_5d = vr5_num / vr5_den.where(vr5_den > 0)
        turnover20 = (close.iloc[-20:] * vol.iloc[-20:]).mean() / CRORE
        up = (daily_ret > 0).iloc[-20:]
        down = (daily_ret < 0).iloc[-20:]
        v20 = vol.iloc[-20:]
        sum_up = v20.where(up).sum()
        sum_down = v20.where(down).sum()
        updown = sum_up / sum_down.where(sum_down > 0)
    else:
        vol_ratio_5d = pd.Series(np.nan, index=cols)
        turnover20 = pd.Series(np.nan, index=cols)
        updown = pd.Series(np.nan, index=cols)

    # Beta vs Nifty 50 (60-session cov/var)
    beta = pd.Series(np.nan, index=cols)
    if nifty_close is not None and not nifty_close.empty and n >= 61:
        nret = nifty_close.reindex(close.index).pct_change(fill_method=None)
        nr = nret.iloc[-60:]
        var_n = nr.var()
        if var_n and np.isfinite(var_n) and var_n > 0:
            sr = daily_ret.iloc[-60:]
            beta = sr.apply(lambda col: col.cov(nr)) / var_n

    def tier(t: float | None) -> str | None:
        if t is None:
            return None
        if t >= LIQ_GOOD_CR:
            return "Good"
        if t >= LIQ_MODERATE_CR:
            return "Moderate"
        return "Low"

    out: dict[str, StockMetrics] = {}
    for i, sym in enumerate(cols):
        close_i = _f(last[sym])
        if close_i is None:
            continue

        def gv(series, sym=sym):
            return _f(series.get(sym))

        sma20_i, sma50_i = gv(sma20), gv(sma50)
        sma100_i, sma200_i = gv(sma100), gv(sma200)

        def above(c, s):
            return None if (c is None or s is None) else bool(c > s)

        def dist(c, s):
            return None if (c is None or s is None or s == 0) else c / s - 1

        dh = gv(dist_high) if have_level else None
        ds_days = (None if (not have_level or allnan[i])
                   else int(days_since[i]))
        fresh = None if ds_days is None else (ds_days == 0)

        out[sym] = StockMetrics(
            symbol=str(sym),
            date=asof.date().isoformat(),
            close=close_i,
            ret_1d=gv(ret["1d"]), ret_1w=gv(ret["1w"]), ret_1m=gv(ret["1m"]),
            ret_3m=gv(ret["3m"]), ret_6m=gv(ret["6m"]), ret_12m=gv(ret["12m"]),
            sma_20=sma20_i, sma_50=sma50_i, sma_100=sma100_i, sma_200=sma200_i,
            above_20dma=above(close_i, sma20_i),
            above_50dma=above(close_i, sma50_i),
            above_100dma=above(close_i, sma100_i),
            above_200dma=above(close_i, sma200_i),
            dist_20dma_pct=dist(close_i, sma20_i),
            dist_50dma_pct=dist(close_i, sma50_i),
            dist_100dma_pct=dist(close_i, sma100_i),
            dist_200dma_pct=dist(close_i, sma200_i),
            slope_50dma_20d=gv(slope50),
            slope_200dma_20d=gv(slope200),
            dma_50_above_200=(None if (sma50_i is None or sma200_i is None)
                              else bool(sma50_i > sma200_i)),
            dist_52w_high_pct=dh,
            dist_52w_low_pct=(gv(dist_low) if have_level else None),
            days_since_52w_high=ds_days,
            drawdown_from_peak_pct=(gv(dd_peak) if have_level else None),
            fresh_52w_high=fresh,
            atr_14=gv(atr), atr_pct=gv(atr_pct),
            vol_20d_annualized=gv(vol20), vol_60d_annualized=gv(vol60),
            vol_percentile_1y=(gv(vol_pctile) if have_level else None),
            beta_60d=gv(beta),
            max_drawdown_1y_pct=(gv(dd_1y) if have_level else None),
            max_drawdown_6m_pct=gv(dd_6m),
            rsi_14=gv(rsi),
            ret_5d_pctile_1y=(gv(r5_pctile) if have_level else None),
            pct_positive_weeks_6m=gv(pos_weeks),
            vol_ratio=gv(vol_ratio), vol_ratio_5d=gv(vol_ratio_5d),
            avg_turnover_20d_cr=gv(turnover20),
            updown_vol_ratio_20d=gv(updown),
            liquidity_tier=tier(gv(turnover20)),
        )
    return out


# ─────────────────────────── caching wrapper ───────────────────────────

_MEM_CACHE: dict[str, dict[str, StockMetrics]] = {}


def _cache_file(date_key: str) -> Path:
    return get_settings().data_dir / "cache" / "insights" / f"stock_metrics_{date_key}.pkl"


def _resolve_asof(asof: pd.Timestamp | None, index: pd.DatetimeIndex) -> pd.Timestamp | None:
    if asof is None:
        return index.max() if len(index) else None
    asof = pd.Timestamp(asof)
    valid = index[index <= asof]
    return valid.max() if len(valid) else None


def _cache_fresh(cache: Path) -> bool:
    if not cache.exists():
        return False
    sentinel = _prices_dir() / "RELIANCE_day.csv"
    if sentinel.exists() and sentinel.stat().st_mtime > cache.stat().st_mtime:
        return False
    return True


def get_stock_metrics(
    asof: pd.Timestamp | None = None,
    force_rebuild: bool = False,
) -> dict[str, StockMetrics]:
    """Feature frame for `asof` (default latest), cached in-memory + pkl.

    Returns {symbol: StockMetrics}. Empty dict if the panel is unavailable
    (e.g. data not yet provisioned) — callers degrade gracefully.
    """
    panels = load_ohlcv_panels()
    if not panels:
        return {}
    resolved = _resolve_asof(asof, panels["close"].index)
    if resolved is None:
        return {}
    key = resolved.date().isoformat()

    if not force_rebuild and key in _MEM_CACHE:
        return _MEM_CACHE[key]

    cache = _cache_file(key)
    if not force_rebuild and _cache_fresh(cache):
        data = pd.read_pickle(cache)  # noqa: S301  # internal cache only
        _MEM_CACHE[key] = data
        return data

    data = compute_stock_metrics(resolved, panels, nifty_close=_nifty_close())
    cache.parent.mkdir(parents=True, exist_ok=True)
    try:
        pd.to_pickle(data, cache)
    except Exception:
        pass
    _MEM_CACHE[key] = data
    return data


def get_price_dma_volume_series(
    symbol: str,
    asof: pd.Timestamp | None = None,
    lookback: int = TD_12M,
) -> dict:
    """Detail-page timeseries: 1y of close + 50/200-DMA + volume ratio for
    one symbol. Contract for the C4/C5 stock-detail page. Empty dict if the
    symbol is absent from the panel."""
    panels = load_ohlcv_panels()
    if not panels or symbol not in panels["close"].columns:
        return {}
    close = panels["close"][symbol].loc[:asof].ffill(limit=5) if asof is not None \
        else panels["close"][symbol].ffill(limit=5)
    vol = panels["volume"][symbol].reindex(close.index)
    sma50 = close.rolling(50, min_periods=50).mean()
    sma200 = close.rolling(200, min_periods=200).mean()
    vol_ratio = vol / vol.rolling(20, min_periods=20).mean().shift(1)
    tail = close.index[-lookback:]

    def ser(s):
        return [None if pd.isna(v) else float(v) for v in s.reindex(tail)]

    return {
        "symbol": symbol,
        "dates": [d.date().isoformat() for d in tail],
        "close": ser(close),
        "sma_50": ser(sma50),
        "sma_200": ser(sma200),
        "vol_ratio": ser(vol_ratio),
    }


def clear_cache() -> None:
    """Drop in-memory + on-disk stock-metrics caches and panel loaders.
    Wired into reading.clear_all_caches()."""
    _MEM_CACHE.clear()
    load_ohlcv_panels.cache_clear()
    _nifty_close.cache_clear()
    cache_dir = get_settings().data_dir / "cache" / "insights"
    if cache_dir.exists():
        for f in cache_dir.glob("stock_metrics_*.pkl"):
            try:
                f.unlink()
            except OSError:
                pass
