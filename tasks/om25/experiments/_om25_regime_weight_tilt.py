"""OM25 regime-tilt: regime shifts UC/CR weight blend instead of cash on/off.

Strategy stays fully invested. Score weights tilt based on regime:
- Bull regime → bull_weights (e.g., 0.7 UC + 0.3 CR — more aggressive)
- Bear regime → bear_weights (e.g., 0.3 UC + 0.7 CR — more defensive)

Same regime signal as the cash-filter test: 100 DMA + 3-day confirmation.

This avoids the re-entry friction and CAGR cost of going to cash, while
still adapting selection to market regime.

Sweep:
- Universes: NSE 500, Nifty 250
- Cadences: monthly, biweekly
- Regime indices: NIFTY 50, NIFTY 100, NIFTY 200
- Weight pairs (bull → bear):
    (0.7/0.3 → 0.3/0.7)   # mild swing
    (0.7/0.3 → 0.0/1.0)   # bull aggressive, bear defensive (CR-only in bear)
    (0.6/0.4 → 0.4/0.6)   # gentle swing
    (0.8/0.2 → 0.2/0.8)   # heavier swing
    (0.5/0.5 → 0.0/1.0)   # production-blend in bull, CR-only in bear
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
from scripts.backfill_gdf_indices import safe_filename  # noqa
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import (
    evaluate_all_windows, passes_criteria,
)
from tasks.om25.experiments._om25_regime_100dma_3conf import (
    build_regime_panel_confirmed,
)


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
LOOKBACK = 252
MIN_OBS = 220
TOP_N = 25
EXIT_BUFFER = 20
RETURN_FILTER = True
MA_WINDOW = 100
CONFIRM_DAYS = 3

UNIVERSES = [
    ("NSE_500",   ROOT / "data/static/nse500_universe.csv"),
    ("Nifty_250", ROOT / "data/static/nifty250_universe.csv"),
]
REGIME_INDICES = [
    ("NIFTY_50",  ROOT / "indices_data_historical/NIFTY_50.csv"),
    ("NIFTY_100", ROOT / "indices_data_historical/NIFTY_100.csv"),
    ("NIFTY_200", ROOT / "indices_data_historical/NIFTY_200.csv"),
]
CADENCES = ["monthly", "biweekly"]
# (bull_uc, bull_cr) → (bear_uc, bear_cr)
WEIGHT_PAIRS = [
    ((0.7, 0.3), (0.3, 0.7)),
    ((0.7, 0.3), (0.0, 1.0)),
    ((0.6, 0.4), (0.4, 0.6)),
    ((0.8, 0.2), (0.2, 0.8)),
    ((0.5, 0.5), (0.0, 1.0)),
    ((0.5, 0.5), (0.3, 0.7)),
]


def make_om25_tilt_score(returns_universe: pd.DataFrame, regime_panel: pd.Series,
                         bull_uc: float, bull_cr: float,
                         bear_uc: float, bear_cr: float,
                         return_filter: bool = True,
                         lookback: int = 252, min_obs: int = 220):
    """Score function that picks weights based on regime at signal_date.

    regime_panel: Series indexed by date, True=bull (already lagged by caller).
    """
    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback:
            return pd.Series(dtype=float)
        # Determine regime at signal_date (regime_panel already lagged)
        try:
            rv = regime_panel.get(signal_date, True)
            is_bull = bool(rv) if rv is not None else True
        except Exception:
            is_bull = True
        if is_bull:
            w_uc, w_cr = bull_uc, bull_cr
        else:
            w_uc, w_cr = bear_uc, bear_cr
        if w_uc + w_cr <= 0:
            return pd.Series(dtype=float)
        w_sum = w_uc + w_cr
        w_uc_n, w_cr_n = w_uc / w_sum, w_cr / w_sum

        window = returns_universe.iloc[idx - lookback + 1:idx + 1]
        market_ret = window.mean(axis=1)
        results = {}
        for sym in window.columns:
            r = window[sym].dropna()
            if len(r) < min_obs:
                continue
            if return_filter and ((1 + r).prod() - 1) <= 0:
                continue
            common = r.index.intersection(market_ret.index)
            sr = r.loc[common]
            mr = market_ret.loc[common]
            up = mr > 0
            dn = mr < 0
            if up.sum() < 50 or dn.sum() < 50:
                continue
            uc = sr[up].mean() / mr[up].mean() if mr[up].mean() > 0 else 0
            dc = sr[dn].mean() / mr[dn].mean() if mr[dn].mean() < 0 else 1
            ratio = uc / dc if dc > 0 else uc
            results[sym] = {"up": uc, "ratio": ratio}
        if not results:
            return pd.Series(dtype=float)
        df = pd.DataFrame(results).T
        up_pct = df["up"].rank(method="average") / len(df)
        cr_pct = df["ratio"].rank(method="average") / len(df)
        return w_uc_n * up_pct + w_cr_n * cr_pct

    return score_fn


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    out_dir = ROOT / f"experiments/oos_retune/{ts}_om25_regime_tilt"
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
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[LOOKBACK]]

    regime_panels = {}
    for idx_name, idx_path in REGIME_INDICES:
        if not idx_path.exists():
            continue
        regime_panels[idx_name] = build_regime_panel_confirmed(
            idx_path, MA_WINDOW, CONFIRM_DAYS, calendar=calendar
        )

    # Build configs: 2 univ × 2 cad × 3 indices × 6 weight pairs = 72
    # Plus 4 baselines (no tilt; fixed 50/50)
    configs = []
    # Baselines
    for univ_name, univ_path in UNIVERSES:
        for cad in CADENCES:
            configs.append({
                "label": f"{univ_name}__{cad}__NONE__base50_50",
                "universe": univ_name, "univ_path": univ_path,
                "cadence": cad, "regime": None,
                "bull_uc": 0.5, "bull_cr": 0.5,
                "bear_uc": 0.5, "bear_cr": 0.5,
            })
    # Tilt configs
    for univ_name, univ_path in UNIVERSES:
        for cad in CADENCES:
            for idx_name in regime_panels:
                for (bull_w, bear_w) in WEIGHT_PAIRS:
                    configs.append({
                        "label": (f"{univ_name}__{cad}__{idx_name}__"
                                  f"bull{bull_w[0]}_{bull_w[1]}__"
                                  f"bear{bear_w[0]}_{bear_w[1]}"),
                        "universe": univ_name, "univ_path": univ_path,
                        "cadence": cad, "regime": idx_name,
                        "bull_uc": bull_w[0], "bull_cr": bull_w[1],
                        "bear_uc": bear_w[0], "bear_cr": bear_w[1],
                    })
    print(f"[grid] {len(configs)} configs")

    summary_rows = []
    t0 = time.time()
    for i, c in enumerate(configs, 1):
        universe = load_universe(c["univ_path"])
        cols = [s for s in close_panel.columns if s in universe]
        returns_uni = close_panel[cols].pct_change()

        if c["cadence"] == "monthly":
            entry_dates = monthly_first[monthly_first >= close_panel.index[LOOKBACK]]
        else:
            entry_dates = biweekly_fri[biweekly_fri >= close_panel.index[LOOKBACK]]

        # Use a constant always-bull panel for baselines; real panel for tilts
        if c["regime"] is None:
            regime_p = pd.Series(True, index=calendar)
        else:
            regime_p = regime_panels[c["regime"]]

        score_fn = make_om25_tilt_score(
            returns_uni, regime_p,
            bull_uc=c["bull_uc"], bull_cr=c["bull_cr"],
            bear_uc=c["bear_uc"], bear_cr=c["bear_cr"],
            return_filter=RETURN_FILTER,
            lookback=LOOKBACK, min_obs=MIN_OBS,
        )

        try:
            res = run_strategy(
                close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                entry_signal_dates=entry_dates,
                weekly_signal_dates=weekly_filt,
                signal_function=score_fn, signal_function_args={},
                sma_200_panel=sma_200, atr_20_panel=atr_20,
                top_n=TOP_N, exit_buffer=EXIT_BUFFER,
                atr_mult=0.0, atr_min_floor=0.0,
                max_weight=0.075, slippage=0.002,
                use_trailing_stop=False,
                regime_panel=None, bear_exposure=0.0,  # NO cash on/off here
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
        if i % 6 == 0 or i == len(configs):
            print(f"  [{i:2d}/{len(configs)}] {c['label']:80s} "
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

    print(f"\n{'=' * 130}")
    print(f"REGIME-TILT (100 DMA + {CONFIRM_DAYS}-conf) — top 20 by OOS Sharpe (PASS only)")
    print(f"{'=' * 130}\n")
    cols = ["universe", "cadence", "regime",
            "bull_uc", "bull_cr", "bear_uc", "bear_cr", "passes",
            "IS_sharpe", "OOS_full_sharpe", "OOS_full_cagr", "OOS_full_dd"]
    df_pass = df[df["passes"] == True].sort_values("OOS_full_sharpe", ascending=False)
    print(df_pass[cols].head(20).to_string(index=False))
    print(f"\n[wrote] {out_dir}/summary.csv")


if __name__ == "__main__":
    main()
