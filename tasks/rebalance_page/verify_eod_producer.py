"""Sanity-check the EOD producer's placeholder-bar approach.

Runs the engine twice on the same signal date:

1. **Placeholder mode** (what the producer does at 16:00 IST on signal day):
   panels are truncated at ``signal_date`` and a fake next-day bar is
   appended where every price equals the signal-day close. The engine
   executes the rebalance against that fake bar.
2. **Real-bar mode** (what the engine actually does later, once the next
   bar arrives): panels are truncated at ``signal_date + ~3 trading days``
   so the engine sees a real next bar.

Then derives the membership-only proposal (exits / entries / continuing)
from each and diffs them. Membership should be **identical**: the engine
selects from signal-day data only, so the next-day fill price affects
share counts and PnL but never the chosen names.

Output: a one-line per-symbol diff. If anything differs, the producer's
approach is broken — that's the bug to fix.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.engine_readout import partition_membership_by_date
from data_pipeline.eod_proposal import (
    _STRATEGIES, _append_placeholder_bar, _pick_signal_date,
)
from scripts._clean_engine import run_strategy


def _engine_membership(strategy: str, signal_date: pd.Timestamp,
                        prices_dir: Path, *, real_bar: bool,
                        backtest_start: str = "2018-01-01") -> dict:
    state = _STRATEGIES[strategy](prices_dir=prices_dir)

    if real_bar:
        # Truncate the panel calendar enough to expose the next trading day
        # after `signal_date`, but no further (so weekly rank-exit on later
        # weeks doesn't pollute the membership at exec_date).
        # 5 calendar days is plenty for any weekend / single holiday.
        cap = signal_date + pd.Timedelta(days=5)
        cap = min(cap, state.close_panel.index[-1])
        for attr in ("close_panel", "trade_panel", "sma_200", "atr_20"):
            df = getattr(state, attr)
            setattr(state, attr, df[df.index <= cap].copy())
        state.benchmark_aligned = state.benchmark_aligned[
            state.benchmark_aligned.index <= cap
        ].copy()
        if state.regime_panel is not None:
            state.regime_panel = state.regime_panel[
                state.regime_panel.index <= cap
            ].copy()
        cal = state.close_panel.index
        next_day = cal[cal > signal_date]
        if len(next_day) == 0:
            raise RuntimeError("No trading day after signal_date in truncated calendar")
        exec_date = next_day[0]
        print(f"  real-bar: cal ends at {cal[-1].date()}, exec_date = {exec_date.date()}")
    else:
        # Producer mode — truncate to signal_date, then append placeholder.
        for attr in ("close_panel", "trade_panel", "sma_200", "atr_20"):
            df = getattr(state, attr)
            setattr(state, attr, df[df.index <= signal_date].copy())
        state.benchmark_aligned = state.benchmark_aligned[
            state.benchmark_aligned.index <= signal_date
        ].copy()
        if state.regime_panel is not None:
            state.regime_panel = state.regime_panel[
                state.regime_panel.index <= signal_date
            ].copy()
        exec_date = _append_placeholder_bar(state, signal_date)
        print(f"  placeholder: cal ends at "
              f"{state.close_panel.index[-1].date()}, exec_date = {exec_date.date()}")

    start_ts = pd.Timestamp(backtest_start)
    entry_dates = state.entry_signal_dates[
        (state.entry_signal_dates >= start_ts)
        & (state.entry_signal_dates <= signal_date)
    ]
    weekly_dates = state.weekly_signal_dates[
        (state.weekly_signal_dates >= start_ts)
        & (state.weekly_signal_dates <= signal_date)
    ]

    res = run_strategy(
        close_panel=state.close_panel,
        trade_panel=state.trade_panel,
        calendar=state.close_panel.index,
        benchmark_aligned=state.benchmark_aligned,
        entry_signal_dates=entry_dates,
        weekly_signal_dates=weekly_dates,
        signal_function=state.score_fn, signal_function_args={},
        sma_200_panel=state.sma_200, atr_20_panel=state.atr_20,
        top_n=state.top_n, exit_buffer=state.exit_buffer,
        max_weight=state.max_weight, slippage=state.slippage,
        atr_mult=0.0, atr_min_floor=state.drawdown_stop,
        use_trailing_stop=state.drawdown_stop > 0,
        use_dma_exit=False,
        weekly_rank_check=state.weekly_rank_check,
        regime_panel=state.regime_panel, bear_exposure=state.bear_exposure,
        initial_capital=1_000_000,
    )
    trades = res["trades"]
    trades_capped = trades[pd.to_datetime(trades["date"]) <= exec_date]
    parts = partition_membership_by_date(trades_capped, exec_date=exec_date)
    return parts


def diff_membership(label: str, signal_date: pd.Timestamp,
                     placeholder: dict, realbar: dict) -> bool:
    a_exits, b_exits = set(placeholder["exits"]), set(realbar["exits"])
    a_entries, b_entries = set(placeholder["entries"]), set(realbar["entries"])
    a_cont, b_cont = set(placeholder["continuing"]), set(realbar["continuing"])

    ok = (a_exits == b_exits and a_entries == b_entries and a_cont == b_cont)
    print(f"\n=== {label}  signal={signal_date.date()}  match={ok} ===")
    print(f"  placeholder  : exits={len(a_exits)} entries={len(a_entries)} "
          f"continuing={len(a_cont)}")
    print(f"  real-bar     : exits={len(b_exits)} entries={len(b_entries)} "
          f"continuing={len(b_cont)}")
    if not ok:
        print(f"  exits diff   : {(a_exits ^ b_exits) or '∅'}")
        print(f"  entries diff : {(a_entries ^ b_entries) or '∅'}")
        print(f"  cont diff    : {(a_cont ^ b_cont) or '∅'}")
    return ok


def main():
    prices_dir = ROOT / "nse500_data_merged"
    cases = [
        ("tl25_v3", pd.Timestamp("2025-12-19")),
        ("tl25_v3", pd.Timestamp("2025-11-07")),
        ("tl25_v3", pd.Timestamp("2026-03-13")),
        ("om25_v3", pd.Timestamp("2025-10-10")),
        ("om25_v3", pd.Timestamp("2025-11-21")),
    ]
    results = []
    for strategy, sd in cases:
        print(f"\n--- {strategy} {sd.date()} ---")
        print("[placeholder]")
        ph = _engine_membership(strategy, sd, prices_dir, real_bar=False)
        print("[real-bar]")
        rb = _engine_membership(strategy, sd, prices_dir, real_bar=True)
        ok = diff_membership(strategy, sd, ph, rb)
        results.append((strategy, sd, ok))

    print("\n=== summary ===")
    for strategy, sd, ok in results:
        print(f"  {strategy} {sd.date()}: {'PASS' if ok else 'FAIL'}")
    if not all(ok for _, _, ok in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
