"""L6 v2 vs legacy parallel-run diff harness.

Runs nightly (or on demand) during the L6 engine migration parallel-run
window. Loads the latest L6 v2 holdings and the latest legacy L6 holdings,
computes symbol-level + weight-level diff, and reports.

Acceptance criteria (from PRODUCTIONIZATION.md):
  - ≥ 80% holding overlap
  - Positions that differ should have rank-tie or boundary explanations
  - CAGR/Sharpe delta < 1pp on the production-window comparison

Output: tasks/MM-tuning/l6_parallel_diff.csv (one row per diff run, daily)
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def _latest_dir(pattern: str) -> Path | None:
    """Return the latest timestamped dir matching pattern.

    Only matches dirs whose name ends with a YYYYMMDD or YYYYMMDD_HHMMSS
    timestamp; ignores ad-hoc test dirs.
    """
    import re
    ts_re = re.compile(r"_(\d{8}(_\d{6}|\d{6}))$")
    dirs = [d for d in glob.glob(pattern) if ts_re.search(Path(d).name)]
    dirs = sorted(dirs, reverse=True)
    return Path(dirs[0]) if dirs else None


def _load_holdings(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Normalize column names
    if "Symbol" in df.columns and "symbol" not in df.columns:
        df = df.rename(columns={"Symbol": "symbol"})
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-pattern", type=str,
                    default=str(ROOT / "experiments/final_portfolio/final_portfolio_*"),
                    help="Glob pattern for legacy L6 timestamped dirs")
    ap.add_argument("--v2-pattern", type=str,
                    default=str(ROOT / "data/l6_v2_portfolios/l6_v2_portfolio_*"),
                    help="Glob pattern for L6 v2 timestamped dirs")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "tasks/MM-tuning/l6_parallel_diff.csv")
    args = ap.parse_args()

    legacy_dir = _latest_dir(args.legacy_pattern)
    v2_dir = _latest_dir(args.v2_pattern)

    if legacy_dir is None:
        print(f"ERROR: no legacy dir match: {args.legacy_pattern}")
        sys.exit(1)
    if v2_dir is None:
        print(f"ERROR: no v2 dir match: {args.v2_pattern}")
        sys.exit(1)

    print(f"[legacy] {legacy_dir.name}")
    print(f"[v2]     {v2_dir.name}")

    # Try a few common legacy holdings paths
    legacy_holdings_paths = [
        legacy_dir / "backtests" / "baseline" / "momentum_holdings.csv",
        legacy_dir / "momentum_holdings.csv",
        legacy_dir / "holdings.csv",
    ]
    legacy_holdings = pd.DataFrame()
    legacy_used = None
    for p in legacy_holdings_paths:
        if p.exists():
            legacy_holdings = _load_holdings(p)
            legacy_used = p
            break
    if legacy_holdings.empty:
        # Final fallback: production CSV at data/final_portfolio
        prod = ROOT / "data/final_portfolio/final_portfolio_24.csv"
        if prod.exists():
            legacy_holdings = _load_holdings(prod)
            legacy_used = prod

    v2_holdings_path = v2_dir / "backtests" / "baseline" / "momentum_holdings.csv"
    v2_holdings = _load_holdings(v2_holdings_path)

    print(f"[legacy holdings] {legacy_used}  →  {len(legacy_holdings)} positions")
    print(f"[v2 holdings]     {v2_holdings_path}  →  {len(v2_holdings)} positions")

    if legacy_holdings.empty or v2_holdings.empty:
        print("ERROR: one or both holdings sets empty")
        sys.exit(1)

    legacy_syms = set(legacy_holdings["symbol"].astype(str).str.strip())
    v2_syms = set(v2_holdings["symbol"].astype(str).str.strip())

    overlap = legacy_syms & v2_syms
    only_legacy = legacy_syms - v2_syms
    only_v2 = v2_syms - legacy_syms

    overlap_pct = 100.0 * len(overlap) / max(len(legacy_syms), len(v2_syms))

    print(f"\n=== HOLDINGS DIFF ===")
    print(f"  Overlap:     {len(overlap)} / {len(legacy_syms)} legacy "
          f"({overlap_pct:.1f}%)")
    print(f"  Only legacy: {len(only_legacy)} symbols: {sorted(only_legacy)}")
    print(f"  Only v2:     {len(only_v2)} symbols: {sorted(only_v2)}")

    pass_threshold = 80.0
    status = "PASS" if overlap_pct >= pass_threshold else "FAIL"
    print(f"\n  Acceptance threshold: {pass_threshold:.0f}% overlap → {status}")

    # Append to historical diff log
    row = {
        "date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "legacy_dir": legacy_dir.name,
        "v2_dir": v2_dir.name,
        "legacy_n": len(legacy_syms),
        "v2_n": len(v2_syms),
        "overlap_n": len(overlap),
        "overlap_pct": round(overlap_pct, 1),
        "only_legacy": ";".join(sorted(only_legacy)),
        "only_v2": ";".join(sorted(only_v2)),
        "status": status,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        existing = pd.read_csv(args.output)
        out_df = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    else:
        out_df = pd.DataFrame([row])
    out_df.to_csv(args.output, index=False)
    print(f"\n[wrote] {args.output} (log of {len(out_df)} diff runs)")

    if status == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
