"""Internal content radar — the daily "what should I make today?" inbox.

Part of the Content OS ideation layer (finance-content-os reconstruct, Phase 3;
sanctioned production tooling like analyse_topic.py, not a research probe).
Scans the insight-engine surfaces the dashboard already computes daily and emits
a ranked list of candidate content Ideas, each carrying the live readings that
make it timely.

An Idea is NOT a piece. The founder triages the inbox; a picked idea is routed
through scripts/analyse_topic.py (its topic_phrase is written to hit the right
routing keywords) for a full verified TopicDossier before any writing begins.
Contract: ~/finance-content-os/schemas/idea.schema.json.

Output: ~/finance-content-os/data/content_ideas/<date>.json
        {date, generated_at, source, ideas: [...]} sorted by rank.total desc.

Ranking v1 (transparent, founder-tunable):
    total = 0.50*signal + 0.20*freshness + 0.15*format_fit + 0.15*brand_fit
            - dedupe_penalty
- signal: magnitude parsed from the reading (percent / percentile / count),
  squashed to 0-1. Crude by design; the dossier is the real verification.
- freshness: 1.0 (everything here is computed today).
- format_fit / brand_fit: static per-category priors (reel-first pipeline).
- dedupe_penalty: 0.5 if finance-content-os/data/memory/topic_index.md already
  covers adjacent ground (keyword overlap), with a note saying what matched.

Usage:
    python scripts/content_radar.py                # today's inbox
    python scripts/content_radar.py --asof 2026-08-01
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
for p in (str(SCRIPTS_DIR),):
    if p not in sys.path:
        sys.path.insert(0, p)

import analyse_topic  # noqa: E402  (sibling module; sets up kite-api imports)

FCOS_ROOT = Path.home() / "finance-content-os"
INBOX_DIR = FCOS_ROOT / "data" / "content_ideas"
TOPIC_INDEX = FCOS_ROOT / "data" / "memory" / "topic_index.md"
IDEA_SCHEMA = FCOS_ROOT / "schemas" / "idea.schema.json"

WEIGHTS = {"signal": 0.50, "freshness": 0.20, "format_fit": 0.15, "brand_fit": 0.15}
DEDUPE_PENALTY = 0.5

# Per-category priors: (topic_phrase template routes analyse_topic correctly),
# format/brand fit for a reel-first pipeline, persona hint (frame-piece decides).
CATEGORIES: dict[str, dict[str, Any]] = {
    "sector_rs":     {"format_fit": 0.9, "brand_fit": 0.9, "persona": "karan"},
    "watchlists":    {"format_fit": 0.9, "brand_fit": 0.8, "persona": "karan"},
    "regime_stress": {"format_fit": 0.8, "brand_fit": 0.9, "persona": "meera"},
    "concentration": {"format_fit": 0.8, "brand_fit": 0.8, "persona": "karan"},
    "cross_asset":   {"format_fit": 0.7, "brand_fit": 0.8, "persona": "ananya"},
}


def _signal_from_facts(facts: list[dict[str, Any]]) -> float:
    """0-1 signal strength parsed from fact strings. Percent moves squash at
    ~20%; percentiles map directly; bare counts squash at ~15."""
    best = 0.0
    for f in facts:
        text = str(f.get("fact", ""))
        m = re.search(r"(\d+)(?:st|nd|rd|th)\s+percentile", text)
        if m:
            best = max(best, min(int(m.group(1)) / 100.0, 1.0))
            continue
        m = re.search(r"([+-]?\d+(?:\.\d+)?)%", text)
        if m:
            best = max(best, min(abs(float(m.group(1))) / 20.0, 1.0))
            continue
        m = re.search(r"\b(\d+)\s+stocks?\b", text)
        if m:
            best = max(best, min(int(m.group(1)) / 15.0, 1.0))
    return round(best if best > 0 else 0.5, 2)


def _dedupe(idea_keywords: list[str]) -> tuple[float, str]:
    if not TOPIC_INDEX.exists():
        return 0.0, ""
    index_text = TOPIC_INDEX.read_text().lower()
    hits = [k for k in idea_keywords if k.lower() in index_text]
    if hits:
        return DEDUPE_PENALTY, f"topic_index already covers: {', '.join(hits)}"
    return 0.0, ""


def _mk_idea(date: str, n: int, category: str, module: str, topic_phrase: str,
             angle_hint: str, facts: list[dict[str, Any]],
             dedupe_keywords: list[str]) -> dict[str, Any]:
    pri = CATEGORIES[category]
    signal = _signal_from_facts(facts)
    penalty, note = _dedupe(dedupe_keywords)
    rank = {
        "signal": signal,
        "freshness": 1.0,
        "format_fit": pri["format_fit"],
        "brand_fit": pri["brand_fit"],
        "dedupe_penalty": penalty,
        "total": round(sum(WEIGHTS[k] * v for k, v in {
            "signal": signal, "freshness": 1.0,
            "format_fit": pri["format_fit"], "brand_fit": pri["brand_fit"],
        }.items()) - penalty, 3),
    }
    if note:
        rank["dedupe_note"] = note
    return {
        "id": f"{date}-{category}-{n:02d}",
        "date": date,
        "source": "internal_radar",
        "radar_module": module,
        "topic_phrase": topic_phrase,
        "angle_hint": angle_hint,
        "evidence": [{"fact": f.get("fact", ""), "source": f.get("source", module)}
                     for f in facts if f.get("fact")],
        "suggested_format": "reel",
        "suggested_persona": pri["persona"],
        "rank": rank,
        "dossier_ref": None,
        "status": "candidate",
    }


def scan(asof: str) -> list[dict[str, Any]]:
    ideas: list[dict[str, Any]] = []
    date = asof

    # --- sector leadership (analyse_sector) --------------------------------
    try:
        d = analyse_topic.analyse_sector("sector leadership", asof)
        facts = d.get("verified_facts", [])
        leader = next((f for f in facts if "lead" in f.get("fact", "").lower()), None)
        if leader:
            m = re.search(r"NIFTY_([A-Z_]+)", leader["fact"])
            sector = (m.group(1).replace("_", " ").lower() if m else "the leading sector")
            ideas.append(_mk_idea(
                date, 1, "sector_rs", "sector_rs",
                f"{sector} sector leadership",
                f"The market's strongest sector right now is {sector} — what leading the market actually means, told through the live leader.",
                facts, [sector, "sector leadership"]))
    except Exception as e:  # a dead surface shouldn't kill the inbox
        print(f"  ⚠ sector_rs scan failed: {e}", file=sys.stderr)

    # --- watchlists: breakouts + multi-year highs (analyse_watchlist) ------
    try:
        d = analyse_topic.analyse_watchlist("breakout", asof)
        facts = d.get("verified_facts", [])
        fresh = [f for f in facts if "breakout" in f.get("fact", "").lower()]
        if fresh:
            ideas.append(_mk_idea(
                date, 1, "watchlists", "watchlists.breakouts",
                "fresh breakout stocks today",
                "Names crossing key levels today — what a breakout is and how to read the day's list without turning it into tips.",
                fresh, ["breakout"]))
        multi = [f for f in facts if "multi-year" in f.get("fact", "").lower()]
        if multi:
            ideas.append(_mk_idea(
                date, 2, "watchlists", "watchlists.multi_year",
                "multi-year breakout highs",
                "Stocks clearing every price they've traded in years — the overhead-supply story on today's names.",
                multi, ["multi-year", "overhead", "new high"]))
    except Exception as e:
        print(f"  ⚠ watchlists scan failed: {e}", file=sys.stderr)

    # --- regime / stress (analyse_regime) ----------------------------------
    try:
        d = analyse_topic.analyse_regime("market state", asof)
        facts = d.get("verified_facts", [])
        if facts:
            ideas.append(_mk_idea(
                date, 1, "regime_stress", "regime+stress",
                "market state check",
                "What the market's current state (trend + stress) says — a calm read of where we actually are.",
                facts, ["market state", "regime", "stress"]))
    except Exception as e:
        print(f"  ⚠ regime scan failed: {e}", file=sys.stderr)

    # --- concentration (analyse_concentration) -----------------------------
    try:
        d = analyse_topic.analyse_concentration("index concentration", asof)
        facts = d.get("verified_facts", [])
        if facts:
            ideas.append(_mk_idea(
                date, 1, "concentration", "concentration",
                "index concentration today",
                "Who actually moved the Nifty today — the index number vs what most stocks did.",
                facts, ["concentration", "index concentration"]))
    except Exception as e:
        print(f"  ⚠ concentration scan failed: {e}", file=sys.stderr)

    # --- cross-asset (analyse_currency) ------------------------------------
    try:
        d = analyse_topic.analyse_currency("rupee dollar macro", asof)
        facts = d.get("verified_facts", [])
        if facts:
            ideas.append(_mk_idea(
                date, 1, "cross_asset", "cross_asset",
                "rupee and cross-asset check",
                "The slow-moving variables (rupee, crude, gold, yields) and which one is actually stretched right now.",
                facts, ["rupee", "currency", "cross-asset"]))
    except Exception as e:
        print(f"  ⚠ cross_asset scan failed: {e}", file=sys.stderr)

    ideas.sort(key=lambda i: i["rank"]["total"], reverse=True)
    return ideas


def validate_contract(ideas: list[dict[str, Any]]) -> None:
    """Validate emitted Ideas against the contract FILE (content-os X.1).

    The schema is read from finance-content-os every run — never a copy kept
    here — so a contract change on the consumer side fails this producer
    loudly instead of drifting silently. Unlike a dead surface (which
    degrades gracefully), a contract violation kills the write: a malformed
    inbox is worse than no inbox.
    """
    if not IDEA_SCHEMA.exists():
        raise SystemExit(f"Idea contract not found: {IDEA_SCHEMA}")
    schema = json.loads(IDEA_SCHEMA.read_text())
    try:
        from jsonschema import Draft7Validator

        validator = Draft7Validator(schema)
        errors = [
            f"{idea.get('id', f'idea[{n}]')}: {err.message}"
            for n, idea in enumerate(ideas)
            for err in validator.iter_errors(idea)
        ]
    except ImportError:
        required = schema.get("required", [])
        errors = [
            f"{idea.get('id', f'idea[{n}]')}: missing required '{key}'"
            for n, idea in enumerate(ideas)
            for key in required
            if key not in idea
        ]
    if errors:
        raise SystemExit(
            "radar ideas violate idea.schema.json — inbox NOT written:\n  "
            + "\n  ".join(errors[:10])
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", default=None, help="YYYY-MM-DD (default today)")
    args = parser.parse_args(argv)
    asof = args.asof or datetime.now().strftime("%Y-%m-%d")

    ideas = scan(asof)
    if not ideas:
        raise SystemExit("radar produced no ideas — every surface scan failed?")
    validate_contract(ideas)

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    out = INBOX_DIR / f"{asof}.json"
    out.write_text(json.dumps({
        "date": asof,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "internal_radar",
        "ideas": ideas,
    }, indent=2, ensure_ascii=False) + "\n")

    print(f"✓ Morning inbox: {out}  ({len(ideas)} candidate ideas)")
    print(f"{'rank':>6}  {'id':<34} {'phrase':<34} note")
    for i in ideas:
        note = i["rank"].get("dedupe_note", "")
        print(f"{i['rank']['total']:>6}  {i['id']:<34} {i['topic_phrase']:<34} {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
