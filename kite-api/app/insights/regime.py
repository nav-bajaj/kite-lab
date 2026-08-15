"""Market regime classifier — 4-state model with persistence tracking.

Classifies each trading day into one of:

  - TREND_BULL : healthy uptrend, broad participation, vol contained
  - DRIFT      : neutral / sideways / the messy middle
  - STRETCHED  : market above trend AND very broad AND very low vol →
                 overheated / complacent — historically precedes pullbacks
  - STRESS     : VIX elevated OR market below trend with deteriorating
                 breadth — drawdown / panic phase

Inputs (all from already-built modules):
  - NIFTY 100 close vs 100-DMA (trend filter; reuses the COMBO regime gate)
  - pct_above_200dma from breadth.py (broad participation)
  - vix_zscore_252d from macro.py (vol regime)

Smoothing: raw daily classification is "noisy" near boundaries. We
require 3 consecutive days in a new regime before declaring a
transition, so the published regime is stable.

Output:
  compute_regime_panel() → DataFrame with one row per date, columns:
    raw_regime, regime, persistence_days, days_since_last_change.

  get_regime_snapshot(asof=None) → RegimeSnapshot for the latest day
    with the inputs that drove the classification, suitable for
    commentary to summarize.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.insights import breadth as _breadth
from app.insights import macro as _macro
from app.insights._freshness import file_signature
from app.insights.breadth import get_breadth_panel
from app.insights.macro import get_macro_panel


# Regime labels
TREND_BULL = "TREND_BULL"
DRIFT = "DRIFT"
STRETCHED = "STRETCHED"
STRESS = "STRESS"

REGIMES = (TREND_BULL, DRIFT, STRETCHED, STRESS)

# Smoothing — require this many consecutive days in a new state before
# declaring a transition. Avoids day-to-day flip-flopping.
SMOOTHING_DAYS = 3


@dataclass
class RegimeSnapshot:
    """Current regime + the inputs that drove the classification."""
    date: pd.Timestamp
    regime: str                       # one of REGIMES
    persistence_days: int              # how long current regime has held
    days_since_last_change: int        # alias / clarity
    # Inputs that drove the call (for commentary to surface)
    nifty100_above_100dma: bool        # legacy alias of index_above_100dma
    pct_above_200dma: float | None
    vix_zscore_252d: float | None
    # Previous regime (for transition narratives)
    prev_regime: str | None
    prev_regime_lasted_days: int | None
    # Scope. `universe` is None for the legacy market-wide reading.
    universe: str | None = None
    index_label: str = "Nifty 100"
    index_above_100dma: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat() if isinstance(self.date, pd.Timestamp) else self.date
        return d


def _indices_dir() -> Path:
    settings = get_settings()
    external = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
    if external.exists():
        return external
    return settings.data_dir / "indices_data_historical"


# Universe-scoped regime (insights_dashboard_v2): a Nifty 500 TREND_BULL
# reads the NIFTY 500's own trend and the NSE 500's own breadth. Each
# universe's regime therefore starts where its index series starts —
# NIFTY 500 from 2015, LARGEMID250 from 2020 — which is why the
# no-argument call keeps the legacy market-wide definition below
# (NIFTY 100 trend + NSE 500 breadth, 2010+) for the note generator,
# conditional distributions and calendar lookbacks that need the depth.
REGIME_UNIVERSES = _breadth.BREADTH_UNIVERSES

_UNIVERSE_INDEX: dict[str, tuple[str, str]] = {
    "nse500": ("NIFTY_500.csv", "Nifty 500"),
    "nifty250": ("NIFTY_LARGEMID250.csv", "Nifty 250"),
    "nifty100": ("NIFTY_100.csv", "Nifty 100"),
    "nifty50": ("NIFTY_50.csv", "Nifty 50"),
}

# VIX is market-wide — there is no per-universe volatility index, so every
# universe's regime shares the same volatility input. Documented rather
# than silently assumed.
_TREND_DMA = 100


def _check_universe(universe: str) -> None:
    if universe not in _UNIVERSE_INDEX:
        raise ValueError(
            f"Unknown universe {universe!r}; expected one of {REGIME_UNIVERSES}"
        )


def regime_index_label(universe: str) -> str:
    """Display name of the index whose trend defines this universe's regime."""
    _check_universe(universe)
    return _UNIVERSE_INDEX[universe][1]


def _universe_index_path(universe: str) -> Path:
    _check_universe(universe)
    return _indices_dir() / _UNIVERSE_INDEX[universe][0]


def regime_index_close(universe: str) -> pd.Series:
    """Close series of the universe's own index (full available history)."""
    return _index_close_cached(universe, file_signature(_universe_index_path(universe)))


@lru_cache(maxsize=8)
def _index_close_cached(universe: str, signature: float) -> pd.Series:
    p = _universe_index_path(universe)
    if not p.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
    return df["close"].dropna()


def _index_above_100dma(universe: str) -> pd.Series:
    """Bool series: True on days the universe's index closed above its
    100-day average. NaN warm-up days are dropped, which is what bounds
    each universe's regime history."""
    close = regime_index_close(universe)
    if close.empty:
        return pd.Series(dtype=bool)
    dma = close.rolling(_TREND_DMA, min_periods=_TREND_DMA).mean()
    return (close > dma)[dma.notna()].astype(bool)


def _nifty100_signature() -> tuple:
    return (file_signature(_indices_dir() / "NIFTY_100.csv"),)


def _signature() -> tuple:
    """Signature of the regime panel — it derives from breadth, macro, and the
    NIFTY 100 trend filter, so fold all three source signatures together."""
    return _breadth._signature() + _macro._signature() + _nifty100_signature()


def _nifty100_above_100dma() -> pd.Series:
    """Bool series: True on days NIFTY 100 closed > 100-DMA.

    Reuses the trend filter from combo_defensive (without the 3-day
    confirmation hysteresis — we apply our own smoothing at regime level).
    """
    return _nifty100_above_100dma_cached(_nifty100_signature())


@lru_cache(maxsize=2)
def _nifty100_above_100dma_cached(signature) -> pd.Series:
    p = _indices_dir() / "NIFTY_100.csv"
    if not p.exists():
        return pd.Series(dtype=bool)
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
    close = df["close"]
    dma = close.rolling(100, min_periods=100).mean()
    return (close > dma).astype(bool)


def _classify_one(*, nifty_up: bool,
                   pct_200: float | None,
                   vix_z: float | None) -> str:
    """Classify a single day given its inputs."""
    if pct_200 is None and vix_z is None:
        return DRIFT  # default before enough data is available

    # STRESS — strongest signal wins regardless of trend filter
    if vix_z is not None and vix_z > 1.5:
        return STRESS
    if not nifty_up and pct_200 is not None and pct_200 < 0.35:
        return STRESS

    # If trend is down, we're in drift at best (not stretched/bull)
    if not nifty_up:
        return DRIFT

    # STRETCHED — uptrend + extreme breadth + low vol
    if (pct_200 is not None and pct_200 > 0.85
            and vix_z is not None and vix_z < -1.0):
        return STRETCHED

    # TREND_BULL — uptrend + healthy breadth
    if pct_200 is not None and pct_200 > 0.55:
        return TREND_BULL

    return DRIFT


def _apply_smoothing(raw: pd.Series, min_consecutive: int) -> pd.Series:
    """Smooth a raw regime series: only accept a state change if the new
    state persists for `min_consecutive` consecutive days."""
    out = raw.copy()
    if raw.empty:
        return out
    current = raw.iloc[0]
    candidate = current
    candidate_count = 0
    for i, v in enumerate(raw):
        if v == current:
            candidate_count = 0
            candidate = current
            out.iloc[i] = current
        elif v == candidate:
            candidate_count += 1
            if candidate_count >= min_consecutive:
                current = candidate
                out.iloc[i] = current
                candidate_count = 0
            else:
                out.iloc[i] = current
        else:
            candidate = v
            candidate_count = 1
            out.iloc[i] = current
    return out


def _compute_persistence(regime_series: pd.Series) -> pd.Series:
    """For each date, how many consecutive days (including today) the
    current regime has been in effect."""
    persistence = pd.Series(0, index=regime_series.index, dtype=int)
    counter = 0
    prev = None
    for i, v in enumerate(regime_series):
        if v == prev:
            counter += 1
        else:
            counter = 1
        persistence.iloc[i] = counter
        prev = v
    return persistence


_nifty100_above_100dma.cache_clear = _nifty100_above_100dma_cached.cache_clear


def compute_regime_panel(universe: str | None = None) -> pd.DataFrame:
    """Time series of regime classifications with persistence tracking.

    `universe=None` is the legacy market-wide reading (NIFTY 100 trend +
    NSE 500 breadth, 2010+). Passing a universe scopes both the trend
    filter and the participation input to that universe's own index and
    own breadth panel, and bounds the history to where that index starts.
    """
    if universe is None:
        return _compute_regime_panel_cached(_signature())
    _check_universe(universe)
    return _compute_universe_panel_cached(_universe_signature(universe))


def _universe_signature(universe: str) -> tuple:
    return (
        (universe,)
        + _breadth._signature(universe)
        + _macro._signature()
        + (file_signature(_universe_index_path(universe)),)
    )


@lru_cache(maxsize=8)
def _compute_universe_panel_cached(signature) -> pd.DataFrame:
    universe = signature[0]
    breadth_panel = get_breadth_panel(universe)
    macro_panel = get_macro_panel()
    index_up = _index_above_100dma(universe)
    if breadth_panel.empty or index_up.empty:
        return pd.DataFrame()

    # The universe's own index bounds the history — no regime before its
    # 100-DMA exists. Breadth/macro are then aligned onto that calendar.
    idx = breadth_panel.index.intersection(index_up.index)
    if len(idx) == 0:
        return pd.DataFrame()

    macro_aligned = macro_panel.reindex(idx).ffill()
    index_aligned = index_up.reindex(idx).ffill().fillna(False).astype(bool)
    pct_200 = breadth_panel.loc[idx, "pct_above_200dma"]
    vix_z = macro_aligned["vix_zscore_252d"]

    raw = pd.Series("", index=idx, dtype=object)
    for i in range(len(idx)):
        raw.iloc[i] = _classify_one(
            nifty_up=bool(index_aligned.iloc[i]),
            pct_200=(None if pd.isna(pct_200.iloc[i]) else float(pct_200.iloc[i])),
            vix_z=(None if pd.isna(vix_z.iloc[i]) else float(vix_z.iloc[i])),
        )

    smoothed = _apply_smoothing(raw, SMOOTHING_DAYS)
    return pd.DataFrame({
        "raw_regime": raw,
        "regime": smoothed,
        "persistence_days": _compute_persistence(smoothed),
        "index_above_100dma": index_aligned,
        "pct_above_200dma": pct_200,
        "vix_zscore_252d": vix_z,
    })


@lru_cache(maxsize=2)
def _compute_regime_panel_cached(signature) -> pd.DataFrame:
    breadth = get_breadth_panel()
    macro = get_macro_panel()
    nifty_up = _nifty100_above_100dma()

    # Align on breadth's index (NSE 500 trading calendar — same as macro)
    idx = breadth.index
    macro_aligned = macro.reindex(idx).ffill()
    nifty_aligned = nifty_up.reindex(idx).ffill().fillna(False).astype(bool)

    pct_200 = breadth["pct_above_200dma"]
    vix_z = macro_aligned["vix_zscore_252d"]

    raw = pd.Series("", index=idx, dtype=object)
    for i in range(len(idx)):
        raw.iloc[i] = _classify_one(
            nifty_up=bool(nifty_aligned.iloc[i]),
            pct_200=(None if pd.isna(pct_200.iloc[i]) else float(pct_200.iloc[i])),
            vix_z=(None if pd.isna(vix_z.iloc[i]) else float(vix_z.iloc[i])),
        )

    smoothed = _apply_smoothing(raw, SMOOTHING_DAYS)
    persistence = _compute_persistence(smoothed)

    return pd.DataFrame({
        "raw_regime": raw,
        "regime": smoothed,
        "persistence_days": persistence,
        "nifty100_above_100dma": nifty_aligned,
        "index_above_100dma": nifty_aligned,
        "pct_above_200dma": pct_200,
        "vix_zscore_252d": vix_z,
    })


def get_regime_snapshot(
    asof: pd.Timestamp | None = None,
    universe: str | None = None,
) -> RegimeSnapshot | None:
    """Regime snapshot for `asof` (default: most recent date), scoped to
    `universe` when given (see `compute_regime_panel`)."""
    panel = compute_regime_panel(universe)
    if panel.empty:
        return None

    if asof is None:
        asof = panel.index.max()
    asof = pd.Timestamp(asof)
    valid = panel.index[panel.index <= asof]
    if valid.empty:
        return None
    asof = valid.max()

    row = panel.loc[asof]

    # Find previous regime + how long it lasted
    prior = panel.loc[:asof].iloc[:-1]
    prev_regime: str | None = None
    prev_lasted: int | None = None
    if not prior.empty:
        # Walk backwards: find the last day in a different regime, then count
        current_regime = row["regime"]
        different = prior[prior["regime"] != current_regime]
        if not different.empty:
            transition_idx = different.index[-1]
            prev_regime = different.loc[transition_idx, "regime"]
            prev_lasted = int(different.loc[transition_idx, "persistence_days"])

    index_up = bool(row["index_above_100dma"])
    return RegimeSnapshot(
        date=asof,
        regime=row["regime"],
        persistence_days=int(row["persistence_days"]),
        days_since_last_change=int(row["persistence_days"]),
        nifty100_above_100dma=index_up,
        pct_above_200dma=(float(row["pct_above_200dma"])
                          if pd.notna(row["pct_above_200dma"]) else None),
        vix_zscore_252d=(float(row["vix_zscore_252d"])
                         if pd.notna(row["vix_zscore_252d"]) else None),
        prev_regime=prev_regime,
        prev_regime_lasted_days=prev_lasted,
        universe=universe,
        index_label=regime_index_label(universe) if universe else "Nifty 100",
        index_above_100dma=index_up,
    )


def get_regime_history(universe: str | None = None) -> pd.DataFrame:
    """Summary table: one row per regime episode, with start/end dates,
    duration, and what the scope's index did across the spell.

    `index_return_pct` is the close-to-close move of the universe's own
    index over the episode (NIFTY 100 for the legacy market-wide call) —
    so the UI can say what the market actually returned during it.
    """
    panel = compute_regime_panel(universe)
    if panel.empty:
        return pd.DataFrame()

    closes = regime_index_close(universe) if universe else _legacy_index_close()

    # Group consecutive runs of the same regime
    regime_series = panel["regime"]
    changes = (regime_series != regime_series.shift()).cumsum()
    episodes = []
    for _, episode in regime_series.groupby(changes):
        start, end = episode.index[0], episode.index[-1]
        episodes.append({
            "regime": episode.iloc[0],
            "start": start,
            "end": end,
            "days": len(episode),
            "index_return_pct": _window_return(closes, start, end),
        })
    return pd.DataFrame(episodes)


def _legacy_index_close() -> pd.Series:
    return _index_close_cached("nifty100", file_signature(_universe_index_path("nifty100")))


def _window_return(closes: pd.Series, start, end) -> float | None:
    """Close-to-close return across [start, end], or None when the index
    has no data covering the window."""
    if closes.empty:
        return None
    window = closes.loc[start:end]
    if len(window) < 2:
        return None
    first, last = float(window.iloc[0]), float(window.iloc[-1])
    if first <= 0:
        return None
    return last / first - 1.0


compute_regime_panel.cache_clear = _compute_regime_panel_cached.cache_clear


def clear_cache() -> None:
    _nifty100_above_100dma_cached.cache_clear()
    _compute_regime_panel_cached.cache_clear()
    _compute_universe_panel_cached.cache_clear()
    _index_close_cached.cache_clear()
