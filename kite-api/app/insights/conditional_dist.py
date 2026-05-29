"""Conditional forward-return distributions.

Where `analog_finder` returns the top-K closest historical neighbors,
this module aggregates ALL historical dates that share a categorical
state with today and reports the forward-return distribution for that
bucket. Coarser than KNN but more statistically robust (n is in the
hundreds/thousands per bucket).

Buckets:
  by_regime          one of REGIMES (TREND_BULL / DRIFT / STRETCHED / STRESS)
  by_stress_quintile 0 (calmest 20%) .. 4 (most stressed 20%)
  by_regime_x_stress (regime, stress_quintile) — joint conditioning

For each bucket and forward horizon, returns:
  n, mean, median, p5, p25, p75, p95, and pct_positive (fraction of
  observations where the forward return was > 0).

Daily Quant Note usage example:
  "Markets are in DRIFT regime with stress at the 60th percentile.
  Historically (n=187 similar days), Nifty's median forward 20-day
  return has been +0.4%, with 58% of observations positive and the
  middle half of outcomes falling between -1.8% and +2.7%."
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.insights.regime import REGIMES, compute_regime_panel
from app.insights.stress import compute_stress_panel


FORWARD_HORIZONS = [5, 10, 20, 60, 120]
N_STRESS_QUINTILES = 5


@dataclass
class ConditionalDist:
    """Forward-return distribution for one bucket × one horizon."""
    bucket: str                      # e.g. "regime=DRIFT" or "stress_q=3"
    horizon_days: int
    n: int                           # how many historical observations
    mean: float | None
    median: float | None
    p5: float | None
    p25: float | None
    p75: float | None
    p95: float | None
    pct_positive: float | None       # fraction with fwd return > 0

    def to_dict(self) -> dict:
        return asdict(self)


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
def _build_joint_panel() -> pd.DataFrame:
    """Combine regime, stress score, and Nifty forward returns into one panel."""
    regime_panel = compute_regime_panel()
    stress_panel = compute_stress_panel()
    nifty = _nifty_close()

    idx = regime_panel.index
    stress_a = stress_panel.reindex(idx).ffill()
    nifty_a = nifty.reindex(idx).ffill()

    df = pd.DataFrame(index=idx)
    df["regime"] = regime_panel["regime"]
    df["stress_score"] = stress_a["score"]
    # Stress quintile, computed on all-history score distribution.
    # qcut returns NaN where score is NaN.
    df["stress_quintile"] = pd.qcut(
        stress_a["score"], q=N_STRESS_QUINTILES,
        labels=False, duplicates="drop"
    )

    # Forward Nifty returns at each horizon
    for h in FORWARD_HORIZONS:
        df[f"fwd_{h}d"] = nifty_a.pct_change(h, fill_method=None).shift(-h)
    return df


def _distribution(returns: pd.Series, bucket_label: str, horizon: int) -> ConditionalDist:
    r = returns.dropna()
    if r.empty:
        return ConditionalDist(
            bucket=bucket_label, horizon_days=horizon, n=0,
            mean=None, median=None, p5=None, p25=None, p75=None, p95=None,
            pct_positive=None,
        )
    arr = r.values
    return ConditionalDist(
        bucket=bucket_label,
        horizon_days=horizon,
        n=len(arr),
        mean=float(arr.mean()),
        median=float(np.median(arr)),
        p5=float(np.percentile(arr, 5)),
        p25=float(np.percentile(arr, 25)),
        p75=float(np.percentile(arr, 75)),
        p95=float(np.percentile(arr, 95)),
        pct_positive=float((arr > 0).mean()),
    )


def by_regime(
    horizons: list[int] | None = None,
) -> dict[str, dict[int, ConditionalDist]]:
    """Return {regime → {horizon_days → ConditionalDist}}."""
    panel = _build_joint_panel()
    horizons = horizons or FORWARD_HORIZONS
    out: dict[str, dict[int, ConditionalDist]] = {}
    for r in REGIMES:
        mask = panel["regime"] == r
        out[r] = {
            h: _distribution(panel.loc[mask, f"fwd_{h}d"], f"regime={r}", h)
            for h in horizons
        }
    return out


def by_stress_quintile(
    horizons: list[int] | None = None,
) -> dict[int, dict[int, ConditionalDist]]:
    """Return {quintile (0..4) → {horizon → ConditionalDist}}.

    Quintile 0 = calmest 20% of history, quintile 4 = most stressed 20%.
    """
    panel = _build_joint_panel()
    horizons = horizons or FORWARD_HORIZONS
    out: dict[int, dict[int, ConditionalDist]] = {}
    for q in range(N_STRESS_QUINTILES):
        mask = panel["stress_quintile"] == q
        out[q] = {
            h: _distribution(panel.loc[mask, f"fwd_{h}d"], f"stress_q={q}", h)
            for h in horizons
        }
    return out


def by_regime_x_stress(
    horizons: list[int] | None = None,
) -> dict[tuple[str, int], dict[int, ConditionalDist]]:
    """Return {(regime, stress_quintile) → {horizon → ConditionalDist}}.

    Joint conditioning lets us answer "given we're in DRIFT regime with
    high stress, what historically has come next?" — more specific than
    either condition alone.
    """
    panel = _build_joint_panel()
    horizons = horizons or FORWARD_HORIZONS
    out: dict[tuple[str, int], dict[int, ConditionalDist]] = {}
    for r in REGIMES:
        for q in range(N_STRESS_QUINTILES):
            mask = (panel["regime"] == r) & (panel["stress_quintile"] == q)
            out[(r, q)] = {
                h: _distribution(
                    panel.loc[mask, f"fwd_{h}d"],
                    f"regime={r}, stress_q={q}", h,
                )
                for h in horizons
            }
    return out


def get_today_conditional(asof: pd.Timestamp | None = None) -> dict:
    """Convenience: return the bucket label for today + the matching
    distribution across all horizons.

    Used by the Daily Quant Note to embed historical context:
    "today is REGIME=DRIFT, STRESS_Q=3 → historical fwd 20d median +0.4%".
    """
    panel = _build_joint_panel()
    if asof is None:
        asof = panel.index.max()
    asof = pd.Timestamp(asof)
    valid = panel.index[panel.index <= asof]
    if valid.empty:
        return {}
    asof = valid.max()

    row = panel.loc[asof]
    today_regime = row["regime"]
    today_q = int(row["stress_quintile"]) if pd.notna(row["stress_quintile"]) else None

    by_r = by_regime()
    by_q = by_stress_quintile()
    by_rq = by_regime_x_stress()

    return {
        "date": asof.isoformat(),
        "today_regime": today_regime,
        "today_stress_quintile": today_q,
        "today_stress_score": (float(row["stress_score"])
                               if pd.notna(row["stress_score"]) else None),
        "by_regime": {
            h: by_r.get(today_regime, {}).get(h).to_dict()
            for h in FORWARD_HORIZONS
            if by_r.get(today_regime, {}).get(h) is not None
        },
        "by_stress_quintile": (
            {h: by_q.get(today_q, {}).get(h).to_dict()
             for h in FORWARD_HORIZONS
             if today_q is not None and by_q.get(today_q, {}).get(h) is not None}
            if today_q is not None else {}
        ),
        "by_regime_x_stress": (
            {h: by_rq.get((today_regime, today_q), {}).get(h).to_dict()
             for h in FORWARD_HORIZONS
             if today_q is not None and by_rq.get((today_regime, today_q), {}).get(h) is not None}
            if today_q is not None else {}
        ),
    }


def clear_cache() -> None:
    _nifty_close.cache_clear()
    _build_joint_panel.cache_clear()
