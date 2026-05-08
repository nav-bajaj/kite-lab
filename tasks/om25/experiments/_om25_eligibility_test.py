"""OM25 — eligibility filter variants.

All other parameters at production locked-in:
- Composite 50/50 upside + capture ratio
- 252d return window, min 220 valid obs
- Top-N=25, exit_buffer=15
- NO trailing stop (200 DMA hard exit only — locked-in May 2026)
- Equal weight 1/N, max 7.5%, drift after entry
- 20 bps slippage
- Daily-peak engine (irrelevant since no trailing stop)

Eligibility variants:
  V1 (current): 220+ obs + positive 252d total return
  V2 no filter: 220+ obs only
  V3 + above 200 DMA: V1 + Close > 200 DMA at signal_date
  V4 + 50 > 200:      V1 + 50 DMA > 200 DMA at signal_date
  V5 TL25 trend gate: V1 + Close > 200 + 50 > 200 + 200 rising 20d
  V6 pos 126d only:   220+ obs + positive 126d total return (no 252d filter)
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

sma_50_full = close_panel.rolling(50, min_periods=50).mean()
sma_200_full = close_panel.rolling(200, min_periods=200).mean()
atr_20_panel = close_panel.pct_change().rolling(20).std()

weekly_fri = fridays(calendar)
biweekly_fri = biweekly_fridays(calendar)
monthly_first = monthly_first_trading_day(calendar)


def make_score_fn(variant):
    """Return a score function implementing the given eligibility variant."""
    def score(signal_date, returns_universe=None, close_uni=None,
              sma_50=None, sma_200=None, min_obs=220):
        if signal_date not in returns_universe.index:
            return pd.Series()
        idx = returns_universe.index.get_loc(signal_date)
        if idx < 252:
            return pd.Series()
        # 252-day return window
        window = returns_universe.iloc[idx - 251:idx + 1]
        # 126-day return window for V6
        window_126 = returns_universe.iloc[idx - 125:idx + 1]

        market_ret = window.mean(axis=1)
        results = {}

        close_t = close_uni.loc[signal_date] if signal_date in close_uni.index else None
        s50_t = sma_50.loc[signal_date] if signal_date in sma_50.index else None
        s200_t = sma_200.loc[signal_date] if signal_date in sma_200.index else None
        s200_20ago_panel = sma_200.shift(20)
        s200_20 = (s200_20ago_panel.loc[signal_date]
                   if signal_date in s200_20ago_panel.index else None)

        for sym in window.columns:
            r = window[sym].dropna()
            if len(r) < min_obs:
                continue

            # Variant-specific return filter
            if variant == 'V6_pos126':
                r126 = window_126[sym].dropna()
                if len(r126) < int(126 * 220 / 252):
                    continue
                tr = (1 + r126).prod() - 1
                if tr <= 0:
                    continue
            elif variant == 'V2_no_filter':
                tr = (1 + r).prod() - 1
            else:
                tr = (1 + r).prod() - 1
                if tr <= 0:
                    continue

            # Variant-specific price/MA gates
            if variant in ('V3_above200', 'V4_50over200', 'V5_tl25_gate'):
                ct = close_t.get(sym, np.nan) if close_t is not None else np.nan
                s2 = s200_t.get(sym, np.nan) if s200_t is not None else np.nan
                if pd.isna(ct) or pd.isna(s2):
                    continue
                if variant == 'V3_above200':
                    if not (ct > s2):
                        continue
                if variant in ('V4_50over200', 'V5_tl25_gate'):
                    s5 = s50_t.get(sym, np.nan) if s50_t is not None else np.nan
                    if pd.isna(s5) or not (s5 > s2):
                        continue
                if variant == 'V5_tl25_gate':
                    if not (ct > s2):
                        continue
                    s2_20 = s200_20.get(sym, np.nan) if s200_20 is not None else np.nan
                    if pd.isna(s2_20) or not (s2 > s2_20):
                        continue

            # Capture computation (same as score_om25_composite)
            common = r.index.intersection(market_ret.index)
            sr = r.loc[common]
            mr = market_ret.loc[common]
            up = mr > 0
            dn = mr < 0
            if up.sum() < 50 or dn.sum() < 50:
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


def run(*, universe_path, entry_signal_dates, score_fn, label):
    universe = load_universe(Path(universe_path))
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    sma_50_uni = sma_50_full[cols]
    sma_200_uni = sma_200_full[cols]
    returns_uni = close_uni.pct_change()

    min_date = close_uni.index[252]
    entry_filt = entry_signal_dates[entry_signal_dates >= min_date]
    weekly_filt = weekly_fri[weekly_fri >= min_date]

    args = {
        'returns_universe': returns_uni,
        'close_uni': close_uni,
        'sma_50': sma_50_uni,
        'sma_200': sma_200_uni,
        'min_obs': 220,
    }
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_filt, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args=args,
        sma_200_panel=sma_200_full, atr_20_panel=atr_20_panel,
        top_n=25, exit_buffer=15,
        atr_mult=0.0, atr_min_floor=0.0,
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=False,  # locked-in: no trailing stop
    )
    if res is None:
        return None
    return compute_metrics(res, label)


variants = [
    ('V1 current',     'V1_current'),
    ('V2 no filter',   'V2_no_filter'),
    ('V3 +above 200',  'V3_above200'),
    ('V4 +50>200',     'V4_50over200'),
    ('V5 TL25 gate',   'V5_tl25_gate'),
    ('V6 pos 126d',    'V6_pos126'),
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
        print(f"{'Variant':<16} {'CAGR':>7} {'Max DD':>8} {'LongDD':>7} "
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
            print(f"{v_name:<16} "
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
