"""ATR(14) × 6 stop — OOS validation after IS-only selection.

User picked ATR(14) × 6 based on IS Sharpe (tied 1.60 with fixed 20%, but
+0.46pp CAGR, 33% fewer stop fires, vol-adaptive). Now testing OOS.

Reports full multi-window metrics + year-by-year + comparison to the
prior locked-in (fixed 20%).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts._clean_engine_stops import (
    load_ohlc_panels, compute_true_atr_pct,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import evaluate_all_windows, passes_criteria
from tasks.om25.experiments._om25_regime_100dma_3conf import (
    build_regime_panel_confirmed,
)
from tasks.om25.experiments._om25_regime_weight_tilt import make_om25_tilt_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"


def yearly(eq: pd.DataFrame, label: str) -> pd.DataFrame:
    pv = eq.set_index("date")["pv"].astype(float).sort_index()
    pv.index = pd.to_datetime(pv.index)
    rows = []
    for y, gp in pv.groupby(pv.index.year):
        if len(gp) < 5:
            continue
        r = gp.pct_change().dropna()
        cagr = gp.iloc[-1] / gp.iloc[0] - 1
        vol = r.std() * math.sqrt(252)
        sh = (r.mean() * 252) / vol if vol > 0 else float("nan")
        cum = gp / gp.cummax()
        dd = (cum.min() - 1) * 100
        rows.append({"year": y, label: round(cagr * 100, 2),
                     f"{label}_sh": round(sh, 2),
                     f"{label}_dd": round(dd, 1)})
    return pd.DataFrame(rows).set_index("year")


def main():
    print("[load] panels...")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
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

    print("[load] OHLC + ATR(14)...")
    H, L, C = load_ohlc_panels(PRICES_DIR, universe=universe)
    H = H.reindex(calendar).ffill()
    L = L.reindex(calendar).ffill()
    C = C.reindex(calendar).ffill()
    atr14 = compute_true_atr_pct(H, L, C, window=14)

    print("\n[run A] Locked-in (fixed 20% from peak) ...")
    res_A = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=close_panel.pct_change().rolling(20).std(),
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.20,
        use_trailing_stop=True, use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
    )

    print("[run B] True ATR(14) × 6 ...")
    res_B = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr14,
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=6.0, atr_min_floor=0.0,
        use_trailing_stop=True, use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
    )

    eqA, eqB = res_A["equity"], res_B["equity"]
    exA, exB = res_A["exits"], res_B["exits"]

    wA = evaluate_all_windows(eqA)
    wB = evaluate_all_windows(eqB)
    okA, _ = passes_criteria(wA)
    okB, _ = passes_criteria(wB)

    print("\n" + "=" * 90)
    print("PER-WINDOW COMPARISON")
    print("=" * 90)
    cols = ["window", "yrs", "cagr_pct", "sharpe", "max_dd_pct"]
    print("\n[A] Fixed 20% from peak")
    print(wA[cols].to_string(index=False))
    print(f"  PASS: {okA}")
    print("\n[B] True ATR(14) × 6")
    print(wB[cols].to_string(index=False))
    print(f"  PASS: {okB}")

    # Side-by-side
    print("\n" + "=" * 90)
    print("DELTA (B - A)")
    print("=" * 90)
    merged = wA[cols].merge(wB[cols], on="window", suffixes=("_A", "_B"))
    merged["d_cagr"] = merged["cagr_pct_B"] - merged["cagr_pct_A"]
    merged["d_sharpe"] = merged["sharpe_B"] - merged["sharpe_A"]
    merged["d_dd"] = merged["max_dd_pct_B"] - merged["max_dd_pct_A"]
    print(merged[["window", "cagr_pct_A", "cagr_pct_B", "d_cagr",
                  "sharpe_A", "sharpe_B", "d_sharpe",
                  "max_dd_pct_A", "max_dd_pct_B", "d_dd"]].round(2).to_string(index=False))

    # Year-by-year
    print("\n" + "=" * 90)
    print("YEAR-BY-YEAR (CAGR / Sharpe / DD)")
    print("=" * 90)
    yA = yearly(eqA, "fixed20")
    yB = yearly(eqB, "atr14x6")
    yr = yA.join(yB, how="outer")

    def era(y):
        if y <= 2016: return "IS"
        if 2017 <= y <= 2019: return "OOS_A"
        if 2020 <= y <= 2022: return "OOS_B"
        return "OOS_C"
    yr.insert(0, "era", [era(y) for y in yr.index])
    print(yr.to_string())

    # Exit reason breakdown
    print("\n" + "=" * 90)
    print("EXIT BREAKDOWN")
    print("=" * 90)
    for label, ex in [("[A] fixed 20%", exA), ("[B] true ATR(14)×6", exB)]:
        print(f"\n{label}")
        if "reason" in ex.columns:
            rc = ex["reason"].value_counts()
            for r, n in rc.items():
                print(f"  {r:>10}: {n} ({n/len(ex)*100:.1f}%)")
            grp = ex.groupby("reason").agg(
                n=("pnl_pct", "count"),
                avg_pnl=("pnl_pct", "mean"),
                median_pnl=("pnl_pct", "median"),
                hit=("pnl_pct", lambda s: (s > 0).mean()),
                avg_hold=("hold_days", "mean"),
            ).round(3)
            print(grp.to_string())

    # Save artifacts
    out = ROOT / "tasks/oos_retune_2026/winner_artifacts"
    eqB.to_csv(out / "om25_winner_atr14x6_equity.csv", index=False)
    res_B["trades"].to_csv(out / "om25_winner_atr14x6_trades.csv", index=False)
    exB.to_csv(out / "om25_winner_atr14x6_exits.csv", index=False)
    print(f"\n[wrote] B variant artifacts to {out}/")


if __name__ == "__main__":
    main()
