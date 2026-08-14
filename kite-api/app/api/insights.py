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
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.auth import require_admin
from app.insights import (
    analog_finder,
    breadth,
    calendar_content,
    concentration,
    cross_asset,
    macro,
    regime as regime_mod,
    rs_rank,
    scores as scores_mod,
    sector_breadth,
    sector_constituents,
    sector_rs,
    stock_metrics,
    stress,
    subgroups,
    watchlists,
    zerodha_sectors,
)
from app.insights.reading import clear_all_caches, get_market_reading

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


# ---------- admin cache lifecycle ----------

@router.post("/cache/clear")
async def clear_cache_endpoint(user: dict = Depends(require_admin)) -> dict:
    """Drop every insight-engine cache (in-memory lru + on-disk pkl) so the
    next read rebuilds from the freshest panels.

    Admin-only: this is the one mutating route on an otherwise public,
    read-only surface. It exists so a data refresh (e.g. after the daily
    pipeline appends new EOD rows) can be forced without a redeploy. The
    caches are per-process, so this clears the caches of the worker that
    serves the request; single-worker deploys refresh fully in one call.
    """
    clear_all_caches()
    return {"status": "cleared"}


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
    universe: str = Query(
        "nse500",
        description="Universe scope: nse500 (default), nifty250, nifty100, nifty50",
    ),
) -> dict:
    """Breadth metrics over the last `days` trading days.

    Optionally restrict to a subset of metrics via `?metrics=col1,col2`.
    Available columns: pct_above_21dma, pct_above_50dma, pct_above_100dma,
    pct_above_200dma, avg_dist_from_200dma, ad_diff_pct, cumulative_ad,
    mcclellan_osc, mcclellan_sum, new_52w_highs_pct, new_52w_lows_pct,
    net_new_highs_pct, dispersion, n_active.
    """
    _set_cache(response)
    if universe not in breadth.BREADTH_UNIVERSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown universe {universe!r}. "
                   f"Available: {list(breadth.BREADTH_UNIVERSES)}",
        )
    panel = breadth.get_breadth_panel(universe)
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


@router.get("/macro/timeseries")
async def macro_timeseries(
    response: Response,
    days: int = Query(252, ge=20, le=4000),
    metrics: Optional[str] = Query(
        None,
        description="Comma-separated metric names. Default: all. "
                    "Available: vix_close, vix_zscore_60d, vix_zscore_252d, "
                    "vix_roc_5d, vix_above_20, sector_pct_above_50dma, "
                    "sector_pct_above_200dma, sector_breadth_st_lt, "
                    "sector_dispersion_20d",
    ),
) -> dict:
    """Macro (VIX + sector-index breadth) metrics over the last `days`
    trading days. Same shape as the breadth/stress timeseries."""
    _set_cache(response)
    panel = macro.get_macro_panel()
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


@router.get("/concentration/timeseries")
async def concentration_timeseries(
    response: Response,
    days: int = Query(252, ge=20, le=4000),
) -> dict:
    """Cap-weighted vs equal-weighted Nifty 50 spread history (narrow-
    vs-broad tape). Columns are fixed: cap_ret_pct, eq_ret_pct,
    cap_vs_equal_spread_pp, spread_20d_avg_pp."""
    _set_cache(response)
    panel = concentration.compute_concentration_panel()
    if panel.empty:
        return {"index": [], "data": {}}
    sub = panel.tail(days)
    return {
        "index": [d.isoformat() for d in sub.index],
        "data": {col: [_jsonable(v) for v in sub[col].values] for col in sub.columns},
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


# ---------- stock-level screener + detail ----------

# Fields dropped from the screener row to hold the ~500-row payload under the
# 500 KB budget. All are either (a) shown only on the detail page — which uses
# the full, undropped row — or (b) trivially derivable client-side:
#   - absolute rupee DMA / ATR levels: UI reads the % distances + ATR%
#   - above_*dma booleans: sign of the matching dist_*dma_pct
#   - rank_21d_ago: rank + rank_delta_21d
#   - raw score inputs (slopes, 5d/positive-week percentiles, up/down vol,
#     6m drawdown, one annualized-vol series): summarised by the composite
#     Trend / Extension / Volume / Consistency scores, which ARE included.
_SCREENER_ROW_DROP = (
    "date",
    "sma_20", "sma_50", "sma_100", "sma_200", "atr_14",
    "above_20dma", "above_50dma", "above_100dma", "above_200dma",
    "rank_21d_ago",
    "slope_50dma_20d", "slope_200dma_20d",
    "vol_20d_annualized",
    "ret_5d_pctile_1y", "pct_positive_weeks_6m",
    "updown_vol_ratio_20d", "max_drawdown_6m_pct",
)


def _compact(v):
    """JSON-safe + float-trimmed. Rounds every float to 4 decimals so the
    ~500-row screener payload stays small; scores/percentiles already carry
    ≤2 decimals upstream, returns are ratios where 4dp = 0.01% resolution."""
    if isinstance(v, dict):
        return {k: _compact(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_compact(x) for x in v]
    v = _jsonable(v)
    if isinstance(v, float):
        return round(v, 4)
    return v


def _build_row(sym: str, m, rs_entry, sc, sectors: tuple[str, ...],
               zerodha_sector: Optional[str] = None,
               super_sector: Optional[str] = None,
               drop: tuple[str, ...] = ()) -> dict:
    """Zip one stock's metrics + RS entry + scores into a flat row.

    `symbol`/`date` from the sub-records are deduped; `sectors` is the NSE
    index-basket reverse-mapping list (may be empty for names outside every
    basket); `zerodha_sector` is the single canonical Zerodha sector (~100%
    tracked coverage); `super_sector` is the coarser 15-bucket study rollup."""
    row = m.to_dict()
    if rs_entry is not None:
        rd = rs_entry.to_dict()
        rd.pop("symbol", None)
        row.update(rd)
    if sc is not None:
        sd = sc.to_dict()
        sd.pop("symbol", None)
        row.update(sd)
    for k in drop:
        row.pop(k, None)
    row["sectors"] = list(sectors)
    row["zerodha_sector"] = zerodha_sector
    row["super_sector"] = super_sector
    return _compact(row)


@router.get("/screener")
async def screener_endpoint(
    response: Response,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest."),
) -> dict:
    """One payload zipping the per-stock feature frame, RS ranking, and
    composite scores/tags for the whole NSE 500 as of `date`.

    Filtering and sorting are client-side (500 rows is trivial in-browser).
    Degrades to an empty row list with `data_available=False` when the
    stock-metrics panel is unprovisioned (prod before the founder upload) —
    never 500s on missing data."""
    _set_cache(response)
    asof = _parse_date(date)
    metrics = stock_metrics.get_stock_metrics(asof)
    if not metrics:
        return {"asof": None, "data_available": False, "rows": []}

    rs_table = rs_rank.get_rs_table(asof)
    all_scores = scores_mod.get_scores(asof)
    sym_sectors = sector_constituents.get_symbol_to_sectors()
    z_sectors = zerodha_sectors.get_symbol_to_sector()
    z_super = zerodha_sectors.get_symbol_to_super_sector()
    asof_date = next(iter(metrics.values())).date

    rows = [
        _build_row(sym, m, rs_table.get(sym), all_scores.get(sym),
                   sym_sectors.get(sym, ()), z_sectors.get(sym),
                   z_super.get(sym), drop=_SCREENER_ROW_DROP)
        for sym, m in metrics.items()
    ]
    return {"asof": asof_date, "data_available": True, "rows": rows}


def _rs_rank_history(symbol: str, asof: Optional[pd.Timestamp],
                     dates: list[str], step: int = 21) -> list[dict]:
    """Coarse (monthly) RS-rank history for the detail-page sparkline.

    Per-date RS ranking is a full-universe cross-sectional build (~240ms
    cold each, then pkl-cached). Sampling every `step` (~21) trading days
    keeps this to ~12 builds for a year; the sampled per-date RS tables are
    shared/cached across every stock page, so only the first detail request
    after a cache clear pays the build cost. Documented as a coarse monthly
    series, not a daily one."""
    if not dates:
        return []
    sampled = dates[::step]
    if dates[-1] not in sampled:
        sampled.append(dates[-1])
    out: list[dict] = []
    for d in sampled:
        table = rs_rank.get_rs_table(pd.Timestamp(d))
        entry = table.get(symbol)
        if entry is None or entry.rank is None:
            continue
        out.append({"date": d, "rank": entry.rank,
                    "percentile": round(entry.percentile, 2)
                    if entry.percentile is not None else None})
    return out


def _sector_peers(symbol: str, rs_table: dict, sectors: tuple[str, ...],
                  limit: int = 5) -> list[dict]:
    """Top-`limit` sector siblings by RS rank (strongest first), excluding
    the stock itself. Uses the symbol's first (alphabetical) index basket."""
    if not sectors:
        return []
    primary = sectors[0]
    try:
        sector = sector_constituents.get_sector(primary)
    except KeyError:
        return []
    cand = [
        (s, rs_table[s].rank)
        for s in sector.symbols
        if s != symbol and s in rs_table and rs_table[s].rank is not None
    ]
    cand.sort(key=lambda x: x[1])
    return [{"symbol": s, "rank": rk, "sector": primary} for s, rk in cand[:limit]]


@router.get("/stocks/{symbol}")
async def stock_detail_endpoint(
    response: Response,
    symbol: str,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest."),
) -> dict:
    """Everything the screener has for one stock plus detail-page timeseries:
    1y of close + 50/200-DMA + volume ratio, and a coarse (monthly) RS-rank
    history for the sparkline. Score history is intentionally omitted — a
    per-date score is a full-universe rebuild, too costly to serialise here;
    the page shows current scores. Peer strip = top-5 sector siblings by RS.

    404 on an unknown symbol; empty `data_available=False` payload when the
    panel is unprovisioned."""
    _set_cache(response)
    asof = _parse_date(date)
    metrics = stock_metrics.get_stock_metrics(asof)
    if not metrics:
        return {"symbol": symbol, "data_available": False, "row": None,
                "series": {}, "rs_rank_history": [], "peers": []}
    if symbol not in metrics:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown symbol {symbol!r}. Valid universe is the NSE 500 "
                   f"(see /api/insights/screener for the full list).",
        )

    rs_table = rs_rank.get_rs_table(asof)
    all_scores = scores_mod.get_scores(asof)
    sym_sectors = sector_constituents.get_symbol_to_sectors()
    sectors = sym_sectors.get(symbol, ())

    row = _build_row(symbol, metrics[symbol], rs_table.get(symbol),
                     all_scores.get(symbol), sectors,
                     zerodha_sectors.get_sector_for(symbol),
                     zerodha_sectors.get_super_sector_for(symbol))
    series = stock_metrics.get_price_dma_volume_series(symbol, asof)
    history = _rs_rank_history(symbol, asof, series.get("dates", []))
    peers = _sector_peers(symbol, rs_table, sectors)

    return {
        "symbol": symbol,
        "data_available": True,
        "asof": metrics[symbol].date,
        "row": row,
        "series": _compact(series),
        "rs_rank_history": history,
        "peers": peers,
    }


@router.get("/movers")
async def movers_endpoint(
    response: Response,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest."),
) -> dict:
    """Small aggregates for the Pulse enrichment cards (C6): fresh 52-week
    highs / lows (count + top names) and the biggest 21-day RS-rank improvers.

    Deliberately lean — derived directly from the engine contracts so
    MarketReading stays free of the full per-stock table. Fresh highs use the
    engine's `fresh_52w_high` flag; fresh lows are close at the trailing-year
    minimum (`dist_52w_low_pct ≈ 0`). Named lists are ordered by RS strength
    (highs strongest-first, lows weakest-first). RS improvers come from the
    inflection cohort and are OBSERVATION-ONLY per the validity study —
    rank change is a fact, no forward-return claim attaches."""
    _set_cache(response)
    asof = _parse_date(date)
    metrics = stock_metrics.get_stock_metrics(asof)
    if not metrics:
        return {"asof": None, "data_available": False,
                "fresh_highs": {"count": 0, "names": []},
                "fresh_lows": {"count": 0, "names": []},
                "rs_improvers": []}

    rs_table = rs_rank.get_rs_table(asof)
    sym_sectors = sector_constituents.get_symbol_to_sectors()
    asof_date = next(iter(metrics.values())).date

    def _rank(sym):
        e = rs_table.get(sym)
        return e.rank if (e and e.rank is not None) else 10_000

    def _name(sym, m):
        return _compact({
            "symbol": sym, "close": m.close, "ret_1d": m.ret_1d,
            "rank": rs_table[sym].rank if sym in rs_table else None,
            "sectors": list(sym_sectors.get(sym, ())),
        })

    fresh_highs = [s for s, m in metrics.items() if m.fresh_52w_high]
    fresh_lows = [s for s, m in metrics.items()
                  if m.dist_52w_low_pct is not None and m.dist_52w_low_pct <= 1e-4]
    highs_top = sorted(fresh_highs, key=_rank)[:5]
    lows_top = sorted(fresh_lows, key=_rank, reverse=True)[:5]

    improvers = rs_rank.get_live_inflection_cohort(asof, top_n=5)

    return {
        "asof": asof_date,
        "data_available": True,
        "fresh_highs": {"count": len(fresh_highs),
                        "names": [_name(s, metrics[s]) for s in highs_top]},
        "fresh_lows": {"count": len(fresh_lows),
                       "names": [_name(s, metrics[s]) for s in lows_top]},
        "rs_improvers": [
            _compact({"symbol": e.symbol, "rank": e.rank,
                      "rank_21d_ago": e.rank_21d_ago,
                      "rank_delta_21d": e.rank_delta_21d,
                      "sectors": list(sym_sectors.get(e.symbol, ()))})
            for e in improvers
        ],
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


# ---------- cross-asset ----------

@router.get("/cross-asset")
async def cross_asset_endpoint(response: Response) -> dict:
    """Per-asset cross-asset feature snapshot (close, z-scores, ROCs,
    distance-from-200DMA, percentile). India 10y is the only series
    currently sourced; USDINR / gold / US 10y / crude are registered
    but `data_available=False` pending data sourcing — see
    `app/insights/cross_asset.py` for the registry."""
    _set_cache(response)
    try:
        snap = cross_asset.get_cross_asset_snapshot()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {a: e.to_dict() for a, e in snap.items()}


# ---------- anniversary / calendar ----------

@router.get("/calendar/on-this-day")
async def calendar_on_this_day(
    response: Response,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest reading date."),
) -> dict:
    """For the given date, return anniversaries at 1/3/5/10 years back
    annotated with regime + stress + any matching curated event tag.
    Used by the premarket note's on_this_day learn-moment."""
    _set_cache(response)
    asof = _parse_date(date)
    if asof is None:
        # Use latest stress-panel date as 'today' for the lookback
        panel = stress.compute_stress_panel()
        asof = panel.index.max() if not panel.empty else pd.Timestamp.today()
    try:
        anns = calendar_content.get_on_this_day(asof)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "asof": asof.isoformat(),
        "anniversaries": {str(years): snap.to_dict()
                          for years, snap in anns.items()},
    }


@router.get("/calendar/seasonality")
async def calendar_seasonality(
    response: Response,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest panel date."),
) -> dict:
    """Historical calendar-month (and ISO-week) Nifty return profile for the
    as-of date: median / middle-half range / % positive years / n.

    Descriptive-only historical observation — with ~16 years per month this
    cannot clear the forward-return validity bar, so it carries no forecast.
    Degrades to a null profile when the Nifty panel is unprovisioned."""
    _set_cache(response)
    asof = _parse_date(date)
    try:
        profile = calendar_content.get_seasonality(asof)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "asof": profile.asof.isoformat(),
        "data_available": profile.month is not None,
        "seasonality": profile.to_dict(),
    }


@router.get("/calendar/pre-event")
async def calendar_pre_event(
    response: Response,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest panel date."),
    window_days: int = Query(7, ge=1, le=90, description="Look-ahead window in days."),
) -> dict:
    """Curated events falling within the next `window_days`, each attached to
    the historical Nifty move around past events of the same type (budget /
    RBI / election). The curated file holds only past events by design, so
    `upcoming` is empty until forward-dated events are added manually —
    documented in `app/insights/calendar_content.py`."""
    _set_cache(response)
    asof = _parse_date(date)
    if asof is None:
        panel = stress.compute_stress_panel()
        asof = panel.index.max() if not panel.empty else pd.Timestamp.today()
    try:
        upcoming = calendar_content.get_pre_event(asof, window_days=window_days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "asof": asof.isoformat(),
        "window_days": window_days,
        "upcoming": [e.to_dict() for e in upcoming],
    }


# ---------- sector subgroups ----------

@router.get("/subgroups")
async def subgroups_endpoint(
    response: Response,
    date: Optional[str] = Query(None, description="As-of date, ISO YYYY-MM-DD. Default: latest."),
) -> dict:
    """Sector-subgroup snapshot (PSU vs private banks, large vs mid pharma,
    auto OEMs vs ancillaries, etc.) and the pair-level 60d RS spreads.
    See `data/static/`-style notes in `app/insights/subgroups.py` for
    membership definitions."""
    _set_cache(response)
    asof = _parse_date(date)
    try:
        snaps = subgroups.get_subgroup_snapshot(asof)
        spreads = subgroups.get_sibling_spreads(asof)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "subgroups": {k: v.to_dict() for k, v in snaps.items()},
        "sibling_spreads": [s.to_dict() for s in spreads],
    }


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
