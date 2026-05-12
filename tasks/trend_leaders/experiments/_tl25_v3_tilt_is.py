"""TL25 v3 — single-config vs regime-tilt comparison on IS only.

All variants:
  - NSE 500, biweekly, top-25, buffer-20
  - Windows: persistence 252d, drawdown 126d (squared), momentum 63d
  - Fixed 20% DD stop, no 200 DMA exit
  - Equal 1/N sizing, 7.5% max, 20bps slippage
  - Regime: NIFTY 100 close vs 100-DMA, 3-day confirmation hysteresis

Variants tested:
  Single-config (no tilt):
    A1) Equal 1/3 — V2 baseline reference
    A2) Persistence-heavy 50/25/25 (Top-by-Sharpe-and-DD)
    A3) Offensive P+M 40/20/40 (Top-by-CAGR)

  Regime-tilt:
    B1) Offensive (40/20/40) → P+DD (50/50/0)
    B2) Persistence-heavy (50/25/25) → P+DD (50/50/0)
    B3) Equal 1/3 → P+DD (50/50/0)
    B4) Offensive (40/20/40) → Persistence-heavy (50/25/25)

NO OOS METRICS shown.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy
from scripts.multi_window_oos_eval import period_metrics
from scripts.tl25_v3 import make_tl25_score
from scripts.om25_v3 import build_regime_panel_confirmed
from tasks.trend_leaders.experiments._tl25_v3_baseline import setup as tl25_setup


REGIME_INDEX = ROOT / "indices_data_historical/NIFTY_100.csv"


VARIANTS = [
    # (label, bull_wp, bull_wd, bull_wm, bear_wp, bear_wd, bear_wm)
    # Single-config (no tilt — bear weights = bull weights)
    ("A1) Equal 1/3 — V2 baseline",                       1/3,  1/3,  1/3,    1/3,  1/3,  1/3),
    ("A2) Persistence-heavy 50/25/25 (single)",           0.50, 0.25, 0.25,   0.50, 0.25, 0.25),
    ("A3) Offensive P+M 40/20/40 (single)",               0.40, 0.20, 0.40,   0.40, 0.20, 0.40),
    # Regime-tilt variants
    ("B1) Offensive (40/20/40) → P+DD (50/50/0)",         0.40, 0.20, 0.40,   0.50, 0.50, 0.00),
    ("B2) Persistence-heavy (50/25/25) → P+DD (50/50/0)", 0.50, 0.25, 0.25,   0.50, 0.50, 0.00),
    ("B3) Equal 1/3 → P+DD (50/50/0)",                    1/3,  1/3,  1/3,    0.50, 0.50, 0.00),
    ("B4) Offensive (40/20/40) → Persistence-heavy",      0.40, 0.20, 0.40,   0.50, 0.25, 0.25),
]


def run_one(label, ctx, regime, bull, bear):
    bp, bd, bm = bull
    rp, rd, rm = bear
    t0 = time.time()
    print(f"  [run] {label} ...", flush=True)
    atr_panel = ctx["close_panel"].pct_change().rolling(20).std()
    score_fn = make_tl25_score(
        ctx["panels"],
        w_persistence=bp, w_drawdown=bd, w_momentum=bm,
        regime_panel=regime,
        bear_w_persistence=rp, bear_w_drawdown=rd, bear_w_momentum=rm,
    )
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=ctx["entry_dates"], weekly_signal_dates=ctx["weekly_filt"],
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=atr_panel,
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.20,
        use_trailing_stop=True, use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
    )
    eq = res["equity"]
    exits = res["exits"]
    is_m = period_metrics(eq, "IS", "2009-09-01", "2016-12-31")
    if not exits.empty:
        exits["exit_date"] = pd.to_datetime(exits["exit_date"])
        is_exits = exits[exits["exit_date"] <= pd.Timestamp("2016-12-31")]
    else:
        is_exits = exits
    elapsed = time.time() - t0
    print(f"      done {elapsed:.0f}s — CAGR={is_m.get('cagr_pct')} "
          f"Sharpe={is_m.get('sharpe')} DD={is_m.get('max_dd_pct')} "
          f"exits={len(is_exits)}", flush=True)
    return {
        "label": label,
        "bull_w": f"{bp:.2f}/{bd:.2f}/{bm:.2f}",
        "bear_w": f"{rp:.2f}/{rd:.2f}/{rm:.2f}",
        "is_cagr": is_m.get("cagr_pct"),
        "is_sharpe": is_m.get("sharpe"),
        "is_dd": is_m.get("max_dd_pct"),
        "is_vol": is_m.get("vol_pct"),
        "exits_total_is": len(is_exits),
    }


def main():
    ctx = tl25_setup()
    print(f"[regime] building NIFTY 100 100-DMA 3-conf panel...", flush=True)
    regime = build_regime_panel_confirmed(
        REGIME_INDEX, ma_window=100, confirm_days=3, calendar=ctx["calendar"]
    )

    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_tl25_v3_tilt_is"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[sweep] single-config vs regime-tilt variants (IS only)\n", flush=True)
    rows = []
    for label, *weights in VARIANTS:
        bull = weights[:3]
        bear = weights[3:]
        rows.append(run_one(label, ctx, regime, bull, bear))

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "is_tilt_sweep.csv", index=False)

    df_sorted = df.sort_values("is_sharpe", ascending=False)
    print(f"\n{'=' * 110}")
    print("TL25 v3 — Single-config vs Regime-tilt comparison (IS only). Sorted by IS Sharpe.")
    print(f"{'=' * 110}")
    print(df_sorted[["label", "bull_w", "bear_w", "is_sharpe", "is_cagr", "is_dd", "is_vol", "exits_total_is"]]
          .to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_tilt_sweep.csv")


if __name__ == "__main__":
    main()
