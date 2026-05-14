"""L6 momentum + regime filter sweep.

Tests the NIFTY 100 regime filter (same one used in OM25 v3) layered on top
of L6 production config. Reduces gross exposure to `bear_exposure` when
NIFTY 100 closes below its MA for `confirm_days` consecutive days.

Sweeps:
  ma_window ∈ {100, 200}
  confirm_days ∈ {0, 3}
  bear_exposure ∈ {0.0, 0.25, 0.50, 1.0}  (1.0 = no de-risk = baseline)

Reports IS, OOS sub-windows, OOS_full, and Production window.
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
from scripts.om25_v3 import build_regime_panel_confirmed
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
    if d is None or pd.isna(d) or abs(d) < 1e-6: return None
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

    # Pre-compute regime panels for the configs we want
    regime_cache = {}
    def get_regime(ma_window, confirm_days):
        key = (ma_window, confirm_days)
        if key not in regime_cache:
            regime_cache[key] = build_regime_panel_confirmed(
                ROOT / "indices_data_historical/NIFTY_100.csv",
                ma_window, confirm_days, calendar=calendar,
            )
        return regime_cache[key]

    # === Config grid ===
    configs = []
    # baseline (no regime)
    configs.append(("NO REGIME (production)", None, 1.0, None, None))
    # 100-DMA with 3-day confirm at multiple bear exposures
    for be in [0.0, 0.25, 0.50]:
        configs.append((f"100-DMA + 3-day confirm, bear={int(be*100)}%",
                         get_regime(100, 3), be, 100, 3))
    # 200-DMA with 3-day confirm
    for be in [0.0, 0.25, 0.50]:
        configs.append((f"200-DMA + 3-day confirm, bear={int(be*100)}%",
                         get_regime(200, 3), be, 200, 3))
    # 100-DMA no confirm (more reactive, more whipsaw)
    for be in [0.0, 0.50]:
        configs.append((f"100-DMA + 0-day confirm, bear={int(be*100)}%",
                         get_regime(100, 0), be, 100, 0))

    all_rows = []
    for label, regime, bear_exp, ma, conf in configs:
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start="2009-09-01", end="2026-05-08", config={},
            regime_panel=regime, bear_exposure=bear_exp,
        )
        eq = res["equity"]; exits = res["exits"]
        # Count regime-driven exits if present
        n_regime = (exits["reason"] == "regime_bear").sum() if "reason" in exits.columns else 0
        for w_id, start, end in WINDOWS:
            m = period_metrics(eq, w_id, start, end)
            cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
            all_rows.append({
                "config": label, "ma": ma, "confirm": conf,
                "bear_exposure": bear_exp, "window": w_id,
                "cagr_pct": round(cagr, 2) if cagr is not None else None,
                "sharpe": round(sh, 2) if sh is not None else None,
                "sortino": round(_sortino(eq, start, end), 2)
                            if _sortino(eq, start, end) is not None else None,
                "calmar": round(_calmar(cagr, dd), 2)
                           if _calmar(cagr, dd) is not None else None,
                "max_dd_pct": round(dd, 2) if dd is not None else None,
            })
        print(f"  {label:50s}  (n_regime_exits={n_regime})", flush=True)

    df = pd.DataFrame(all_rows)
    out_dir = ROOT / "tasks/MM-tuning"
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "regime_test.csv", index=False)

    # Print per-window pivot tables
    print(f"\n{'=' * 110}")
    print("L6 + REGIME FILTER — vs NO REGIME baseline (L6 production config)")
    print(f"{'=' * 110}")
    for w in ["IS", "OOS_full", "OOS_A", "OOS_B", "OOS_C", "Prod window"]:
        sub = df[df["window"] == w]
        if sub.empty: continue
        print(f"\n--- {w} ---")
        cols_show = ["config", "cagr_pct", "sharpe", "sortino", "calmar", "max_dd_pct"]
        print(sub[cols_show].to_string(index=False))

    print(f"\n[wrote] {out_dir / 'regime_test.csv'}")


if __name__ == "__main__":
    main()
