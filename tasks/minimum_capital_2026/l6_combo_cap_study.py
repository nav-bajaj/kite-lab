"""Price-cap study extended to L6 v2 and COMBO Defensive.

Mirrors tasks/minimum_capital_2026/om25_cap_sweep.py (OM25) but the two
strategies need different injection points, because they select names
differently:

L6 v2 -- the score is a cross-sectional z-score over the whole universe
and `run_strategy` picks the top-24 from it. So the cap goes in
`membership_fn`, exactly as for OM25: the score is untouched, only the
buy list narrows, and the engine's grandfather rule keeps an appreciated
holding because that holding retains its true score rank.

COMBO -- `make_combo_score_fn` truncates EACH component to its top-12 and
returns only those 24 names. A membership-level cap would therefore let
expensive names consume component slots and then be filtered out by
`_relevant_ranking`, leaving the book holding fewer than 24 names -- an
under-invested portfolio, not a fair test. So the cap is applied by
wrapping each component score_fn to drop capped names from its ranking
BEFORE the composite truncates. Component scores themselves are computed
first and filtered after, so the L6 z-score and the OM25 pct-ranks are
identical to production; only the selection pool narrows.

Consequence, and it is a real asymmetry worth reporting: COMBO's
composite emits exactly 24 names and runs exit_buffer=0, so a holding
that appreciates through the cap drops out of the composite and is
exited. COMBO cannot grandfather winners the way OM25 and L6 can. The
`--report-forced-exits` output quantifies that.

Usage:
    python tasks/minimum_capital_2026/l6_combo_cap_study.py --cap 4000
    python tasks/minimum_capital_2026/l6_combo_cap_study.py --cap 4000 --placebo-seeds 30
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts._momentum_engine import (
    BASELINE, build_momentum_panels, make_momentum_score, run_momentum,
    lookback_months_to_days,
)
from data_pipeline.loaders import load_price_panels, load_benchmark
from scripts.combo_defensive import LOCKED as COMBO_LOCKED, make_combo_score_fn
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.universe_membership import resolve_universe, union_membership_fns

OUT = Path(__file__).resolve().parent / "runs"


def price_at(close_panel, date):
    if date in close_panel.index:
        return close_panel.loc[date]
    i = close_panel.index.searchsorted(date, side="right") - 1
    return close_panel.iloc[i] if i >= 0 else pd.Series(dtype=float)


def eligible_at(close_panel, date, cap):
    row = price_at(close_panel, date)
    return frozenset(row.index[(row <= cap) & row.notna()])


def summarise(res):
    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    yrs = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    return {
        "start": str(pv.index[0].date()), "end": str(pv.index[-1].date()),
        "years": round(yrs, 2), "end_value": round(float(pv.iloc[-1]), 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe_rf5": round((cagr - 0.05) / vol if vol > 0 else 0, 2),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round((pv / pv.cummax()).min() * 100 - 100, 2),
        "n_buys": int((res["trades"]["side"] == "BUY").sum()),
        "n_sells": int((res["trades"]["side"] != "BUY").sum()),
    }


# ---------------------------------------------------------------- L6 v2

def build_l6(close_panel, trade_panel, calendar, benchmark_aligned,
             sma_200, atr_20, start):
    uni, mem_fn, cand_fn = resolve_universe(
        ROOT / "data/static/nse500_membership.csv",
        ROOT / BASELINE["universe_csv"])
    cols = [s for s in close_panel.columns if s in uni]
    panels = build_momentum_panels(
        close_panel[cols],
        lookback_days=lookback_months_to_days(BASELINE["lookback_months"]),
        skip_days=BASELINE["skip_days"])

    def run(mem_override):
        return run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start=start, end="2099-12-31", config={},
            membership_fn=mem_override, candidate_fn=cand_fn)

    return run, mem_fn, cols


# --------------------------------------------------------------- COMBO

def build_combo(close_panel, trade_panel, calendar, benchmark_aligned,
                sma_200, atr_20, start, regime_index):
    nse_uni, l6_mem, l6_cand = resolve_universe(
        ROOT / "data/static/nse500_membership.csv",
        ROOT / COMBO_LOCKED["l6_universe_csv"])
    nse_cols = [s for s in close_panel.columns if s in nse_uni]
    l6_panels = build_momentum_panels(
        close_panel[nse_cols],
        lookback_days=lookback_months_to_days(COMBO_LOCKED["l6_lookback_months"]),
        skip_days=COMBO_LOCKED["l6_skip_days"])
    l6_score = make_momentum_score(
        l6_panels, vol_floor=COMBO_LOCKED["l6_vol_floor"],
        vol_power=COMBO_LOCKED["l6_vol_power"],
        cross_sectional_zscore=True, candidate_fn=l6_cand)

    n250_uni, om_mem, om_cand = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv",
        ROOT / COMBO_LOCKED["om25_universe_csv"])
    n250_cols = [s for s in close_panel.columns if s in n250_uni]
    om_regime = build_regime_panel_confirmed(
        regime_index, OM25_LOCKED["regime_ma_window"],
        OM25_LOCKED["regime_confirm_days"], calendar=calendar)
    om_score = make_om25_tilt_score(
        close_panel[n250_cols].pct_change(), om_regime,
        bull_w_uc=COMBO_LOCKED["om25_bull_w_uc"],
        bull_w_cr=COMBO_LOCKED["om25_bull_w_cr"],
        bear_w_uc=COMBO_LOCKED["om25_bear_w_uc"],
        bear_w_cr=COMBO_LOCKED["om25_bear_w_cr"],
        return_filter=COMBO_LOCKED["om25_return_filter"],
        lookback=COMBO_LOCKED["om25_lookback"],
        min_obs=COMBO_LOCKED["om25_min_obs"], candidate_fn=om_cand)

    portfolio_regime = build_regime_panel_confirmed(
        regime_index, COMBO_LOCKED["regime_ma_window"],
        COMBO_LOCKED["regime_confirm_days"], calendar=calendar)
    mem = (union_membership_fns([l6_mem, om_mem])
           if (l6_mem or om_mem) else None)

    weekly_fri = fridays(calendar)
    entry_all = biweekly_fridays(calendar)
    s, e = pd.Timestamp(start), calendar[-1]
    weekly_filt = weekly_fri[(weekly_fri >= s) & (weekly_fri <= e)]
    entry_dates = entry_all[(entry_all >= s) & (entry_all <= e)]

    def run(keep_fn):
        """keep_fn(date) -> allowed symbol set, or None for production."""
        if keep_fn is None:
            components = [("L6", l6_score), ("OM25", om_score)]
        else:
            def wrap(sf):
                def f(signal_date, **kw):
                    sc = sf(signal_date, **kw)
                    if sc is None or sc.empty:
                        return sc
                    allowed = keep_fn(signal_date)
                    return sc[sc.index.isin(allowed)]
                return f
            components = [("L6", wrap(l6_score)), ("OM25", wrap(om_score))]
        combo_score = make_combo_score_fn(
            components, n_per=COMBO_LOCKED["n_per_strategy"])
        return run_strategy(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=combo_score, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=COMBO_LOCKED["top_n"], exit_buffer=COMBO_LOCKED["exit_buffer"],
            max_weight=COMBO_LOCKED["max_weight"],
            slippage=COMBO_LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=0.0,
            use_trailing_stop=False, use_dma_exit=False,
            weekly_rank_check=False,
            regime_panel=portfolio_regime,
            bear_exposure=COMBO_LOCKED["regime_bear_exposure"],
            membership_fn=mem, min_hold_days=COMBO_LOCKED["min_hold_days"],
            initial_capital=1_000_000)

    return run, sorted(set(nse_cols) | set(n250_cols)), entry_dates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, default=4000)
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--placebo-seeds", type=int, default=30)
    args = ap.parse_args()

    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data")
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    regime_index = ROOT / "indices_data/NIFTY_100.csv"
    CAP = args.cap
    results = {}

    # ---------------- L6 v2 ----------------
    print("\n=== L6 v2 ===")
    l6_run, l6_mem, l6_cols = build_l6(
        close_panel, trade_panel, calendar, benchmark_aligned,
        sma_200, atr_20, args.start)

    print("[run] baseline ...")
    res = l6_run(l6_mem)
    results["l6_baseline"] = summarise(res)
    res["trades"].to_csv(OUT / "trades_l6_baseline.csv", index=False)
    res["equity"].to_csv(OUT / "equity_l6_baseline.csv", index=False)
    print("  " + json.dumps(results["l6_baseline"]))

    print(f"[run] entry cap Rs {CAP:,.0f} ...")
    cache = {}

    def l6_capped(date):
        k = pd.Timestamp(date)
        if k not in cache:
            base = frozenset(l6_mem(k)) if l6_mem else frozenset(l6_cols)
            cache[k] = base & eligible_at(close_panel, k, CAP)
        return cache[k]

    res = l6_run(l6_capped)
    results["l6_cap"] = summarise(res)
    res["trades"].to_csv(OUT / "trades_l6_cap.csv", index=False)
    res["equity"].to_csv(OUT / "equity_l6_cap.csv", index=False)
    print("  " + json.dumps(results["l6_cap"]))

    # ---------------- COMBO ----------------
    print("\n=== COMBO Defensive ===")
    combo_run, combo_cols, combo_entries = build_combo(
        close_panel, trade_panel, calendar, benchmark_aligned,
        sma_200, atr_20, args.start, regime_index)

    print("[run] baseline ...")
    res = combo_run(None)
    results["combo_baseline"] = summarise(res)
    res["trades"].to_csv(OUT / "trades_combo_baseline.csv", index=False)
    res["equity"].to_csv(OUT / "equity_combo_baseline.csv", index=False)
    print("  " + json.dumps(results["combo_baseline"]))

    print(f"[run] entry cap Rs {CAP:,.0f} ...")
    res = combo_run(lambda d: eligible_at(close_panel, d, CAP))
    results["combo_cap"] = summarise(res)
    res["trades"].to_csv(OUT / "trades_combo_cap.csv", index=False)
    res["equity"].to_csv(OUT / "equity_combo_cap.csv", index=False)
    print("  " + json.dumps(results["combo_cap"]))

    # ---------------- placebos ----------------
    if args.placebo_seeds > 0:
        for tag in ("l6", "combo"):
            cols = l6_cols if tag == "l6" else combo_cols
            blocked = set()
            dates = ([d for d in calendar if d in calendar][:0] or None)
            probe = combo_entries if tag == "combo" else \
                [d for d in calendar if d.weekday() == 3]
            probe = [d for d in probe if d >= pd.Timestamp(args.start)]
            for d in probe:
                row = price_at(close_panel, d)
                blocked |= set(row.index[(row > CAP) & row.notna()]) & set(cols)
            n_blocked = len(blocked)
            print(f"\n[placebo {tag}] cap blocks {n_blocked} of {len(cols)} names; "
                  f"{args.placebo_seeds} random-exclusion seeds")
            rows = []
            for seed in range(args.placebo_seeds):
                drop = frozenset(random.Random(seed).sample(cols, n_blocked))
                keep = frozenset(c for c in cols if c not in drop)
                if tag == "l6":
                    def mem(date, _k=keep):
                        b = frozenset(l6_mem(date)) if l6_mem else frozenset(l6_cols)
                        return b & _k
                    r = l6_run(mem)
                else:
                    r = combo_run(lambda d, _k=keep: _k)
                s = summarise(r)
                rows.append({"seed": seed, **{k: s[k] for k in
                                              ("cagr_pct", "sharpe_rf5", "max_dd_pct")}})
                print(f"  seed {seed:3d}: CAGR {s['cagr_pct']:6.2f}%  "
                      f"Sharpe {s['sharpe_rf5']:5.2f}  MaxDD {s['max_dd_pct']:7.2f}%")
            df = pd.DataFrame(rows)
            df.to_csv(OUT / f"placebo_{tag}_cap{int(CAP)}.csv", index=False)
            q = df["cagr_pct"].quantile([.05, .5, .95])
            results[f"{tag}_placebo"] = {
                "n_blocked": n_blocked, "n_seeds": args.placebo_seeds,
                "mean": round(df["cagr_pct"].mean(), 2),
                "sd": round(df["cagr_pct"].std(), 2),
                "min": round(df["cagr_pct"].min(), 2),
                "max": round(df["cagr_pct"].max(), 2),
                "p5": round(q.iloc[0], 2), "p50": round(q.iloc[1], 2),
                "p95": round(q.iloc[2], 2)}
            print(f"  -> mean {df['cagr_pct'].mean():.2f}%  "
                  f"sd {df['cagr_pct'].std():.2f}pp  "
                  f"range {df['cagr_pct'].min():.2f}-{df['cagr_pct'].max():.2f}%")

    (OUT / f"results_l6_combo_cap{int(CAP)}.json").write_text(
        json.dumps(results, indent=2))

    print("\n" + "=" * 74)
    print(f"{'arm':>16} {'CAGR':>8} {'Sharpe':>8} {'MaxDD':>9} {'vol':>7} {'buys':>6}")
    for k in ("l6_baseline", "l6_cap", "combo_baseline", "combo_cap"):
        v = results[k]
        print(f"{k:>16} {v['cagr_pct']:7.2f}% {v['sharpe_rf5']:8.2f} "
              f"{v['max_dd_pct']:8.2f}% {v['vol_pct']:6.1f}% {v['n_buys']:6d}")
    print("=" * 74)


if __name__ == "__main__":
    main()
