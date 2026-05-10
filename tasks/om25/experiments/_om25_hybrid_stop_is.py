"""IS-only test of regime-aware hybrid stop.

Hypothesis: ATR adapts well in stable bull regimes (lets winners run
with vol-scaled trails); fixed % keeps discipline in bear regimes
(when ATR would widen too much during vol shocks).

Pre-committed parameters (from earlier IS-only selection):
- ATR(14) × 6 (the IS pick)
- Fixed 20% from peak (the locked-in)

Variants tested in IS:
- Baseline (no stop)
- Fixed 20% only
- ATR(14)×6 only
- Hybrid: bull → ATR(14)×6,   bear → fixed 20%   ← principled
- Reverse: bull → fixed 20%,  bear → ATR(14)×6   ← sanity check

Sanity check rationale: if the principled hybrid is meaningfully better
AND the reverse hybrid is meaningfully worse, the mechanism is real.
If both hybrids look similar to baselines, we're seeing noise.

NO OOS METRICS shown.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts._clean_engine_stops import load_ohlc_panels, compute_true_atr_pct
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics
from tasks.om25.experiments._om25_regime_100dma_3conf import (
    build_regime_panel_confirmed,
)
from tasks.om25.experiments._om25_regime_weight_tilt import make_om25_tilt_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
IS_END = "2016-12-31"

ATR_WINDOW = 14
ATR_MULT = 6.0
FIXED_PCT = 0.20


def build_hybrid_trail_panel(atr_pct: pd.DataFrame, regime: pd.Series,
                              bull_use_atr: bool) -> pd.DataFrame:
    """Build a Date × Symbol trail panel with regime-aware stop selection.

    bull_use_atr=True  → bull→ATR(14)×6,  bear→fixed 20%   (principled)
    bull_use_atr=False → bull→fixed 20%,  bear→ATR(14)×6   (reverse)
    """
    atr_trail = atr_pct * ATR_MULT
    fixed_trail = pd.DataFrame(FIXED_PCT, index=atr_pct.index, columns=atr_pct.columns)
    reg = regime.reindex(atr_pct.index).ffill().fillna(True)
    bull_mask = reg.astype(bool).values[:, None]  # broadcast across columns
    if bull_use_atr:
        result = np.where(bull_mask, atr_trail.values, fixed_trail.values)
    else:
        result = np.where(bull_mask, fixed_trail.values, atr_trail.values)
    return pd.DataFrame(result, index=atr_pct.index, columns=atr_pct.columns)


def setup():
    print("[load] panels...", flush=True)
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    old_atr20 = close_panel.pct_change().rolling(20).std()
    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]
    entry_dates = biweekly_fri[biweekly_fri >= close_panel.index[252]]

    universe = load_universe(ROOT / "data/static/nifty250_universe.csv")
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()
    regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 100, 3, calendar=calendar
    )
    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_uc=0.5, bull_cr=0.5, bear_uc=0.0, bear_cr=1.0,
        return_filter=True, lookback=252, min_obs=220,
    )

    print("[load] OHLC + ATR(14)...", flush=True)
    H, L, C = load_ohlc_panels(PRICES_DIR, universe=universe)
    H = H.reindex(calendar).ffill()
    L = L.reindex(calendar).ffill()
    C = C.reindex(calendar).ffill()
    atr14 = compute_true_atr_pct(H, L, C, window=ATR_WINDOW)

    return dict(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned, sma_200=sma_200,
        weekly_filt=weekly_filt, entry_dates=entry_dates,
        score_fn=score_fn, regime=regime, atr14=atr14, old_atr20=old_atr20,
    )


def run_one(label, ctx, *, atr_panel, atr_mult, atr_min_floor, use_trail):
    t0 = time.time()
    print(f"  [run] {label} ...", flush=True)
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=ctx["entry_dates"], weekly_signal_dates=ctx["weekly_filt"],
        signal_function=ctx["score_fn"], signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=atr_panel,
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=atr_mult, atr_min_floor=atr_min_floor,
        use_trailing_stop=use_trail, use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
    )
    eq = res["equity"]
    exits = res["exits"]
    is_metrics = period_metrics(eq, "IS", "2009-09-01", IS_END)
    if not exits.empty:
        exits["exit_date"] = pd.to_datetime(exits["exit_date"])
        is_exits = exits[exits["exit_date"] <= pd.Timestamp(IS_END)]
    else:
        is_exits = exits
    by_reason = is_exits["reason"].value_counts().to_dict() if not is_exits.empty else {}
    elapsed = time.time() - t0
    print(f"      done {elapsed:.0f}s — CAGR={is_metrics.get('cagr_pct')} "
          f"Sharpe={is_metrics.get('sharpe')} DD={is_metrics.get('max_dd_pct')}  "
          f"exits={len(is_exits)}", flush=True)

    return {
        "label": label,
        "is_cagr": is_metrics.get("cagr_pct"),
        "is_sharpe": is_metrics.get("sharpe"),
        "is_dd": is_metrics.get("max_dd_pct"),
        "is_vol": is_metrics.get("vol_pct"),
        "exits_total": len(is_exits),
        "exits_rank": by_reason.get("rank", 0),
        "exits_stop": by_reason.get("atr_stop", 0),
    }


def main():
    ctx = setup()

    # Build hybrid panels
    print("[compute] hybrid trail panels...", flush=True)
    hybrid_principled = build_hybrid_trail_panel(ctx["atr14"], ctx["regime"], bull_use_atr=True)
    hybrid_reverse = build_hybrid_trail_panel(ctx["atr14"], ctx["regime"], bull_use_atr=False)

    print("\n[run] sweep variants...\n", flush=True)
    rows = []

    # Baseline (no stop)
    rows.append(run_one("baseline (no stop)", ctx,
                        atr_panel=ctx["old_atr20"],
                        atr_mult=0.0, atr_min_floor=0.0, use_trail=False))

    # Fixed 20%
    rows.append(run_one("fixed 20% only", ctx,
                        atr_panel=ctx["old_atr20"],
                        atr_mult=0.0, atr_min_floor=FIXED_PCT, use_trail=True))

    # ATR(14) × 6 only
    rows.append(run_one("ATR(14)×6 only", ctx,
                        atr_panel=ctx["atr14"],
                        atr_mult=ATR_MULT, atr_min_floor=0.0, use_trail=True))

    # Hybrid: bull→ATR, bear→fixed (principled)
    rows.append(run_one("HYBRID: bull→ATR, bear→fixed (principled)", ctx,
                        atr_panel=hybrid_principled,
                        atr_mult=1.0, atr_min_floor=0.0, use_trail=True))

    # Reverse: bull→fixed, bear→ATR (sanity check)
    rows.append(run_one("REVERSE: bull→fixed, bear→ATR (sanity)", ctx,
                        atr_panel=hybrid_reverse,
                        atr_mult=1.0, atr_min_floor=0.0, use_trail=True))

    df = pd.DataFrame(rows)
    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_om25_hybrid_is"
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "is_results.csv", index=False)

    print("\n" + "=" * 100)
    print(f"IS-ONLY RESULTS (2009-09-01 → {IS_END}) — OOS not shown")
    print("=" * 100)
    print(df.to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_results.csv")


if __name__ == "__main__":
    main()
