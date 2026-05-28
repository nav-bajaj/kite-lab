"""Public insights API — read-only endpoints serving the Insight Engine
data to the web dashboard (and any future client).

All routes:
  - Public (no auth)
  - GET only
  - Cache-friendly (Cache-Control: public, max-age=900) — the upstream
    panels are EOD-refresh anyway; 15-minute browser cache reduces load
    during market hours

Mounted at `/api/insights/*` from main.py.

Coverage in v1:
  /reading                  — full MarketReading bundle
  /stress/timeseries        — stress score panel slice for charting
  /breadth/timeseries       — breadth + macro metrics panel slice
  /sectors                  — sector RS + breadth (all 10/12 sectors)
  /sectors/{name}           — drill into one sector
  /analogs                  — top-K analog matches + fwd-return distribution
  /watchlists               — all five quant-driven watchlists
  /watchlists/{name}        — drill into one list
  /regime/history           — historical regime episode table

Notes archive (storage layer) and note rendering endpoints are deferred
to a follow-up — currently the CLI is the only producer of notes.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Response

from app.insights import (
    analog_finder,
    breadth,
    concentration,
    macro,
    regime as regime_mod,
    sector_breadth,
    sector_rs,
    stress,
    watchlists,
)
from app.insights.reading import get_market_reading

router = APIRouter(prefix="/api/insights", tags=["insights"])

# Default cache header — 15 minutes (matches the dashboard's intraday cadence
# target). EOD pipeline refreshes the underlying panels once a day; the
# server-side lru_cache makes subsequent hits ~free.
CACHE_TTL_SECONDS = 900


def _set_cache(response: Response, ttl: int = CACHE_TTL_SECONDS) -> None:
    response.headers["Cache-Control"] = f"public, max-age={ttl}"


def _parse_date(date_str: Optional[str]) -> Optional[pd.Timestamp]:
    if not date_str:
        return None
    try:
        return pd.Timestamp(date_str)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date {date_str!r}; expected ISO format YYYY-MM-DD",
        )


# ---------- top-level reading ----------

@router.get("/reading")
async def reading_endpoint(
    response: Response,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest."),
) -> dict:
    """Full MarketReading for `date`. Includes regime, stress, sector views,
    analog matches, conditional distributions, watchlists — everything the
    Daily Quant Note has access to."""
    _set_cache(response)
    asof = _parse_date(date)
    try:
        r = get_market_reading(asof)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return r.to_dict()


# ---------- timeseries endpoints ----------

@router.get("/stress/timeseries")
async def stress_timeseries(
    response: Response,
    days: int = Query(252, ge=20, le=4000, description="Trailing trading days"),
) -> dict:
    """Stress score + components over the last `days` trading days."""
    _set_cache(response)
    panel = stress.compute_stress_panel()
    if panel.empty:
        return {"index": [], "data": {}}
    sub = panel.tail(days)
    return {
        "index": [d.isoformat() for d in sub.index],
        "data": {
            col: [_jsonable(v) for v in sub[col].values]
            for col in [
                "score", "score_percentile",
                "vix_pctile_component", "drawdown_component",
                "below_200dma_component", "dispersion_component",
                "vix_close", "nifty_drawdown_pct",
                "pct_above_200dma", "dispersion_z",
            ]
            if col in sub.columns
        },
    }


@router.get("/breadth/timeseries")
async def breadth_timeseries(
    response: Response,
    days: int = Query(252, ge=20, le=4000),
    metrics: Optional[str] = Query(
        None,
        description="Comma-separated metric names. Default: all. "
                    "e.g. 'pct_above_200dma,mcclellan_osc'",
    ),
) -> dict:
    """Breadth metrics over the last `days` trading days.

    Optionally restrict to a subset of metrics via `?metrics=col1,col2`.
    Available columns: pct_above_50dma, pct_above_100dma, pct_above_200dma,
    ad_diff_pct, cumulative_ad, mcclellan_osc, new_52w_highs_pct,
    new_52w_lows_pct, net_new_highs_pct, dispersion, n_active.
    """
    _set_cache(response)
    panel = breadth.get_breadth_panel()
    if panel.empty:
        return {"index": [], "data": {}}
    sub = panel.tail(days)
    if metrics:
        wanted = [m.strip() for m in metrics.split(",") if m.strip()]
        missing = set(wanted) - set(sub.columns)
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown metrics: {sorted(missing)}. "
                       f"Available: {sorted(sub.columns)}",
            )
        cols = wanted
    else:
        cols = list(sub.columns)
    return {
        "index": [d.isoformat() for d in sub.index],
        "data": {col: [_jsonable(v) for v in sub[col].values] for col in cols},
    }


# ---------- sectors ----------

@router.get("/sectors")
async def sectors_endpoint(
    response: Response,
    date: Optional[str] = Query(None),
) -> dict:
    """Full sector view: per-sector breadth (constituents-level) + RS ranking +
    60-day leaderboard for `date` (default: latest)."""
    _set_cache(response)
    asof = _parse_date(date)
    breadth_snaps = sector_breadth.get_sector_breadth_snapshot(asof)
    rs_snaps = sector_rs.get_sector_rs_snapshot(asof)
    leaderboard = sector_rs.get_leaderboard("60d", asof)

    return {
        "date": next(iter(breadth_snaps.values())).date.isoformat() if breadth_snaps else None,
        "sector_breadth": {k: v.to_dict() for k, v in breadth_snaps.items()},
        "sector_rs":      {k: v.to_dict() for k, v in rs_snaps.items()},
        "leaderboard_60d": [s.to_dict() for s in leaderboard],
    }


@router.get("/sectors/{name}")
async def sector_drill(
    response: Response,
    name: str,
    date: Optional[str] = Query(None),
) -> dict:
    """Per-sector drill: breadth snapshot + RS snapshot + a year of
    historical breadth+RS time series for charting."""
    _set_cache(response)
    asof = _parse_date(date)
    breadth_snaps = sector_breadth.get_sector_breadth_snapshot(asof)
    rs_snaps = sector_rs.get_sector_rs_snapshot(asof)

    if name not in breadth_snaps and name not in rs_snaps:
        raise HTTPException(status_code=404, detail=f"Unknown sector {name!r}")

    # Per-sector time series (last year) — pull from the panels
    out_ts: dict = {}
    bp = sector_breadth.compute_sector_breadth_panel()
    if name in bp.columns.get_level_values("sector"):
        sub = bp[name].tail(252)
        out_ts["breadth"] = {
            "index": [d.isoformat() for d in sub.index],
            "data": {col: [_jsonable(v) for v in sub[col].values]
                     for col in sub.columns},
        }
    rsp = sector_rs.compute_sector_rs_panel()
    if name in rsp.columns.get_level_values("sector"):
        sub = rsp[name].tail(252)
        # Flatten (window, metric) → "window.metric"
        flat_cols = {f"{w}_{m}": sub[(w, m)] for w, m in sub.columns}
        out_ts["rs"] = {
            "index": [d.isoformat() for d in sub.index],
            "data": {k: [_jsonable(x) for x in v.values] for k, v in flat_cols.items()},
        }

    return {
        "sector": name,
        "breadth": breadth_snaps[name].to_dict() if name in breadth_snaps else None,
        "rs":      rs_snaps[name].to_dict() if name in rs_snaps else None,
        "timeseries": out_ts,
    }


# ---------- analogs ----------

@router.get("/analogs")
async def analogs_endpoint(
    response: Response,
    date: Optional[str] = Query(None),
    k: int = Query(20, ge=1, le=50),
) -> dict:
    """Top-K analog matches for `date` plus the forward-return distribution
    aggregated across the top K."""
    _set_cache(response)
    asof = _parse_date(date)
    matches = analog_finder.find_analogs(asof, k=k)
    dist = analog_finder.get_analog_distribution(asof, k=k)
    return {
        "date": (matches[0].match_date.isoformat() if matches else
                 (asof.isoformat() if asof else None)),
        "k": k,
        "matches": [m.to_dict() for m in matches],
        "distribution": {h: d.to_dict() for h, d in dist.items()},
    }


# ---------- watchlists ----------

@router.get("/watchlists")
async def watchlists_endpoint(
    response: Response,
    date: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=100),
) -> dict:
    """All five quant-driven watchlists for `date`."""
    _set_cache(response)
    asof = _parse_date(date)
    all_lists = watchlists.get_all_watchlists(asof, limit=limit)
    return {
        "date": asof.isoformat() if asof else None,
        "lists": {name: [e.to_dict() for e in entries]
                  for name, entries in all_lists.items()},
    }


@router.get("/watchlists/{name}")
async def watchlist_drill(
    response: Response,
    name: str,
    date: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
) -> dict:
    """Single watchlist with optionally higher limit for the dashboard table view."""
    _set_cache(response)
    asof = _parse_date(date)
    builders = {
        "breakouts":         lambda: watchlists.get_breakouts(asof, limit=limit),
        "rs_leaders":        lambda: watchlists.get_rs_leaders(asof, limit=limit),
        "coiled_springs":    lambda: watchlists.get_coiled_springs(asof, limit=limit),
        "stretched":         lambda: watchlists.get_stretched(asof, limit=limit),
        "recent_breakdowns": lambda: watchlists.get_recent_breakdowns(asof, limit=limit),
    }
    if name not in builders:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown watchlist {name!r}. "
                   f"Available: {sorted(builders.keys())}",
        )
    entries = builders[name]()
    return {
        "name": name,
        "date": asof.isoformat() if asof else None,
        "entries": [e.to_dict() for e in entries],
    }


# ---------- concentration / attribution ----------

@router.get("/concentration")
async def concentration_endpoint(
    response: Response,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest."),
) -> dict:
    """Nifty 50 cap-weighted contribution attribution for the given date.

    Decomposes today's Nifty 50 move into per-constituent contributions
    (`weight * return`), aggregates top-3 / top-5 / Reliance shares, and
    compares cap-weighted vs equal-weighted returns to detect narrow vs
    broad rallies. Weights are loaded from a static factsheet snapshot at
    `data/static/nifty50_weights.csv` — current weights only; not
    historical."""
    _set_cache(response)
    asof = _parse_date(date)
    try:
        r = concentration.compute_concentration(asof)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return r.to_dict()


# ---------- regime history ----------

@router.get("/regime/history")
async def regime_history(response: Response) -> dict:
    """Episode-level regime history — one row per consecutive run of a
    regime. Useful for timeline visualisations and for grounding 'this
    phase typically lasts X days' commentary."""
    _set_cache(response)
    history = regime_mod.get_regime_history()
    if history.empty:
        return {"episodes": []}
    return {
        "episodes": [
            {
                "regime": str(row["regime"]),
                "start": row["start"].isoformat(),
                "end": row["end"].isoformat(),
                "days": int(row["days"]),
            }
            for _, row in history.iterrows()
        ],
    }


# ---------- helpers ----------

def _jsonable(v):
    """Convert numpy/pandas scalar to JSON-safe Python primitive. None for NaN."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):
        return v.item()
    return v
