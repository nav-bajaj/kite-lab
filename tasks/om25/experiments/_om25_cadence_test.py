"""OM25 — entry cadence variants under locked-in stack.

All other parameters at production locked-in (May 2026 review):
- Composite 50/50 upside + capture ratio
- 252d lookback, 220+ obs, 50+ up/dn days
- Eligibility: V2 no filter (data-quantity only)
- Top-N=25, exit_buffer=15
- NO trailing stop (200 DMA hard exit only)
- Equal weight 1/N, max 7.5%, drift after entry
- 20 bps slippage
- Daily-peak engine (irrelevant since no trailing stop)

Variants: entry frequency only. Weekly exit check (Friday) stays the same
for all — only entry rebalance cadence varies.

  Weekly         every Friday
  Bi-weekly      every other Friday  (current Tier 2)
  Tri-weekly     every 3rd Friday
  Monthly        1st trading day of month  (current Tier 1)
  Mid-monthly    middle Friday of each month
  Bi-monthly     1st trading day of every other month
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


def triweekly_fridays(idx):
    return pd.DatetimeIndex(fridays(idx).values[::3])


def midmonth_fridays(idx):
    """Middle Friday of each month."""
    fris = fridays(idx)
    df = pd.DataFrame({'fri': fris, 'ym': fris.to_period('M')})
    # take the 2nd Friday of each month (typical "mid-month")
    out = []
    for _, group in df.groupby('ym'):
        if len(group) >= 2:
            out.append(group['fri'].iloc[1])
    return pd.DatetimeIndex(out).sort_values()


def bimonthly_first(idx):
    """1st trading day of every other month."""
    return pd.DatetimeIndex(monthly_first_trading_day(idx).values[::2])


tri_fri = triweekly_fridays(calendar)
midmonth = midmonth_fridays(calendar)
bi_monthly = bimonthly_first(calendar)


def run(*, universe_path, entry_signal_dates, label):
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
        atr_mult=0.0, atr_min_floor=0.0,
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=False,
    )
    if res is None:
        return None
    return compute_metrics(res, label)


cadences = [
    ('Weekly',      weekly_fri),
    ('Bi-weekly',   biweekly_fri),
    ('Monthly',     monthly_first),
    ('Bi-monthly',  bi_monthly),
]
universes = [
    ('NSE 500',   'data/static/nse500_universe.csv'),
    ('Nifty 250', 'data/static/nifty250_universe.csv'),
    ('Nifty 100', 'data/static/nifty100_universe.csv'),
]

for u_name, u_path in universes:
    print(f"\n=== {u_name} ===")
    print(f"{'Cadence':<14} {'CAGR':>7} {'Max DD':>8} {'LongDD':>7} "
          f"{'Sharpe':>7} {'Sortino':>8} {'Calmar':>7} "
          f"{'AvgCash':>8} {'Trades':>7}")
    print('-' * 84)
    rows = []
    for c_name, sig_dates in cadences:
        m = run(universe_path=u_path, entry_signal_dates=sig_dates,
                label=f'{u_name} {c_name}')
        if m is None:
            continue
        rows.append((c_name, m))
        print(f"{c_name:<14} "
              f"{m['cagr']*100:>+6.1f}% {m['max_dd']*100:>+7.1f}% "
              f"{m['longest_dd_days']:>6}d "
              f"{m['sharpe']:>7.2f} {m['sortino']:>8.2f} "
              f"{m['calmar']:>7.2f} {m['avg_cash']*100:>7.1f}% "
              f"{m['trades']:>7}")
    if rows:
        ranked = sorted(rows, key=lambda r: -r[1]['sharpe'])
        print(f"  Best Sharpe: {ranked[0][0]} ({ranked[0][1]['sharpe']:.2f})")
        ranked_cagr = sorted(rows, key=lambda r: -r[1]['cagr'])
        print(f"  Best CAGR:   {ranked_cagr[0][0]} ({ranked_cagr[0][1]['cagr']*100:+.1f}%)")
        ranked_dd = sorted(rows, key=lambda r: -r[1]['max_dd'])
        print(f"  Best DD:     {ranked_dd[0][0]} ({ranked_dd[0][1]['max_dd']*100:+.1f}%)")
