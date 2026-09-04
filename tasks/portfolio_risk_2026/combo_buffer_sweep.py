"""COMBO Defensive: full-history rebuild + exit-buffer sweep.

Two jobs:
  1. Rebuild COMBO from 2010 (the production runner only has a 2020+ curve
     because it runs on the live price panel), so the three-way investor
     comparison against L6 covers the full OOS window rather than 6 years.
  2. Sweep `exit_buffer` on COMBO the way `exit_buffer_sweep.py` does for L6.

Why this needs its own score fn: production `make_combo_score_fn` emits
exactly n_per * n_components = 24 names, so the engine's
`nlargest(top_n + exit_buffer)` keep-set can never be wider than the entry
set and `exit_buffer` is a silent no-op. `make_combo_score_fn_deep` below
extends each component's contribution past its quota while leaving the
first 24 in the identical priority-dedup order, so entries are unchanged and
only the keep-set widens — matching L6 buffer semantics.

Regime source: production LOCKED points at indices_data_historical, which
stops 2026-05-08. `runs/nifty100_regime_merged.csv` splices the live
indices_data rows after that date (1572 overlapping days agree to 5e-6).

Usage:
  python tasks/portfolio_risk_2026/combo_buffer_sweep.py
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts._momentum_engine import (
    build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.combo_defensive import LOCKED
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.universe_membership import resolve_universe, union_membership_fns

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
sys.path.insert(0, str(HERE))
from exit_buffer_sweep import window_metrics, WINDOWS  # noqa: E402


def make_combo_score_fn_deep(component_score_fns, *, n_per=12, extra_per=0):
    """Priority-dedup combo score with depth beyond the entry quota.

    First `n_per` from each component in priority order (identical to
    production), then up to `extra_per` more from each in the same order.
    Entry set = top 24 is unchanged; only ranks 25+ gain content, which is
    exactly what exit_buffer reads.
    """
    def score_fn(signal_date, **_):
        picked, rows = set(), []
        ranked_cache = []
        for _label, sf in component_score_fns:
            scores = sf(signal_date)
            ranked_cache.append(
                None if scores is None or scores.empty
                else scores.dropna().sort_values(ascending=False)
            )
        for quota in (n_per, extra_per):
            if quota <= 0:
                continue
            for ranked in ranked_cache:
                if ranked is None:
                    continue
                taken = 0
                for sym in ranked.index:
                    if sym in picked:
                        continue
                    picked.add(sym)
                    rows.append(sym)
                    taken += 1
                    if taken >= quota:
                        break
        if not rows:
            return pd.Series(dtype=float)
        n = len(rows)
        return pd.Series({sym: float(n - i) for i, sym in enumerate(rows)})
    return score_fn


def parse_args():
    ap = argparse.ArgumentParser(description="COMBO Defensive exit-buffer sweep")
    ap.add_argument("--buffers", type=int, nargs="+", default=[0, 5, 10, 15, 20])
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path,
                    default=RUNS / "nifty100_regime_merged.csv")
    # NIFTY 100 history starts 2010-01-04; the 100-DMA needs ~100 sessions,
    # so entries start once the regime signal is actually defined.
    ap.add_argument("--start", default="2010-07-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--slippage", type=float, default=LOCKED["slippage"])
    ap.add_argument("--output", type=Path, default=RUNS)
    return ap.parse_args()


def main():
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print(f"[load] panels {args.prices_dir.name} ...", flush=True)
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    end = pd.Timestamp(args.end) if args.end else calendar[-1]

    print(f"[component] L6 on NSE 500 ...", flush=True)
    nse500_uni, l6_mem_fn, l6_cand_fn = resolve_universe(
        ROOT / "data/static/nse500_membership.csv",
        ROOT / LOCKED["l6_universe_csv"])
    l6_cols = [s for s in close_panel.columns if s in nse500_uni]
    l6_panels = build_momentum_panels(
        close_panel[l6_cols],
        lookback_days=lookback_months_to_days(LOCKED["l6_lookback_months"]),
        skip_days=LOCKED["l6_skip_days"])
    l6_score = make_momentum_score(
        l6_panels, vol_floor=LOCKED["l6_vol_floor"],
        vol_power=LOCKED["l6_vol_power"], cross_sectional_zscore=True,
        candidate_fn=l6_cand_fn)

    print(f"[component] OM25 v3 on Nifty 250 ...", flush=True)
    n250_uni, om25_mem_fn, om25_cand_fn = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv",
        ROOT / LOCKED["om25_universe_csv"])
    n250_cols = [s for s in close_panel.columns if s in n250_uni]
    om25_returns = close_panel[n250_cols].pct_change()
    om25_regime = build_regime_panel_confirmed(
        args.regime_index, OM25_LOCKED["regime_ma_window"],
        OM25_LOCKED["regime_confirm_days"], calendar=calendar)
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime,
        bull_w_uc=LOCKED["om25_bull_w_uc"], bull_w_cr=LOCKED["om25_bull_w_cr"],
        bear_w_uc=LOCKED["om25_bear_w_uc"], bear_w_cr=LOCKED["om25_bear_w_cr"],
        return_filter=LOCKED["om25_return_filter"],
        lookback=LOCKED["om25_lookback"], min_obs=LOCKED["om25_min_obs"],
        candidate_fn=om25_cand_fn)

    portfolio_regime = build_regime_panel_confirmed(
        args.regime_index, LOCKED["regime_ma_window"],
        LOCKED["regime_confirm_days"], calendar=calendar)
    print(f"[regime] {args.regime_index.name}: "
          f"{portfolio_regime.notna().sum()} defined days, "
          f"{(portfolio_regime == False).sum()} bear days")

    weekly_fri = fridays(calendar)
    entry_all = biweekly_fridays(calendar)
    s = pd.Timestamp(args.start)
    entry_dates = entry_all[(entry_all >= s) & (entry_all <= end)]
    weekly_filt = weekly_fri[(weekly_fri >= s) & (weekly_fri <= end)]
    membership_fn = (union_membership_fns([l6_mem_fn, om25_mem_fn])
                     if (l6_mem_fn or om25_mem_fn) else None)

    windows = [(lbl, st, str(end.date()) if e == "PANEL_END" else e)
               for lbl, st, e in WINDOWS]
    all_rows = []
    for buf in args.buffers:
        t = time.time()
        print(f"\n[run] COMBO exit_buffer={buf} ...", flush=True)
        combo_score = make_combo_score_fn_deep(
            [("L6", l6_score), ("OM25", om25_score)],
            n_per=LOCKED["n_per_strategy"],
            # Each component supplies half the extra depth, mirroring the
            # 12+12 split of the entry quota.
            extra_per=(buf + 1) // 2,
        )
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=combo_score, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=LOCKED["top_n"], exit_buffer=buf,
            max_weight=LOCKED["max_weight"], slippage=args.slippage,
            atr_mult=0.0, atr_min_floor=0.0,
            use_trailing_stop=False, use_dma_exit=False,
            weekly_rank_check=False,
            regime_panel=portfolio_regime,
            bear_exposure=LOCKED["regime_bear_exposure"],
            membership_fn=membership_fn,
            min_hold_days=LOCKED["min_hold_days"],
            initial_capital=1_000_000,
        )
        if res is None or res["equity"].empty:
            print(f"  [skip] empty result")
            continue
        eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
        trades = res["trades"].copy(); trades["date"] = pd.to_datetime(trades["date"])
        exits = res["exits"].copy()
        if not exits.empty:
            exits["exit_date"] = pd.to_datetime(exits["exit_date"])

        tag = f"combo_buf{buf:02d}"
        eq.to_csv(args.output / f"{tag}_equity.csv", index=False)
        trades.to_csv(args.output / f"{tag}_trades.csv", index=False)
        exits.to_csv(args.output / f"{tag}_exits.csv", index=False)
        for lbl, st, e in windows:
            row = window_metrics(lbl, eq, trades, exits, st, e)
            row["exit_buffer"] = buf
            all_rows.append(row)
        print(f"  done in {time.time()-t:.1f}s ({len(trades)} trades)", flush=True)

    df = pd.DataFrame(all_rows)
    out = args.output / "combo_summary.csv"
    df.to_csv(out, index=False)
    print(f"\n[wrote] {out}")
    show = ["exit_buffer", "cagr_pct", "vol_pct", "sharpe", "max_dd_pct",
            "calmar", "rt_per_year", "hit_rate_pct", "avg_hold_days", "n_trades"]
    for lbl, st, e in windows:
        sub = df[df["window"] == lbl]
        if sub.empty or sub["n_days"].iloc[0] < 3:
            continue
        print(f"\n{'='*100}\n{lbl}   {st} -> {e}\n{'='*100}")
        print(sub[[c for c in show if c in sub.columns]].to_string(index=False))
    print(f"\n[total] {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
