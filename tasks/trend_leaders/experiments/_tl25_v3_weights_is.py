"""TL25 v3 weight sweep (IS-only) — Fixed 20% DD stop locked in.

Score components: persistence (252d) + drawdown (126d squared) + momentum (63d).
All variants share: NSE 500 / biweekly / top-25 / buffer-20 / fixed 20% DD stop / no 200 DMA.

NO OOS metrics shown. Selection on IS only, OOS test comes later.
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
from tasks.trend_leaders.experiments._tl25_v3_baseline import setup as tl25_setup


# (w_persistence, w_drawdown, w_momentum) — names for clarity
WEIGHT_VARIANTS = [
    ("Equal 1/3 each (V2 baseline)",       1/3,  1/3,  1/3),
    ("Persistence-heavy 50/25/25",         0.50, 0.25, 0.25),
    ("Drawdown-heavy 25/50/25",            0.25, 0.50, 0.25),
    ("Momentum-heavy 25/25/50",            0.25, 0.25, 0.50),
    ("P+DD 50/50/0 (no momentum)",         0.50, 0.50, 0.00),
    ("P+M 50/0/50 (no DD)",                0.50, 0.00, 0.50),
    ("DD+M 0/50/50 (no persistence)",      0.00, 0.50, 0.50),
    ("Persistence only 100/0/0",           1.00, 0.00, 0.00),
    ("Drawdown only 0/100/0",              0.00, 1.00, 0.00),
    ("Momentum only 0/0/100",              0.00, 0.00, 1.00),
    # Intermediate / tilted variants
    ("Defensive P+DD heavy 40/40/20",      0.40, 0.40, 0.20),
    ("Offensive P+M heavy 40/20/40",       0.40, 0.20, 0.40),
    ("DD+M heavy 20/40/40",                0.20, 0.40, 0.40),
]


def run_one(label, ctx, wp, wd, wm):
    t0 = time.time()
    print(f"  [run] {label:42s} (w={wp:.2f}/{wd:.2f}/{wm:.2f}) ...", flush=True)
    atr_panel = ctx["close_panel"].pct_change().rolling(20).std()
    score_fn = make_tl25_score(
        ctx["panels"],
        w_persistence=wp, w_drawdown=wd, w_momentum=wm,
    )
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=ctx["entry_dates"], weekly_signal_dates=ctx["weekly_filt"],
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=atr_panel,
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.20,   # ← Fixed 20% DD stop
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
    by_reason = is_exits["reason"].value_counts().to_dict() if not is_exits.empty else {}
    elapsed = time.time() - t0
    print(f"      done {elapsed:.0f}s — CAGR={is_m.get('cagr_pct')} "
          f"Sharpe={is_m.get('sharpe')} DD={is_m.get('max_dd_pct')} "
          f"exits={len(is_exits)}", flush=True)
    return {
        "label": label,
        "w_persistence": wp, "w_drawdown": wd, "w_momentum": wm,
        "is_cagr": is_m.get("cagr_pct"),
        "is_sharpe": is_m.get("sharpe"),
        "is_dd": is_m.get("max_dd_pct"),
        "is_vol": is_m.get("vol_pct"),
        "exits_total_is": len(is_exits),
        "exits_rank_is": by_reason.get("rank", 0),
        "exits_stop_is": by_reason.get("atr_stop", 0),
    }


def main():
    ctx = tl25_setup()
    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_tl25_v3_weights_is"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[sweep] TL25 v3 weight variants on IS (Fixed 20% DD stop)\n", flush=True)
    rows = []
    for label, wp, wd, wm in WEIGHT_VARIANTS:
        rows.append(run_one(label, ctx, wp, wd, wm))

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "is_weight_sweep.csv", index=False)

    df_sorted = df.sort_values("is_sharpe", ascending=False)
    print(f"\n{'=' * 110}")
    print("TL25 v3 — IS-only weight sweep (Fixed 20% DD stop). OOS not shown. Sorted by IS Sharpe.")
    print(f"{'=' * 110}")
    print(df_sorted[["label","w_persistence","w_drawdown","w_momentum",
                     "is_sharpe","is_cagr","is_dd","is_vol",
                     "exits_total_is"]].to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_weight_sweep.csv")


if __name__ == "__main__":
    main()
