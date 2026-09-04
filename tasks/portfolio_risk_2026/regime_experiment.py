"""COMBO Defensive — regime-signal experiment.

COMBO's overlay reads NIFTY 100 vs its 100-DMA. That is a large-cap trend
filter, and COMBO's OM25 half draws from the Nifty 250, so in the 2018-19
mid-cap bear the signal saw a healthy index while half the book fell 37%.
This sweeps the regime CONTROL only — index choice and signal mechanic —
holding every other COMBO parameter at LOCKED.

Arms:
  ma_<INDEX>     close vs 100-DMA, 3-day confirm (production mechanic)
  roc<N>_<INDEX> N-day rate-of-change > 0, 3-day confirm

Data reality (see RESULTS.md):
  NIFTY_500        2015-01 -> usable regime from ~2015-06
  NIFTY_LARGEMID250 2020-01 -> CANNOT be tested on 2018-19 at all
  NIFTY_200 / NIFTY_MIDCAP_50 have no live tail; regime ffills its last
  state after 2026-05-08, which touches only the final ~3.5 months.

Common evaluation start is therefore 2015-07-01, set by NIFTY 500.

Only the PORTFOLIO-level overlay varies. OM25's internal bull/bear score
tilt stays on NIFTY 100 per its locked spec, so this isolates one lever.

Usage:
  python tasks/portfolio_risk_2026/regime_experiment.py
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
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
IDX = RUNS / "regime_idx"
sys.path.insert(0, str(HERE))
from exit_buffer_sweep import window_metrics          # noqa: E402
from rolling_returns import underwater_stats, rolling_stats  # noqa: E402

EVAL_START = "2015-07-01"
WINDOWS = [
    ("BEAR_2018", "2018-01-15", "2019-12-31"),   # the failure episode
    ("COVID",     "2020-01-01", "2020-12-31"),   # must not lose this
    ("POST2021",  "2021-01-01", "PANEL_END"),
    ("EVAL",      EVAL_START,   "PANEL_END"),
]

ARMS = [
    ("ma_NIFTY_100", "NIFTY_100", "ma", 100, 3),   # production baseline
    ("ma_NIFTY_500", "NIFTY_500", "ma", 100, 3),
    ("ma_NIFTY_200", "NIFTY_200", "ma", 100, 3),
    ("ma_NIFTY_MIDCAP_50", "NIFTY_MIDCAP_50", "ma", 100, 3),
    ("roc21_NIFTY_500", "NIFTY_500", "roc", 21, 3),
    ("roc42_NIFTY_500", "NIFTY_500", "roc", 42, 3),
    ("roc63_NIFTY_500", "NIFTY_500", "roc", 63, 3),
    ("roc126_NIFTY_500", "NIFTY_500", "roc", 126, 3),
    ("roc252_NIFTY_500", "NIFTY_500", "roc", 252, 3),
    ("roc126_NIFTY_100", "NIFTY_100", "roc", 126, 3),   # mechanic control
    ("roc126_NIFTY_MIDCAP_50", "NIFTY_MIDCAP_50", "roc", 126, 3),
    # Holdout arms: NIFTY 100 has history from 2010, so the ROC *mechanic*
    # can be tested on 2012-2015 — a stretch not used to pick anything.
    ("roc21_NIFTY_100", "NIFTY_100", "roc", 21, 3),
    ("roc42_NIFTY_100", "NIFTY_100", "roc", 42, 3),
    # Nifty 250: usable history only from 2020-01, so this arm can only be
    # run on a post-2020 window. It cannot speak to the 2018-19 episode.
    ("ma_NIFTY_LARGEMID250", "NIFTY_LARGEMID250", "ma", 100, 3),
]


def _confirm(raw: pd.Series, confirm_days: int) -> pd.Series:
    """Sticky state machine + 1-day lag, identical to om25_v3's MA version.

    Flips to bear only after `confirm_days` consecutive False, back to bull
    only after `confirm_days` consecutive True. Lagged one session so the
    decision uses a prior-day close.
    """
    n_true = raw.rolling(confirm_days, min_periods=confirm_days).sum()
    state, vals = True, []
    for v in n_true.values:
        if np.isnan(v):
            vals.append(state)
            continue
        if state and v == 0:
            state = False
        elif not state and v == confirm_days:
            state = True
        vals.append(state)
    return pd.Series(vals, index=raw.index, dtype=bool).shift(1)


def build_regime(index_name: str, kind: str, param: int, *, calendar,
                 confirm_days: int = 3) -> pd.Series:
    path = IDX / f"{index_name}.csv"
    if kind == "ma":
        r = build_regime_panel_confirmed(path, param, confirm_days,
                                         calendar=calendar)
    elif kind == "roc":
        df = pd.read_csv(path, parse_dates=["date"])
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
        s = df.sort_values("date").set_index("date")["close"]
        roc = s / s.shift(param) - 1.0
        # Encode as float so the warmup window stays NaN: a bool series would
        # report False there and fire a spurious bear right at the start.
        raw = (roc > 0).astype(float)
        raw[roc.isna()] = np.nan
        r = _confirm(raw, confirm_days).reindex(calendar).ffill()
    else:
        raise ValueError(kind)
    # Dates before the index series begins come back NaN. A NaN reaches
    # run_strategy's `float(rv)` branch and poisons target_exposure, so
    # resolve to bull (fully invested) — the same default the engine uses
    # when no regime panel is supplied. Backtests start well after this.
    return r.where(r.notna(), True).astype(bool)


def parse_args():
    ap = argparse.ArgumentParser(description="COMBO regime-signal experiment")
    ap.add_argument("--arms", nargs="+", default=None, help="subset of arm names")
    ap.add_argument("--exit-buffer", type=int, default=LOCKED["exit_buffer"])
    ap.add_argument("--start", default=EVAL_START)
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--output", type=Path, default=RUNS / "regime")
    ap.add_argument("--grid-index", default=None,
                    help="Run a (lookback x confirm) ROC grid on this index "
                         "instead of the named ARMS.")
    ap.add_argument("--grid-lookbacks", type=int, nargs="+",
                    default=[10, 15, 21, 31, 42, 52, 63])
    ap.add_argument("--grid-confirms", type=int, nargs="+", default=[1, 2, 3, 5, 8])
    return ap.parse_args()


def main():
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.grid_index:
        arms = [(f"roc{lb}_c{cd}", args.grid_index, "roc", lb, cd)
                for lb in args.grid_lookbacks for cd in args.grid_confirms]
    else:
        arms = [a for a in ARMS if args.arms is None or a[0] in args.arms]
    t0 = time.time()

    print(f"[load] panels ...", flush=True)
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    end = calendar[-1]

    nse500_uni, l6_mem, l6_cand = resolve_universe(
        ROOT / "data/static/nse500_membership.csv", ROOT / LOCKED["l6_universe_csv"])
    l6_panels = build_momentum_panels(
        close_panel[[s for s in close_panel.columns if s in nse500_uni]],
        lookback_days=lookback_months_to_days(LOCKED["l6_lookback_months"]),
        skip_days=LOCKED["l6_skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=LOCKED["l6_vol_floor"],
                                   vol_power=LOCKED["l6_vol_power"],
                                   cross_sectional_zscore=True, candidate_fn=l6_cand)

    n250_uni, om25_mem, om25_cand = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv", ROOT / LOCKED["om25_universe_csv"])
    om25_returns = close_panel[[s for s in close_panel.columns if s in n250_uni]].pct_change()
    # OM25's own tilt stays on NIFTY 100 (its locked spec) so only the
    # portfolio overlay is under test.
    om25_regime = build_regime("NIFTY_100", "ma", OM25_LOCKED["regime_ma_window"],
                               calendar=calendar,
                               confirm_days=OM25_LOCKED["regime_confirm_days"])
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime,
        bull_w_uc=LOCKED["om25_bull_w_uc"], bull_w_cr=LOCKED["om25_bull_w_cr"],
        bear_w_uc=LOCKED["om25_bear_w_uc"], bear_w_cr=LOCKED["om25_bear_w_cr"],
        return_filter=LOCKED["om25_return_filter"],
        lookback=LOCKED["om25_lookback"], min_obs=LOCKED["om25_min_obs"],
        candidate_fn=om25_cand)

    from scripts.combo_defensive import make_combo_score_fn
    from combo_buffer_sweep import make_combo_score_fn_deep
    combo_score = (make_combo_score_fn([("L6", l6_score), ("OM25", om25_score)],
                                       n_per=LOCKED["n_per_strategy"])
                   if args.exit_buffer == 0 else
                   make_combo_score_fn_deep([("L6", l6_score), ("OM25", om25_score)],
                                            n_per=LOCKED["n_per_strategy"],
                                            extra_per=(args.exit_buffer + 1) // 2))

    s = pd.Timestamp(args.start)
    entry_dates = biweekly_fridays(calendar)
    entry_dates = entry_dates[(entry_dates >= s) & (entry_dates <= end)]
    weekly_filt = fridays(calendar)
    weekly_filt = weekly_filt[(weekly_filt >= s) & (weekly_filt <= end)]
    membership_fn = union_membership_fns([l6_mem, om25_mem]) if (l6_mem or om25_mem) else None
    windows = [(l, a, str(end.date()) if b == "PANEL_END" else b) for l, a, b in WINDOWS]

    rows, inv_rows = [], []
    for name, index_name, kind, param, confirm in arms:
        t = time.time()
        regime = build_regime(index_name, kind, param, calendar=calendar,
                              confirm_days=confirm)
        seg = regime.loc[s:end]
        bear_pct = float((~seg).mean() * 100)
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=combo_score, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=LOCKED["top_n"], exit_buffer=args.exit_buffer,
            max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=0.0, use_trailing_stop=False,
            use_dma_exit=False, weekly_rank_check=False,
            regime_panel=regime, bear_exposure=LOCKED["regime_bear_exposure"],
            membership_fn=membership_fn, min_hold_days=LOCKED["min_hold_days"],
            initial_capital=1_000_000)
        if res is None or res["equity"].empty:
            print(f"  [skip] {name}")
            continue
        eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
        trades = res["trades"].copy(); trades["date"] = pd.to_datetime(trades["date"])
        exits = res["exits"].copy()
        if not exits.empty:
            exits["exit_date"] = pd.to_datetime(exits["exit_date"])
        eq.to_csv(args.output / f"{name}_equity.csv", index=False)

        for lbl, a, b in windows:
            r = window_metrics(lbl, eq, trades, exits, a, b)
            r["arm"] = name; r["bear_pct"] = round(bear_pct, 1)
            r["lookback"] = param; r["confirm"] = confirm
            rows.append(r)
        pv = eq.set_index("date")["pv"].astype(float)
        inv_rows.append({"arm": name, "lookback": param, "confirm": confirm,
                         "bear_pct": round(bear_pct, 1),
                         **underwater_stats(pv),
                         "pct_12m_negative": rolling_stats(pv, 252).get("pct_negative"),
                         "median_12m": rolling_stats(pv, 252).get("median")})
        print(f"  {name:<26} bear {bear_pct:>4.1f}%  ({time.time()-t:.0f}s)", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(args.output / "regime_summary.csv", index=False)
    inv = pd.DataFrame(inv_rows)
    inv.to_csv(args.output / "regime_investor.csv", index=False)

    show = ["arm", "bear_pct", "cagr_pct", "sharpe", "max_dd_pct", "calmar", "rt_per_year"]
    for lbl, a, b in windows:
        sub = df[df["window"] == lbl]
        if sub.empty:
            continue
        print(f"\n{'='*96}\n{lbl}   {a} -> {b}\n{'='*96}")
        print(sub[[c for c in show if c in sub.columns]].to_string(index=False))
    print(f"\n{'='*96}\nInvestor lens over {EVAL_START} -> {end.date()}\n{'='*96}")
    print(inv[["arm", "bear_pct", "max_dd_pct", "pct_days_dd_gt_20",
               "longest_uw_days", "ulcer_index", "pct_12m_negative",
               "median_12m"]].to_string(index=False))
    print(f"\n[total] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
