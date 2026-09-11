"""Run one OM25 v3 config at a given entry cadence and universe.

Everything except entry cadence and universe is held at the production
locked-in stack (scripts/om25_v3.py:LOCKED). Weekly exit checks (the
20%-from-peak drawdown stop) run at every Friday for all cadences, exactly
as production does — only the entry rebalance frequency varies.

Rank exits fire at entry rebalance dates (weekly_rank_check=False, matching
production), so a weekly cadence also means weekly rank-exit evaluation.
That is the same construction the archived May 2026 sweep used
(tasks/om25/experiments/_om25_cadence_test.py on the archive branch).

Usage:
    python tasks/om25_cadence_2026/_cadence_run.py \
        --universe nifty250 --cadence weekly
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (  # noqa: E402
    run_strategy, fridays, biweekly_fridays, monthly_first_trading_day,
)
from data_pipeline.loaders import load_price_panels, load_benchmark  # noqa: E402
from scripts.om25_v3 import (  # noqa: E402
    LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.universe_membership import resolve_universe  # noqa: E402

UNIVERSES = {
    "nifty250": ("data/static/nifty250_universe.csv",
                 "data/static/nifty250_membership.csv"),
    "nse500": ("data/static/nse500_universe.csv",
               "data/static/nse500_membership.csv"),
}

CADENCES = {
    "weekly": fridays,
    "biweekly": biweekly_fridays,
    "monthly": monthly_first_trading_day,
}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", choices=sorted(UNIVERSES), required=True)
    ap.add_argument("--cadence", choices=sorted(CADENCES), required=True)
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged")
    ap.add_argument("--start", default="2010-01-01",
                    help="First entry signal date (needs 252d lookback before it)")
    ap.add_argument("--end", default=None)
    ap.add_argument("--biweekly-phase", type=int, choices=[0, 1], default=0,
                    help="Which alternate Friday the biweekly grid starts on. "
                         "fridays()[phase::2]. The archive's v3 runs used phase 1.")
    ap.add_argument("--no-membership", action="store_true",
                    help="Legacy behaviour: snapshot universe, no date masking "
                         "(what the May 2026 v3 retune ran)")
    ap.add_argument("--tag", default=None, help="Override output dir name")
    ap.add_argument("--out-root", type=Path,
                    default=Path(__file__).resolve().parent / "runs")
    return ap.parse_args()


def main():
    args = parse_args()
    t0 = time.time()
    uni_csv, mem_csv = UNIVERSES[args.universe]
    out_dir = args.out_root / (args.tag or f"{args.universe}_{args.cadence}")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{args.universe}/{args.cadence}] loading panels ...", flush=True)
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_all = fridays(calendar)
    if args.cadence == "biweekly":
        entry_all = pd.DatetimeIndex(weekly_all.values[args.biweekly_phase::2])
    else:
        entry_all = CADENCES[args.cadence](calendar)
    start_ts = pd.Timestamp(args.start)
    end_ts = pd.Timestamp(args.end) if args.end else calendar[-1]
    weekly_filt = weekly_all[(weekly_all >= start_ts) & (weekly_all <= end_ts)]
    entry_dates = entry_all[(entry_all >= start_ts) & (entry_all <= end_ts)]

    mem_path = ROOT / mem_csv
    if args.no_membership:
        mem_path = ROOT / "__no_such_membership__.csv"
    universe, membership_fn, candidate_fn = resolve_universe(
        mem_path, ROOT / uni_csv)
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()
    print(f"[{args.universe}/{args.cadence}] {len(cols)} symbols, "
          f"{len(entry_dates)} entries, {len(weekly_filt)} weekly checks",
          flush=True)

    regime = build_regime_panel_confirmed(
        ROOT / LOCKED["regime_index_path"],
        LOCKED["regime_ma_window"], LOCKED["regime_confirm_days"],
        calendar=calendar,
    )

    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
        bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
        return_filter=LOCKED["return_filter"],
        lookback=LOCKED["lookback"], min_obs=LOCKED["min_obs"],
        candidate_fn=candidate_fn,
    )

    print(f"[{args.universe}/{args.cadence}] backtesting ...", flush=True)
    res = run_strategy(
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
        membership_fn=membership_fn,
        initial_capital=1_000_000,
    )
    if res is None:
        raise SystemExit(f"no result for {args.universe}/{args.cadence}")

    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq.to_csv(out_dir / "equity.csv", index=False)
    res["trades"].to_csv(out_dir / "trades.csv", index=False)
    res["exits"].to_csv(out_dir / "exits.csv", index=False)

    trades = res["trades"]
    meta = {
        "universe": args.universe,
        "cadence": args.cadence,
        "prices_dir": str(args.prices_dir),
        "n_symbols": len(cols),
        "membership": not args.no_membership,
        "start_arg": args.start,
        "biweekly_phase": args.biweekly_phase,
        "n_entry_dates": len(entry_dates),
        "n_weekly_checks": len(weekly_filt),
        "start": str(eq["date"].iloc[0].date()),
        "end": str(eq["date"].iloc[-1].date()),
        "n_buys": int((trades["side"] == "BUY").sum()),
        "n_sells": int((trades["side"] == "SELL").sum()),
        "runtime_sec": round(time.time() - t0, 1),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[{args.universe}/{args.cadence}] done in "
          f"{meta['runtime_sec']}s -> {out_dir}", flush=True)


if __name__ == "__main__":
    main()
