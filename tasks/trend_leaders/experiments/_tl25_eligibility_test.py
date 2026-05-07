"""TL25 — test Eligibility filter variants.

Locked-in changes:
- 5x ATR no floor (exit)
- Concave (squared) drawdown, 126d window
- Persistence: 252-day window, 100 DMA reference
- Momentum: 63-day window, percentile-ranked
- MA Structure: DROPPED (1/3 persistence + 1/3 drawdown + 1/3 momentum)

Engine exit always uses 200 DMA (Close < 200 DMA on weekly Friday signal)
plus 5x ATR trailing stop. We're varying ENTRY eligibility only.

Eligibility variants:
1. current        - Close > 200 + 50 > 200 + 200 rising 20d
2. drop_slope     - Close > 200 + 50 > 200
3. drop_50_200    - Close > 200 + 200 rising
4. close_200_only - Close > 200
5. stricter_50    - Close > 200 + 50 > 200 + 200 rising + Close > 50
6. ref_150        - Close > 150 + 50 > 150 + 150 rising
7. ref_100        - Close > 100 + 50 > 100 + 100 rising
8. none           - No eligibility filter
"""
import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[3]))
from pathlib import Path
import numpy as np
import pandas as pd

from scripts._clean_engine import (
    run_strategy, compute_metrics, fridays, biweekly_fridays
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe


print("Loading shared data...")
close_panel, trade_panel = load_price_panels(Path('nse500_data'))
calendar = close_panel.index
benchmark = load_benchmark(Path('data/benchmarks/nifty100.csv'))
benchmark_aligned = benchmark.reindex(calendar).ffill()

sma_50_full = close_panel.rolling(50, min_periods=50).mean()
sma_100_full = close_panel.rolling(100, min_periods=100).mean()
sma_150_full = close_panel.rolling(150, min_periods=150).mean()
sma_200_full = close_panel.rolling(200, min_periods=200).mean()
atr_20_panel = close_panel.pct_change().rolling(20).std()


def make_score_fn(elig_variant='current'):
    def score(signal_date,
              close_panel_universe=None, sma_50=None, sma_100=None,
              sma_150=None, sma_200=None):
        if signal_date not in close_panel_universe.index:
            return pd.Series()
        if signal_date not in sma_200.index:
            return pd.Series()

        close_t = close_panel_universe.loc[signal_date]
        s50_t = sma_50.loc[signal_date]
        s100_t = sma_100.loc[signal_date]
        s150_t = sma_150.loc[signal_date]
        s200_t = sma_200.loc[signal_date]

        s200_20ago_panel = sma_200.shift(20)
        s200_20 = (s200_20ago_panel.loc[signal_date]
                   if signal_date in s200_20ago_panel.index else None)
        s150_20ago_panel = sma_150.shift(20)
        s150_20 = (s150_20ago_panel.loc[signal_date]
                   if signal_date in s150_20ago_panel.index else None)
        s100_20ago_panel = sma_100.shift(20)
        s100_20 = (s100_20ago_panel.loc[signal_date]
                   if signal_date in s100_20ago_panel.index else None)

        # Eligibility
        if elig_variant == 'current':
            eligible = (close_t > s200_t) & (s50_t > s200_t)
            if s200_20 is not None:
                eligible = eligible & (s200_t > s200_20)
        elif elig_variant == 'drop_slope':
            eligible = (close_t > s200_t) & (s50_t > s200_t)
        elif elig_variant == 'drop_50_200':
            eligible = (close_t > s200_t)
            if s200_20 is not None:
                eligible = eligible & (s200_t > s200_20)
        elif elig_variant == 'close_200_only':
            eligible = (close_t > s200_t)
        elif elig_variant == 'stricter_50':
            eligible = ((close_t > s200_t) & (s50_t > s200_t)
                        & (close_t > s50_t))
            if s200_20 is not None:
                eligible = eligible & (s200_t > s200_20)
        elif elig_variant == 'ref_150':
            eligible = (close_t > s150_t) & (s50_t > s150_t)
            if s150_20 is not None:
                eligible = eligible & (s150_t > s150_20)
        elif elig_variant == 'ref_100':
            eligible = (close_t > s100_t) & (s50_t > s100_t)
            if s100_20 is not None:
                eligible = eligible & (s100_t > s100_20)
        elif elig_variant == 'none':
            eligible = pd.Series(True, index=close_t.index)
        else:
            raise ValueError(elig_variant)

        eligible = eligible.fillna(False)
        if eligible.sum() == 0:
            return pd.Series()

        # Persistence: 252-day window, 100 DMA
        above_100 = (close_panel_universe > sma_100).astype(float)
        persist_panel = above_100.rolling(252, min_periods=252).mean()
        persistence = persist_panel.loc[signal_date]

        # Drawdown: concave (squared), 126d
        rolling_high = close_panel_universe.rolling(126, min_periods=126).max()
        dd_raw = (close_panel_universe / rolling_high).clip(0, 1) ** 2
        dd_score = dd_raw.loc[signal_date]

        # Momentum: 63d / pct rank
        mom_window = 63
        mom_raw_panel = (close_panel_universe
                         / close_panel_universe.shift(mom_window) - 1)
        mom_raw = mom_raw_panel.loc[signal_date]
        mom_eligible = mom_raw.where(eligible).dropna()
        mom_score = pd.Series(np.nan, index=close_t.index)
        if len(mom_eligible) > 1:
            ranked = mom_eligible.rank(method='average', ascending=True)
            pct = (ranked - 1) / (len(ranked) - 1)
            mom_score = pct.reindex(close_t.index).fillna(0)

        weighted = ((1/3) * persistence.fillna(0)
                    + (1/3) * dd_score.fillna(0)
                    + (1/3) * mom_score.fillna(0))
        weighted = weighted.where(eligible)
        return weighted
    return score


weekly_fri = fridays(close_panel.index)
biweekly_fri = biweekly_fridays(close_panel.index)


def run(*, universe_path, score_fn, label):
    universe = load_universe(Path(universe_path))
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    sma50_uni = sma_50_full[cols]
    sma100_uni = sma_100_full[cols]
    sma150_uni = sma_150_full[cols]
    sma200_uni = sma_200_full[cols]

    min_date = close_uni.index[252]
    biweekly_filt = biweekly_fri[biweekly_fri >= min_date]
    weekly_filt = weekly_fri[weekly_fri >= min_date]

    args = {
        'close_panel_universe': close_uni,
        'sma_50': sma50_uni, 'sma_100': sma100_uni,
        'sma_150': sma150_uni, 'sma_200': sma200_uni,
    }
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=biweekly_filt, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args=args,
        sma_200_panel=sma_200_full, atr_20_panel=atr_20_panel,
        top_n=25, exit_buffer=20,
        atr_mult=5.0, atr_min_floor=0.0,
        max_weight=0.075, slippage=0.002, use_trailing_stop=True
    )
    if res is None:
        return None
    return compute_metrics(res, label)


variants = [
    ('Current',                make_score_fn('current')),
    ('Drop slope',             make_score_fn('drop_slope')),
    ('Drop 50>200',            make_score_fn('drop_50_200')),
    ('Close > 200 only',       make_score_fn('close_200_only')),
    ('Stricter (+Close>50)',   make_score_fn('stricter_50')),
    ('Reference 150 DMA',      make_score_fn('ref_150')),
    ('Reference 100 DMA',      make_score_fn('ref_100')),
    ('None (no filter)',       make_score_fn('none')),
]

universes = [
    ('NSE 500',  'data/static/nse500_universe.csv'),
    ('Nifty 250','data/static/nifty250_universe.csv'),
    ('Nifty 100','data/static/nifty100_universe.csv'),
]

print(f"\n{'Universe':<12} {'Variant':<24} {'CAGR':>7} {'Max DD':>8} {'LongDD':>7} "
      f"{'Sharpe':>7} {'Sortino':>8} {'Calmar':>7}")
print('-' * 88)

for u_name, u_path in universes:
    for v_name, v_fn in variants:
        m = run(universe_path=u_path, score_fn=v_fn,
                label=f'{u_name} {v_name}')
        if m:
            print(f"{u_name:<12} {v_name:<24} "
                  f"{m['cagr']*100:>+6.1f}% {m['max_dd']*100:>+7.1f}% "
                  f"{m['longest_dd_days']:>6}d "
                  f"{m['sharpe']:>7.2f} {m['sortino']:>8.2f} "
                  f"{m['calmar']:>7.2f}")
    print()
