"""Pre-sync CSV validation for the daily pipeline.

Called by ``scripts/sync_to_database.py`` before any DB writes. If any
universe fails validation, the sync aborts — preventing malformed or
partial portfolio outputs from corrupting the production database.

The orchestrator (``run_daily_pipeline.py``) already exits on the first
portfolio failure, so it never reaches sync with missing outputs. This
module's job is to catch the subtler case: a portfolio script that
*exited 0* but wrote bad/empty CSVs (e.g. an engine that swallowed an
exception, or a partial flush before a kill).

Scope (deliberately small for Phase 1.2):
  - presence checks for the four dashboard CSVs
  - schema + non-empty + invariant checks on each
  - returns a structured ValidationReport per universe

Out of scope:
  - In-DB transaction restructuring (would require sync_service rework).
  - Cross-universe consistency (e.g. dates aligned across portfolios).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]

# Daily-pipeline-produced universes whose metrics schema is written by
# scripts/metrics_common.write_dashboard_metrics. The legacy universes
# (nse500/nifty100/nifty250 from run_final_momentum_portfolio.py) use a
# different metrics CSV schema and are out of scope for this validator.
RUN_DIR_GLOBS = {
    "om25_v3":         ("data/om25_v3_portfolios",         "om25_v3_portfolio_"),
    "tl25_v3":         ("data/tl25_v3_portfolios",         "tl25_v3_portfolio_"),
    "l6_v2":           ("data/l6_v2_portfolios",           "l6_v2_portfolio_"),
    "combo_defensive": ("data/combo_defensive_portfolios", "combo_defensive_portfolio_"),
}

DASHBOARD_FILES = (
    "momentum_equity.csv",
    "momentum_trades.csv",
    "momentum_holdings.csv",
    "momentum_metrics.csv",
)

# Required columns per file. Extra columns are allowed.
REQUIRED_COLUMNS = {
    "momentum_equity.csv":   {"date", "portfolio_value"},
    "momentum_trades.csv":   {"date", "symbol", "side", "shares", "price"},
    "momentum_holdings.csv": {"symbol", "shares", "avg_cost"},
    "momentum_metrics.csv":  {"start", "end", "cagr", "max_drawdown",
                              "sharpe_ratio", "trades_total"},
}


@dataclass
class ValidationReport:
    universe: str
    run_dir: Path | None
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def _latest_run_dir(parent_rel: str, prefix: str) -> Path | None:
    parent = REPO_ROOT / parent_rel
    if not parent.exists():
        return None
    candidates = sorted(
        (p for p in parent.iterdir() if p.is_dir() and p.name.startswith(prefix)),
        key=lambda p: p.name,
    )
    # Mirror sync_service: require momentum_holdings.csv to consider the run.
    for run in reversed(candidates):
        if (run / "backtests" / "baseline" / "momentum_holdings.csv").exists():
            return run
    return None


def _validate_equity(df: pd.DataFrame, rep: ValidationReport) -> None:
    if df.empty:
        rep.fail("momentum_equity.csv is empty")
        return
    dates = pd.to_datetime(df["date"], errors="coerce")
    if dates.isna().any():
        rep.fail("momentum_equity.csv has unparseable dates")
    if not dates.is_monotonic_increasing:
        rep.fail("momentum_equity.csv dates are not strictly increasing")
    pv = pd.to_numeric(df["portfolio_value"], errors="coerce")
    if pv.isna().any():
        rep.fail("momentum_equity.csv has NaN portfolio_value rows")
    if (pv <= 0).any():
        rep.fail("momentum_equity.csv has non-positive portfolio_value rows")
    # Sanity: at least 30 days of equity for a daily-pipeline product.
    if len(df) < 30:
        rep.warn(f"momentum_equity.csv only has {len(df)} rows (<30)")


def _validate_trades(df: pd.DataFrame, rep: ValidationReport) -> None:
    if df.empty:
        # Empty trades is allowed (a brand-new portfolio could have none)
        rep.warn("momentum_trades.csv is empty")
        return
    sides = df["side"].astype(str).str.upper().unique().tolist()
    bad_sides = [s for s in sides if s not in ("BUY", "SELL")]
    if bad_sides:
        rep.fail(f"momentum_trades.csv has unrecognised sides: {bad_sides}")
    if "shares" in df.columns:
        sh = pd.to_numeric(df["shares"], errors="coerce")
        if (sh <= 0).any() or sh.isna().any():
            rep.fail("momentum_trades.csv has non-positive or NaN shares")
    if "price" in df.columns:
        px = pd.to_numeric(df["price"], errors="coerce")
        if (px <= 0).any() or px.isna().any():
            rep.fail("momentum_trades.csv has non-positive or NaN price")


def _validate_holdings(df: pd.DataFrame, rep: ValidationReport) -> None:
    # Empty holdings is allowed (e.g. COMBO Defensive in deep bear regime).
    if df.empty:
        rep.warn("momentum_holdings.csv has no current positions")
        return
    if df["symbol"].isna().any() or (df["symbol"].astype(str).str.strip() == "").any():
        rep.fail("momentum_holdings.csv has empty symbol rows")
    if "shares" in df.columns:
        sh = pd.to_numeric(df["shares"], errors="coerce")
        if (sh <= 0).any() or sh.isna().any():
            rep.fail("momentum_holdings.csv has non-positive or NaN shares")
    # No top-N upper-bound check: caps vary per strategy (24, 25, ...).


def _validate_metrics(df: pd.DataFrame, rep: ValidationReport) -> None:
    if len(df) != 1:
        rep.fail(f"momentum_metrics.csv has {len(df)} rows (expected exactly 1)")
        return
    row = df.iloc[0]
    for fld in ("cagr", "max_drawdown", "sharpe_ratio"):
        if fld not in row.index:
            continue
        v = float(row[fld])
        if not math.isfinite(v):
            rep.fail(f"momentum_metrics.csv.{fld} is not finite ({v!r})")
    if "max_drawdown" in row.index and float(row["max_drawdown"]) > 0:
        rep.fail("momentum_metrics.csv.max_drawdown is positive (should be ≤ 0)")
    if "trades_total" in row.index and int(row["trades_total"]) < 0:
        rep.fail("momentum_metrics.csv.trades_total is negative")


_FILE_VALIDATORS = {
    "momentum_equity.csv":   _validate_equity,
    "momentum_trades.csv":   _validate_trades,
    "momentum_holdings.csv": _validate_holdings,
    "momentum_metrics.csv":  _validate_metrics,
}


def validate_universe(universe: str) -> ValidationReport:
    """Run all checks for one universe. Skip silently if no run dir exists.

    A universe with no run dir is reported as ``ok=True`` with a warning
    so that newly added universes don't break the sync on day 1.
    """
    rep = ValidationReport(universe=universe, run_dir=None)
    if universe not in RUN_DIR_GLOBS:
        rep.warn(f"no glob pattern registered for universe '{universe}'")
        return rep
    parent, prefix = RUN_DIR_GLOBS[universe]
    run = _latest_run_dir(parent, prefix)
    if run is None:
        rep.warn(f"no run dir found under {parent}/{prefix}*")
        return rep
    rep.run_dir = run
    dash = run / "backtests" / "baseline"
    for fname in DASHBOARD_FILES:
        path = dash / fname
        if not path.exists():
            rep.fail(f"missing {path.relative_to(REPO_ROOT)}")
            continue
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            rep.fail(f"unreadable {path.relative_to(REPO_ROOT)}: {exc}")
            continue
        required = REQUIRED_COLUMNS[fname]
        missing = required - set(df.columns)
        if missing:
            rep.fail(f"{path.name} missing columns: {sorted(missing)}")
            continue
        _FILE_VALIDATORS[fname](df, rep)
    return rep


def validate_universes(universes: list[str]) -> dict[str, ValidationReport]:
    return {u: validate_universe(u) for u in universes}


def format_report(rep: ValidationReport) -> str:
    head = f"[{'OK' if rep.ok else 'FAIL'}] {rep.universe}"
    if rep.run_dir is not None:
        head += f"  ({rep.run_dir.relative_to(REPO_ROOT)})"
    lines = [head]
    for e in rep.errors:
        lines.append(f"    error: {e}")
    for w in rep.warnings:
        lines.append(f"    warn:  {w}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Pre-sync validation of portfolio CSVs")
    ap.add_argument("--universe", action="append", default=None,
                    help="Specific universe(s). Default: all.")
    args = ap.parse_args()

    universes = args.universe or list(RUN_DIR_GLOBS.keys())
    reports = validate_universes(universes)
    any_fail = False
    for u in universes:
        rep = reports[u]
        print(format_report(rep))
        if not rep.ok:
            any_fail = True
    sys.exit(1 if any_fail else 0)
