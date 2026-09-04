"""Regime overlay on the standalone production portfolios: L6 v2 and OM25 v3.

Neither currently has an exposure overlay. L6 v2 has no regime anything.
OM25 v3 uses regime only to TILT its score weights (NIFTY 100 MA) and carries
a 20% trailing drawdown stop; it passes `regime_panel=None, bear_exposure=0.0`
to the engine, so exposure is never cut.

Implementation variants tested (all engine-native, no engine changes):

  exposure_XX  bear -> scale gross exposure to XX% (COMBO's mechanic).
               bear_skips_entries=True, the engine default: no new entries
               while bear, so the book also dwindles.
  entry_gate   bear -> hold everything, just stop adding. Implemented as
               bear_exposure=0.999: the engine only honours
               bear_skips_entries when is_bear (target_exposure < 1.0), and
               at 0.999 the pro-rata sell resolves to zero shares for normal
               position sizes. A soft de-risk that never force-sells.
  scaled_XX    bear -> cut exposure to XX% but KEEP entering at reduced
               weight (bear_skips_entries=False), preserving the N-name
               structure instead of letting holdings decay.

Not tested here: changing the SCORE in bear (OM25 already does this on
NIFTY 100), and replacing OM25's 20% DD stop with the overlay. Both are
larger changes; see RESULTS.md.

Signals compared: production baseline (no overlay), ma_NIFTY_100 (COMBO's
current control) and roc31_c3 on NIFTY 500 (the candidate from the grid).

Usage:
  python tasks/portfolio_risk_2026/overlay_experiment.py
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

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays, thursdays,
)
from scripts._momentum_engine import (
    BASELINE as L6_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.om25_v3 import LOCKED as OM25_LOCKED, make_om25_tilt_score
from scripts.universe_membership import resolve_universe

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
sys.path.insert(0, str(HERE))
from exit_buffer_sweep import window_metrics                # noqa: E402
from rolling_returns import underwater_stats, rolling_stats  # noqa: E402
from regime_experiment import build_regime, WINDOWS, EVAL_START  # noqa: E402

SIGNALS = [
    ("ma_N100",   dict(index_name="NIFTY_100", kind="ma",  param=100, confirm_days=3)),
    ("roc31_N500", dict(index_name="NIFTY_500", kind="roc", param=31,  confirm_days=3)),
]

# (label, bear_exposure, bear_skips_entries)
VARIANTS = [
    ("exposure_00",  0.00,  True),
    ("exposure_25",  0.25,  True),
    ("exposure_50",  0.50,  True),
    ("exposure_75",  0.75,  True),
    ("entry_gate",   0.999, True),
    ("scaled_50",    0.50,  False),
]


def parse_args():
    ap = argparse.ArgumentParser(description="Regime overlay on L6 v2 / OM25 v3")
    ap.add_argument("--portfolios", nargs="+", default=["l6", "om25"])
    ap.add_argument("--start", default=EVAL_START)
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--output", type=Path, default=RUNS / "overlay")
    return ap.parse_args()


def main():
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print("[load] panels ...", flush=True)
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    s, end = pd.Timestamp(args.start), calendar[-1]
    windows = [(l, a, str(end.date()) if b == "PANEL_END" else b)
               for l, a, b in WINDOWS]

    regimes = {name: build_regime(calendar=calendar, **cfg) for name, cfg in SIGNALS}

    # ---- L6 v2: production config, exit_buffer 0, no stop, no overlay ----
    nse500_uni, l6_mem, l6_cand = resolve_universe(
        ROOT / "data/static/nse500_membership.csv", ROOT / L6_BASELINE["universe_csv"])
    l6_panels = build_momentum_panels(
        close_panel[[c for c in close_panel.columns if c in nse500_uni]],
        lookback_days=lookback_months_to_days(L6_BASELINE["lookback_months"]),
        skip_days=L6_BASELINE["skip_days"])
    l6_score = make_momentum_score(
        l6_panels, vol_floor=L6_BASELINE["vol_floor"],
        vol_power=L6_BASELINE["vol_power"], cross_sectional_zscore=True,
        candidate_fn=l6_cand)
    l6_entry = thursdays(calendar)
    l6_entry = l6_entry[(l6_entry >= s) & (l6_entry <= end)]

    # ---- OM25 v3: locked config. Score tilt stays on NIFTY 100 per spec so
    # only the exposure overlay is under test. 20% DD stop retained.
    om_uni, om_mem, om_cand = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv",
        ROOT / OM25_LOCKED["universe_csv"])
    om_returns = close_panel[[c for c in close_panel.columns if c in om_uni]].pct_change()
    om_score = make_om25_tilt_score(
        om_returns, regimes["ma_N100"],
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
        candidate_fn=om_cand)
    om_entry = biweekly_fridays(calendar)
    om_entry = om_entry[(om_entry >= s) & (om_entry <= end)]
    weekly_fri = fridays(calendar)
    weekly_fri = weekly_fri[(weekly_fri >= s) & (weekly_fri <= end)]
    weekly_thu = thursdays(calendar)
    weekly_thu = weekly_thu[(weekly_thu >= s) & (weekly_thu <= end)]

    SPECS = {
        "l6": dict(score=l6_score, entry=l6_entry, weekly=weekly_thu,
                   top_n=L6_BASELINE["top_n"], exit_buffer=L6_BASELINE["exit_buffer"],
                   max_weight=L6_BASELINE["max_weight"], slippage=L6_BASELINE["slippage"],
                   dd_stop=0.0, min_hold=L6_BASELINE["min_hold_days"], mem=l6_mem),
        "om25": dict(score=om_score, entry=om_entry, weekly=weekly_fri,
                     top_n=OM25_LOCKED["top_n"], exit_buffer=OM25_LOCKED["exit_buffer"],
                     max_weight=OM25_LOCKED["max_weight"], slippage=OM25_LOCKED["slippage"],
                     dd_stop=OM25_LOCKED["drawdown_stop_pct"], min_hold=0, mem=om_mem),
    }

    def run(pf, label, regime, bear_exp, skips):
        c = SPECS[pf]
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
            benchmark_aligned=benchmark_aligned,
            entry_signal_dates=c["entry"], weekly_signal_dates=c["weekly"],
            signal_function=c["score"], signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=c["top_n"], exit_buffer=c["exit_buffer"],
            max_weight=c["max_weight"], slippage=c["slippage"],
            atr_mult=0.0, atr_min_floor=c["dd_stop"],
            use_trailing_stop=c["dd_stop"] > 0, use_dma_exit=False,
            weekly_rank_check=False,
            regime_panel=regime, bear_exposure=bear_exp,
            bear_skips_entries=skips,
            membership_fn=c["mem"], min_hold_days=c["min_hold"],
            initial_capital=1_000_000)
        if res is None or res["equity"].empty:
            return None
        eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
        tr = res["trades"].copy(); tr["date"] = pd.to_datetime(tr["date"])
        ex = res["exits"].copy()
        if not ex.empty:
            ex["exit_date"] = pd.to_datetime(ex["exit_date"])
        eq.to_csv(args.output / f"{pf}_{label}_equity.csv", index=False)
        return eq, tr, ex

    rows, inv = [], []
    for pf in args.portfolios:
        jobs = [("production", None, 0.0, True)]
        for sig_name in [n for n, _ in SIGNALS]:
            for vlabel, bexp, skips in VARIANTS:
                jobs.append((f"{sig_name}_{vlabel}", regimes[sig_name], bexp, skips))
        for label, regime, bexp, skips in jobs:
            t = time.time()
            out = run(pf, label, regime, bexp, skips)
            if out is None:
                print(f"  [skip] {pf} {label}"); continue
            eq, tr, ex = out
            for wl, a, b in windows:
                r = window_metrics(wl, eq, tr, ex, a, b)
                r["portfolio"] = pf; r["variant"] = label
                rows.append(r)
            pv = eq.set_index("date")["pv"].astype(float)
            r12 = rolling_stats(pv, 252)
            inv.append({"portfolio": pf, "variant": label, **underwater_stats(pv),
                        "pct_12m_negative": r12.get("pct_negative"),
                        "median_12m": r12.get("median"),
                        "avg_cash_pct": round(eq["cash_pct"].mean() * 100, 1),
                        "avg_holdings": round(eq["holdings"].mean(), 1)})
            print(f"  {pf:<5} {label:<28} ({time.time()-t:.0f}s)", flush=True)

    pd.DataFrame(rows).to_csv(args.output / "overlay_summary.csv", index=False)
    pd.DataFrame(inv).to_csv(args.output / "overlay_investor.csv", index=False)
    print(f"\n[wrote] {args.output}/overlay_summary.csv")
    print(f"[total] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
