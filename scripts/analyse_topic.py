"""Analyse a content-topic phrase against the insight engine and emit a TopicDossier JSON.

The content factory in ~/finance-content-os reads the dossier as the
verified-data input to its writers. This script is the
"quick-analysis tool" the founder runs before opening a writing
session — it guarantees that any piece grounded in this dossier has
real numbers, not invented ones.

Usage:
    python scripts/analyse_topic.py --topic "defence sector momentum"
    python scripts/analyse_topic.py --topic "rupee weakness this week" --asof 2026-06-01
    python scripts/analyse_topic.py --topic "Reliance share of Nifty move" --slug nifty_reliance_share

By default writes to data/topic_dossiers/<slug>.json. See
data/topic_dossiers/SCHEMA.md for the dossier shape.

Handlers read the LOCAL insight engine, with one exception: `analyse_stock_rs`
reads the live production API (see its docstring for why). Set
MARKETWORKS_API_BASE to point it elsewhere.

Out-of-scope: subgroup analysis (PSU vs private banks etc.) and
anniversary/calendar phrases. Add wrapper functions when those topics
become recurring — per-stock relative strength graduated that way in
2026-08 and is now `analyse_stock_rs`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
KITE_API = REPO_ROOT / "kite-api"
if str(KITE_API) not in sys.path:
    sys.path.insert(0, str(KITE_API))

DOSSIERS_DIR = REPO_ROOT / "data" / "topic_dossiers"


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

@dataclass
class RoutingRule:
    category: str
    keywords: tuple[str, ...]
    handler_name: str          # name resolved against module-level handlers


ROUTING_RULES: list[RoutingRule] = [
    RoutingRule(
        category="sector",
        keywords=(
            "sector", "rotation", "leadership", "leader", "laggard",
            "defence", "defense", "metal", "bank", "fmcg", "it",
            "pharma", "auto", "energy", "realty", "psu", "infra",
            "capital good", "consumer durable", "media",
        ),
        handler_name="analyse_sector",
    ),
    RoutingRule(
        category="currency",
        keywords=(
            "rupee", "usdinr", "dollar", "currency", "gold", "crude",
            "oil", "macro", "fx", "yield", "10y",
        ),
        handler_name="analyse_currency",
    ),
    RoutingRule(
        category="concentration",
        keywords=(
            "reliance", "concentration", "narrow", "index", "nifty move",
            "index move", "top stock", "heavyweight", "weighted",
            "hide", "hides", "hiding",
        ),
        handler_name="analyse_concentration",
    ),
    RoutingRule(
        category="watchlist",
        keywords=(
            "breakout", "52-week", "52 week", "52w", "200-day", "200 day",
            "50-day", "50 day", "trend break", "coiled", "stretched",
            "uptrend", "downtrend", "multi-year", "leader",
        ),
        handler_name="analyse_watchlist",
    ),
    RoutingRule(
        category="regime",
        keywords=(
            "drift", "regime", "trending", "trend", "stress", "volatile",
            "calm", "state of market", "market state",
        ),
        handler_name="analyse_regime",
    ),
    RoutingRule(
        category="stock_rs",
        keywords=(
            "relative strength", "rs rank", "rs score", "rs of",
            "cross-sectional", "cross sectional", "time-series momentum",
            "time series momentum", "stock momentum", "vs the index",
            "against the index",
        ),
        handler_name="analyse_stock_rs",
    ),
]


def route(phrase: str) -> list[RoutingRule]:
    """Return all routing rules whose keywords match the phrase."""
    phrase_lower = phrase.lower()
    matched: list[RoutingRule] = []
    seen: set[str] = set()
    for rule in ROUTING_RULES:
        if any(kw in phrase_lower for kw in rule.keywords):
            if rule.category not in seen:
                matched.append(rule)
                seen.add(rule.category)
    return matched


# ---------------------------------------------------------------------------
# Sector matching helper
# ---------------------------------------------------------------------------

SECTOR_KEYWORD_MAP: dict[str, list[str]] = {
    "NIFTY_DEFENCE":  ["defence", "defense"],
    "NIFTY_METAL":    ["metal"],
    "NIFTY_BANK":     ["bank"],
    "NIFTY_FMCG":     ["fmcg"],
    "NIFTY_IT":       [" it ", "it sector", "tech "],
    "NIFTY_PHARMA":   ["pharma"],
    "NIFTY_AUTO":     ["auto"],
    "NIFTY_ENERGY":   ["energy"],
    "NIFTY_REALTY":   ["realty"],
    "NIFTY_PSU_BANK": ["psu bank", "psu"],
    "NIFTY_INFRA":    ["infra"],
}


def named_sectors_in(phrase: str) -> list[str]:
    """Return the canonical sector indices named in a phrase (best-effort)."""
    phrase_lower = " " + phrase.lower() + " "
    found: list[str] = []
    for symbol, keywords in SECTOR_KEYWORD_MAP.items():
        if any(kw in phrase_lower for kw in keywords):
            found.append(symbol)
    return found


# ---------------------------------------------------------------------------
# Module wrappers
# ---------------------------------------------------------------------------

def _format_pct(value: Optional[float], digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:+.{digits}f}%"


def analyse_sector(phrase: str, asof) -> dict[str, Any]:
    """Sector RS analysis."""
    from app.insights.sector_rs import get_leaderboard, get_sector_rs_snapshot
    leaderboard = get_leaderboard(window="60d", asof=asof) or []
    named = named_sectors_in(phrase)
    verified_facts: list[dict[str, Any]] = []
    data_points: list[dict[str, Any]] = []
    chart_suggestions: list[str] = []
    related: list[str] = []
    claim_verified: bool | str = "not_applicable"
    claim_evidence = ""

    if not leaderboard:
        return {
            "modules_invoked": ["sector_rs"],
            "verified_facts": [],
            "data_points": [],
            "chart_suggestions": [],
            "related_signals": [],
            "claim_verified": "not_applicable",
            "claim_evidence": "Sector RS leaderboard not available",
            "confidence": "low",
        }

    rank_by_sector = {snap.sector: rank for rank, snap in enumerate(leaderboard)}
    top = leaderboard[0]
    bottom = leaderboard[-1]

    # If the phrase named specific sectors, focus on those
    focus_sectors = [s for s in named if s in rank_by_sector]
    if focus_sectors:
        for sector in focus_sectors:
            rank = rank_by_sector[sector]
            snap = leaderboard[rank]
            rs_60d = getattr(snap, "rs_60d", None) or getattr(snap, "rs", None)
            verified_facts.append({
                "fact": f"{sector} 60-day RS: {_format_pct(rs_60d)} (rank {rank + 1} of {len(leaderboard)})",
                "source": "sector_rs",
                "value": rs_60d,
                "context": f"vs Nifty over trailing 60 days",
            })
            data_points.append({
                "label": f"{sector} 60-day RS",
                "value": _format_pct(rs_60d),
                "context": f"rank {rank + 1} of {len(leaderboard)}",
            })
            chart_suggestions.append(
                f"Line chart: {sector} vs NIFTY over trailing 12 months"
            )
        # Claim verification: if the phrase implies leadership for the named sector
        if "lead" in phrase.lower() or "outperform" in phrase.lower() or "momentum" in phrase.lower():
            top_focus = focus_sectors[0]
            rank = rank_by_sector[top_focus]
            claim_verified = rank < 3
            claim_evidence = (
                f"{top_focus} is at rank {rank + 1} of {len(leaderboard)} on 60d RS — "
                f"{'this supports the claim' if rank < 3 else 'this does not support a leadership claim'}"
            )
    else:
        # No specific sector named — just give the leaderboard
        verified_facts.append({
            "fact": f"{top.sector} leads sectors over 60 days: {_format_pct(getattr(top, 'rs_60d', None))}",
            "source": "sector_rs",
            "value": getattr(top, "rs_60d", None),
            "context": "top of leaderboard",
        })
        verified_facts.append({
            "fact": f"{bottom.sector} lags: {_format_pct(getattr(bottom, 'rs_60d', None))}",
            "source": "sector_rs",
            "value": getattr(bottom, "rs_60d", None),
            "context": "bottom of leaderboard",
        })
        data_points.append({
            "label": "Leadership 60d",
            "value": f"{top.sector} {_format_pct(getattr(top, 'rs_60d', None))}",
            "context": "vs Nifty",
        })
        data_points.append({
            "label": "Laggard 60d",
            "value": f"{bottom.sector} {_format_pct(getattr(bottom, 'rs_60d', None))}",
            "context": "vs Nifty",
        })
        chart_suggestions.append("Bar chart: sector RS leaderboard (60d) — green leaders, red laggards")

    # Always add related signals — 2nd-rank sector
    if len(leaderboard) > 1:
        runner = leaderboard[1]
        related.append(
            f"{runner.sector} is also outperforming: {_format_pct(getattr(runner, 'rs_60d', None))} 60d RS"
        )

    return {
        "modules_invoked": ["sector_rs"],
        "verified_facts": verified_facts,
        "data_points": data_points,
        "chart_suggestions": chart_suggestions,
        "related_signals": related,
        "claim_verified": claim_verified,
        "claim_evidence": claim_evidence,
        "confidence": "high" if verified_facts else "low",
    }


def analyse_currency(phrase: str, asof) -> dict[str, Any]:
    """Cross-asset (USDINR, gold, crude, india_10y)."""
    from app.insights.cross_asset import get_cross_asset_snapshot
    snapshot = get_cross_asset_snapshot() or {}
    verified_facts: list[dict[str, Any]] = []
    data_points: list[dict[str, Any]] = []
    chart_suggestions: list[str] = []
    related: list[str] = []
    claim_verified: bool | str = "not_applicable"
    claim_evidence = ""

    asset_aliases = {
        "usdinr": ["rupee", "usdinr", "dollar", "currency", "fx"],
        "gold":   ["gold"],
        "crude":  ["crude", "oil"],
        "india_10y": ["10y", "yield", "rates"],
    }

    phrase_lower = phrase.lower()
    focus_assets: list[str] = []
    for aid, kws in asset_aliases.items():
        if any(kw in phrase_lower for kw in kws):
            focus_assets.append(aid)
    if not focus_assets:
        focus_assets = list(snapshot.keys())

    for aid in focus_assets:
        entry = snapshot.get(aid)
        if entry is None or not entry.data_available:
            continue
        feats = entry.features
        roc_5d = feats.roc_5d
        roc_20d = feats.roc_20d
        roc_60d = feats.roc_60d
        pctile = feats.pctile_252d

        verified_facts.append({
            "fact": f"{entry.label}: {_format_pct(roc_20d)} over 20 days, {_format_pct(roc_60d)} over 60 days",
            "source": "cross_asset",
            "value": roc_60d,
            "context": entry.as_of_date or "",
        })
        if pctile is not None:
            # pctile_252d is a 0-1 fraction (rank-percentile of close within 252d window)
            pctile_pct = pctile * 100.0
            verified_facts.append({
                "fact": f"{entry.label} sits at the {pctile_pct:.0f}th percentile of its trailing year",
                "source": "cross_asset",
                "value": pctile,
                "context": "1y percentile of close",
            })
            data_points.append({
                "label": f"{entry.label} 1y percentile",
                "value": f"{pctile_pct:.0f}th",
                "context": "of trailing 252 sessions",
            })
        data_points.append({
            "label": f"{entry.label} 60d change",
            "value": _format_pct(roc_60d),
            "context": "ROC over trailing 60 sessions",
        })
        chart_suggestions.append(
            f"Line chart: {entry.label} over trailing 12 months with 200-DMA overlay"
        )

        # Claim verification — rupee weakness, gold rally, etc.
        if aid == "usdinr" and ("weak" in phrase_lower or "depreciat" in phrase_lower):
            if pctile is not None and pctile >= 0.70:
                claim_verified = True
                claim_evidence = f"USDINR at {pctile * 100:.0f}th percentile of trailing year — rupee is genuinely weak"
            elif pctile is not None:
                claim_verified = False
                claim_evidence = f"USDINR only at {pctile * 100:.0f}th percentile — not particularly weak by recent history"
        elif aid == "gold" and ("rally" in phrase_lower or "up" in phrase_lower):
            if roc_60d is not None and roc_60d > 0.05:
                claim_verified = True
                claim_evidence = f"Gold is up {_format_pct(roc_60d)} over 60 days — rally is real"
            elif roc_60d is not None:
                claim_verified = False
                claim_evidence = f"Gold is only {_format_pct(roc_60d)} over 60 days — no meaningful rally"

    return {
        "modules_invoked": ["cross_asset"],
        "verified_facts": verified_facts,
        "data_points": data_points,
        "chart_suggestions": chart_suggestions,
        "related_signals": related,
        "claim_verified": claim_verified,
        "claim_evidence": claim_evidence,
        "confidence": "high" if verified_facts else "low",
    }


def analyse_concentration(phrase: str, asof) -> dict[str, Any]:
    """Nifty concentration / Reliance impact."""
    from app.insights.concentration import compute_concentration
    reading = compute_concentration(date=asof)

    verified_facts: list[dict[str, Any]] = []
    data_points: list[dict[str, Any]] = []
    chart_suggestions: list[str] = []
    related: list[str] = []

    top3 = getattr(reading, "top_3_share_of_move", None)
    top5 = getattr(reading, "top_5_share_of_move", None)
    reliance_share = getattr(reading, "reliance_share_of_move", None)
    # nifty_return_pct in the engine is already a percent like 0.4 = +0.4%
    nifty_change = getattr(reading, "nifty_return_pct", None)
    top_3_symbols = getattr(reading, "top_3_symbols", []) or []

    def _fmt_nifty_pct(v):
        return f"{v:+.2f}%" if v is not None else "n/a"

    if top3 is not None and nifty_change is not None:
        verified_facts.append({
            "fact": f"Top 3 stocks contributed {top3 * 100:.0f}% of today's Nifty move ({_fmt_nifty_pct(nifty_change)})",
            "source": "concentration",
            "value": top3,
            "context": str(asof),
        })
        data_points.append({
            "label": "Top 3 share of Nifty move",
            "value": f"{top3 * 100:.0f}%",
            "context": f"on Nifty {_fmt_nifty_pct(nifty_change)} day",
        })
    if top5 is not None:
        verified_facts.append({
            "fact": f"Top 5 stocks contributed {top5 * 100:.0f}% of the move",
            "source": "concentration",
            "value": top5,
            "context": str(asof),
        })
    if reliance_share is not None:
        data_points.append({
            "label": "Reliance share of move",
            "value": f"{reliance_share * 100:.0f}%",
            "context": "single-stock contribution",
        })
    if top_3_symbols:
        related.append(f"Top 3 contributors today: {', '.join(top_3_symbols)}")

    chart_suggestions.append(
        "Pie chart: Nifty 50 weighted contributors today — top 3-5 in colour, the rest as thin grey slivers"
    )
    chart_suggestions.append(
        "Bar chart: per-stock contribution to Nifty move (sorted, top 10)"
    )

    return {
        "modules_invoked": ["concentration"],
        "verified_facts": verified_facts,
        "data_points": data_points,
        "chart_suggestions": chart_suggestions,
        "related_signals": related,
        "claim_verified": "not_applicable",
        "claim_evidence": "",
        "confidence": "high" if verified_facts else "low",
    }


def analyse_watchlist(phrase: str, asof) -> dict[str, Any]:
    """Breakouts, RS leaders, etc."""
    from app.insights.watchlists import (
        get_breakouts, get_rs_leaders, get_multi_year_breakouts,
    )
    verified_facts: list[dict[str, Any]] = []
    data_points: list[dict[str, Any]] = []
    chart_suggestions: list[str] = []
    related: list[str] = []

    phrase_lower = phrase.lower()

    def _names(entries) -> list[str]:
        return [e.symbol for e in (entries or []) if hasattr(e, "symbol")]

    if "multi-year" in phrase_lower or "5-year" in phrase_lower:
        names = _names(get_multi_year_breakouts(asof=asof))
        if names:
            verified_facts.append({
                "fact": f"{len(names)} stocks at multi-year highs today: {', '.join(names[:5])}",
                "source": "watchlists.multi_year_breakouts",
                "value": len(names),
                "context": str(asof),
            })
            data_points.append({"label": "Multi-year breakouts", "value": f"{len(names)} stocks", "context": ", ".join(names[:3])})
    else:
        bo = _names(get_breakouts(asof=asof))
        rs = _names(get_rs_leaders(asof=asof))
        if bo:
            verified_facts.append({
                "fact": f"Fresh breakouts today: {', '.join(bo[:5])}",
                "source": "watchlists.breakouts",
                "value": len(bo),
                "context": str(asof),
            })
            data_points.append({"label": "Fresh breakouts today", "value": f"{len(bo)} stocks", "context": ", ".join(bo[:3])})
        if rs:
            related.append(f"Strongest RS leaders: {', '.join(rs[:3])}")

    chart_suggestions.append("Small-multiples: 3 of the named stocks' price + 200-DMA overlay")

    return {
        "modules_invoked": ["watchlists"],
        "verified_facts": verified_facts,
        "data_points": data_points,
        "chart_suggestions": chart_suggestions,
        "related_signals": related,
        "claim_verified": "not_applicable",
        "claim_evidence": "",
        "confidence": "high" if verified_facts else "low",
    }


def analyse_regime(phrase: str, asof) -> dict[str, Any]:
    """State-of-market — regime + stress."""
    from app.insights.regime import get_regime_snapshot
    from app.insights.stress import get_stress_snapshot
    reg = get_regime_snapshot(asof=asof)
    stress = get_stress_snapshot(asof=asof)

    verified_facts: list[dict[str, Any]] = []
    data_points: list[dict[str, Any]] = []
    chart_suggestions: list[str] = []
    related: list[str] = []

    if reg is not None:
        verified_facts.append({
            "fact": f"Current regime: {reg.regime} for {reg.persistence_days} trading days",
            "source": "regime",
            "value": None,
            "context": "regime classification",
        })
        data_points.append({
            "label": "Market regime",
            "value": reg.regime,
            "context": f"{reg.persistence_days} trading days running",
        })
    if stress is not None:
        verified_facts.append({
            "fact": f"Stress score: {stress.score:.0f}/100 (at the {stress.score_percentile:.0f}th percentile of 5y readings)",
            "source": "stress",
            "value": stress.score / 100.0,
            "context": "composite stress",
        })
        data_points.append({
            "label": "Stress score",
            "value": f"{stress.score:.0f}/100",
            "context": f"{stress.score_percentile:.0f}th percentile of 5y",
        })

    chart_suggestions.append("Regime timeline strip over trailing 24 months with shaded blocks per regime")
    chart_suggestions.append("Stress score line over trailing 12 months with calm/elevated/extreme bands")

    return {
        "modules_invoked": ["regime", "stress"],
        "verified_facts": verified_facts,
        "data_points": data_points,
        "chart_suggestions": chart_suggestions,
        "related_signals": related,
        "claim_verified": "not_applicable",
        "claim_evidence": "",
        "confidence": "high" if verified_facts else "low",
    }


# ---------------------------------------------------------------------------
# Stock-level relative strength (production-sourced)
# ---------------------------------------------------------------------------

PROD_API_BASE = os.environ.get(
    "MARKETWORKS_API_BASE", "https://kite-lab-production.up.railway.app"
).rstrip("/")

# Spoken/company names a content brief is likely to use, mapped to NSE symbols.
# Extend as briefs need them; unmapped bare symbols are picked up by the
# uppercase-token rule in symbols_in().
STOCK_NAME_MAP: dict[str, str] = {
    "hdfc bank": "HDFCBANK", "hdfcbank": "HDFCBANK",
    "icici bank": "ICICIBANK", "icicibank": "ICICIBANK",
    "state bank": "SBIN", "sbi": "SBIN", "sbin": "SBIN",
    "kotak": "KOTAKBANK", "kotak mahindra": "KOTAKBANK", "kotakbank": "KOTAKBANK",
    "axis bank": "AXISBANK", "axisbank": "AXISBANK",
    "indusind": "INDUSINDBK", "federal bank": "FEDERALBNK",
}

_SYMBOL_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9&]{3,}\b")


def symbols_in(phrase: str) -> list[str]:
    """Resolve NSE symbols named in a phrase, preserving first-mention order.

    Longest names match first, and a matched span is consumed so its words
    cannot be re-read as a bare symbol — otherwise "HDFC Bank" yields both
    HDFCBANK and a phantom HDFC, and the phantom 404s against production.
    """
    found: list[str] = []
    remainder = phrase
    for name in sorted(STOCK_NAME_MAP, key=len, reverse=True):
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        if pattern.search(remainder):
            symbol = STOCK_NAME_MAP[name]
            if symbol not in found:
                found.append(symbol)
            remainder = pattern.sub(" ", remainder)
    for token in _SYMBOL_TOKEN_RE.findall(remainder):
        if token not in found:
            found.append(token)
    return found


def _fetch_json(path: str, timeout: int = 90) -> dict[str, Any]:
    """GET JSON from the configured API host.

    The scheme is checked because MARKETWORKS_API_BASE is operator-supplied;
    urlopen would otherwise honour `file:` and turn a config typo into a local
    file read.
    """
    import urllib.request
    url = f"{PROD_API_BASE}{path}"
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"refusing non-HTTP API base: {PROD_API_BASE!r}")
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - scheme checked above
        return json.load(resp)


def analyse_stock_rs(phrase: str, asof) -> dict[str, Any]:
    """Per-stock relative strength for named stocks, from PRODUCTION.

    Unlike the other handlers, this one reads the live production API rather
    than importing the local engine. Content dossiers must carry the same
    numbers the published dashboard shows; local price mirrors can lag the
    16:30 IST pipeline, and a reel quoting a number the site contradicts is
    worse than no reel. Override the host with MARKETWORKS_API_BASE.

    The returned facts carry PRODUCTION's as-of date, which may trail the
    requested one (weekends, holidays, a late pipeline). That mismatch is
    surfaced as a fact rather than silently accepted, so the writer dates the
    claim correctly.
    """
    symbols = symbols_in(phrase)
    if not symbols:
        return {"modules_invoked": [], "verified_facts": [], "data_points": [],
                "chart_suggestions": [], "related_signals": [], "supersedes": [],
                "claim_verified": "not_applicable", "claim_evidence": "",
                "confidence": "low"}

    verified_facts: list[dict[str, Any]] = []
    data_points: list[dict[str, Any]] = []
    related: list[str] = []
    prod_asof: str | None = None
    rows: list[tuple[str, dict[str, Any]]] = []

    for symbol in symbols:
        try:
            payload = _fetch_json(f"/api/insights/stocks/{symbol}")
        except Exception as exc:
            print(f"  ⚠  {symbol}: production fetch failed: {exc}", file=sys.stderr)
            continue
        row = payload.get("row")
        if not payload.get("data_available", True) or not row:
            print(f"  ⚠  {symbol}: no production data", file=sys.stderr)
            continue
        prod_asof = prod_asof or str(row.get("date", ""))[:10]
        rows.append((symbol, row))

    for symbol, row in rows:
        rank, pct = row.get("rank"), row.get("percentile")
        if rank is None:
            continue
        verified_facts.append({
            "fact": (f"{symbol} RS rank {rank} of 500 "
                     f"({pct:.0f}th percentile) on {str(row.get('date'))[:10]}"),
            "source": f"production:api/insights/stocks/{symbol}.rank",
            "value": rank,
            "context": f"rs_score {row.get('rs_score')}",
        })
        for horizon, key in (("3-month", "ret_3m"), ("12-month", "ret_12m")):
            val = row.get(key)
            if val is None:
                continue
            verified_facts.append({
                "fact": f"{symbol} {horizon} return {val * 100:+.1f}%",
                "source": f"production:api/insights/stocks/{symbol}.{key}",
                "value": val,
                "context": str(row.get("date"))[:10],
            })
        # Own-trend state. A stock's position against its own 200-day average
        # is the time-series (absolute) reading, as opposed to the rank, which
        # is the cross-sectional (relative) one — the contrast a piece
        # separating the two momentum families needs.
        above = row.get("above_200dma")
        if above is not None:
            dist = row.get("dist_200dma_pct")
            verified_facts.append({
                "fact": (f"{symbol} is {'above' if above else 'below'} its 200-day average"
                         + (f" by {abs(dist) * 100:.1f}%" if dist is not None else "")),
                "source": f"production:api/insights/stocks/{symbol}.above_200dma",
                "value": bool(above),
                "context": str(row.get("date"))[:10],
            })
        # The average's own direction, which is NOT recoverable from the gap
        # above. A 200-day average follows the price that built it, so a stock
        # can sit well above a flat or falling average purely by bouncing,
        # while another sits barely above one that has been climbing all year.
        # Any piece explaining WHY an own-trend reading and a cross-sectional
        # rank disagree needs the slope; the gap alone will mislead it.
        slope = row.get("slope_200dma_20d")
        if slope is not None:
            verified_facts.append({
                "fact": (f"{symbol}'s own 200-day average is "
                         f"{'rising' if slope > 0 else 'falling'} at "
                         f"{abs(slope) * 100:.2f}% over the last 20 trading days"),
                "source": f"production:api/insights/stocks/{symbol}.slope_200dma_20d",
                "value": slope,
                "context": str(row.get("date"))[:10],
            })
        data_points.append({
            "label": f"{symbol} RS rank",
            "value": f"{rank}/500",
            "context": f"{pct:.0f}th pctile · 3m {row.get('ret_3m', 0) * 100:+.1f}%",
        })

    # Sector context: how the stocks' sector is doing against the Nifty.
    sectors = named_sectors_in(phrase)
    if sectors:
        try:
            snap = _fetch_json("/api/insights/sectors").get("sector_rs", {})
            for sector in sectors:
                entry = snap.get(sector)
                if not entry:
                    continue
                rs60 = entry.get("rs_60d")
                if rs60 is None:
                    continue
                verified_facts.append({
                    "fact": (f"{sector} is {rs60 * 100:+.1f}% against the Nifty "
                             f"over 60 trading days (rank {entry.get('rank_60d')} of sectors)"),
                    "source": f"production:api/insights/sectors.{sector}.rs_60d",
                    "value": rs60,
                    "context": str(entry.get("date"))[:10],
                })
                data_points.append({
                    "label": f"{sector} vs Nifty (60d)",
                    "value": f"{rs60 * 100:+.1f}%",
                    "context": f"sector rank {entry.get('rank_60d')}",
                })
        except Exception as exc:
            print(f"  ⚠  sector context failed: {exc}", file=sys.stderr)

    requested = str(asof)[:10]
    if prod_asof and prod_asof != requested:
        related.append(
            f"Production data is as of {prod_asof}, not the requested {requested} "
            f"— date every claim {prod_asof}."
        )

    # sector_rank/sector_size are deliberately NOT surfaced: rs_rank keeps a
    # stock's BEST rank across every sector it belongs to and reports that
    # sector's size, without naming which sector won. Two banks in the same
    # sector can therefore report different denominators (HDFCBANK 14/14 from
    # NIFTY_FIN_SERVICE vs KOTAKBANK 9/20 from NIFTY_BANK), so the numbers are
    # not comparable to each other and must not go on screen.

    return {
        "modules_invoked": ["production:insights.stocks", "production:insights.sectors"],
        # Local sector_rs computes the same sector-vs-Nifty metric off local
        # price mirrors and disagrees with production (+4.6% vs +4.3%, and a
        # different sector universe). Two numbers for one metric in one
        # dossier is how a wrong figure reaches a screen, so production wins.
        "supersedes": ["sector_rs"] if verified_facts else [],
        "verified_facts": verified_facts,
        "data_points": data_points,
        "chart_suggestions": [
            "Ranked bar of the named stocks by RS rank (lower = stronger), labelled with each 3m and 12m return",
            "Small-multiples: each stock's price rebased to 100 against the Nifty over 12 months",
        ],
        "related_signals": related,
        "claim_verified": "not_applicable",
        "claim_evidence": "",
        "confidence": "high" if verified_facts else "low",
    }


HANDLERS: dict[str, Callable[[str, Any], dict[str, Any]]] = {
    "analyse_sector":        analyse_sector,
    "analyse_currency":      analyse_currency,
    "analyse_concentration": analyse_concentration,
    "analyse_watchlist":     analyse_watchlist,
    "analyse_regime":        analyse_regime,
    "analyse_stock_rs":      analyse_stock_rs,
}


# ---------------------------------------------------------------------------
# Slug + I/O
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def slugify(phrase: str) -> str:
    s = phrase.lower().replace("-", "_").replace(" ", "_")
    s = _SLUG_RE.sub("", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:60] or "topic"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def assemble_dossier(phrase: str, slug: str, asof_str: str) -> dict[str, Any]:
    import pandas as pd
    asof = pd.Timestamp(asof_str)

    matched = route(phrase)
    if not matched:
        # Fallback: regime + concentration
        matched = [
            r for r in ROUTING_RULES if r.handler_name in ("analyse_regime", "analyse_concentration")
        ]
        category = "unrouted"
    else:
        category = matched[0].category

    modules_invoked: list[str] = []
    verified_facts: list[dict[str, Any]] = []
    data_points: list[dict[str, Any]] = []
    chart_suggestions: list[str] = []
    related: list[str] = []
    claim_verified: bool | str = "not_applicable"
    claim_evidence = ""
    confidences: list[str] = []

    superseded: set[str] = set()

    for rule in matched:
        handler = HANDLERS.get(rule.handler_name)
        if handler is None:
            continue
        try:
            result = handler(phrase, asof)
        except Exception as exc:
            print(f"  ⚠  handler {rule.handler_name} failed: {exc}", file=sys.stderr)
            continue
        superseded.update(result.get("supersedes", ()))
        modules_invoked.extend(result.get("modules_invoked", []))
        verified_facts.extend(result.get("verified_facts", []))
        data_points.extend(result.get("data_points", []))
        chart_suggestions.extend(result.get("chart_suggestions", []))
        related.extend(result.get("related_signals", []))
        confidences.append(result.get("confidence", "low"))
        # Pick the strongest claim verification across handlers
        if result.get("claim_verified") is True and claim_verified is not True:
            claim_verified = True
            claim_evidence = result.get("claim_evidence", "")
        elif result.get("claim_verified") is False and claim_verified == "not_applicable":
            claim_verified = False
            claim_evidence = result.get("claim_evidence", "")

    # A handler may declare that it supersedes another source for the same
    # metric (e.g. production sector RS over the locally-computed one). Drop
    # the superseded facts so the dossier never offers a writer two different
    # numbers for one thing.
    if superseded:
        def _kept(item: dict[str, Any]) -> bool:
            src = str(item.get("source", ""))
            return not any(src == s or src.startswith(f"{s}.") for s in superseded)

        dropped = [f for f in verified_facts if not _kept(f)]
        verified_facts = [f for f in verified_facts if _kept(f)]
        for fact in dropped:
            print(f"  ·  superseded by production: {fact['fact'][:70]}", file=sys.stderr)

    if "high" in confidences:
        confidence = "high"
    elif "medium" in confidences:
        confidence = "medium"
    elif "low" in confidences:
        confidence = "low"
    else:
        confidence = "not_supported"

    return {
        "topic_phrase": phrase,
        "slug": slug,
        "asof": asof_str,
        "generated_at": _now_utc_iso(),
        "category": category,
        "modules_invoked": sorted(set(modules_invoked)),
        "claim": {
            "stated": phrase,
            "verified": claim_verified,
            "evidence": claim_evidence,
        },
        "verified_facts": verified_facts,
        "data_points": data_points,
        "chart_suggestions": chart_suggestions,
        "related_signals": related,
        "confidence": confidence,
    }


def write_dossier(dossier: dict[str, Any]) -> Path:
    DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)
    out = DOSSIERS_DIR / f"{dossier['slug']}.json"
    out.write_text(json.dumps(dossier, indent=2, ensure_ascii=False, default=str) + "\n")
    return out


def print_summary(dossier: dict[str, Any], out_path: Path) -> None:
    print(f"✓ Topic dossier: {out_path.relative_to(REPO_ROOT)}")
    print(f"  topic       {dossier['topic_phrase']}")
    print(f"  category    {dossier['category']}")
    print(f"  modules     {', '.join(dossier['modules_invoked']) or '(none)'}")
    print(f"  confidence  {dossier['confidence']}")
    print(f"  facts       {len(dossier['verified_facts'])}")
    claim = dossier["claim"]
    if claim["verified"] != "not_applicable":
        print(f"  claim       verified={claim['verified']}  ·  {claim['evidence'][:80]}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True, help="Topic phrase (free text)")
    parser.add_argument("--slug", default=None, help="Override the auto-slug")
    parser.add_argument("--asof", default=None,
                        help="As-of date YYYY-MM-DD (defaults to today)")
    args = parser.parse_args(argv)

    slug = args.slug or slugify(args.topic)
    asof_str = args.asof or datetime.now().strftime("%Y-%m-%d")

    dossier = assemble_dossier(args.topic, slug, asof_str)
    out_path = write_dossier(dossier)
    print_summary(dossier, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
