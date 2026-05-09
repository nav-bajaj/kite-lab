"""OM25 — ATR multiplier × floor grid (and no-stop baseline).

All other parameters at production locked-in:
- Composite 50/50 upside + capture ratio
- 252d return window, min 220 valid obs, positive 252d return required
- Top-N=25, exit_buffer=15
- Equal weight 1/N, max 7.5% cap, drift after entry
- 20 bps slippage
- Daily-peak trailing stop (engine fixed May 2026)

Variants tested (per universe × cadence):
- No trailing stop (200 DMA hard exit only)
- ATR mult ∈ {3, 4, 5, 6, 8} with floor=0
- ATR mult ∈ {4, 5, 6} with floor ∈ {5%, 10%}

Run on NSE 500, Nifty 250, Nifty 100, both Monthly and Bi-weekly.
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


def run(*, universe_path, entry_signal_dates, atr_mult, atr_floor,
        use_trailing_stop, label):
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
        atr_mult=atr_mult, atr_min_floor=atr_floor,
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=use_trailing_stop,
    )
    if res is None:
        return None
    return compute_metrics(res, label)


# Configs: (label, atr_mult, atr_floor, use_trailing_stop)
configs = [
    ('No stop',     0.0, 0.0, False),
    ('3x / 0',      3.0, 0.0, True),
    ('4x / 0',      4.0, 0.0, True),
    ('5x / 0',      5.0, 0.0, True),
    ('6x / 0',      6.0, 0.0, True),
    ('8x / 0',      8.0, 0.0, True),
    ('4x / 5%',     4.0, 0.05, True),
    ('4x / 10%',    4.0, 0.10, True),
    ('5x / 5%',     5.0, 0.05, True),
    ('5x / 10%',    5.0, 0.10, True),
    ('6x / 5%',     6.0, 0.05, True),
    ('6x / 10%',    6.0, 0.10, True),
]

universes = [
    ('NSE 500',   'data/static/nse500_universe.csv'),
    ('Nifty 250', 'data/static/nifty250_universe.csv'),
    ('Nifty 100', 'data/static/nifty100_universe.csv'),
]
cadences = [
    ('Monthly',   monthly_first),
    ('Bi-weekly', biweekly_fri),
]


for u_name, u_path in universes:
    for c_name, sig_dates in cadences:
        print(f"\n=== {u_name} — {c_name} ===")
        print(f"{'Config':<12} {'CAGR':>7} {'Max DD':>8} {'LongDD':>7} "
              f"{'Sharpe':>7} {'Sortino':>8} {'Calmar':>7} "
              f"{'AvgCash':>8} {'Trades':>7}")
        print('-' * 80)
        rows = []
        for cfg_label, atr_mult, atr_floor, use_ts in configs:
            m = run(universe_path=u_path, entry_signal_dates=sig_dates,
                    atr_mult=atr_mult, atr_floor=atr_floor,
                    use_trailing_stop=use_ts,
                    label=f'{u_name} {c_name} {cfg_label}')
            if m is None:
                continue
            rows.append((cfg_label, m))
            print(f"{cfg_label:<12} "
                  f"{m['cagr']*100:>+6.1f}% {m['max_dd']*100:>+7.1f}% "
                  f"{m['longest_dd_days']:>6}d "
                  f"{m['sharpe']:>7.2f} {m['sortino']:>8.2f} "
                  f"{m['calmar']:>7.2f} {m['avg_cash']*100:>7.1f}% "
                  f"{m['trades']:>7}")

        # Best by Sharpe (excluding no-stop which we'll call out separately)
        if rows:
            ranked = sorted(rows, key=lambda r: -r[1]['sharpe'])
            print(f"  Best Sharpe: {ranked[0][0]} ({ranked[0][1]['sharpe']:.2f})")
            ranked_cagr = sorted(rows, key=lambda r: -r[1]['cagr'])
            print(f"  Best CAGR:   {ranked_cagr[0][0]} ({ranked_cagr[0][1]['cagr']*100:+.1f}%)")
            ranked_dd = sorted(rows, key=lambda r: r[1]['max_dd'])
            # max_dd is negative; "best" means closest to 0 (largest value)
            ranked_dd = sorted(rows, key=lambda r: -r[1]['max_dd'])
            print(f"  Best DD:     {ranked_dd[0][0]} ({ranked_dd[0][1]['max_dd']*100:+.1f}%)")
