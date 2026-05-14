"""50-50 L6 + OM25 combo portfolio.

12 stocks from each strategy (24 total). Priority dedup: L6 first, then
OM25 backfills with next-highest non-overlapping picks.

Compares against:
  - L6 standalone (24 stocks, weekly Thursday)
  - OM25 standalone (24 stocks, weekly Thursday)
  - L6 + Regime filter (winner from regime_test)
  - Combined L6+OM25 (this)
  - Combined L6+OM25 + Regime filter (this with regime overlay)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, thursdays, fridays
from scripts._momentum_engine import (
    BASELINE as MM_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics


N_PER_STRATEGY = 12


def make_combined_score_fn(score_fns_in_priority_order: list, n_per: int = 12):
    def score_fn(signal_date, **_):
        picked = set()
        rows = []
        for label, sf in score_fns_in_priority_order:
            scores = sf(signal_date)
            if scores is None or scores.empty:
                continue
            ranked = scores.dropna().sort_values(ascending=False)
            taken = 0
            for sym in ranked.index:
                if sym in picked: continue
                picked.add(sym)
                rows.append(sym)
                taken += 1
                if taken >= n_per: break
        if not rows:
            return pd.Series(dtype=float)
        n = len(rows)
        return pd.Series({sym: float(n - i) for i, sym in enumerate(rows)})
    return score_fn


WINDOWS = [
    ("IS",          "2009-09-01", "2016-12-31"),
    ("OOS_A",       "2017-01-01", "2019-12-31"),
    ("OOS_B",       "2020-01-01", "2022-12-31"),
    ("OOS_C",       "2023-01-01", "2026-05-08"),
    ("OOS_full",    "2017-01-01", "2026-05-08"),
    ("Prod window", "2020-07-10", "2026-05-08"),
]


def _calmar(c, d):
    if d is None or pd.isna(d) or abs(d) < 1e-6: return None
    return c / abs(d)


def _sortino(eq, s, e):
    s = pd.Timestamp(s); e = pd.Timestamp(e)
    sub = eq[(eq["date"] >= s) & (eq["date"] <= e)]
    if len(sub) < 5: return None
    rets = sub["pv"].astype(float).pct_change().dropna()
    if rets.empty: return None
    downside = rets[rets < 0]
    if downside.empty or downside.std() == 0: return None
    excess = rets.mean() * 252 - 0.05
    return excess / (downside.std() * math.sqrt(252))


def eval_track(label, score_fn, ctx, top_n, entry_dates, weekly_filt,
                regime_panel=None, bear_exposure=0.0):
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=top_n, exit_buffer=0,
        max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
        weekly_rank_check=False,
        regime_panel=regime_panel, bear_exposure=bear_exposure,
        min_hold_days=8, initial_capital=1_000_000,
    )
    eq = res["equity"]
    rows = []
    for w_id, start, end in WINDOWS:
        m = period_metrics(eq, w_id, start, end)
        cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
        rows.append({
            "track": label, "window": w_id,
            "cagr_pct": round(cagr, 2) if cagr is not None else None,
            "sharpe": round(sh, 2) if sh is not None else None,
            "sortino": round(_sortino(eq, start, end), 2)
                        if _sortino(eq, start, end) is not None else None,
            "calmar": round(_calmar(cagr, dd), 2) if _calmar(cagr, dd) is not None else None,
            "max_dd_pct": round(dd, 2) if dd is not None else None,
        })
    return rows


def main():
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    print("[setup] L6 score on NSE 500 ...")
    nse500_uni = load_universe(ROOT / "data/static/nse500_universe.csv")
    nse500_cols = [s for s in close_panel.columns if s in nse500_uni]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(MM_BASELINE["lookback_months"]),
        skip_days=MM_BASELINE["skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=MM_BASELINE["vol_floor"],
        vol_power=MM_BASELINE["vol_power"], cross_sectional_zscore=True,
    )

    print("[setup] OM25 v3 score on Nifty 250 ...")
    nifty250_uni = load_universe(ROOT / "data/static/nifty250_universe.csv")
    nifty250_cols = [s for s in close_panel.columns if s in nifty250_uni]
    om25_returns = close_panel[nifty250_cols].pct_change()
    om25_regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )

    ctx = dict(close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                sma_200=sma_200, atr_20=atr_20)

    entry_thu = thursdays(calendar)
    weekly_thu = entry_thu  # DD-check day = Thursday (matches entry)
    s_ts = pd.Timestamp("2009-09-01"); e_ts = pd.Timestamp("2026-05-08")
    entry_dates = entry_thu[(entry_thu >= s_ts) & (entry_thu <= e_ts)]
    weekly_filt = weekly_thu[(weekly_thu >= s_ts) & (weekly_thu <= e_ts)]

    # === Run all tracks ===
    all_rows = []

    # 1. L6 standalone
    print("\n[run] L6 standalone (Thu, 24 stocks) ...")
    all_rows.extend(eval_track("L6 standalone", l6_score, ctx,
                                  top_n=24, entry_dates=entry_dates, weekly_filt=weekly_filt))

    # 2. OM25 standalone
    print("[run] OM25 standalone (Thu, 24 stocks) ...")
    all_rows.extend(eval_track("OM25 standalone", om25_score, ctx,
                                  top_n=24, entry_dates=entry_dates, weekly_filt=weekly_filt))

    # 3. L6 + Regime (winner from regime test)
    print("[run] L6 + regime (100-DMA, 3conf, bear=50%) ...")
    regime_100_3 = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 100, 3, calendar=calendar,
    )
    all_rows.extend(eval_track("L6 + Regime (100/3/50%)", l6_score, ctx,
                                  top_n=24, entry_dates=entry_dates,
                                  weekly_filt=weekly_filt,
                                  regime_panel=regime_100_3, bear_exposure=0.5))

    # 4. 50-50 combo (L6 priority)
    print("[run] 50-50 L6+OM25 (L6 priority, 12+12) ...")
    combo_50_50 = make_combined_score_fn(
        [("L6", l6_score), ("OM25", om25_score)], n_per=12,
    )
    all_rows.extend(eval_track("COMBO L6+OM25 (12+12, L6 priority)", combo_50_50,
                                  ctx, top_n=24, entry_dates=entry_dates,
                                  weekly_filt=weekly_filt))

    # 5. 50-50 combo + regime
    print("[run] 50-50 L6+OM25 + regime (100/3/50%) ...")
    all_rows.extend(eval_track("COMBO L6+OM25 + Regime (100/3/50%)", combo_50_50,
                                  ctx, top_n=24, entry_dates=entry_dates,
                                  weekly_filt=weekly_filt,
                                  regime_panel=regime_100_3, bear_exposure=0.5))

    # 6. 50-50 combo (OM25 priority)
    print("[run] 50-50 L6+OM25 (OM25 priority, 12+12) ...")
    combo_om25 = make_combined_score_fn(
        [("OM25", om25_score), ("L6", l6_score)], n_per=12,
    )
    all_rows.extend(eval_track("COMBO L6+OM25 (12+12, OM25 priority)", combo_om25,
                                  ctx, top_n=24, entry_dates=entry_dates,
                                  weekly_filt=weekly_filt))

    df = pd.DataFrame(all_rows)
    out = ROOT / "tasks/MM-tuning/multi_strategy_50_50.csv"
    df.to_csv(out, index=False)

    print(f"\n{'=' * 120}")
    print("50-50 L6+OM25 combo (12+12 stocks, weekly Thursday) vs constituents")
    print(f"{'=' * 120}")
    for w in ["IS", "OOS_full", "OOS_A", "OOS_B", "OOS_C", "Prod window"]:
        sub = df[df["window"] == w]
        if sub.empty: continue
        print(f"\n--- {w} ---")
        cols = ["track", "cagr_pct", "sharpe", "sortino", "calmar", "max_dd_pct"]
        print(sub[cols].to_string(index=False))

    print(f"\n[wrote] {out}")


if __name__ == "__main__":
    main()
