"""Capture a deterministic snapshot of daily-pipeline outputs.

This is the regression oracle for the pipeline-improvements refactor.
Phase 0 captures a baseline; subsequent phases re-snapshot and diff.

For each production portfolio (om25_v3, tl25_v3, l6_v2, combo_defensive)
it locates the latest timestamped run directory under
data/<universe>_portfolios/ and hashes the dashboard-schema CSVs:

  <run_dir>/backtests/baseline/momentum_equity.csv
  <run_dir>/backtests/baseline/momentum_trades.csv
  <run_dir>/backtests/baseline/momentum_holdings.csv
  <run_dir>/backtests/baseline/momentum_metrics.csv

It also captures the legacy momentum-signals output
(data/momentum/top25_signals.csv) so we can confirm pruning that step
later doesn't silently break anything we missed.

Output: tasks/pipeline_improvements/golden_master_<ts>.json
Optionally diffs against an earlier snapshot with --diff <path>.

Usage:
  python scripts/snapshot_pipeline_outputs.py
  python scripts/snapshot_pipeline_outputs.py --diff tasks/pipeline_improvements/golden_master_20260515.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Portfolio -> (run-dir parent, run-prefix glob)
PORTFOLIOS = {
    "om25_v3":          ("data/om25_v3_portfolios",         "om25_v3_portfolio_"),
    "tl25_v3":          ("data/tl25_v3_portfolios",         "tl25_v3_portfolio_"),
    "l6_v2":            ("data/l6_v2_portfolios",           "l6_v2_portfolio_"),
    "combo_defensive":  ("data/combo_defensive_portfolios", "combo_defensive_portfolio_"),
}

DASHBOARD_FILES = [
    "momentum_equity.csv",
    "momentum_trades.csv",
    "momentum_holdings.csv",
    "momentum_metrics.csv",
]

LEGACY_SIGNALS = "data/momentum/top25_signals.csv"


# ---------------------------------------------------------------------------
# Hashing / fingerprinting
# ---------------------------------------------------------------------------

# Floats are rounded to this many decimals before hashing so that
# floating-point noise from different machines or pandas versions doesn't
# cause spurious diffs.  10 dp is far below any economically meaningful
# precision (sub-paise on lakhs).
FLOAT_DECIMALS = 10


def _stable_repr(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if math.isnan(v):
            return "NaN"
        if math.isinf(v):
            return "Inf" if v > 0 else "-Inf"
        return f"{round(v, FLOAT_DECIMALS):.{FLOAT_DECIMALS}f}"
    return str(v)


def hash_dataframe(df: pd.DataFrame) -> str:
    """Stable SHA256 of a DataFrame.

    Independent of column order (we sort columns) and row order is
    preserved (we do NOT sort rows — order is semantically meaningful for
    equity/trades/holdings time-series).
    """
    cols = sorted(df.columns.tolist())
    h = hashlib.sha256()
    h.update(("|".join(cols) + "\n").encode())
    for row in df[cols].itertuples(index=False, name=None):
        h.update(("|".join(_stable_repr(v) for v in row) + "\n").encode())
    return h.hexdigest()


def numeric_summary(df: pd.DataFrame, cols: list[str]) -> dict[str, dict[str, float | None]]:
    """min/max/mean/last for the listed numeric columns (if present)."""
    out: dict[str, dict[str, float | None]] = {}
    for col in cols:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            out[col] = {"min": None, "max": None, "mean": None, "last": None}
            continue
        out[col] = {
            "min": round(float(s.min()),  FLOAT_DECIMALS),
            "max": round(float(s.max()),  FLOAT_DECIMALS),
            "mean": round(float(s.mean()), FLOAT_DECIMALS),
            "last": round(float(s.iloc[-1]), FLOAT_DECIMALS),
        }
    return out


# Key columns to summarise per dashboard file.  Hashes catch full content;
# the numeric summary makes diffs human-readable.
SUMMARY_COLS: dict[str, list[str]] = {
    "momentum_equity.csv":   ["portfolio_value", "drawdown", "benchmark"],
    "momentum_trades.csv":   ["shares", "price", "notional", "slippage"],
    "momentum_holdings.csv": ["shares", "avg_cost", "last_price", "pnl_pct",
                              "notional", "contribution_pct", "holding_days"],
    "momentum_metrics.csv":  ["total_return", "cagr", "max_drawdown",
                              "sharpe_ratio", "annualized_volatility",
                              "hit_rate_overall", "avg_holding_days",
                              "trades_total", "buys", "sells"],
}


def fingerprint_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return {"exists": True, "error": f"{type(exc).__name__}: {exc}"}
    cols_for_summary = SUMMARY_COLS.get(path.name, [])
    return {
        "exists": True,
        "path": str(path.relative_to(ROOT)),
        "size_bytes": path.stat().st_size,
        "row_count": int(len(df)),
        "columns": sorted(df.columns.tolist()),
        "sha256": hash_dataframe(df),
        "summary": numeric_summary(df, cols_for_summary),
    }


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def latest_run_dir(parent_rel: str, prefix: str) -> Path | None:
    parent = ROOT / parent_rel
    if not parent.exists():
        return None
    candidates = sorted(
        (p for p in parent.iterdir() if p.is_dir() and p.name.startswith(prefix)),
        key=lambda p: p.name,
    )
    return candidates[-1] if candidates else None


def snapshot_portfolio(universe: str, parent_rel: str, prefix: str) -> dict[str, Any]:
    run = latest_run_dir(parent_rel, prefix)
    if run is None:
        return {"found": False, "parent": parent_rel, "prefix": prefix}
    dash = run / "backtests" / "baseline"
    return {
        "found": True,
        "run_dir": str(run.relative_to(ROOT)),
        "run_mtime": datetime.fromtimestamp(run.stat().st_mtime).isoformat(timespec="seconds"),
        "files": {name: fingerprint_csv(dash / name) for name in DASHBOARD_FILES},
    }


def snapshot_all() -> dict[str, Any]:
    return {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "portfolios": {
            name: snapshot_portfolio(name, parent, prefix)
            for name, (parent, prefix) in PORTFOLIOS.items()
        },
        "legacy_signals": fingerprint_csv(ROOT / LEGACY_SIGNALS),
    }


# ---------------------------------------------------------------------------
# Diffing
# ---------------------------------------------------------------------------

def _walk(prefix: str, obj: Any, out: dict[str, Any]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _walk(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = obj


def diff_snapshots(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """Return human-readable differences. Ignores `captured_at`, `run_mtime`."""
    ignore_keys = {"captured_at", "run_mtime", "size_bytes"}
    fa, fb = {}, {}
    _walk("", a, fa)
    _walk("", b, fb)
    lines = []
    for k in sorted(set(fa) | set(fb)):
        if any(part in ignore_keys for part in k.split(".")):
            continue
        va, vb = fa.get(k, "<missing>"), fb.get(k, "<missing>")
        if va != vb:
            lines.append(f"{k}\n  baseline: {va}\n  current : {vb}")
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=None,
                    help="Output JSON path. Default: tasks/pipeline_improvements/golden_master_<ts>.json")
    ap.add_argument("--diff", type=Path, default=None,
                    help="Optional baseline JSON to diff against")
    ap.add_argument("--label", type=str, default=None,
                    help="Optional tag (e.g. 'phase0_baseline') embedded in the JSON")
    args = ap.parse_args()

    snap = snapshot_all()
    if args.label:
        snap["label"] = args.label

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.output or (ROOT / f"tasks/pipeline_improvements/golden_master_{ts}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=2, sort_keys=False, default=str))

    try:
        out_display = out.relative_to(ROOT)
    except ValueError:
        out_display = out
    print(f"Snapshot written: {out_display}")
    print()
    for name, p in snap["portfolios"].items():
        if not p.get("found"):
            print(f"  {name:18s} MISSING ({p['parent']})")
            continue
        files = p["files"]
        rows = ", ".join(
            f"{f.split('.')[0]}={files[f].get('row_count', '?')}"
            for f in DASHBOARD_FILES if files.get(f, {}).get("exists")
        )
        print(f"  {name:18s} {p['run_dir']}  [{rows}]")
    leg = snap["legacy_signals"]
    if leg.get("exists"):
        print(f"  legacy_signals     rows={leg['row_count']}  sha={leg['sha256'][:12]}...")
    else:
        print("  legacy_signals     MISSING")

    if args.diff:
        if not args.diff.exists():
            print(f"\nERROR: --diff baseline not found: {args.diff}", file=sys.stderr)
            sys.exit(2)
        baseline = json.loads(args.diff.read_text())
        diffs = diff_snapshots(baseline, snap)
        print(f"\nDiff vs {args.diff.relative_to(ROOT) if args.diff.is_absolute() else args.diff}:")
        if not diffs:
            print("  (no differences)")
        else:
            for line in diffs:
                print(f"  - {line}")
            print(f"\n{len(diffs)} differences.")
            sys.exit(1)


if __name__ == "__main__":
    main()
