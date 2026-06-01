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

Out-of-scope for v1: subgroup analysis (PSU vs private banks etc.) and
anniversary/calendar phrases. Add wrapper functions when those topics
become recurring.
"""
from __future__ import annotations

import argparse
import json
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


HANDLERS: dict[str, Callable[[str, Any], dict[str, Any]]] = {
    "analyse_sector":        analyse_sector,
    "analyse_currency":      analyse_currency,
    "analyse_concentration": analyse_concentration,
    "analyse_watchlist":     analyse_watchlist,
    "analyse_regime":        analyse_regime,
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

    for rule in matched:
        handler = HANDLERS.get(rule.handler_name)
        if handler is None:
            continue
        try:
            result = handler(phrase, asof)
        except Exception as exc:
            print(f"  ⚠  handler {rule.handler_name} failed: {exc}", file=sys.stderr)
            continue
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
