"""Exit-buffer sweep on production L6 v2.

Runs the locked L6 v2 config with `exit_buffer` varied over a list of values,
one continuous backtest per value, then slices each equity curve into the
oos_retune_2026 IS/OOS windows and reports per-window metrics.

Continuous-run-then-slice (rather than one backtest per window) so OOS windows
start from a live portfolio instead of re-warming from cash at each boundary.

Usage:
  python tasks/portfolio_risk_2026/exit_buffer_sweep.py
  python tasks/portfolio_risk_2026/exit_buffer_sweep.py --buffers 0 5 10 15 20
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._momentum_engine import (
    BASELINE, build_momentum_panels, run_momentum, lookback_months_to_days,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe

HERE = Path(__file__).resolve().parent

# oos_retune_2026 split. PANEL_END fills in from the loaded calendar.
WINDOWS = [
    ("IS",        "2009-09-01", "2016-12-31"),
    ("OOS_A",     "2017-01-01", "2019-12-31"),
    ("OOS_B",     "2020-01-01", "2022-12-31"),
    ("OOS_C",     "2023-01-01", "2026-05-08"),
    ("OOS_FULL",  "2017-01-01", "2026-05-08"),
    ("LIVE_2026", "2026-05-09", "PANEL_END"),
    ("FULL",      "2009-09-01", "PANEL_END"),
]


def window_metrics(label, eq, trades, exits, start, end) -> dict:
    """Metrics over one date slice of a continuous run."""
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    sub = eq[(eq["date"] >= s) & (eq["date"] <= e)]
    row = {"window": label, "start": start, "end": end}
    if len(sub) < 3:
        return {**row, "n_days": len(sub)}

    pv = sub.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    yrs = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    downside = rets[rets < 0].std() * math.sqrt(252)
    max_dd = (pv / pv.cummax() - 1).min()

    tr = trades[(trades["date"] >= s) & (trades["date"] <= e)]
    ex = exits[(exits["exit_date"] >= s) & (exits["exit_date"] <= e)]
    pnl = ex["pnl_pct"].dropna() if "pnl_pct" in ex.columns else pd.Series(dtype=float)

    return {
        **row,
        "n_days": len(sub),
        "yrs": round(yrs, 2),
        "cagr_pct": round(cagr * 100, 2),
        "vol_pct": round(vol * 100, 2),
        # docs/portfolios.md convention (CAGR/vol) and the multi-window
        # evaluator convention (arithmetic mean/vol) — they diverge on
        # skewed windows, so report both rather than pick a side.
        "sharpe": round(cagr / vol, 2) if vol > 0 else np.nan,
        "sharpe_ar": round((rets.mean() * 252) / vol, 2) if vol > 0 else np.nan,
        "sortino": round(cagr / downside, 2) if downside and downside > 0 else np.nan,
        "max_dd_pct": round(max_dd * 100, 2),
        "calmar": round(cagr / abs(max_dd), 2) if max_dd < 0 else np.nan,
        "n_trades": len(tr),
        "rt_per_year": round(len(ex) / yrs, 1),
        "hit_rate_pct": round(pnl.gt(0).mean() * 100, 1) if len(pnl) else np.nan,
        "avg_hold_days": (round(ex["hold_days"].dropna().mean(), 1)
                          if "hold_days" in ex.columns and len(ex) else np.nan),
        # Slippage paid per year as % of portfolio value at the time of the
        # trade. Cumulative-over-initial-capital is meaningless on a
        # compounding curve, so normalise each trade by same-day PV.
        "cost_pct_pv_yr": (round(
            (tr["slippage"] / tr["date"].map(pv).ffill()).sum() / yrs * 100, 2)
            if len(tr) else 0.0),
    }


def parse_args():
    ap = argparse.ArgumentParser(description="L6 v2 exit-buffer sweep")
    ap.add_argument("--buffers", type=int, nargs="+", default=[0, 5, 10, 15, 20])
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--universe", type=Path, default=ROOT / BASELINE["universe_csv"])
    ap.add_argument("--membership", type=Path,
                    default=ROOT / "data/static/nse500_membership.csv")
    ap.add_argument("--slippage", type=float, default=BASELINE["slippage"],
                    help="Per-side slippage; sensitivity runs use 0.004 / 0.006")
    ap.add_argument("--start", default="2009-09-01")
    ap.add_argument("--end", default=None, help="default: panel end")
    ap.add_argument("--output", type=Path, default=HERE / "runs")
    return ap.parse_args()


def main():
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"[load] price panels {args.prices_dir.name} ...", flush=True)
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    panel_end = calendar[-1]
    end = pd.Timestamp(args.end) if args.end else panel_end
    print(f"  calendar {calendar[0].date()} -> {panel_end.date()} "
          f"({len(calendar)} days, {len(close_panel.columns)} symbols)")

    membership_fn = candidate_fn = None
    if args.membership.exists():
        from scripts.universe_membership import (
            load_membership, all_ever_members, make_membership_fn, make_candidate_fn,
        )
        mdf = load_membership(args.membership)
        universe = all_ever_members(mdf)
        membership_fn = make_membership_fn(mdf)
        candidate_fn = make_candidate_fn(mdf)
        print(f"  membership: {args.membership.name} ({len(universe)} all-ever symbols)")
    else:
        universe = load_universe(args.universe)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  universe matched {len(cols)} symbols  ({time.time()-t0:.1f}s)", flush=True)

    print(f"[panels] L{BASELINE['lookback_months']} momentum + vol ...", flush=True)
    panels = build_momentum_panels(
        close_uni,
        lookback_days=lookback_months_to_days(BASELINE["lookback_months"]),
        skip_days=BASELINE["skip_days"],
    )

    windows = [(lbl, s, str(end.date()) if e == "PANEL_END" else e)
               for lbl, s, e in WINDOWS]

    all_rows = []
    for buf in args.buffers:
        t = time.time()
        print(f"\n[run] exit_buffer={buf} slippage={args.slippage} ...", flush=True)
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start=args.start, end=str(end.date()),
            config={"exit_buffer": buf, "slippage": args.slippage},
            membership_fn=membership_fn, candidate_fn=candidate_fn,
        )
        if res is None or res["equity"].empty:
            print(f"  [skip] empty result for buffer={buf}")
            continue

        eq = res["equity"].copy()
        eq["date"] = pd.to_datetime(eq["date"])
        trades = res["trades"].copy()
        trades["date"] = pd.to_datetime(trades["date"])
        exits = res["exits"].copy()
        if not exits.empty:
            exits["exit_date"] = pd.to_datetime(exits["exit_date"])

        tag = f"buf{buf:02d}"
        eq.to_csv(args.output / f"{tag}_equity.csv", index=False)
        trades.to_csv(args.output / f"{tag}_trades.csv", index=False)
        exits.to_csv(args.output / f"{tag}_exits.csv", index=False)

        for lbl, s, e in windows:
            row = window_metrics(lbl, eq, trades, exits, s, e)
            row["exit_buffer"] = buf
            all_rows.append(row)
        print(f"  done in {time.time()-t:.1f}s  "
              f"({len(trades)} trades, {len(exits)} exits)", flush=True)

    df = pd.DataFrame(all_rows)
    cols_order = ["exit_buffer", "window", "start", "end", "yrs", "cagr_pct",
                  "vol_pct", "sharpe", "sharpe_ar", "sortino", "max_dd_pct",
                  "calmar", "n_trades", "rt_per_year", "hit_rate_pct",
                  "avg_hold_days", "cost_pct_pv_yr", "n_days"]
    df = df[[c for c in cols_order if c in df.columns]]
    out = args.output / "summary.csv"
    df.to_csv(out, index=False)
    print(f"\n[wrote] {out}")

    show = ["exit_buffer", "cagr_pct", "vol_pct", "sharpe", "sharpe_ar",
            "max_dd_pct", "calmar", "rt_per_year", "hit_rate_pct",
            "avg_hold_days", "cost_pct_pv_yr", "n_trades"]
    for lbl, s, e in windows:
        sub = df[df["window"] == lbl]
        if sub.empty:
            continue
        print(f"\n{'='*104}")
        print(f"{lbl}   {s} -> {e}   ({sub['yrs'].iloc[0]}y)")
        print(f"{'='*104}")
        print(sub[[c for c in show if c in sub.columns]].to_string(index=False))
    print(f"\n[total] {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
