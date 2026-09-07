"""OM25 v3 price-cap study — what a per-share price ceiling costs.

Motivation: at a Rs 5-10L account the position size is capital/25, so a
share priced above the position is unbuyable. Excluding expensive names
outright would make the published book replicable at lower capital. This
measures what that exclusion costs.

Design: the cap is applied ONLY to entry eligibility, by wrapping
`membership_fn`. It is deliberately NOT applied to `candidate_fn` --
candidate_fn feeds the cross-sectional score (market_ret is the
equal-weight mean over candidate columns, and both metrics are
pct-ranked over them), so capping it would change every surviving
stock's score and confound "restricted buy list" with "different score".
Wrapping membership_fn leaves the production score byte-identical and
changes exactly one thing: which names may be bought.

The engine's grandfather rule then gives the economically right
behaviour for free -- a held name that appreciates through the cap is
kept, not force-sold. Forced exit on breach is run separately as the
`hard` mode, because a cap that sells winners is a different (and much
worse) strategy.

Usage:
    python tasks/minimum_capital_2026/om25_cap_sweep.py
    python tasks/minimum_capital_2026/om25_cap_sweep.py --caps 4000
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from data_pipeline.loaders import load_price_panels, load_benchmark
from scripts.om25_v3 import (
    LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.universe_membership import resolve_universe

OUT = Path(__file__).resolve().parent / "runs"


def price_at(close_panel: pd.DataFrame, date: pd.Timestamp) -> pd.Series:
    """Last known close on or before `date` (panel is already ffilled)."""
    if date in close_panel.index:
        return close_panel.loc[date]
    i = close_panel.index.searchsorted(date, side="right") - 1
    if i < 0:
        return pd.Series(dtype=float)
    return close_panel.iloc[i]


def make_capped_membership_fn(base_fn, close_panel, cap, all_symbols):
    """members(date) intersected with {price <= cap} at that date.

    base_fn is None under the legacy-snapshot path, in which case the
    universe itself is the unmasked member set.
    """
    cache = {}

    def fn(date):
        key = pd.Timestamp(date)
        if key in cache:
            return cache[key]
        base = frozenset(base_fn(key)) if base_fn is not None else all_symbols
        row = price_at(close_panel, key)
        cheap = frozenset(row.index[(row <= cap) & row.notna()])
        out = base & cheap
        cache[key] = out
        return out

    return fn


def summarise(eq: pd.DataFrame, trades: pd.DataFrame) -> dict:
    pv = eq.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    yrs = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    mdd = (pv / pv.cummax()).min() - 1
    return {
        "start": str(pv.index[0].date()),
        "end": str(pv.index[-1].date()),
        "years": round(yrs, 2),
        "end_value": round(float(pv.iloc[-1]), 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe_rf5": round((cagr - 0.05) / vol if vol > 0 else 0, 2),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(mdd * 100, 2),
        "n_buys": int((trades["side"] == "BUY").sum()),
        "n_sells": int((trades["side"] == "SELL").sum()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--caps", type=float, nargs="*",
                    default=[2000, 4000, 8000])
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data")
    ap.add_argument("--regime-index", type=Path,
                    default=ROOT / "indices_data/NIFTY_100.csv")
    args = ap.parse_args()

    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_fri = fridays(calendar)
    entry_all = biweekly_fridays(calendar)
    start_ts = pd.Timestamp(args.start)
    end_ts = calendar[-1]
    weekly_filt = weekly_fri[(weekly_fri >= start_ts) & (weekly_fri <= end_ts)]
    entry_dates = entry_all[(entry_all >= start_ts) & (entry_all <= end_ts)]

    universe, membership_fn, candidate_fn = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv",
        ROOT / LOCKED["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()
    all_symbols = frozenset(cols)
    print(f"  universe {len(cols)} symbols, {len(entry_dates)} entry dates")

    regime = build_regime_panel_confirmed(
        args.regime_index, LOCKED["regime_ma_window"],
        LOCKED["regime_confirm_days"], calendar=calendar)

    # Score is identical across every arm -- built once, deliberately with
    # the production candidate_fn.
    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
        bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
        return_filter=LOCKED["return_filter"],
        lookback=LOCKED["lookback"], min_obs=LOCKED["min_obs"],
        candidate_fn=candidate_fn,
    )

    def run(mem_fn):
        return run_strategy(
            close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
            benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
            max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=LOCKED["drawdown_stop_pct"],
            use_trailing_stop=True, use_dma_exit=False,
            regime_panel=None, bear_exposure=0.0,
            membership_fn=mem_fn, initial_capital=1_000_000,
        )

    results = {}
    print("\n[run] baseline (no cap) ...")
    res = run(membership_fn)
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    results["baseline"] = summarise(eq, res["trades"])
    res["equity"].to_csv(OUT / "om25_equity_baseline.csv", index=False)
    res["trades"].to_csv(OUT / "om25_trades_baseline.csv", index=False)
    print("  " + json.dumps(results["baseline"]))

    for cap in args.caps:
        tag = f"cap{int(cap)}"
        print(f"\n[run] entry cap Rs {cap:,.0f} ...")
        mem = make_capped_membership_fn(membership_fn, close_panel, cap,
                                        all_symbols)
        res = run(mem)
        eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
        results[tag] = summarise(eq, res["trades"])
        res["equity"].to_csv(OUT / f"om25_equity_{tag}.csv", index=False)
        res["trades"].to_csv(OUT / f"om25_trades_{tag}.csv", index=False)
        print("  " + json.dumps(results[tag]))

    (OUT / "om25_cap_sweep_results.json").write_text(json.dumps(results, indent=2))

    print("\n" + "=" * 78)
    print(f"{'arm':>12} {'CAGR':>8} {'Sharpe':>8} {'MaxDD':>8} {'vol':>7} "
          f"{'endRs':>12} {'buys':>6} {'sells':>6}")
    for k, v in results.items():
        print(f"{k:>12} {v['cagr_pct']:7.2f}% {v['sharpe_rf5']:8.2f} "
              f"{v['max_dd_pct']:7.2f}% {v['vol_pct']:6.1f}% "
              f"{v['end_value']:12,.0f} {v['n_buys']:6d} {v['n_sells']:6d}")
    print("=" * 78)


if __name__ == "__main__":
    main()
