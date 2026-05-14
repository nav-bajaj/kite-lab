"""Run all 9 momentum configs on the production data window (2020-07 → today)
and compare to the live-portfolio numbers we see in `data/final_portfolio/`.

Same 9 tracks as momentum_oos_validate.py — but here the window is the actual
deployment period of the live momentum portfolio, not the OOS slice.

Purpose: establish what _momentum_engine.py produces for the current
production config on the same window where CLAUDE.md claims
59.4% CAGR / 1.92 Sharpe / -30% MaxDD. Any meaningful gap is a flag for
deeper investigation (e.g., production uses different signal builder, different
universe filtering, different pricing).
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

from scripts.momentum_oos_validate import TRACKS


WINDOW_START = "2020-07-10"   # matches the production-report start
WINDOW_END   = "2026-05-08"


def _calmar(c, d):
    if d is None or pd.isna(d) or abs(d) < 1e-6:
        return None
    return c / abs(d)


def _sortino(eq, start, end):
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    sub = eq[(eq["date"] >= s) & (eq["date"] <= e)]
    if len(sub) < 5: return None
    rets = sub["pv"].astype(float).pct_change().dropna()
    if rets.empty: return None
    downside = rets[rets < 0]
    if downside.empty or downside.std() == 0: return None
    excess = rets.mean() * 252 - 0.05
    return excess / (downside.std() * math.sqrt(252))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--output", type=Path, default=ROOT / "tasks/MM-tuning")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"[load] panels {args.prices_dir.name} ...")
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

    rows = []
    for label, cfg in TRACKS:
        cfg_full = {**BASELINE, **cfg}
        # Build panels for this (lookback, skip) tuple
        panels = build_momentum_panels(
            close_uni,
            lookback_days=lookback_months_to_days(cfg_full["lookback_months"]),
            skip_days=cfg_full["skip_days"],
        )
        # Run on FULL panel (so warmup is complete) then slice metrics to window
        t_run = time.time()
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start="2009-09-01", end=WINDOW_END, config=cfg,
        )
        if res is None or res["equity"].empty:
            continue
        eq = res["equity"]
        m = period_metrics(eq, "window", WINDOW_START, WINDOW_END)
        cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct")
        # Round trips per year over the window
        exits = res["exits"]
        exits = exits[pd.to_datetime(exits["exit_date"]) >= pd.Timestamp(WINDOW_START)]
        yrs = (pd.Timestamp(WINDOW_END) - pd.Timestamp(WINDOW_START)).days / 365.25
        rt_per_year = len(exits) / yrs if yrs > 0 else 0
        elapsed = time.time() - t_run
        rows.append({
            "track": label,
            "cagr_pct": round(cagr, 2) if cagr is not None else None,
            "sharpe": round(m.get("sharpe"), 2) if m.get("sharpe") is not None else None,
            "sortino": round(_sortino(eq, WINDOW_START, WINDOW_END), 2)
                        if _sortino(eq, WINDOW_START, WINDOW_END) is not None else None,
            "calmar": round(_calmar(cagr, dd), 2) if _calmar(cagr, dd) is not None else None,
            "vol_pct": round(m.get("vol_pct"), 2) if m.get("vol_pct") is not None else None,
            "max_dd_pct": round(dd, 2) if dd is not None else None,
            "rt_per_year": round(rt_per_year, 1),
            "n_trades": len(res["trades"]),
        })
        print(f"  {label:32s} CAGR={cagr:.2f}%  Sharpe={m.get('sharpe'):.2f}  "
              f"DD={dd:.2f}%  Calmar={_calmar(cagr, dd):.2f}  RT/yr={rt_per_year:.1f}  "
              f"({elapsed:.1f}s)", flush=True)

    df = pd.DataFrame(rows)
    out_csv = args.output / "production_window_compare.csv"
    df.to_csv(out_csv, index=False)

    print(f"\n{'=' * 110}")
    print(f"PRODUCTION WINDOW COMPARISON — {WINDOW_START} → {WINDOW_END}")
    print(f"  Live production claim (CLAUDE.md): CAGR 59.4% / Sharpe 1.92 / MaxDD -30.0%")
    print(f"{'=' * 110}")
    print(df.to_string(index=False))
    print(f"\n[wrote] {out_csv}")


if __name__ == "__main__":
    main()
