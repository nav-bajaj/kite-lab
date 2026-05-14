"""Test whether the Thursday-signal lift applies to OM25 v3 and TL25 v3.

Both strategies use `_clean_engine.run_strategy` with `entry_signal_dates`
derived from `biweekly_fridays(calendar)`. If we switch them to
`biweekly_thursdays(calendar)`, do we see a similar 6.5pp CAGR / 0.20 Sharpe
lift as we observed for L6 momentum production?

This is a focused test, NOT a re-lock. We just want to know: was the locked v3
performance suppressed by the Friday-signal choice? If yes, this is a major
opportunity for OM25 v3 and TL25 v3.

Output: per-strategy comparison Friday vs Thursday signals on OOS 2017-2026.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays, thursdays, biweekly_thursdays,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics

from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.tl25_v3 import (
    V3_LOCKED as TL25_LOCKED, build_tl25_panels, make_tl25_score,
)


WINDOWS = [
    ("IS",       "2009-09-01", "2016-12-31"),
    ("OOS_A",    "2017-01-01", "2019-12-31"),
    ("OOS_B",    "2020-01-01", "2022-12-31"),
    ("OOS_C",    "2023-01-01", "2026-05-08"),
    ("OOS_full", "2017-01-01", "2026-05-08"),
]


def _sharpe_rf5_cagr(cagr_pct, vol_pct):
    if cagr_pct is None or vol_pct is None or vol_pct <= 0:
        return None
    return (cagr_pct - 5) / vol_pct


def run_strategy_thursday_vs_friday(strategy_name, build_score_and_engine,
                                      ctx, signal_days):
    """Run one strategy under both signal_day choices over the full panel."""
    results = {}
    for sd in signal_days:
        if sd == "friday":
            entry_all = biweekly_fridays(ctx["calendar"])
        elif sd == "thursday":
            entry_all = biweekly_thursdays(ctx["calendar"])
        else:
            raise ValueError(sd)
        weekly_filt_all = fridays(ctx["calendar"])  # weekly exit always Friday
        start_ts = pd.Timestamp("2009-09-01")
        end_ts = pd.Timestamp("2026-05-08")
        entry_dates = entry_all[(entry_all >= start_ts) & (entry_all <= end_ts)]
        weekly_filt = weekly_filt_all[(weekly_filt_all >= start_ts)
                                       & (weekly_filt_all <= end_ts)]

        score_fn, engine_kwargs = build_score_and_engine(ctx)
        res = run_strategy(
            close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
            calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
            initial_capital=1_000_000,
            **engine_kwargs,
        )
        if res is None or res.get("equity") is None or res["equity"].empty:
            continue
        eq = res["equity"]
        window_metrics = {}
        for w_id, start, end in WINDOWS:
            m = period_metrics(eq, w_id, start, end)
            window_metrics[w_id] = {
                "cagr_pct": m.get("cagr_pct"),
                "sharpe": m.get("sharpe"),
                "vol_pct": m.get("vol_pct"),
                "max_dd_pct": m.get("max_dd_pct"),
                "sharpe_rf5": _sharpe_rf5_cagr(m.get("cagr_pct"), m.get("vol_pct")),
            }
        results[sd] = window_metrics
    return results


def main():
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    # OM25 v3 — Nifty 250 universe, regime-tilted UC/CR
    print("[setup] OM25 v3 on Nifty 250 ...")
    om25_uni = load_universe(ROOT / "data/static/nifty250_universe.csv")
    om25_cols = [s for s in close_panel.columns if s in om25_uni]
    om25_returns = close_panel[om25_cols].pct_change()
    om25_regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_ctx = dict(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned, sma_200=sma_200, atr_20=atr_20,
    )
    def om25_build(ctx):
        score_fn = make_om25_tilt_score(
            om25_returns, om25_regime,
            bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
            bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
            return_filter=OM25_LOCKED["return_filter"],
            lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
        )
        engine_kwargs = dict(
            top_n=OM25_LOCKED["top_n"], exit_buffer=OM25_LOCKED["exit_buffer"],
            max_weight=OM25_LOCKED["max_weight"], slippage=OM25_LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=OM25_LOCKED["drawdown_stop_pct"],
            use_trailing_stop=True, use_dma_exit=False,
            weekly_rank_check=False,
            regime_panel=None, bear_exposure=0.0,
        )
        return score_fn, engine_kwargs

    # TL25 v3 — NSE 500 universe
    print("[setup] TL25 v3 on NSE 500 ...")
    tl25_uni = load_universe(ROOT / "data/static/nse500_universe.csv")
    tl25_cols = [s for s in close_panel.columns if s in tl25_uni]
    tl25_panels = build_tl25_panels(
        close_panel[tl25_cols],
        dma_short=TL25_LOCKED["dma_short"], dma_long=TL25_LOCKED["dma_long"],
        dma_persist_ref=TL25_LOCKED["dma_persist_ref"],
        persistence_window=TL25_LOCKED["persistence_window"],
        drawdown_window=TL25_LOCKED["drawdown_window"],
        drawdown_concavity=TL25_LOCKED["drawdown_concavity"],
        momentum_window=TL25_LOCKED["momentum_window"],
    )
    def tl25_build(ctx):
        score_fn = make_tl25_score(
            tl25_panels,
            w_persistence=TL25_LOCKED["w_persistence"],
            w_drawdown=TL25_LOCKED["w_drawdown"],
            w_momentum=TL25_LOCKED["w_momentum"],
        )
        engine_kwargs = dict(
            top_n=TL25_LOCKED["top_n"], exit_buffer=TL25_LOCKED["exit_buffer"],
            max_weight=TL25_LOCKED["max_weight"], slippage=TL25_LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=TL25_LOCKED["atr_min_floor"],
            use_trailing_stop=True, use_dma_exit=False,
            weekly_rank_check=True,
            regime_panel=None, bear_exposure=0.0,
        )
        return score_fn, engine_kwargs

    # Run both
    print("\n[run] OM25 v3 — Friday vs Thursday signal day ...")
    om25_res = run_strategy_thursday_vs_friday(
        "om25_v3", om25_build, om25_ctx, signal_days=["friday", "thursday"])

    print("[run] TL25 v3 — Friday vs Thursday signal day ...")
    tl25_res = run_strategy_thursday_vs_friday(
        "tl25_v3", tl25_build, om25_ctx, signal_days=["friday", "thursday"])

    # Pretty print
    print(f"\n{'=' * 100}")
    print("THURSDAY vs FRIDAY signals — locked v3 configs")
    print(f"{'=' * 100}")

    for strat_name, results in [("OM25 v3", om25_res), ("TL25 v3", tl25_res)]:
        print(f"\n=== {strat_name} ===")
        rows = []
        for sd, windows in results.items():
            for w in ["IS", "OOS_A", "OOS_B", "OOS_C", "OOS_full"]:
                m = windows.get(w, {})
                rows.append({
                    "signal_day": sd, "window": w,
                    "cagr_pct": m.get("cagr_pct"),
                    "sharpe_rf0": m.get("sharpe"),
                    "sharpe_rf5": m.get("sharpe_rf5"),
                    "vol_pct": m.get("vol_pct"),
                    "max_dd_pct": m.get("max_dd_pct"),
                })
        df = pd.DataFrame(rows)
        # Reorder: pivot to show side-by-side
        pivoted = df.set_index(["window", "signal_day"])
        print(pivoted[["cagr_pct", "sharpe_rf5", "max_dd_pct"]]
              .unstack("signal_day").round(2).to_string())

        # Compute the deltas for OOS_full
        of_fri = next((r for r in rows if r["signal_day"] == "friday" and r["window"] == "OOS_full"), None)
        of_thu = next((r for r in rows if r["signal_day"] == "thursday" and r["window"] == "OOS_full"), None)
        if of_fri and of_thu:
            print(f"\n  OOS_full Δ (Thursday − Friday):")
            print(f"    CAGR: {of_thu['cagr_pct'] - of_fri['cagr_pct']:+.2f}pp")
            if of_thu.get("sharpe_rf5") and of_fri.get("sharpe_rf5"):
                print(f"    Sharpe (rf=5%): {of_thu['sharpe_rf5'] - of_fri['sharpe_rf5']:+.3f}")
            print(f"    MaxDD: {of_thu['max_dd_pct'] - of_fri['max_dd_pct']:+.2f}pp")

    # Save
    all_rows = []
    for strat_name, results in [("om25_v3", om25_res), ("tl25_v3", tl25_res)]:
        for sd, windows in results.items():
            for w_id, m in windows.items():
                all_rows.append({"strategy": strat_name, "signal_day": sd,
                                  "window": w_id, **m})
    pd.DataFrame(all_rows).to_csv(
        ROOT / "tasks/MM-tuning/om25_tl25_thursday_test.csv", index=False)
    print(f"\n[wrote] tasks/MM-tuning/om25_tl25_thursday_test.csv")


if __name__ == "__main__":
    main()
