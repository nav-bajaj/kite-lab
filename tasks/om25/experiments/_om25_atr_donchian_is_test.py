"""IS-only sweep of true ATR and Donchian-low stops.

Tests these stop variants on the OM25 winner config (Nifty 250
biweekly + regime tilt):
- Baseline (no stop)
- Fixed 20% drawdown (current locked-in)
- True ATR (14-day window): 3, 4, 5, 6× multiplier
- True ATR (20-day window): 3, 4, 5, 6× multiplier
- Donchian 20-day low
- Donchian 50-day low
- Donchian 100-day low
- Donchian 150-day low

REPORTS ONLY IS METRICS. No OOS shown to avoid biased selection.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts._clean_engine_stops import (
    load_ohlc_panels, compute_true_atr_pct, compute_donchian_low,
)
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


def setup():
    """Load all panels needed for backtests."""
    print("[load] panels...")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    # Old "atr_20" used by engine when no panel override (kept for ATR multiplier)
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

    # Load OHLC for true ATR and Donchian
    print("[load] OHLC panels for true ATR + Donchian...")
    H, L, C = load_ohlc_panels(PRICES_DIR, universe=universe)
    # Reindex to match close_panel calendar
    H = H.reindex(calendar).ffill()
    L = L.reindex(calendar).ffill()
    C = C.reindex(calendar).ffill()

    return dict(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned, sma_200=sma_200, old_atr20=old_atr20,
        weekly_filt=weekly_filt, entry_dates=entry_dates,
        score_fn=score_fn, H=H, L=L, C=C,
    )


def run_one(label, ctx, **stop_kwargs):
    """Run a single backtest variant and return IS-only metrics + exit breakdown."""
    import time
    t0 = time.time()
    print(f"  [run] {label} ...", flush=True)
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"],
        benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=ctx["entry_dates"], weekly_signal_dates=ctx["weekly_filt"],
        signal_function=ctx["score_fn"], signal_function_args={},
        sma_200_panel=ctx["sma_200"],
        atr_20_panel=stop_kwargs.pop("atr_panel", ctx["old_atr20"]),
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        use_dma_exit=False, regime_panel=None, bear_exposure=0.0,
        **stop_kwargs,
    )
    eq = res["equity"]
    trades = res["trades"]
    exits = res["exits"]
    # IS-only slice
    is_metrics = period_metrics(eq, "IS", "2009-09-01", IS_END)

    # IS-period exit breakdown
    if not exits.empty:
        exits["exit_date"] = pd.to_datetime(exits["exit_date"])
        is_exits = exits[exits["exit_date"] <= pd.Timestamp(IS_END)]
    else:
        is_exits = exits

    by_reason = {}
    if not is_exits.empty and "reason" in is_exits.columns:
        by_reason = is_exits["reason"].value_counts().to_dict()

    elapsed = time.time() - t0
    is_cagr = is_metrics.get("cagr_pct", "?")
    is_sh = is_metrics.get("sharpe", "?")
    is_dd = is_metrics.get("max_dd_pct", "?")
    print(f"      done in {elapsed:.0f}s — CAGR={is_cagr} Sharpe={is_sh} DD={is_dd}  exits={len(is_exits)}", flush=True)

    return {
        "label": label,
        "is_cagr": is_metrics.get("cagr_pct"),
        "is_sharpe": is_metrics.get("sharpe"),
        "is_dd": is_metrics.get("max_dd_pct"),
        "is_vol": is_metrics.get("vol_pct"),
        "exits_total_is": len(is_exits),
        "exits_rank_is": by_reason.get("rank", 0),
        "exits_atr_is": by_reason.get("atr_stop", 0),
        "exits_donchian_is": by_reason.get("donchian", 0),
    }


def main():
    ctx = setup()
    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_om25_atr_donchian_is"
    out_dir.mkdir(parents=True, exist_ok=True)

    # True ATR panels
    print("[compute] true ATR panels...")
    atr14 = compute_true_atr_pct(ctx["H"], ctx["L"], ctx["C"], window=14)
    atr20 = compute_true_atr_pct(ctx["H"], ctx["L"], ctx["C"], window=20)

    # Donchian low panels (uses low, shifted by 1 to exclude today)
    print("[compute] Donchian low panels...")
    don20 = compute_donchian_low(ctx["L"], window=20)
    don50 = compute_donchian_low(ctx["L"], window=50)
    don100 = compute_donchian_low(ctx["L"], window=100)
    don150 = compute_donchian_low(ctx["L"], window=150)

    print("\n[run] sweep variants...")
    results = []

    # 1. Baseline (no stop)
    results.append(run_one("baseline (no stop)", ctx,
                           atr_mult=0.0, atr_min_floor=0.0,
                           use_trailing_stop=False))

    # 2. Fixed 20% drawdown (current locked-in)
    results.append(run_one("fixed 20% from peak", ctx,
                           atr_mult=0.0, atr_min_floor=0.20,
                           use_trailing_stop=True))

    # 3. True ATR(14)
    for mult in (3, 4, 5, 6):
        results.append(run_one(f"true ATR(14) × {mult}", ctx,
                               atr_panel=atr14,
                               atr_mult=float(mult), atr_min_floor=0.0,
                               use_trailing_stop=True))

    # 4. True ATR(20)
    for mult in (3, 4, 5, 6):
        results.append(run_one(f"true ATR(20) × {mult}", ctx,
                               atr_panel=atr20,
                               atr_mult=float(mult), atr_min_floor=0.0,
                               use_trailing_stop=True))

    # 5. Donchian
    for window, panel in [(20, don20), (50, don50), (100, don100), (150, don150)]:
        results.append(run_one(f"donchian {window}d low", ctx,
                               atr_mult=0.0, atr_min_floor=0.0,
                               use_trailing_stop=False,
                               donchian_low_panel=panel))

    df = pd.DataFrame(results)
    df.to_csv(out_dir / "is_results.csv", index=False)
    print(f"\n{'=' * 100}")
    print("IS-ONLY RESULTS (2009-09-01 → 2016-12-31)  — OOS not shown")
    print(f"{'=' * 100}")
    print(df.to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_results.csv")


if __name__ == "__main__":
    main()
