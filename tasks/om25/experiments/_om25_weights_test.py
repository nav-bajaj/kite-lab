"""OM25 — composite signal weight variants.

All other parameters at production locked-in:
- 252d lookback window, min 220 valid obs (50 up/dn days)
- Eligibility: V2 no filter (data-quantity only)
- Top-N=25, exit_buffer=15
- NO trailing stop (200 DMA hard exit only)
- Equal weight 1/N, max 7.5%, drift after entry
- 20 bps slippage

The signal is a percentile-rank composite of stock-level metrics computed
over the 252-day return window:
  - upside_capture (UC)   = avg(stock ret | market up) / avg(market ret | up)
  - capture_ratio (CR)    = UC / downside_capture
  - total_return (TR)     = (1+r).prod() - 1 over the window
  - inv_downside (INVDC)  = 1 - pct_rank(downside_capture)  (lower DC = better)

Variants:
  V1 50/50              0.5*pctR(UC) + 0.5*pctR(CR)            CURRENT
  V2 70/30              0.7*pctR(UC) + 0.3*pctR(CR)
  V3 30/70              0.3*pctR(UC) + 0.7*pctR(CR)
  V4 UC only            1.0*pctR(UC)
  V5 CR only            1.0*pctR(CR)
  V6 3comp equal        1/3*pctR(UC) + 1/3*pctR(CR) + 1/3*pctR(TR)
  V7 3comp ratio-heavy  0.25*pctR(UC) + 0.50*pctR(CR) + 0.25*pctR(TR)
  V8 UC + invDC         0.5*pctR(UC) + 0.5*INVDC
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


def make_score_fn(variant):
    """Score function with the given composite-weight variant."""
    def score(signal_date, returns_universe=None, min_obs=220):
        if signal_date not in returns_universe.index:
            return pd.Series()
        idx = returns_universe.index.get_loc(signal_date)
        if idx < 252:
            return pd.Series()
        window = returns_universe.iloc[idx - 251:idx + 1]
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
            if up.sum() < 50 or dn.sum() < 50:
                continue
            uc = sr[up].mean() / mr[up].mean() if mr[up].mean() > 0 else 0
            dc_raw = sr[dn].mean() / mr[dn].mean() if mr[dn].mean() < 0 else 1
            ratio = uc / dc_raw if dc_raw > 0 else uc
            tr = (1 + r).prod() - 1
            results[sym] = {'uc': uc, 'cr': ratio, 'dc': dc_raw, 'tr': tr}

        if not results:
            return pd.Series()
        df = pd.DataFrame(results).T
        n = len(df)
        if n < 2:
            return pd.Series()
        uc_pct = df['uc'].rank(ascending=True, method='average') / n
        cr_pct = df['cr'].rank(ascending=True, method='average') / n
        dc_pct = df['dc'].rank(ascending=True, method='average') / n
        tr_pct = df['tr'].rank(ascending=True, method='average') / n
        invdc_pct = 1.0 - dc_pct  # lower downside-capture = better

        if variant == 'V1_50_50':
            score_s = 0.5 * uc_pct + 0.5 * cr_pct
        elif variant == 'V2_70_30':
            score_s = 0.7 * uc_pct + 0.3 * cr_pct
        elif variant == 'V3_30_70':
            score_s = 0.3 * uc_pct + 0.7 * cr_pct
        elif variant == 'V4_UC_only':
            score_s = uc_pct
        elif variant == 'V5_CR_only':
            score_s = cr_pct
        elif variant == 'V6_3comp_eq':
            score_s = (uc_pct + cr_pct + tr_pct) / 3.0
        elif variant == 'V7_3comp_rh':
            score_s = 0.25 * uc_pct + 0.50 * cr_pct + 0.25 * tr_pct
        elif variant == 'V8_UC_invDC':
            score_s = 0.5 * uc_pct + 0.5 * invdc_pct
        else:
            raise ValueError(f"unknown variant {variant}")
        return score_s
    return score


def run(*, universe_path, entry_signal_dates, score_fn, label):
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


variants = [
    ('V1 50/50',       'V1_50_50'),
    ('V2 70/30',       'V2_70_30'),
    ('V3 30/70',       'V3_30_70'),
    ('V4 UC only',     'V4_UC_only'),
    ('V5 CR only',     'V5_CR_only'),
    ('V6 3comp eq',    'V6_3comp_eq'),
    ('V7 3comp rh',    'V7_3comp_rh'),
    ('V8 UC+invDC',    'V8_UC_invDC'),
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
        print(f"{'Variant':<14} {'CAGR':>7} {'Max DD':>8} {'LongDD':>7} "
              f"{'Sharpe':>7} {'Sortino':>8} {'Calmar':>7} "
              f"{'AvgCash':>8} {'Trades':>7}")
        print('-' * 84)
        rows = []
        for v_name, v_key in variants:
            fn = make_score_fn(v_key)
            m = run(universe_path=u_path, entry_signal_dates=sig_dates,
                    score_fn=fn,
                    label=f'{u_name} {c_name} {v_name}')
            if m is None:
                continue
            rows.append((v_name, m))
            print(f"{v_name:<14} "
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
