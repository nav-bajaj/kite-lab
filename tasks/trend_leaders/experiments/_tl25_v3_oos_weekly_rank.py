"""TL25 v3 — OOS validation of weekly rank-exit variant.

DD-reduction tweak from IS test: fire rank-exit at every weekly Friday
(not just biweekly). IS improved DD by +2.39pp at cost of -0.03 Sharpe / -1.30pp CAGR.

All other config locked from A3 baseline:
  NSE 500, biweekly entry + weekly exit checks
  Score weights 40/20/40 (P/DD/M)
  Windows: persistence 252d, drawdown 126d squared, momentum 63d
  Top-25, exit-buffer 20
  Fixed 20% DD stop, 7.5% max weight, 20 bps slippage
  No regime tilt

Reports multi-window OOS metrics + pass criteria + comparison to A3 baseline.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import evaluate_all_windows, passes_criteria
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
UNIVERSE = ROOT / "data/static/nse500_universe.csv"


def yearly(eq):
    pv = eq.set_index("date")["pv"].astype(float).sort_index()
    pv.index = pd.to_datetime(pv.index)
    rows = []
    for y, gp in pv.groupby(pv.index.year):
        if len(gp) < 5: continue
        r = gp.pct_change().dropna()
        cagr = gp.iloc[-1]/gp.iloc[0] - 1
        vol = r.std() * math.sqrt(252)
        sh = (r.mean()*252)/vol if vol > 0 else 0
        cum = gp/gp.cummax()
        dd = (cum.min() - 1) * 100
        era = "IS" if y <= 2016 else ("OOS_A" if y<=2019 else ("OOS_B" if y<=2022 else "OOS_C"))
        rows.append({"year": y, "era": era,
                     "ret_pct": round(cagr*100, 2),
                     "sharpe": round(sh, 2),
                     "dd_pct": round(dd, 1)})
    return pd.DataFrame(rows)


def run_variant(label, weekly_rank, ctx):
    print(f"\n[run] {label} (weekly_rank_check={weekly_rank})", flush=True)
    score_fn = make_tl25_score(ctx["panels"],
                                w_persistence=0.40, w_drawdown=0.20, w_momentum=0.40)
    t0 = time.time()
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=ctx["entry_dates"], weekly_signal_dates=ctx["weekly_filt"],
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_panel"],
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.20,
        use_trailing_stop=True, use_dma_exit=False,
        weekly_rank_check=weekly_rank,
        regime_panel=None, bear_exposure=0.0,
    )
    elapsed = time.time() - t0
    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    win = evaluate_all_windows(eq)
    ok, reasons = passes_criteria(win)
    print(f"  done {elapsed:.0f}s, PASS={ok}", flush=True)
    return {
        "label": label, "weekly_rank": weekly_rank,
        "equity": eq, "windows": win, "passes": ok, "reasons": reasons,
        "trades": res["trades"], "exits": res["exits"],
    }


def main():
    print("[load] price panels...", flush=True)
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_panel = close_panel.pct_change().rolling(20).std()
    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]
    entry_dates = biweekly_fri[biweekly_fri >= close_panel.index[252]]

    universe = load_universe(UNIVERSE)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    panels = build_tl25_panels(close_uni)

    ctx = dict(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned, sma_200=sma_200, atr_panel=atr_panel,
        weekly_filt=weekly_filt, entry_dates=entry_dates,
        panels=panels,
    )

    a3 = run_variant("A3 baseline (biweekly rank)", False, ctx)
    new = run_variant("Candidate (weekly rank-exit)", True, ctx)

    print(f"\n{'=' * 100}")
    print("TL25 v3 — Candidate (weekly rank-exit) vs A3 baseline, OOS validation")
    print(f"{'=' * 100}\n")
    print("[A3 baseline — biweekly rank]")
    print(a3["windows"][["window","yrs","cagr_pct","sharpe","max_dd_pct"]].to_string(index=False))
    print(f"  Pass criteria:")
    for r in a3["reasons"]:
        print(f"    {r}")
    print(f"  Overall: {'PASS' if a3['passes'] else 'FAIL'}")

    print(f"\n[Candidate — weekly rank-exit]")
    print(new["windows"][["window","yrs","cagr_pct","sharpe","max_dd_pct"]].to_string(index=False))
    print(f"  Pass criteria:")
    for r in new["reasons"]:
        print(f"    {r}")
    print(f"  Overall: {'PASS' if new['passes'] else 'FAIL'}")

    print(f"\n=== DELTA (candidate - baseline) ===")
    a = a3["windows"].set_index("window")[["cagr_pct","sharpe","max_dd_pct"]]
    b = new["windows"].set_index("window")[["cagr_pct","sharpe","max_dd_pct"]]
    delta = (b - a).round(2)
    delta.columns = ["d_cagr_pp","d_sharpe","d_dd_pp"]
    print(delta.to_string())

    yr = yearly(new["equity"])
    print(f"\n=== Year-by-year for Candidate (weekly rank-exit) ===")
    print(yr.to_string(index=False))

    out = ROOT / "tasks/oos_retune_2026/winner_artifacts"
    out.mkdir(parents=True, exist_ok=True)
    new["equity"].to_csv(out / "tl25_v3_weekly_rank_equity.csv", index=False)
    new["trades"].to_csv(out / "tl25_v3_weekly_rank_trades.csv", index=False)
    new["exits"].to_csv(out / "tl25_v3_weekly_rank_exits.csv", index=False)
    new["windows"].to_csv(out / "tl25_v3_weekly_rank_windows.csv", index=False)
    yr.to_csv(out / "tl25_v3_weekly_rank_yearly.csv", index=False)
    print(f"\n[wrote] tl25_v3_weekly_rank_* artifacts to {out}/")


if __name__ == "__main__":
    main()
