"""Publish a Marketworks signal — the kite-lab side of the content bridge.

Takes a real artifact from the platform (daily quant note or portfolio
rebalance) and emits a JSON file conforming to
`data/published/schema/signal.schema.json`. Downstream consumers
(currently `~/finance-content-os` via its `bridge/import_from_marketworks.py`)
read from `data/published/signals/`.

Usage:
    python scripts/publish_signal.py from-daily-note \\
        --date 2026-05-31 --mode postclose

    python scripts/publish_signal.py from-rebalance \\
        --portfolio tl25_v3 --changes-csv path/to/changes_2026-05-30.csv

By design this script is read-only against the insight engine and
portfolio outputs — it never mutates platform state, only translates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
KITE_API = REPO_ROOT / "kite-api"
if str(KITE_API) not in sys.path:
    sys.path.insert(0, str(KITE_API))

PUBLISHED_DIR = REPO_ROOT / "data" / "published"
SIGNALS_DIR = PUBLISHED_DIR / "signals"
SCHEMA_PATH = PUBLISHED_DIR / "schema" / "signal.schema.json"
MANIFEST_PATH = SIGNALS_DIR / "MANIFEST.json"

CONTENT_REPO_SCHEMA = Path.home() / "finance-content-os" / "schemas" / "signal.schema.json"

VALID_SIGNAL_TYPES = {
    "momentum", "unusual_move", "rotation", "retail_trap",
    "historical", "portfolio", "news", "event", "definition",
}
VALID_STRENGTHS = {"strong", "moderate", "speculative"}
REQUIRED_FIELDS = ("title", "signal_type", "why_interesting", "why_now", "who_cares")


# ---------------------------------------------------------------------------
# Schema sync check
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_schema_in_sync() -> None:
    """Refuse to run if local schema copy has drifted from the content repo."""
    if not SCHEMA_PATH.exists():
        raise SystemExit(
            f"Schema copy missing at {SCHEMA_PATH}. "
            f"Copy from {CONTENT_REPO_SCHEMA} and retry."
        )
    if not CONTENT_REPO_SCHEMA.exists():
        # Content repo not present on this machine — skip the check but warn.
        print(
            f"  ⚠  Content repo schema not found at {CONTENT_REPO_SCHEMA}; "
            f"skipping drift check. Local schema in use: {SCHEMA_PATH}",
            file=sys.stderr,
        )
        return
    local = _sha256(SCHEMA_PATH)
    remote = _sha256(CONTENT_REPO_SCHEMA)
    if local != remote:
        raise SystemExit(
            "Schema drift detected:\n"
            f"  local:  {SCHEMA_PATH} ({local[:12]}...)\n"
            f"  remote: {CONTENT_REPO_SCHEMA} ({remote[:12]}...)\n"
            "Update one to match the other and retry."
        )


# ---------------------------------------------------------------------------
# Inline validator (avoids adding jsonschema dependency)
# ---------------------------------------------------------------------------

def validate_signal(data: dict[str, Any]) -> None:
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ValueError(f"Signal missing required fields: {missing}")
    if data["signal_type"] not in VALID_SIGNAL_TYPES:
        raise ValueError(
            f"signal_type {data['signal_type']!r} not in {sorted(VALID_SIGNAL_TYPES)}"
        )
    if "strength" in data and data["strength"] not in VALID_STRENGTHS:
        raise ValueError(
            f"strength {data['strength']!r} not in {sorted(VALID_STRENGTHS)}"
        )
    if "data_points" in data and not isinstance(data["data_points"], list):
        raise ValueError("data_points must be a list of strings")
    if "data_points" in data and not all(isinstance(p, str) for p in data["data_points"]):
        raise ValueError("data_points entries must all be strings")


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_signal(data: dict[str, Any], filename: str, *, signal_type_label: str) -> Path:
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SIGNALS_DIR / filename
    if "published_at" not in data:
        data["published_at"] = _now_utc_iso()
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    _update_manifest(filename, signal_type_label, data["published_at"])
    return out_path


def _update_manifest(filename: str, signal_type_label: str, published_at: str) -> None:
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text())
    else:
        manifest = {"signals": []}

    # Remove any existing entry for the same file (idempotent re-publishes)
    manifest["signals"] = [s for s in manifest["signals"] if s["file"] != filename]
    manifest["signals"].append({
        "file": filename,
        "type": signal_type_label,
        "published_at": published_at,
    })
    manifest["signals"].sort(key=lambda s: s["published_at"], reverse=True)
    manifest["last_updated"] = _now_utc_iso()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Subcommand: from-daily-note
# ---------------------------------------------------------------------------

def _classify_daily_signal_type(stress_score: float, regime: str) -> str:
    """Map regime + stress to a Signal type the content engine understands."""
    if stress_score >= 70:
        return "event"
    if regime in {"trending_up", "trending_down"}:
        return "momentum"
    if regime in {"transition", "rangebound"}:
        return "rotation"
    return "rotation"


def _watchlist_names(reading, key: str, limit: int = 3) -> list[str]:
    """Top N tickers from a named watchlist, e.g. 'breakouts_today'."""
    entries = reading.watchlists.get(key, []) or []
    out: list[str] = []
    for entry in entries[:limit]:
        symbol = getattr(entry, "symbol", None) or (
            entry.get("symbol") if isinstance(entry, dict) else None
        )
        if symbol:
            out.append(symbol)
    return out


def _safe_pct(v: float | None, digits: int = 1) -> str:
    """Format a value as a percentage. Accepts either 0-1 fractions or
    0-100 percentile-style numbers (heuristic: > 1.0 ⇒ already a percent)."""
    if v is None:
        return "n/a"
    pct = v if v > 1.0 else v * 100.0
    return f"{pct:.{digits}f}%"


def _daily_note_signal(date_str: str, mode: str) -> dict[str, Any]:
    """Build a Signal dict from today's MarketReading + commentary."""
    import pandas as pd
    from app.insights.reading import get_market_reading
    from app.insights.notes import commentary as commentary_mod

    asof = pd.Timestamp(date_str)
    reading = get_market_reading(asof)
    commentary = commentary_mod.compose(reading, mode=mode)

    regime_name = reading.regime.regime
    stress_score = reading.stress.score
    stress_pctile = reading.stress.score_percentile
    signal_type = _classify_daily_signal_type(stress_score, regime_name)

    # Top adds/breakouts from watchlists (varies by what the engine ships)
    breakouts = _watchlist_names(reading, "breakouts_today", limit=3)
    six_month = _watchlist_names(reading, "strongest_six_month", limit=3)
    trend_breaks = _watchlist_names(reading, "trend_breaks_today", limit=3)

    # Top + bottom sector by 60d RS
    leaderboard = reading.sector_leaderboard_60d or []
    top_sector = leaderboard[0] if leaderboard else None
    bottom_sector = leaderboard[-1] if leaderboard else None

    data_points: list[str] = [
        f"Stress: {stress_score:.0f}/100 "
        f"({_safe_pct(stress_pctile, 0)} of 5y readings)",
        f"Regime: {regime_name} "
        f"({reading.regime.persistence_days} trading days)",
    ]
    if top_sector is not None and bottom_sector is not None:
        top_name = getattr(top_sector, "sector", "?")
        top_rs = getattr(top_sector, "rs_60d", None)
        bot_name = getattr(bottom_sector, "sector", "?")
        bot_rs = getattr(bottom_sector, "rs_60d", None)
        if top_rs is not None and bot_rs is not None:
            data_points.append(
                f"Sector RS 60d: {top_name} {top_rs:+.1%} (lead) / "
                f"{bot_name} {bot_rs:+.1%} (lag)"
            )
    if breakouts:
        data_points.append(f"Fresh breakouts: {', '.join(breakouts)}")
    if six_month:
        data_points.append(f"Strongest 6-month: {', '.join(six_month)}")
    if trend_breaks:
        data_points.append(f"Trend breaks: {', '.join(trend_breaks)}")

    title = f"{commentary.headline.rstrip('.')} — {date_str}"

    signal = {
        "title": title[:200],
        "signal_type": signal_type,
        "ticker_or_theme": "Indian equity market — regime, sectors, watchlists",
        "why_interesting": commentary.regime + " " + commentary.sector,
        "why_now": commentary.conditional + " " + commentary.watch,
        "who_cares": (
            "Indian retail investors who think in momentum + portfolio "
            "frameworks and want a daily quantitative read on the market "
            "without ticker-tip noise."
        ),
        "data_points": data_points,
        "source": f"Marketworks insight engine — daily quant note ({mode}) {date_str}",
        "date": date_str,
        "strength": "strong",
    }
    if commentary.learn_moment:
        signal["learn_moment"] = commentary.learn_moment

    validate_signal(signal)
    return signal


def cmd_from_daily_note(args: argparse.Namespace) -> int:
    _check_schema_in_sync()
    signal = _daily_note_signal(args.date, args.mode)
    filename = f"{args.date}_{args.mode}_note.json"
    out = write_signal(signal, filename, signal_type_label=f"{args.mode}_note")
    print(f"✓ Published {out.relative_to(REPO_ROOT)}")
    print(f"  signal_type={signal['signal_type']}  "
          f"data_points={len(signal['data_points'])}")
    print(f"  Manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: from-rebalance
# ---------------------------------------------------------------------------

def _read_changes_csv(path: Path) -> dict[str, list[str]]:
    additions: list[str] = []
    removals: list[str] = []
    rank_changes: list[str] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            action = (row.get("action") or "").strip().lower()
            sym = (row.get("symbol") or "").strip()
            if not sym:
                continue
            if action in {"add", "addition"}:
                additions.append(sym)
            elif action in {"remove", "removal"}:
                removals.append(sym)
            elif action in {"rank_change", "rank change", "rank_changes"}:
                old = row.get("rank")
                new = row.get("new_rank")
                rank_changes.append(f"{sym} {old}→{new}")
    return {"additions": additions, "removals": removals, "rank_changes": rank_changes}


def _rebalance_signal(portfolio: str, changes_csv: Path, date_str: str | None) -> dict[str, Any]:
    changes = _read_changes_csv(changes_csv)
    n_add = len(changes["additions"])
    n_rem = len(changes["removals"])
    n_rank = len(changes["rank_changes"])
    if date_str is None:
        # Try to infer from filename
        stem = changes_csv.stem
        for part in stem.split("_"):
            try:
                datetime.strptime(part, "%Y-%m-%d")
                date_str = part
                break
            except ValueError:
                continue
        if date_str is None:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

    data_points: list[str] = []
    if changes["additions"]:
        data_points.append(f"Adds: {', '.join(changes['additions'][:8])}")
    if changes["removals"]:
        data_points.append(f"Removes: {', '.join(changes['removals'][:8])}")
    if changes["rank_changes"]:
        data_points.append(
            f"Rank changes: {', '.join(changes['rank_changes'][:8])}"
        )
    data_points.append(
        f"Totals: {n_add} adds, {n_rem} removes, {n_rank} rank changes"
    )

    signal = {
        "title": f"{portfolio} rebalance — {date_str}",
        "signal_type": "portfolio",
        "ticker_or_theme": portfolio,
        "why_interesting": (
            f"{portfolio} just rebalanced: {n_add} new names in, {n_rem} out, "
            f"{n_rank} rank changes. The book reflects the momentum / quality "
            f"framework's current read on the NSE 500."
        ),
        "why_now": (
            "Rebalances are scheduled (not discretionary). The set of "
            "adds/removes is the systematic answer to what the rules see "
            "as ranking changes since the last cut."
        ),
        "who_cares": (
            "Subscribers on this portfolio; broader audience interested in "
            "the live momentum / quality book without the marketing layer."
        ),
        "data_points": data_points,
        "source": f"Marketworks portfolio runner — {portfolio} rebalance {date_str}",
        "date": date_str,
        "strength": "strong",
    }
    validate_signal(signal)
    return signal


def cmd_from_rebalance(args: argparse.Namespace) -> int:
    _check_schema_in_sync()
    changes_csv = Path(args.changes_csv).expanduser().resolve()
    if not changes_csv.exists():
        raise SystemExit(f"changes CSV not found: {changes_csv}")
    signal = _rebalance_signal(args.portfolio, changes_csv, args.date)
    filename = f"{signal['date']}_{args.portfolio}_rebalance.json"
    out = write_signal(signal, filename, signal_type_label=f"{args.portfolio}_rebalance")
    print(f"✓ Published {out.relative_to(REPO_ROOT)}")
    print(f"  adds/removes/rank-changes: "
          f"{sum(1 for p in signal['data_points'] if p.startswith('Adds'))} sections logged")
    print(f"  Manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_note = sub.add_parser(
        "from-daily-note",
        help="Publish a Signal sourced from a daily quant note (MarketReading + commentary).",
    )
    p_note.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_note.add_argument(
        "--mode",
        choices=("premarket", "postclose", "weekly"),
        default="postclose",
        help="Which daily note template to read from (default: postclose).",
    )
    p_note.set_defaults(func=cmd_from_daily_note)

    p_reb = sub.add_parser(
        "from-rebalance",
        help="Publish a Signal sourced from a portfolio rebalance changes CSV.",
    )
    p_reb.add_argument("--portfolio", required=True,
                       help="Portfolio id, e.g. tl25_v3, om25_v3, l6_v2, combo_defensive")
    p_reb.add_argument("--changes-csv", required=True,
                       help="Path to the rebalance changes CSV file.")
    p_reb.add_argument("--date", default=None,
                       help="YYYY-MM-DD; inferred from filename if omitted.")
    p_reb.set_defaults(func=cmd_from_rebalance)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
