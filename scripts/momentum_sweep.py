"""Momentum IS/OOS sweep — one parameter at a time.

Per parameter dimension:
  - Run an IS sweep across candidate values (with all other params locked
    at the current BASELINE).
  - Print per-config IS metrics (CAGR, Sharpe, Sortino, Calmar, MaxDD,
    Turnover proxy, n_trades).
  - Wait for the user to lock a value; then move to the next parameter.

Usage:
    # Run a single param's IS sweep:
    python scripts/momentum_sweep.py --param lookback_months \\
        --values 3 6 9 12 \\
        --is-start 2009-09-01 --is-end 2016-12-31

    # OOS check of one config:
    python scripts/momentum_sweep.py --param lookback_months --values 6 \\
        --is-start 2009-09-01 --is-end 2016-12-31 \\
        --oos-start 2017-01-01 --oos-end 2026-05-08

Locked params (between sweeps) are passed via --lock key=value flags:
    --lock lookback_months=6 --lock top_n=24 ...
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


# ============================================================
# Param parsing
# ============================================================

INT_PARAMS = {"top_n", "skip_days", "min_hold_days", "exit_buffer",
              "lookback_months"}
FLOAT_PARAMS = {"vol_floor", "vol_power", "max_weight", "slippage"}
BOOL_PARAMS = {"cross_sectional_zscore"}
STR_PARAMS = {"rebalance", "universe_csv"}


def _coerce(key, val):
    if key in INT_PARAMS:
        return int(val)
    if key in FLOAT_PARAMS:
        return float(val)
    if key in BOOL_PARAMS:
        return str(val).lower() in ("true", "1", "yes")
    return val


def _parse_locks(lock_strs):
    locks = {}
    for s in lock_strs or []:
        if "=" not in s:
            raise SystemExit(f"bad --lock {s!r}; want key=value")
        k, v = s.split("=", 1)
        if k not in BASELINE:
            raise SystemExit(f"unknown lock key {k!r}; valid: {list(BASELINE.keys())}")
        locks[k] = _coerce(k, v)
    return locks


def _parse_values(param, values):
    return [_coerce(param, v) for v in values]


# ============================================================
# Metric formatting
# ============================================================

def _calmar(cagr_pct, max_dd_pct):
    if max_dd_pct is None or pd.isna(max_dd_pct) or abs(max_dd_pct) < 1e-6:
        return None
    return cagr_pct / abs(max_dd_pct)


def _sortino(eq):
    rets = eq["pv"].astype(float).pct_change().dropna()
    if rets.empty:
        return None
    downside = rets[rets < 0]
    if downside.empty or downside.std() == 0:
        return None
    excess = rets.mean() * 252 - 0.05
    return excess / (downside.std() * math.sqrt(252))


def _summary_row(label, config, res, start, end):
    if res is None or res.get("equity") is None or res["equity"].empty:
        return {"label": label, "config_str": label, "n_trades": 0, "error": "no equity"}
    eq = res["equity"]; trades = res["trades"]; exits = res["exits"]
    m = period_metrics(eq, "x", start, end)
    cagr = m.get("cagr_pct")
    dd = m.get("max_dd_pct")
    sortino = _sortino(eq)
    calmar = _calmar(cagr, dd)
    # Turnover proxy: round trips per year
    yrs = (pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25
    rt_per_year = len(exits) / yrs if yrs > 0 else 0
    return {
        "label": label,
        **{k: v for k, v in config.items() if k != "universe_csv"},
        "n_trades": len(trades),
        "n_exits": len(exits),
        "cagr_pct": round(cagr, 2) if cagr is not None else None,
        "sharpe": round(m.get("sharpe"), 2) if m.get("sharpe") is not None else None,
        "sortino": round(sortino, 2) if sortino is not None else None,
        "calmar": round(calmar, 2) if calmar is not None else None,
        "vol_pct": round(m.get("vol_pct"), 2) if m.get("vol_pct") is not None else None,
        "max_dd_pct": round(dd, 2) if dd is not None else None,
        "rt_per_year": round(rt_per_year, 1),
    }


# ============================================================
# Sweep driver
# ============================================================

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--param", required=True,
                    help="Param to sweep, e.g. lookback_months / top_n / vol_floor")
    ap.add_argument("--values", nargs="+", required=True,
                    help="Candidate values for the swept param")
    ap.add_argument("--lock", action="append", default=[],
                    help="Lock a baseline override, key=value (repeatable)")
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--universe", type=Path, default=None,
                    help="Override universe CSV (default: BASELINE / locks)")
    ap.add_argument("--is-start", default="2009-09-01")
    ap.add_argument("--is-end", default="2016-12-31")
    ap.add_argument("--oos-start", default=None, help="If set, also run OOS")
    ap.add_argument("--oos-end", default="2026-05-08")
    ap.add_argument("--output", type=Path, default=ROOT / "tasks/mm_tuning/sweeps")
    return ap.parse_args()


def main():
    args = parse_args()
    locks = _parse_locks(args.lock)
    param = args.param
    if param not in BASELINE:
        raise SystemExit(f"unknown --param {param!r}; valid: {list(BASELINE.keys())}")
    values = _parse_values(param, args.values)
    print(f"[sweep] param={param}  values={values}")
    print(f"        locks={locks}")
    print(f"        IS  {args.is_start} → {args.is_end}")
    if args.oos_start:
        print(f"        OOS {args.oos_start} → {args.oos_end}")

    args.output.mkdir(parents=True, exist_ok=True)

    # Load panels once
    t0 = time.time()
    print(f"[load] price panels {args.prices_dir.name} ...")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    # Universe (locks > arg > BASELINE)
    uni_csv = (locks.get("universe_csv") or
               (str(args.universe) if args.universe else BASELINE["universe_csv"]))
    if not str(uni_csv).startswith("/"):
        uni_csv = ROOT / uni_csv
    print(f"[load] universe {Path(uni_csv).name}")
    universe = load_universe(Path(uni_csv))
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  matched {len(cols)} symbols, setup in {time.time()-t0:.1f}s")

    # Pre-compute panels per (lookback_months, skip_days) combo only when those vary;
    # otherwise a single panel build covers all sweep values.
    panel_cache: dict[tuple[int, int], dict] = {}

    def _get_panels(lb_months, skip):
        key = (lb_months, skip)
        if key not in panel_cache:
            panel_cache[key] = build_momentum_panels(
                close_uni,
                lookback_days=lookback_months_to_days(lb_months),
                skip_days=skip,
            )
        return panel_cache[key]

    # === IS sweep ===
    is_rows = []
    for v in values:
        config = {**BASELINE, **locks, param: v}
        lb_m = config["lookback_months"]
        skip = config["skip_days"]
        panels = _get_panels(lb_m, skip)
        label = f"{param}={v}"
        t_run = time.time()
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start=args.is_start, end=args.is_end, config=config,
        )
        row = _summary_row(label, config, res, args.is_start, args.is_end)
        elapsed = time.time() - t_run
        print(f"  [IS] {label}  CAGR={row.get('cagr_pct')}  "
              f"Sharpe={row.get('sharpe')}  Calmar={row.get('calmar')}  "
              f"DD={row.get('max_dd_pct')}  RT/yr={row.get('rt_per_year')}  "
              f"({elapsed:.1f}s)",
              flush=True)
        is_rows.append(row)

    is_df = pd.DataFrame(is_rows)
    is_path = args.output / f"is_{param}.csv"
    is_df.to_csv(is_path, index=False)
    print(f"\n[wrote] {is_path}")

    # Pretty print sorted by Sharpe + Calmar
    print(f"\n{'=' * 100}")
    print(f"IS sweep — {param}  (locks: {locks})")
    print(f"{'=' * 100}")
    show_cols = ["label", "cagr_pct", "sharpe", "sortino", "calmar",
                 "vol_pct", "max_dd_pct", "rt_per_year", "n_trades"]
    show_cols = [c for c in show_cols if c in is_df.columns]
    print(is_df[show_cols].to_string(index=False))

    # === Optional OOS run ===
    if args.oos_start:
        oos_rows = []
        print(f"\n[OOS] running {len(values)} configs ...")
        for v in values:
            config = {**BASELINE, **locks, param: v}
            panels = _get_panels(config["lookback_months"], config["skip_days"])
            label = f"{param}={v}"
            res = run_momentum(
                close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
                start=args.oos_start, end=args.oos_end, config=config,
            )
            row = _summary_row(label, config, res, args.oos_start, args.oos_end)
            print(f"  [OOS] {label}  CAGR={row.get('cagr_pct')}  "
                  f"Sharpe={row.get('sharpe')}  Calmar={row.get('calmar')}  "
                  f"DD={row.get('max_dd_pct')}", flush=True)
            oos_rows.append(row)
        oos_df = pd.DataFrame(oos_rows)
        oos_path = args.output / f"oos_{param}.csv"
        oos_df.to_csv(oos_path, index=False)
        print(f"\n[wrote] {oos_path}")
        print(f"\n{'=' * 100}")
        print(f"OOS — {param}  (locks: {locks})")
        print(f"{'=' * 100}")
        print(oos_df[show_cols].to_string(index=False))


if __name__ == "__main__":
    main()
