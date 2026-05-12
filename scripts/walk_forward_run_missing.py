"""Walk-forward Phase 4b — run OOS backtests for missing (window, config) combos.

Reads `alt_metrics/missing_configs.csv` filtered to a chosen (strategy, metric)
and runs OOS backtests for each (strategy, universe, window, config_id) tuple
using the same Context + run_one_backtest machinery as run_walk_forward.py.

Output: tasks/walk_forward/results/alt_metrics/oos_runs_<metric>_<strategy>/
  - per-row OOS Sharpe/CAGR/DD
  - aggregated_<metric>.csv: full-sample (78 windows) OOS Sharpe per metric,
    combining existing chal/base/worst lookups with the new runs

Usage:
    python scripts/walk_forward_run_missing.py --strategy om25_v3 --metric calmar
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_walk_forward import (
    Context, WINDOWS, OM25_GRID, TL25_GRID, _config_id, run_one_backtest,
)
from scripts.multi_window_oos_eval import period_metrics


def _grid_for(strategy: str) -> list[dict]:
    return TL25_GRID if strategy == "tl25_v3" else OM25_GRID


def _params_by_id(strategy: str, cid: str) -> dict | None:
    for p in _grid_for(strategy):
        if _config_id(strategy, p) == cid:
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["tl25_v3", "om25_v3"], required=True)
    ap.add_argument("--metric", choices=["sharpe", "calmar", "multi", "composite"],
                    required=True)
    ap.add_argument("--missing-csv", type=Path,
                    default=ROOT / "tasks/walk_forward/results/alt_metrics/missing_configs.csv")
    ap.add_argument("--alt-vs-sharpe", type=Path,
                    default=ROOT / "tasks/walk_forward/results/alt_metrics/alt_vs_sharpe.csv")
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path,
                    default=ROOT / "indices_data_historical/NIFTY_100.csv")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "tasks/walk_forward/results/alt_metrics")
    args = ap.parse_args()

    missing = pd.read_csv(args.missing_csv)
    target = missing[(missing["strategy"] == args.strategy)
                     & (missing["metric"] == args.metric)].copy()
    if target.empty:
        print(f"[done] no missing configs for {args.strategy}/{args.metric}")
        return

    universes_needed = sorted(target["universe"].unique().tolist())
    print(f"[run] {len(target)} missing OOS backtests for {args.strategy}/{args.metric} "
          f"across universes {universes_needed}")

    ctx = Context(
        prices_dir=args.prices_dir, benchmark_path=args.benchmark,
        regime_index_path=args.regime_index, universes=universes_needed,
    )

    rows = []
    t0 = time.time()
    for _, r in target.iterrows():
        uni = r["universe"]; wid = r["window_id"]; cid = r["config_id"]
        params = _params_by_id(args.strategy, cid)
        if params is None:
            print(f"  skip — unknown config_id {cid}")
            continue
        is_start, is_end, oos_start, oos_end = WINDOWS[wid]
        res = run_one_backtest(args.strategy, params, ctx, uni, oos_start, oos_end)
        if res is None or res.get("equity") is None or res["equity"].empty:
            print(f"  {uni}/{wid}/{cid}: no equity")
            rows.append({
                "strategy": args.strategy, "universe": uni, "window_id": wid,
                "config_id": cid, "oos_sharpe": None, "oos_cagr_pct": None,
                "oos_max_dd_pct": None, "n_trades": 0,
            })
            continue
        m = period_metrics(res["equity"], "oos", oos_start, oos_end)
        rows.append({
            "strategy": args.strategy, "universe": uni, "window_id": wid,
            "config_id": cid,
            "oos_sharpe": m.get("sharpe"),
            "oos_cagr_pct": m.get("cagr_pct"),
            "oos_max_dd_pct": m.get("max_dd_pct"),
            "n_trades": len(res["trades"]) if res.get("trades") is not None else 0,
        })
        print(f"  {uni}/{wid}/{cid}: OOS Sharpe={m.get('sharpe')} "
              f"DD={m.get('max_dd_pct')}", flush=True)
    print(f"[done] {len(rows)} OOS runs in {time.time()-t0:.1f}s")

    new_runs_df = pd.DataFrame(rows)
    out_path = args.output / f"oos_runs_{args.metric}_{args.strategy}.csv"
    new_runs_df.to_csv(out_path, index=False)
    print(f"[wrote] {out_path}")

    # === Aggregate: combine with existing alt_vs_sharpe lookups ===
    alt = pd.read_csv(args.alt_vs_sharpe)
    alt_s = alt[alt["strategy"] == args.strategy].copy()
    # Take metric-specific columns from alt and stitch in new OOS where missing
    pick_col = f"{args.metric}_pick"
    oos_col = f"{args.metric}_oos"
    match_col = f"{args.metric}_match"

    new_lookup = new_runs_df.set_index(["universe", "window_id"])["oos_sharpe"].to_dict()
    # Merge: for rows missing OOS, look up by (universe, window_id)
    def fill_missing(r):
        if r[match_col] == "missing":
            return new_lookup.get((r["universe"], r["window_id"]))
        return r[oos_col]
    alt_s[f"{args.metric}_oos_full"] = alt_s.apply(fill_missing, axis=1)

    # Summary
    full = alt_s.dropna(subset=[f"{args.metric}_oos_full"])
    base = full["baseline_oos"]
    new_full = full[f"{args.metric}_oos_full"]
    sharpe_full = full["sharpe_oos"]

    print(f"\n{'=' * 90}")
    print(f"{args.strategy} — {args.metric} vs Sharpe (FULL SAMPLE, n={len(full)} windows)")
    print(f"{'=' * 90}")
    summary = pd.DataFrame([
        {"metric": "Sharpe (current)",
         "n_windows": len(full),
         "mean_oos_sharpe": round(sharpe_full.mean(), 3),
         "median_oos_sharpe": round(sharpe_full.median(), 3),
         "mean_vs_baseline": round((sharpe_full - base).mean(), 3),
         "pass_count": int((sharpe_full >= 0.7).sum()),
         "pass_rate_pct": round((sharpe_full >= 0.7).mean() * 100, 1)},
        {"metric": f"{args.metric.capitalize()} (alternative)",
         "n_windows": len(full),
         "mean_oos_sharpe": round(new_full.mean(), 3),
         "median_oos_sharpe": round(new_full.median(), 3),
         "mean_vs_baseline": round((new_full - base).mean(), 3),
         "pass_count": int((new_full >= 0.7).sum()),
         "pass_rate_pct": round((new_full >= 0.7).mean() * 100, 1)},
    ])
    print(summary.to_string(index=False))

    # Per-universe breakdown
    print(f"\nPer-universe breakdown ({args.strategy} / {args.metric}):")
    by_uni = []
    for u in sorted(full["universe"].unique()):
        sub = full[full["universe"] == u]
        if sub.empty:
            continue
        by_uni.append({
            "universe": u,
            "n": len(sub),
            "sharpe_pick_mean": round(sub["sharpe_oos"].mean(), 3),
            "alt_pick_mean": round(sub[f"{args.metric}_oos_full"].mean(), 3),
            "delta": round((sub[f"{args.metric}_oos_full"] - sub["sharpe_oos"]).mean(), 3),
            "alt_pass_rate": round((sub[f"{args.metric}_oos_full"] >= 0.7).mean() * 100, 1),
        })
    print(pd.DataFrame(by_uni).to_string(index=False))

    agg_path = args.output / f"aggregated_{args.metric}_{args.strategy}.csv"
    alt_s.to_csv(agg_path, index=False)
    print(f"\n[wrote] {agg_path}")


if __name__ == "__main__":
    main()
