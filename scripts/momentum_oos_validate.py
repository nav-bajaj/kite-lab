"""Momentum OOS validation across 8 IS-tuned tracks + production baseline.

Runs each config on OOS 2017-01 → 2026-05, then slices into A/B/C sub-windows
and the full OOS. Reports pass/fail per track using the oos_retune_2026
criteria:
  - OOS_full Sharpe >= 1.0
  - Each sub-window Sharpe >= 0.7
  - OOS_full Max DD >= -45%

Output: tasks/MM-tuning/oos_validation.csv  (full results)
        tasks/MM-tuning/oos_summary.csv     (one row per track)
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._momentum_engine import (
    BASELINE, build_momentum_panels, run_momentum,
    lookback_months_to_days,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics


# 8 IS-tuned tracks (from sequential param sweeps)
TRACKS = [
    # (label, config_overrides)
    ("PRODUCTION (current)", dict(  # baseline for direct comparison
        lookback_months=6, top_n=24, min_hold_days=8,
        vol_floor=0.05, skip_days=0, vol_power=1.0,
        exit_buffer=0, rebalance="weekly",
    )),
    ("A1_b0 (L6 vf01 vp.5 buf0)", dict(
        lookback_months=6, vol_floor=0.01, vol_power=0.5,
        skip_days=5, exit_buffer=0,
    )),
    ("A1_b6 (L6 vf01 vp.5 buf6)", dict(
        lookback_months=6, vol_floor=0.01, vol_power=0.5,
        skip_days=5, exit_buffer=6,
    )),
    ("A2_b0 (L6 vf05 vp1 buf0)", dict(
        lookback_months=6, vol_floor=0.05, vol_power=1.0,
        skip_days=5, exit_buffer=0,
    )),
    ("A2_b6 (L6 vf05 vp1 buf6)", dict(
        lookback_months=6, vol_floor=0.05, vol_power=1.0,
        skip_days=5, exit_buffer=6,
    )),
    ("B1_b0 (L9 vf01 vp.5 buf0)", dict(
        lookback_months=9, vol_floor=0.01, vol_power=0.5,
        skip_days=5, exit_buffer=0,
    )),
    ("B1_b6 (L9 vf01 vp.5 buf6)", dict(
        lookback_months=9, vol_floor=0.01, vol_power=0.5,
        skip_days=5, exit_buffer=6,
    )),
    ("B2_b0 (L9 vf05 vp1 buf0)", dict(
        lookback_months=9, vol_floor=0.05, vol_power=1.0,
        skip_days=5, exit_buffer=0,
    )),
    ("B2_b6 (L9 vf05 vp1 buf6)", dict(
        lookback_months=9, vol_floor=0.05, vol_power=1.0,
        skip_days=5, exit_buffer=6,
    )),
]

WINDOWS = [
    ("IS",       "2009-09-01", "2016-12-31"),
    ("OOS_A",    "2017-01-01", "2019-12-31"),
    ("OOS_B",    "2020-01-01", "2022-12-31"),
    ("OOS_C",    "2023-01-01", "2026-05-08"),
    ("OOS_full", "2017-01-01", "2026-05-08"),
]


def _calmar(cagr_pct, max_dd_pct):
    if max_dd_pct is None or pd.isna(max_dd_pct) or abs(max_dd_pct) < 1e-6:
        return None
    return cagr_pct / abs(max_dd_pct)


def _sortino_window(eq, start, end):
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    sub = eq[(eq["date"] >= s) & (eq["date"] <= e)]
    if len(sub) < 5:
        return None
    rets = sub["pv"].astype(float).pct_change().dropna()
    if rets.empty:
        return None
    downside = rets[rets < 0]
    if downside.empty or downside.std() == 0:
        return None
    excess = rets.mean() * 252 - 0.05
    return excess / (downside.std() * math.sqrt(252))


def evaluate_one(track_label, config, ctx, full_start="2009-09-01",
                  full_end="2026-05-08"):
    """Run one config over the full panel, slice into IS + OOS windows."""
    cfg = {**BASELINE, **config}
    panels = build_momentum_panels(
        ctx["close_uni"],
        lookback_days=lookback_months_to_days(cfg["lookback_months"]),
        skip_days=cfg["skip_days"],
    )
    res = run_momentum(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        panels=panels, sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        start=full_start, end=full_end, config=config,
    )
    if res is None or res["equity"].empty:
        return None, []
    eq = res["equity"]
    rows = []
    for window_id, start, end in WINDOWS:
        m = period_metrics(eq, window_id, start, end)
        cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
        rows.append({
            "track": track_label,
            "window": window_id, "start": start, "end": end,
            "cagr_pct": cagr, "sharpe": sh,
            "vol_pct": m.get("vol_pct"),
            "max_dd_pct": dd,
            "sortino": _sortino_window(eq, start, end),
            "calmar": _calmar(cagr, dd),
        })
    return res, rows


def passes(per_window_rows):
    """Return (pass_bool, reasons)."""
    by = {r["window"]: r for r in per_window_rows}
    reasons = []
    is_sh = by.get("IS", {}).get("sharpe")
    oos_sh = by.get("OOS_full", {}).get("sharpe")
    oos_dd = by.get("OOS_full", {}).get("max_dd_pct")
    oos_a = by.get("OOS_A", {}).get("sharpe")
    oos_b = by.get("OOS_B", {}).get("sharpe")
    oos_c = by.get("OOS_C", {}).get("sharpe")

    is_ok = is_sh is not None and is_sh >= 1.0
    oos_full_sh_ok = oos_sh is not None and oos_sh >= 1.0
    oos_full_dd_ok = oos_dd is not None and oos_dd >= -45.0
    oos_a_ok = oos_a is not None and oos_a >= 0.7
    oos_b_ok = oos_b is not None and oos_b >= 0.7
    oos_c_ok = oos_c is not None and oos_c >= 0.7

    reasons.append(("IS_Sharpe>=1.0", is_ok, f"{is_sh:.2f}" if is_sh else "?"))
    reasons.append(("OOS_full_Sharpe>=1.0", oos_full_sh_ok, f"{oos_sh:.2f}" if oos_sh else "?"))
    reasons.append(("OOS_full_DD>=-45%", oos_full_dd_ok, f"{oos_dd:.2f}%" if oos_dd else "?"))
    reasons.append(("OOS_A_Sharpe>=0.7", oos_a_ok, f"{oos_a:.2f}" if oos_a else "?"))
    reasons.append(("OOS_B_Sharpe>=0.7", oos_b_ok, f"{oos_b:.2f}" if oos_b else "?"))
    reasons.append(("OOS_C_Sharpe>=0.7", oos_c_ok, f"{oos_c:.2f}" if oos_c else "?"))

    all_ok = is_ok and oos_full_sh_ok and oos_full_dd_ok and oos_a_ok and oos_b_ok and oos_c_ok
    return all_ok, reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--output", type=Path, default=ROOT / "tasks/MM-tuning")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    print("[load] panels ...")
    t0 = time.time()
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_universe(ROOT / BASELINE["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  panels ready in {time.time()-t0:.1f}s ({len(cols)} symbols)")

    ctx = dict(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned, sma_200=sma_200, atr_20=atr_20,
        close_uni=close_uni,
    )

    all_rows = []
    summary_rows = []
    for label, cfg in TRACKS:
        t_run = time.time()
        print(f"[run] {label} ...", flush=True)
        res, rows = evaluate_one(label, cfg, ctx)
        if res is None:
            print(f"  no result")
            continue
        all_rows.extend(rows)
        ok, reasons = passes(rows)
        by = {r["window"]: r for r in rows}
        elapsed = time.time() - t_run
        print(f"  {elapsed:.1f}s  IS Sh={by['IS']['sharpe']:.2f}  "
              f"OOS_full Sh={by['OOS_full']['sharpe']:.2f}  "
              f"CAGR={by['OOS_full']['cagr_pct']:.1f}%  "
              f"DD={by['OOS_full']['max_dd_pct']:.1f}%  "
              f"{'PASS' if ok else 'FAIL'}", flush=True)
        summary_rows.append({
            "track": label,
            "IS_sharpe": by["IS"]["sharpe"],
            "IS_cagr": by["IS"]["cagr_pct"],
            "IS_dd": by["IS"]["max_dd_pct"],
            "OOS_A_sharpe": by["OOS_A"]["sharpe"],
            "OOS_B_sharpe": by["OOS_B"]["sharpe"],
            "OOS_C_sharpe": by["OOS_C"]["sharpe"],
            "OOS_full_sharpe": by["OOS_full"]["sharpe"],
            "OOS_full_cagr": by["OOS_full"]["cagr_pct"],
            "OOS_full_dd": by["OOS_full"]["max_dd_pct"],
            "OOS_full_calmar": by["OOS_full"]["calmar"],
            "OOS_full_sortino": by["OOS_full"]["sortino"],
            "passes": ok,
            "fail_reasons": "; ".join(
                f"FAIL_{n}" for n, ok_b, _ in reasons if not ok_b),
        })

    pd.DataFrame(all_rows).to_csv(args.output / "oos_validation.csv", index=False)
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(args.output / "oos_summary.csv", index=False)

    print(f"\n{'=' * 110}")
    print("OOS VALIDATION SUMMARY")
    print(f"{'=' * 110}")
    show = ["track", "IS_sharpe", "OOS_A_sharpe", "OOS_B_sharpe",
            "OOS_C_sharpe", "OOS_full_sharpe", "OOS_full_cagr",
            "OOS_full_dd", "OOS_full_calmar", "passes"]
    print(summary_df[show].to_string(index=False))

    print(f"\n[wrote] {args.output}/oos_validation.csv")
    print(f"[wrote] {args.output}/oos_summary.csv")


if __name__ == "__main__":
    main()
