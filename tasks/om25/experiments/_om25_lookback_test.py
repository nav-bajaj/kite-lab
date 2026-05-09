"""OM25 — capture lookback window variants.

All other parameters at production locked-in:
- Composite 50/50 upside + capture ratio
- Eligibility: V2 no filter (data-quantity only — locked-in May 2026)
- Top-N=25, exit_buffer=15
- NO trailing stop (200 DMA hard exit only — locked-in May 2026)
- Equal weight 1/N, max 7.5%, drift after entry
- 20 bps slippage

Variants test the daily-returns lookback window used to compute
upside_capture and capture_ratio:
  63d  (3 months — very fast)
  126d (6 months)
  189d (9 months)
  252d (1 year — current)
  378d (1.5 years)
  504d (2 years — very slow)

For each variant:
  - min_obs = 0.87 * lookback (matches current 220/252)
  - min up/down days = max(15, lookback/10) (scales with window)

All variants share a common start date driven by the LONGEST lookback (504d)
so the test period is identical across configs.
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


def make_score_fn(lookback):
    """Score function with adjustable lookback."""
    min_obs = int(0.87 * lookback)
    min_ud = max(15, lookback // 10)

    def score(signal_date, returns_universe=None):
        if signal_date not in returns_universe.index:
            return pd.Series()
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback:
            return pd.Series()
        window = returns_universe.iloc[idx - lookback + 1:idx + 1]
        market_ret = window.mean(axis=1)
        results = {}
        for sym in window.columns:
            r = window[sym].dropna()
            if len(r) < min_obs:
                continue
            common = r.index.intersection(market_ret.index)
            sr = r.loc[common]
            mr = market_ret.loc[common]
            up = mr > 0
            dn = mr < 0
            if up.sum() < min_ud or dn.sum() < min_ud:
                continue
            uc = sr[up].mean() / mr[up].mean() if mr[up].mean() > 0 else 0
            dc = sr[dn].mean() / mr[dn].mean() if mr[dn].mean() < 0 else 1
            ratio = uc / dc if dc > 0 else uc
            results[sym] = {'up': uc, 'ratio': ratio}
        if not results:
            return pd.Series()
        df = pd.DataFrame(results).T
        up_pct = df['up'].rank(ascending=True, method='average') / len(df)
        cr_pct = df['ratio'].rank(ascending=True, method='average') / len(df)
        return 0.5 * up_pct + 0.5 * cr_pct
    return score


# Common min_date based on longest lookback so all variants are tested
# on the same period
LONGEST_LB = 504


def run(*, universe_path, entry_signal_dates, lookback, label):
    universe = load_universe(Path(universe_path))
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    returns_uni = close_uni.pct_change()

    min_date = close_uni.index[LONGEST_LB]  # same start for all variants
    entry_filt = entry_signal_dates[entry_signal_dates >= min_date]
    weekly_filt = weekly_fri[weekly_fri >= min_date]

    score_fn = make_score_fn(lookback)
    args = {'returns_universe': returns_uni}
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_filt, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args=args,
        sma_200_panel=sma_200_full, atr_20_panel=atr_20_panel,
        top_n=25, exit_buffer=15,
        atr_mult=0.0, atr_min_floor=0.0,
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=False,
    )
    if res is None:
        return None
    return compute_metrics(res, label)


variants = [63, 126, 189, 252, 378, 504]
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
        print(f"{'Lookback':<10} {'CAGR':>7} {'Max DD':>8} {'LongDD':>7} "
              f"{'Sharpe':>7} {'Sortino':>8} {'Calmar':>7} "
              f"{'AvgCash':>8} {'Trades':>7}")
        print('-' * 78)
        rows = []
        for lb in variants:
            m = run(universe_path=u_path, entry_signal_dates=sig_dates,
                    lookback=lb, label=f'{u_name} {c_name} {lb}d')
            if m is None:
                continue
            rows.append((lb, m))
            print(f"{lb}d{'':<5} "
                  f"{m['cagr']*100:>+6.1f}% {m['max_dd']*100:>+7.1f}% "
                  f"{m['longest_dd_days']:>6}d "
                  f"{m['sharpe']:>7.2f} {m['sortino']:>8.2f} "
                  f"{m['calmar']:>7.2f} {m['avg_cash']*100:>7.1f}% "
                  f"{m['trades']:>7}")
        if rows:
            ranked = sorted(rows, key=lambda r: -r[1]['sharpe'])
            print(f"  Best Sharpe: {ranked[0][0]}d ({ranked[0][1]['sharpe']:.2f})")
            ranked_cagr = sorted(rows, key=lambda r: -r[1]['cagr'])
            print(f"  Best CAGR:   {ranked_cagr[0][0]}d ({ranked_cagr[0][1]['cagr']*100:+.1f}%)")
            ranked_dd = sorted(rows, key=lambda r: -r[1]['max_dd'])
            print(f"  Best DD:     {ranked_dd[0][0]}d ({ranked_dd[0][1]['max_dd']*100:+.1f}%)")
