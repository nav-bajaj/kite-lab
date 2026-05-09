"""OM25 baseline refresh — under fixed (daily-peak) clean engine.

Re-runs the production OM25 stack across all 3 universes and 2 cadences:

  Locked-in stack:
  - Composite signal: 50/50 upside_capture pct rank + capture_ratio pct rank
  - 252d return window, min 220 valid obs, positive 252d total return
  - Top-N=25, exit_buffer=15
  - Weekly trailing stop: 4x ATR, no floor
  - Weekly hard exit: Close < 200 DMA
  - Equal weight 1/N, max 7.5%, drift after entry
  - 20 bps slippage

  Variants:
  - Monthly entry  (1st trading day signal -> next trading day exec)
  - Bi-weekly entry (every other Friday signal -> next trading day exec)

Used to refresh the README/DESIGN headline numbers after the daily-peak
trailing-stop fix (May 2026). Compare to pre-fix numbers in README.
"""
import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[3]))
from pathlib import Path
import numpy as np
import pandas as pd

from scripts._clean_engine import (
    run_strategy, compute_metrics,
    fridays, biweekly_fridays, monthly_first_trading_day,
    score_om25_composite,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe


print("Loading shared data...")
close_panel, trade_panel = load_price_panels(Path('nse500_data'))
calendar = close_panel.index
benchmark = load_benchmark(Path('data/benchmarks/nifty100.csv'))
benchmark_aligned = benchmark.reindex(calendar).ffill()

sma_200_full = close_panel.rolling(200, min_periods=200).mean()
atr_20_panel = close_panel.pct_change().rolling(20).std()


weekly_fri = fridays(calendar)
biweekly_fri = biweekly_fridays(calendar)
monthly_first = monthly_first_trading_day(calendar)


def run(*, universe_path, cadence_label, entry_signal_dates, label):
    universe = load_universe(Path(universe_path))
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    returns_uni = close_uni.pct_change()

    min_date = close_uni.index[252]
    entry_filt = entry_signal_dates[entry_signal_dates >= min_date]
    weekly_filt = weekly_fri[weekly_fri >= min_date]

    args = {'returns_universe': returns_uni, 'min_obs': 220}
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_filt, weekly_signal_dates=weekly_filt,
        signal_function=score_om25_composite, signal_function_args=args,
        sma_200_panel=sma_200_full, atr_20_panel=atr_20_panel,
        top_n=25, exit_buffer=15,
        atr_mult=4.0, atr_min_floor=0.0,
        max_weight=0.075, slippage=0.002, use_trailing_stop=True
    )
    if res is None:
        return None
    return compute_metrics(res, label)


universes = [
    ('NSE 500',   'data/static/nse500_universe.csv'),
    ('Nifty 250', 'data/static/nifty250_universe.csv'),
    ('Nifty 100', 'data/static/nifty100_universe.csv'),
]
cadences = [
    ('Monthly',   monthly_first),
    ('Bi-weekly', biweekly_fri),
]

print(f"\n{'Universe':<10} {'Cadence':<10} {'CAGR':>7} {'Max DD':>8} {'LongDD':>7} "
      f"{'Sharpe':>7} {'Sortino':>8} {'Calmar':>7} {'AvgCash':>8} {'Trades':>7}")
print('-' * 95)

results = []
for u_name, u_path in universes:
    for c_name, sig_dates in cadences:
        m = run(universe_path=u_path, cadence_label=c_name,
                entry_signal_dates=sig_dates,
                label=f'{u_name} {c_name}')
        if m is None:
            print(f"{u_name:<10} {c_name:<10}  (no result)")
            continue
        results.append((u_name, c_name, m))
        print(f"{u_name:<10} {c_name:<10} "
              f"{m['cagr']*100:>+6.1f}% {m['max_dd']*100:>+7.1f}% "
              f"{m['longest_dd_days']:>6}d "
              f"{m['sharpe']:>7.2f} {m['sortino']:>8.2f} "
              f"{m['calmar']:>7.2f} {m['avg_cash']*100:>7.1f}% "
              f"{m['trades']:>7}")
    print()

print("\n=== Yearly returns (clean engine, daily peak) ===")
for u_name, c_name, m in results:
    yr = m['yearly']
    yr_str = '  '.join(f"{d.year}: {v*100:+5.1f}%" for d, v in yr.items())
    print(f"{u_name} {c_name:<10}  {yr_str}")
