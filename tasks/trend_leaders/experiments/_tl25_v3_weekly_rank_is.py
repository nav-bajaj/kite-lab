"""TL25 v3 — IS test: weekly rank-exit vs biweekly rank-exit.

Same A3 config (40/20/40 weights, NSE 500, biweekly entry, 20% DD stop).
Only difference: rank-exit firing schedule.

Variants:
  A) BASELINE: biweekly rank-exit (current locked) + weekly DD stop
  B) WEEKLY RANK: rank-exit at every Friday + weekly DD stop

This addresses the "rank can lag up to 2 weeks" gap by firing rank-exit
checks every Friday instead of every other Friday.

No new entries on weekly Fridays — those still only happen at biweekly.
NO OOS shown.
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


def run_one(label, ctx, weekly_rank):
    score_fn = make_tl25_score(ctx["panels"],
                                w_persistence=0.40, w_drawdown=0.20, w_momentum=0.40)
    atr_panel = ctx["close_panel"].pct_change().rolling(20).std()
    t0 = time.time()
    print(f"  [run] {label} (weekly_rank_check={weekly_rank}) ...", flush=True)
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=ctx["entry_dates"], weekly_signal_dates=ctx["weekly_filt"],
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=atr_panel,
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.20,
        use_trailing_stop=True, use_dma_exit=False,
        weekly_rank_check=weekly_rank,
        regime_panel=None, bear_exposure=0.0,
    )
    eq = res["equity"]
    trades = res["trades"]
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
          f"Sharpe={is_m.get('sharpe')} DD={is_m.get('max_dd_pct')}  "
          f"exits={len(is_exits)}  by_reason={by_reason}", flush=True)
    return {
        "label": label,
        "weekly_rank_check": weekly_rank,
        "is_cagr": is_m.get("cagr_pct"),
        "is_sharpe": is_m.get("sharpe"),
        "is_dd": is_m.get("max_dd_pct"),
        "is_vol": is_m.get("vol_pct"),
        "exits_total_is": len(is_exits),
        "exits_rank_biweekly_is": by_reason.get("rank", 0),
        "exits_rank_weekly_is": by_reason.get("rank_weekly", 0),
        "exits_atr_is": by_reason.get("atr_stop", 0),
    }


def main():
    ctx = tl25_setup()
    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_tl25_v3_weekly_rank_is"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    rows.append(run_one("A) BASELINE — biweekly rank + weekly DD stop", ctx, weekly_rank=False))
    rows.append(run_one("B) WEEKLY RANK — weekly rank + weekly DD stop", ctx, weekly_rank=True))

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "is_weekly_rank.csv", index=False)

    print(f"\n{'=' * 100}")
    print("TL25 v3 — Weekly rank-exit vs biweekly (IS only)")
    print(f"{'=' * 100}")
    print(df.to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_weekly_rank.csv")


if __name__ == "__main__":
    main()
