"""Market stress composite — single 0-100 score.

Combines four inputs into one interpretable score so the Daily Quant
Note can lead with a number:

  - VIX percentile (over trailing 252d)               weight 0.35
  - Drawdown depth of Nifty 50 from trailing 252d high weight 0.25
  - % NSE 500 BELOW 200-DMA (i.e., 1 − breadth)        weight 0.20
  - Cross-sectional dispersion z-score                  weight 0.20

Each component is normalised to 0-100 (0 = calm, 100 = max stress)
and then weighted-averaged.

Why this composite vs the regime classifier:
  - Regime is a categorical label (4 states); stress is a continuous
    score that lets us say "we're in the 78th percentile of stress
    historically" — more informative than "we're in DRIFT regime"
  - Stress also surfaces transitions earlier than regime (which has
    smoothing); useful as an alert trigger

Reading guide for downstream commentary:
   0-20   very calm
  20-40   normal
  40-60   elevated (worth watching)
  60-80   stressed (defensive setups historically pay off here)
  80-100  panic / capitulation (historically bullish from here at 20-60d
          horizons, per the panic-bounce analysis)
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


# Component weights — sum to 1.0
WEIGHTS = {
    "vix_pctile":     0.35,
    "drawdown":       0.25,
    "below_200dma":   0.20,
    "dispersion":     0.20,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

# Lookbacks. Every input on this indicator is a one-year quantity — the VIX
# percentile ranks over 252d, the drawdown is measured against the 252d high,
# the dispersion z-score uses a 252d mean and stdev — so the headline
# percentile matches them rather than reaching back five years and being the
# odd one out (founder, 2026-08-15).
COMPONENT_WINDOW = 252
SCORE_PERCENTILE_WINDOW = 252


@dataclass
class StressSnapshot:
    date: pd.Timestamp
    score: float | None           # 0-100 composite; None if no input exists
    score_percentile: float | None  # where today sits in the trailing distribution
    # Observations actually behind that percentile. Below
    # SCORE_PERCENTILE_WINDOW the comparison is shallower than the copy
    # implies, so the UI can qualify or suppress it.
    score_percentile_obs: int | None

    # Component contributions (each 0-100)
    vix_pctile_component: float | None
    drawdown_component: float | None
    below_200dma_component: float | None
    dispersion_component: float | None

    # Raw inputs (for transparency in commentary)
    vix_close: float | None
    nifty_drawdown_pct: float | None   # negative number (e.g., -0.05 = -5%)
    pct_above_200dma: float | None
    dispersion_z: float | None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat() if isinstance(self.date, pd.Timestamp) else self.date
        # Ship the weights with the reading: the UI states how the score is
        # computed, and hardcoding them there is how displayed rules drift
        # away from the engine.
        d["weights"] = dict(WEIGHTS)
        # Windows behind the percentile figures, for the same reason.
        d["percentile_window_days"] = SCORE_PERCENTILE_WINDOW
        d["component_window_days"] = COMPONENT_WINDOW
        return d


def _indices_dir() -> Path:
    settings = get_settings()
    external = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
    if external.exists():
        return external
    return settings.data_dir / "indices_data_historical"


def _nifty_signature() -> tuple:
    return (file_signature(_indices_dir() / "NIFTY_50.csv"),)


def _signature() -> tuple:
    """Signature of the stress panel — derives from breadth, macro, and the
    Nifty 50 close, so fold all three source signatures together."""
    return _breadth._signature() + _macro._signature() + _nifty_signature()


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


def _rolling_percentile(series: pd.Series, window: int = COMPONENT_WINDOW) -> pd.Series:
    """For each date, return the percentile rank of today's value within
    the trailing `window` observations. 0 = lowest in window, 1 = highest."""
    return series.rolling(window, min_periods=max(50, window // 4)).rank(pct=True)


def compute_stress_panel() -> pd.DataFrame:
    """Time series of stress score + components, on the breadth calendar."""
    return _compute_stress_panel_cached(_signature())


@lru_cache(maxsize=2)
def _compute_stress_panel_cached(signature) -> pd.DataFrame:
    breadth = get_breadth_panel()
    macro = get_macro_panel()
    nifty = _nifty_close()

    idx = breadth.index
    macro_a = macro.reindex(idx).ffill()
    nifty_a = nifty.reindex(idx).ffill()

    # Component 1: VIX percentile over 252d → already 0..1, multiply by 100
    vix = macro_a["vix_close"]
    vix_pct = _rolling_percentile(vix) * 100.0

    # Component 2: Nifty drawdown from trailing 252d high
    rolling_peak = nifty_a.rolling(252, min_periods=60).max()
    dd = (nifty_a / rolling_peak) - 1.0  # 0 to -1
    # Map drawdown to 0-100: 0% DD → 0, -10% → 50, -20%+ → 100
    drawdown_component = (-dd / 0.20 * 100.0).clip(0, 100)

    # Component 3: % NSE 500 BELOW 200-DMA (1 − pct_above_200dma) × 100
    pct_above = breadth["pct_above_200dma"]
    below_200_component = ((1 - pct_above) * 100.0).clip(0, 100)

    # Component 4: dispersion z-score (over trailing 252d) → map z ∈ [-2, +2] → 0-100
    disp = breadth["dispersion"]
    disp_mean = disp.rolling(252, min_periods=60).mean()
    disp_std = disp.rolling(252, min_periods=60).std()
    disp_z = (disp - disp_mean) / disp_std
    # +2 z = max stress (100), -2 z = no dispersion stress (0)
    dispersion_component = ((disp_z + 2.0) / 4.0 * 100.0).clip(0, 100)

    # Renormalise over the components that actually exist on the day.
    # Filling a missing input with 0 would score "no data" as "maximum
    # calm": in early 2010, with VIX and drawdown not yet available, that
    # understated the composite by ~18 points on dates the snapshot picker
    # can reach (audit, 2026-08-15). Once all four are present the weights
    # sum to 1 and this is a no-op.
    parts = {
        "vix_pctile": vix_pct,
        "drawdown": drawdown_component,
        "below_200dma": below_200_component,
        "dispersion": dispersion_component,
    }
    weighted = sum(WEIGHTS[k] * v.fillna(0) for k, v in parts.items())
    live_weight = sum(WEIGHTS[k] * v.notna() for k, v in parts.items())
    score = (weighted / live_weight).where(live_weight > 0)

    score_pctile = _rolling_percentile(score, window=SCORE_PERCENTILE_WINDOW) * 100.0
    # How many observations actually back each percentile — the window is
    # only nominally five years until enough history accumulates, and the
    # UI states the window out loud.
    score_pctile_obs = (
        score.notna()
        .rolling(SCORE_PERCENTILE_WINDOW, min_periods=1)
        .sum()
        .where(score_pctile.notna())
    )

    return pd.DataFrame({
        "score": score,
        "score_percentile": score_pctile,
        "score_percentile_obs": score_pctile_obs,
        "vix_pctile_component": vix_pct,
        "drawdown_component": drawdown_component,
        "below_200dma_component": below_200_component,
        "dispersion_component": dispersion_component,
        # raw inputs
        "vix_close": vix,
        "nifty_drawdown_pct": dd,
        "pct_above_200dma": pct_above,
        "dispersion_z": disp_z,
    })


def get_stress_snapshot(asof: pd.Timestamp | None = None) -> StressSnapshot | None:
    """Stress snapshot for `asof` (default: most recent date)."""
    panel = compute_stress_panel()
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

    def _f(v) -> float | None:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        try:
            f = float(v)
            return None if np.isnan(f) else f
        except (TypeError, ValueError):
            return None

    # `or 0.0` would turn "unknown" into a confident-looking reading — a
    # missing percentile rendered as "p0" (audit, 2026-08-15). None means
    # None all the way to the UI, which shows an em dash.
    return StressSnapshot(
        date=asof,
        score=_f(row["score"]),
        score_percentile=_f(row["score_percentile"]),
        score_percentile_obs=(
            int(row["score_percentile_obs"])
            if pd.notna(row.get("score_percentile_obs"))
            else None
        ),
        vix_pctile_component=_f(row["vix_pctile_component"]),
        drawdown_component=_f(row["drawdown_component"]),
        below_200dma_component=_f(row["below_200dma_component"]),
        dispersion_component=_f(row["dispersion_component"]),
        vix_close=_f(row["vix_close"]),
        nifty_drawdown_pct=_f(row["nifty_drawdown_pct"]),
        pct_above_200dma=_f(row["pct_above_200dma"]),
        dispersion_z=_f(row["dispersion_z"]),
    )


compute_stress_panel.cache_clear = _compute_stress_panel_cached.cache_clear


def clear_cache() -> None:
    _nifty_close_cached.cache_clear()
    _compute_stress_panel_cached.cache_clear()
