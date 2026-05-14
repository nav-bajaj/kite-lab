"""Test trailing %-from-peak drawdown stops on L6 production config.

Sweeps drawdown_stop ∈ {0 (current), 15%, 20%, 25%} with all other production
params held constant (L6, top24, min_hold=8, vf=0.05, vp=1.0, skip=0, buf=0,
Thursday signals).

Reports IS (2009-2016), OOS_full (2017-2026), OOS sub-windows, and the
production window (2020-07+).
"""
from __future__ import annotations

import math
import sys
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


WINDOWS = [
    ("IS",          "2009-09-01", "2016-12-31"),
    ("OOS_A",       "2017-01-01", "2019-12-31"),
    ("OOS_B",       "2020-01-01", "2022-12-31"),
    ("OOS_C",       "2023-01-01", "2026-05-08"),
    ("OOS_full",    "2017-01-01", "2026-05-08"),
    ("Prod window", "2020-07-10", "2026-05-08"),
]


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
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_universe(ROOT / BASELINE["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    panels = build_momentum_panels(
        close_uni,
        lookback_days=lookback_months_to_days(BASELINE["lookback_months"]),
        skip_days=BASELINE["skip_days"],
    )
    print(f"  {len(cols)} symbols\n")

    stops = [0.0, 0.15, 0.20, 0.25]
    all_rows = []
    for stop in stops:
        label = "PRODUCTION (no stop)" if stop == 0.0 else f"+ {int(stop*100)}% trailing stop"
        cfg = {"drawdown_stop": stop}  # everything else BASELINE
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start="2009-09-01", end="2026-05-08", config=cfg,
        )
        eq = res["equity"]; trades = res["trades"]; exits = res["exits"]
        # Count stop-fires (atr_stop reason)
        n_stops = (exits["reason"] == "atr_stop").sum() if "reason" in exits.columns else 0
        n_rank = (exits["reason"] == "rank").sum() if "reason" in exits.columns else 0
        for w_id, start, end in WINDOWS:
            m = period_metrics(eq, w_id, start, end)
            cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
            all_rows.append({
                "stop": label, "stop_pct": stop * 100, "window": w_id,
                "cagr_pct": round(cagr, 2) if cagr is not None else None,
                "sharpe_rf0": round(sh, 2) if sh is not None else None,
                "calmar": round(_calmar(cagr, dd), 2) if _calmar(cagr, dd) is not None else None,
                "max_dd_pct": round(dd, 2) if dd is not None else None,
                "sortino": round(_sortino(eq, start, end), 2) if _sortino(eq, start, end) is not None else None,
                "n_exits_window": int(((pd.to_datetime(exits["exit_date"]) >= pd.Timestamp(start))
                                        & (pd.to_datetime(exits["exit_date"]) <= pd.Timestamp(end))).sum())
                                   if not exits.empty else 0,
            })
        print(f"  {label}: total exits = {len(exits)}  "
              f"(rank={n_rank}, atr_stop={n_stops})", flush=True)

    df = pd.DataFrame(all_rows)
    out_dir = ROOT / "tasks/MM-tuning"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dd_stop_test.csv"
    df.to_csv(out_path, index=False)

    # Pretty print as pivot
    print(f"\n{'=' * 110}")
    print("L6 momentum + trailing %-from-peak drawdown stop (production config + stop)")
    print(f"{'=' * 110}")
    for metric in ["cagr_pct", "sharpe_rf0", "calmar", "max_dd_pct"]:
        pivot = df.pivot(index="window", columns="stop", values=metric).reindex(
            ["IS", "OOS_A", "OOS_B", "OOS_C", "OOS_full", "Prod window"])
        print(f"\n{metric}:")
        print(pivot.to_string())

    print(f"\n[wrote] {out_path}")


if __name__ == "__main__":
    main()
