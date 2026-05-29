"""Historical analog finder — "When did the market last look like this?"

For any date, finds the K most-similar historical days based on a small
feature vector (breadth + VIX + drawdown + dispersion), then reports
forward Nifty 50 returns from each analog. This is the killer hook for
the Daily Quant Note: instead of "today the VIX is at the 85th percentile
and breadth is at 51%", we can say "today's reading most resembles
2017-09-04 and 2012-03-19 — Nifty added 5.2% over the next 20 days from
the average analog."

Mechanics:
  1. Build feature matrix per date from existing engines (breadth, macro,
     stress, drawdown).
  2. Z-score each feature using all-history mean/std for consistent scale.
  3. For a target date, compute Euclidean distance to every other date.
  4. EXCLUDE dates within ±60 calendar days of target (avoid trivial
     near-duplicate neighbors) and exclude future dates.
  5. Return top K matches sorted ascending by distance.
  6. For each match, attach forward Nifty 50 returns at 5/20/60/120d.

Aggregate distribution helper (`get_analog_distribution`) returns
median + IQR + 5/95 percentiles of forward returns across the top K —
this is the "fan chart" content for the dashboard.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.insights.breadth import get_breadth_panel
from app.insights.macro import get_macro_panel
from app.insights.stress import compute_stress_panel


# Features used for matching. Each gets z-scored before distance is computed.
# Keeping the list small (5 features) — KNN gets noisy with too many dims.
FEATURE_COLUMNS = [
    "pct_above_200dma",   # broad-market breadth
    "vix_close",           # absolute vol regime
    "vix_zscore_252d",     # relative vol regime
    "nifty_drawdown_pct",  # where in the cycle (from stress panel)
    "dispersion_z",        # cross-sectional stress (from stress panel)
]

# Exclude analog dates within this many calendar days of the target.
# Prevents trivial near-duplicate neighbors (markets don't change much
# day-to-day).
EXCLUSION_DAYS = 60

# Forward-return horizons (trading days)
FORWARD_HORIZONS = [5, 20, 60, 120]


@dataclass
class AnalogMatch:
    """One historical date that matched the target."""
    match_date: pd.Timestamp
    distance: float
    # Forward returns from the match date — may be None if the match is so
    # recent that forward window doesn't exist
    fwd_return_5d: float | None
    fwd_return_20d: float | None
    fwd_return_60d: float | None
    fwd_return_120d: float | None
    # The actual feature values at the match — useful for commentary
    pct_above_200dma: float | None
    vix_close: float | None
    nifty_drawdown_pct: float | None
    stress_score: float | None  # not in match vector but useful for narrative

    def to_dict(self) -> dict:
        d = asdict(self)
        d["match_date"] = (
            self.match_date.isoformat()
            if isinstance(self.match_date, pd.Timestamp) else self.match_date
        )
        return d


@dataclass
class AnalogDistribution:
    """Aggregate forward-return distribution across top-K analogs."""
    target_date: pd.Timestamp
    k: int
    horizon_days: int
    # Distribution across the K matches' forward returns at this horizon
    median: float | None
    mean: float | None
    p5: float | None
    p25: float | None
    p75: float | None
    p95: float | None
    n_with_forward_return: int  # how many of the K had full forward windows

    def to_dict(self) -> dict:
        d = asdict(self)
        d["target_date"] = (
            self.target_date.isoformat()
            if isinstance(self.target_date, pd.Timestamp) else self.target_date
        )
        return d


def _indices_dir() -> Path:
    settings = get_settings()
    external = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
    if external.exists():
        return external
    return settings.data_dir / "indices_data_historical"


@lru_cache(maxsize=1)
def _nifty_close() -> pd.Series:
    p = _indices_dir() / "NIFTY_50.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    return (pd.read_csv(p, parse_dates=["date"])
              .set_index("date")["close"]
              .sort_index())


@lru_cache(maxsize=1)
def _build_feature_panel() -> pd.DataFrame:
    """Build the per-date feature matrix used for KNN matching."""
    breadth = get_breadth_panel()
    macro = get_macro_panel()
    stress = compute_stress_panel()

    # Align all to the breadth index
    idx = breadth.index
    macro_a = macro.reindex(idx).ffill()
    stress_a = stress.reindex(idx).ffill()

    df = pd.DataFrame(index=idx)
    df["pct_above_200dma"] = breadth["pct_above_200dma"]
    df["vix_close"] = macro_a["vix_close"]
    df["vix_zscore_252d"] = macro_a["vix_zscore_252d"]
    df["nifty_drawdown_pct"] = stress_a["nifty_drawdown_pct"]
    df["dispersion_z"] = stress_a["dispersion_z"]
    df["stress_score"] = stress_a["score"]  # carried for snapshot output, NOT in distance
    return df


@lru_cache(maxsize=1)
def _standardize_features() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Return (z_scored_features, means, stds) over all history.

    Z-scoring uses the FULL history's mean/std so the feature scale is
    stable. This is fine because we're not trying to predict — we're
    measuring similarity in feature space.
    """
    df = _build_feature_panel()
    features = df[FEATURE_COLUMNS]
    means = features.mean()
    stds = features.std()
    z = (features - means) / stds
    return z, means, stds


@lru_cache(maxsize=1)
def _nifty_forward_returns() -> pd.DataFrame:
    """Pre-compute Nifty forward returns at each horizon. Aligned to the
    feature panel's index so we can directly look up match dates."""
    feat = _build_feature_panel()
    nifty = _nifty_close().reindex(feat.index).ffill()
    out = {}
    for h in FORWARD_HORIZONS:
        out[h] = nifty.pct_change(h, fill_method=None).shift(-h)
    return pd.DataFrame(out)


def find_analogs(
    asof: pd.Timestamp | None = None,
    k: int = 5,
    exclude_days: int = EXCLUSION_DAYS,
) -> list[AnalogMatch]:
    """Find the K historical dates most-similar to `asof` (default: latest).

    Returns top K sorted ascending by Euclidean distance in standardized
    feature space.
    """
    z, _, _ = _standardize_features()
    feat = _build_feature_panel()
    fwd = _nifty_forward_returns()

    if asof is None:
        asof = z.dropna().index.max()
    asof = pd.Timestamp(asof)
    valid = z.index[z.index <= asof]
    if valid.empty:
        return []
    asof = valid.max()

    target = z.loc[asof]
    if target.isna().any():
        return []  # not enough history at target date

    # Compute distances. Drop rows with any NaN feature, dates within
    # exclusion window of target, and any future dates.
    candidates = z.dropna()
    candidates = candidates[candidates.index <= asof]
    mask = (candidates.index < asof - pd.Timedelta(days=exclude_days)) | \
           (candidates.index > asof + pd.Timedelta(days=exclude_days))
    candidates = candidates[mask]

    if candidates.empty:
        return []

    # Euclidean distance
    diff = candidates.values - target.values
    distances = np.sqrt((diff ** 2).sum(axis=1))
    ranked = pd.Series(distances, index=candidates.index).sort_values()

    out: list[AnalogMatch] = []
    for match_date, dist in ranked.head(k).items():
        f = feat.loc[match_date]
        out.append(AnalogMatch(
            match_date=match_date,
            distance=float(dist),
            fwd_return_5d=_lookup_fwd(fwd, match_date, 5),
            fwd_return_20d=_lookup_fwd(fwd, match_date, 20),
            fwd_return_60d=_lookup_fwd(fwd, match_date, 60),
            fwd_return_120d=_lookup_fwd(fwd, match_date, 120),
            pct_above_200dma=_safe_float(f.get("pct_above_200dma")),
            vix_close=_safe_float(f.get("vix_close")),
            nifty_drawdown_pct=_safe_float(f.get("nifty_drawdown_pct")),
            stress_score=_safe_float(f.get("stress_score")),
        ))
    return out


def get_analog_distribution(
    asof: pd.Timestamp | None = None,
    k: int = 20,
) -> dict[int, AnalogDistribution]:
    """For each forward horizon, return the cross-K distribution of forward
    returns. The "fan chart" content: median + IQR + 5/95 percentiles."""
    matches = find_analogs(asof, k=k)
    if not matches:
        return {}

    target_date = matches[0].match_date  # placeholder; replaced below
    if asof is None:
        z, _, _ = _standardize_features()
        target_date = z.dropna().index.max()
    else:
        target_date = pd.Timestamp(asof)

    out: dict[int, AnalogDistribution] = {}
    for h in FORWARD_HORIZONS:
        attr = f"fwd_return_{h}d"
        rets = [getattr(m, attr) for m in matches if getattr(m, attr) is not None]
        if not rets:
            out[h] = AnalogDistribution(
                target_date=target_date, k=k, horizon_days=h,
                median=None, mean=None, p5=None, p25=None, p75=None, p95=None,
                n_with_forward_return=0,
            )
            continue
        arr = np.array(rets)
        out[h] = AnalogDistribution(
            target_date=target_date, k=k, horizon_days=h,
            median=float(np.median(arr)),
            mean=float(arr.mean()),
            p5=float(np.percentile(arr, 5)),
            p25=float(np.percentile(arr, 25)),
            p75=float(np.percentile(arr, 75)),
            p95=float(np.percentile(arr, 95)),
            n_with_forward_return=len(arr),
        )
    return out


# ---------- helpers ----------

def _lookup_fwd(fwd: pd.DataFrame, date: pd.Timestamp, horizon: int) -> float | None:
    if date not in fwd.index or horizon not in fwd.columns:
        return None
    v = fwd.loc[date, horizon]
    return None if pd.isna(v) else float(v)


def _safe_float(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def clear_cache() -> None:
    _nifty_close.cache_clear()
    _build_feature_panel.cache_clear()
    _standardize_features.cache_clear()
    _nifty_forward_returns.cache_clear()
