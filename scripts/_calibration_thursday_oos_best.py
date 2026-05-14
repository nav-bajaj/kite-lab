"""OOS-validate the Thursday-IS-best candidate against production.

After re-running the IS sweep with the corrected Thursday-signal default,
the IS-best parameters shifted (min_hold 8→15, exit_buffer 6→12, skip 21→5).
Test whether this corrected candidate beats production on OOS 2017-2026.

If yes, the retune was real but the original Friday-handicap masked it.
If no, the retune was an artifact and production remains the right config.
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
    ("IS",       "2009-09-01", "2016-12-31"),
    ("OOS_A",    "2017-01-01", "2019-12-31"),
    ("OOS_B",    "2020-01-01", "2022-12-31"),
    ("OOS_C",    "2023-01-01", "2026-05-08"),
    ("OOS_full", "2017-01-01", "2026-05-08"),
]


# Thursday-IS-best candidates (rebuilt after correcting signal_day default)
TRACKS = [
    ("PRODUCTION", dict(
        lookback_months=6, top_n=24, min_hold_days=8,
        vol_floor=0.05, vol_power=1.0, skip_days=0, exit_buffer=0,
    )),
    # Apply IS-best on Thursday signals — L6 track
    ("Thu_IS_best_L6 (min15, vf01, vp.5, skip5, buf12)", dict(
        lookback_months=6, top_n=24, min_hold_days=15,
        vol_floor=0.01, vol_power=0.5, skip_days=5, exit_buffer=12,
    )),
    # L9 variant of same
    ("Thu_IS_best_L9 (min15, vf01, vp.5, skip5, buf12)", dict(
        lookback_months=9, top_n=24, min_hold_days=15,
        vol_floor=0.01, vol_power=0.5, skip_days=5, exit_buffer=12,
    )),
    # L12 emerged as Sharpe-best on Thursday lookback sweep
    ("Thu_IS_best_L12 (min15, vf01, vp.5, skip5, buf12)", dict(
        lookback_months=12, top_n=24, min_hold_days=15,
        vol_floor=0.01, vol_power=0.5, skip_days=5, exit_buffer=12,
    )),
    # Conservative variant: L6 with vol_floor=0.05 (pure momentum) and min=15, buf=12
    ("Thu_conservative_L6 (min15, vf05, vp1, skip5, buf12)", dict(
        lookback_months=6, top_n=24, min_hold_days=15,
        vol_floor=0.05, vol_power=1.0, skip_days=5, exit_buffer=12,
    )),
    # Earlier OOS winner (Thursday signals)
    ("Earlier_OOS_winner B1_b6 (Thu)", dict(
        lookback_months=9, top_n=24, min_hold_days=8,
        vol_floor=0.01, vol_power=0.5, skip_days=5, exit_buffer=6,
    )),
]


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
    print(f"  {len(cols)} symbols\n")

    panel_cache = {}
    summary = []
    for label, cfg in TRACKS:
        lb_m = cfg.get("lookback_months", BASELINE["lookback_months"])
        skip = cfg.get("skip_days", BASELINE["skip_days"])
        key = (lb_m, skip)
        if key not in panel_cache:
            panel_cache[key] = build_momentum_panels(
                close_uni,
                lookback_days=lookback_months_to_days(lb_m),
                skip_days=skip,
            )
        panels = panel_cache[key]
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start="2009-09-01", end="2026-05-08", config=cfg,
        )
        if res is None or res["equity"].empty:
            continue
        eq = res["equity"]
        row = {"track": label}
        for w_id, start, end in WINDOWS:
            m = period_metrics(eq, w_id, start, end)
            cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct")
            row[f"{w_id}_cagr"] = round(cagr, 2) if cagr is not None else None
            row[f"{w_id}_sharpe"] = round(m.get("sharpe"), 2) if m.get("sharpe") is not None else None
            row[f"{w_id}_dd"] = round(dd, 2) if dd is not None else None
        summary.append(row)
        print(f"  {label:60s}  "
              f"IS Sh={row.get('IS_sharpe')}  OOS Sh={row.get('OOS_full_sharpe')}  "
              f"OOS CAGR={row.get('OOS_full_cagr')}%  OOS DD={row.get('OOS_full_dd')}%")

    df = pd.DataFrame(summary)
    print(f"\n{'=' * 110}")
    print("THURSDAY-IS-BEST CANDIDATES vs PRODUCTION (all on Thursday signals)")
    print(f"{'=' * 110}")
    show = ["track", "IS_sharpe", "OOS_A_sharpe", "OOS_B_sharpe",
            "OOS_C_sharpe", "OOS_full_sharpe", "OOS_full_cagr", "OOS_full_dd"]
    print(df[show].to_string(index=False))

    out = ROOT / "tasks/MM-tuning/thursday_oos_best.csv"
    df.to_csv(out, index=False)
    print(f"\n[wrote] {out}")


if __name__ == "__main__":
    main()
