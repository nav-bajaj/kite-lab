"""OM25 regime filter — 100 DMA with 3-day confirmation.

Same setup as _om25_regime_in_engine.py but with:
- MA window: 100 days (faster signal vs 200)
- 3-day confirmation: regime only flips after 3 consecutive days
  of agreement (close < MA for bear, close > MA for bull)

Hysteresis reduces whipsaws — won't flip on a single day's break.
Faster MA reacts sooner than 200 DMA but at risk of more false alarms.
The 3-day buffer should mitigate the false-alarm cost.

Sweep matches the 200-DMA run for direct comparison:
- 2 universes: NSE 500, Nifty 250
- 4 indices: NIFTY 50, NIFTY 100, NIFTY 200, NIFTY LARGEMID250
- 2 bear exposures: 0.0, 0.25
- 2 cadences: monthly, biweekly
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy,
    fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import (
    evaluate_all_windows, passes_criteria,
)
from tasks.om25.experiments._om25_oos_retune import make_om25_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"

CFG = dict(
    w_uc=0.5, w_cr=0.5,
    return_filter=True,
    lookback=252, min_obs=220,
    top_n=25, exit_buffer=20,
)

UNIVERSES = [
    ("NSE_500",   ROOT / "data/static/nse500_universe.csv"),
    ("Nifty_250", ROOT / "data/static/nifty250_universe.csv"),
]

REGIME_INDICES = [
    ("NIFTY_50",         ROOT / "indices_data_historical/NIFTY_50.csv"),
    ("NIFTY_100",        ROOT / "indices_data_historical/NIFTY_100.csv"),
    ("NIFTY_200",        ROOT / "indices_data_historical/NIFTY_200.csv"),
    ("NIFTY_LARGEMID250", ROOT / "indices_data_historical/NIFTY_LARGEMID250.csv"),
]
BEAR_EXPOSURES = [0.0, 0.25]
CADENCES = ["monthly", "biweekly"]

MA_WINDOW = 100
CONFIRM_DAYS = 3


def build_regime_panel_confirmed(idx_path: Path, ma_window: int, confirm_days: int,
                                  calendar=None) -> pd.Series:
    """Bull/bear panel using close vs MA with N-day confirmation hysteresis.

    Regime starts as bull. Flips to bear only after `confirm_days` consecutive
    closes below MA. Flips to bull only after `confirm_days` consecutive
    closes above MA. Lagged by 1 day to avoid lookahead.
    """
    df = pd.read_csv(idx_path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = df.sort_values("date").set_index("date")
    ma = df["close"].rolling(ma_window, min_periods=ma_window).mean()
    above = (df["close"] > ma)
    n_above = above.rolling(confirm_days, min_periods=confirm_days).sum()

    # Build regime: stateful flip
    state = True  # start as bull
    regime_vals = []
    for v in n_above.values:
        if np.isnan(v):
            regime_vals.append(state)
            continue
        if state and v == 0:
            state = False
        elif not state and v == confirm_days:
            state = True
        regime_vals.append(state)
    regime = pd.Series(regime_vals, index=df.index, dtype=bool)
    regime_lagged = regime.shift(1)
    if calendar is not None:
        regime_lagged = regime_lagged.reindex(calendar).ffill()
    return regime_lagged


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    out_dir = ROOT / f"experiments/oos_retune/{ts}_om25_regime_100dma_3conf"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")

    print(f"\n[load] prices from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_fri = fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]

    regime_panels = {}
    for idx_name, idx_path in REGIME_INDICES:
        if not idx_path.exists():
            continue
        regime_panels[idx_name] = build_regime_panel_confirmed(
            idx_path, MA_WINDOW, CONFIRM_DAYS, calendar=calendar
        )
        n_bear = (~regime_panels[idx_name].fillna(True)).sum()
        n_total = regime_panels[idx_name].dropna().shape[0]
        n_flips = (regime_panels[idx_name].fillna(True).astype(int).diff() != 0).sum()
        print(f"  [regime] {idx_name}: {n_bear}/{n_total} bear days "
              f"({n_bear/max(n_total,1)*100:.1f}%), regime flips={n_flips}")

    configs = []
    for univ_name, univ_path in UNIVERSES:
        for cad in CADENCES:
            configs.append({
                "label": f"{univ_name}__{cad}__NONE__base",
                "universe": univ_name, "univ_path": univ_path,
                "cadence": cad, "regime": None, "bear_exp": None,
            })
    for univ_name, univ_path in UNIVERSES:
        for cad in CADENCES:
            for idx_name in regime_panels:
                for bear_exp in BEAR_EXPOSURES:
                    configs.append({
                        "label": f"{univ_name}__{cad}__{idx_name}__be{bear_exp}",
                        "universe": univ_name, "univ_path": univ_path,
                        "cadence": cad,
                        "regime": idx_name, "bear_exp": bear_exp,
                    })
    print(f"\n[grid] {len(configs)} configs")

    summary_rows = []
    t0 = time.time()
    for i, c in enumerate(configs, 1):
        universe = load_universe(c["univ_path"])
        cols = [s for s in close_panel.columns if s in universe]
        returns_uni = close_panel[cols].pct_change()

        if c["cadence"] == "monthly":
            entry_dates = monthly_first[monthly_first >= close_panel.index[CFG["lookback"]]]
        else:
            entry_dates = biweekly_fri[biweekly_fri >= close_panel.index[CFG["lookback"]]]

        score_fn = make_om25_score(
            returns_uni,
            w_uc=CFG["w_uc"], w_cr=CFG["w_cr"],
            return_filter=CFG["return_filter"],
            lookback=CFG["lookback"], min_obs=CFG["min_obs"],
        )
        regime_p = regime_panels.get(c["regime"]) if c["regime"] else None
        bear_exp = c["bear_exp"] if c["bear_exp"] is not None else 0.0

        try:
            res = run_strategy(
                close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                entry_signal_dates=entry_dates,
                weekly_signal_dates=weekly_filt,
                signal_function=score_fn, signal_function_args={},
                sma_200_panel=sma_200, atr_20_panel=atr_20,
                top_n=CFG["top_n"], exit_buffer=CFG["exit_buffer"],
                atr_mult=0.0, atr_min_floor=0.0,
                max_weight=0.075, slippage=0.002,
                use_trailing_stop=False,
                regime_panel=regime_p, bear_exposure=bear_exp,
            )
        except Exception as e:
            print(f"  [{i:2d}/{len(configs)}] {c['label']}  ERROR: {e}")
            continue
        if res is None:
            continue

        eq = res["equity"]
        eq.to_csv(out_dir / f"{c['label']}_equity.csv", index=False)
        win_eval = evaluate_all_windows(eq)
        ok, _ = passes_criteria(win_eval)
        oos_full = win_eval[win_eval["window"] == "OOS_full"].iloc[0]
        is_row = win_eval[win_eval["window"] == "IS"].iloc[0]
        elapsed = time.time() - t0
        print(f"  [{i:2d}/{len(configs)}] {c['label']:55s} "
              f"IS_sh={is_row['sharpe']:>4}  "
              f"OOS_sh={oos_full['sharpe']:>4}  "
              f"OOS_cagr={oos_full['cagr_pct']:>5}%  "
              f"OOS_dd={oos_full['max_dd_pct']:>6}%  "
              f"{'PASS' if ok else 'fail':4s}  ({elapsed:.0f}s)")

        row = {**c, "passes": ok}
        for _, w in win_eval.iterrows():
            lbl = w["window"]
            row[f"{lbl}_cagr"] = w.get("cagr_pct")
            row[f"{lbl}_sharpe"] = w.get("sharpe")
            row[f"{lbl}_dd"] = w.get("max_dd_pct")
        summary_rows.append(row)

    df = pd.DataFrame(summary_rows).drop(columns=["univ_path"], errors="ignore")
    df.to_csv(out_dir / "summary.csv", index=False)

    print(f"\n{'=' * 110}")
    print(f"100-DMA + {CONFIRM_DAYS}-DAY CONFIRMATION — OOS_full results")
    print(f"{'=' * 110}\n")
    cols = ["universe", "cadence", "regime", "bear_exp", "passes",
            "IS_sharpe", "OOS_full_sharpe", "OOS_full_cagr", "OOS_full_dd"]
    print(df[cols].sort_values("OOS_full_sharpe", ascending=False)
          .to_string(index=False))
    print(f"\n[wrote] {out_dir}/summary.csv")


if __name__ == "__main__":
    main()
