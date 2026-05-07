"""TL25 — pyramid into winners test.

All other parameters locked-in (5x ATR no floor, concave squared dd 126d,
persistence 252d/100, momentum 63d, no MA structure, bi-weekly entry weekly
exit, top-25 buffer-20, equal 1/3 weights).

Pyramid mechanic:
  On weekly Friday signal date (after exit check), for each holding:
    - If signal-date close / avg_cost - 1 >= threshold AND not yet pyramided
      max times → schedule pyramid add at next day OHLC/4.
    - Add size = pyramid_size_mult × base_target_weight (where
      base_target_weight = 1/top_n)
    - Total position weight capped at pyramid_cap (raised from max_weight).
    - Funded from available cash; if insufficient cash, skip.
"""
import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[3]))
import math
from pathlib import Path
import numpy as np
import pandas as pd

from scripts._clean_engine import (
    compute_metrics, fridays, biweekly_fridays,
    map_signal_to_trade,
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
sma_200_full = close_panel.rolling(200, min_periods=200).mean()
atr_20_panel = close_panel.pct_change().rolling(20).std()


def score_fn(signal_date,
             close_panel_universe=None, sma_50=None,
             sma_100=None, sma_200=None):
    if signal_date not in close_panel_universe.index:
        return pd.Series()
    if signal_date not in sma_200.index:
        return pd.Series()

    close_t = close_panel_universe.loc[signal_date]
    s50_t = sma_50.loc[signal_date]
    s200_t = sma_200.loc[signal_date]
    s200_20ago_panel = sma_200.shift(20)
    s200_20 = (s200_20ago_panel.loc[signal_date]
               if signal_date in s200_20ago_panel.index else None)

    eligible = (close_t > s200_t) & (s50_t > s200_t)
    if s200_20 is not None:
        eligible = eligible & (s200_t > s200_20)
    eligible = eligible.fillna(False)
    if eligible.sum() == 0:
        return pd.Series()

    above_100 = (close_panel_universe > sma_100).astype(float)
    persist_panel = above_100.rolling(252, min_periods=252).mean()
    persistence = persist_panel.loc[signal_date]

    rolling_high = close_panel_universe.rolling(126, min_periods=126).max()
    dd_raw = (close_panel_universe / rolling_high).clip(0, 1) ** 2
    dd_score = dd_raw.loc[signal_date]

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


def run_with_pyramid(*,
                     close_panel,
                     trade_panel,
                     calendar,
                     benchmark_aligned,
                     entry_signal_dates,
                     weekly_signal_dates,
                     score_args,
                     sma_200_panel,
                     atr_20_panel,
                     top_n=25,
                     exit_buffer=20,
                     atr_mult=5.0,
                     atr_min_floor=0.0,
                     max_weight=0.075,
                     slippage=0.002,
                     initial_capital=1_000_000,
                     pyramid_threshold=None,    # None disables pyramiding
                     pyramid_size_mult=0.5,     # add 0.5x base target
                     pyramid_cap=0.10,          # raised cap for pyramided
                     max_pyramids=1,
                     ):
    signals = {}
    for date in entry_signal_dates:
        if date not in close_panel.index:
            continue
        scores = score_fn(date, **score_args)
        if scores is None or scores.empty:
            continue
        ranked = scores.dropna().nlargest(top_n + exit_buffer)
        if len(ranked) == 0:
            continue
        signals[date] = ranked.index.tolist()

    entry_schedule = {}
    for sd in sorted(signals.keys()):
        td = map_signal_to_trade(sd, calendar)
        if td is not None:
            entry_schedule[pd.Timestamp(td)] = pd.Timestamp(sd)
    rebal_set = set(entry_schedule.keys())

    weekly_exec_to_signal = {}
    for sd in weekly_signal_dates:
        td = map_signal_to_trade(sd, calendar)
        if td is not None:
            weekly_exec_to_signal[pd.Timestamp(td)] = pd.Timestamp(sd)

    if not rebal_set:
        return None

    active_cal = calendar[calendar >= min(rebal_set)]

    holdings = {}
    cost_basis = {}
    entry_meta = {}      # sym -> {'date', 'peak', 'pyramids'}
    cash = initial_capital
    last_prices = {}
    eq_records = []
    trade_records = []
    exit_records = []

    base_target_w = 1.0 / top_n  # base per-position weight
    pyramid_add_w = base_target_w * pyramid_size_mult

    # Pyramid intent: schedule adds for next exec day
    pyramid_intent = {}  # exec_date -> list of (sym, signal_date)

    for date in active_cal:
        cr = close_panel.loc[date]
        for sym in holdings:
            p = cr.get(sym, np.nan)
            if not pd.isna(p):
                last_prices[sym] = p

        pv = cash
        for sym, sh in holdings.items():
            price = cr.get(sym, last_prices.get(sym, 0))
            if pd.isna(price):
                price = last_prices.get(sym, 0)
            pv += sh * price

        eq_records.append({
            'date': date, 'pv': pv, 'cash': cash,
            'cash_pct': cash / pv if pv > 0 else 1,
            'holdings': len(holdings),
            'benchmark': benchmark_aligned.get(date, np.nan),
        })

        # Weekly exit check (signal date close + indicators)
        if date in weekly_exec_to_signal:
            signal_date = weekly_exec_to_signal[date]
            if signal_date in close_panel.index:
                signal_close_row = close_panel.loc[signal_date]

                # Update peaks from signal close
                for sym in list(holdings.keys()):
                    sc = signal_close_row.get(sym, np.nan)
                    if not pd.isna(sc) and sym in entry_meta:
                        entry_meta[sym]['peak'] = max(
                            entry_meta[sym].get('peak', sc), sc
                        )

                # Exits
                exits_now = []
                for sym in list(holdings.keys()):
                    sc = signal_close_row.get(sym, np.nan)
                    s200 = (sma_200_panel.loc[signal_date, sym]
                            if sym in sma_200_panel.columns else np.nan)
                    if pd.isna(sc) or pd.isna(s200):
                        continue
                    pk = entry_meta.get(sym, {}).get('peak', sc)
                    op = sc / pk - 1 if pk > 0 else 0
                    atr = (atr_20_panel.loc[signal_date, sym]
                           if sym in atr_20_panel.columns else 0.02)
                    if pd.isna(atr):
                        atr = 0.02
                    trail = max(atr_mult * atr, atr_min_floor)
                    hit_dma = sc < s200
                    hit_atr = op < -trail
                    if hit_dma or hit_atr:
                        exits_now.append((sym, '200dma' if hit_dma else 'atr_stop'))

                for sym, reason in exits_now:
                    sh = holdings.pop(sym, 0)
                    if sh == 0:
                        continue
                    exec_price = (trade_panel.loc[date, sym]
                                  if sym in trade_panel.columns else np.nan)
                    if pd.isna(exec_price) or exec_price <= 0:
                        holdings[sym] = sh
                        continue
                    cash += sh * exec_price * (1 - slippage)
                    avg_cost = cost_basis.get(sym, 0) / sh if sh else 0
                    meta = entry_meta.pop(sym, {'date': date})
                    pnl_pct = ((exec_price / avg_cost - 1)
                               if avg_cost > 0 else None)
                    exit_records.append({
                        'symbol': sym, 'pnl_pct': pnl_pct, 'reason': reason,
                        'entry_date': meta.get('date'), 'exit_date': date,
                    })
                    cost_basis.pop(sym, None)
                    trade_records.append({
                        'date': date, 'symbol': sym, 'side': 'SELL',
                        'shares': sh, 'price': exec_price,
                        'notional': sh * exec_price,
                        'slippage': sh * exec_price * slippage,
                        'reason': reason,
                    })

                # Pyramid trigger check (after exits)
                if pyramid_threshold is not None:
                    for sym in list(holdings.keys()):
                        meta = entry_meta.get(sym, {})
                        pyramids_so_far = meta.get('pyramids', 0)
                        if pyramids_so_far >= max_pyramids:
                            continue
                        sh = holdings[sym]
                        if sh == 0:
                            continue
                        avg_cost = cost_basis.get(sym, 0) / sh
                        sc = signal_close_row.get(sym, np.nan)
                        if pd.isna(sc) or avg_cost <= 0:
                            continue
                        gain = sc / avg_cost - 1
                        if gain >= pyramid_threshold:
                            # Schedule pyramid add for today (exec at trade_panel)
                            pyramid_intent.setdefault(date, []).append(sym)

        # Execute scheduled pyramid adds (today is exec day)
        if date in pyramid_intent:
            # Compute portfolio value at this point
            pv2 = cash
            for sym, sh in holdings.items():
                p = cr.get(sym, last_prices.get(sym, 0))
                if pd.isna(p):
                    p = last_prices.get(sym, 0)
                pv2 += sh * p

            for sym in pyramid_intent[date]:
                if sym not in holdings:
                    continue  # may have exited same day
                exec_price = (trade_panel.loc[date, sym]
                              if sym in trade_panel.columns else np.nan)
                if pd.isna(exec_price) or exec_price <= 0:
                    continue
                # Current weight
                cur_value = holdings[sym] * exec_price
                cur_w = cur_value / pv2 if pv2 > 0 else 0
                # Target add weight: pyramid_add_w
                # But don't exceed pyramid_cap total weight
                add_w = min(pyramid_add_w, max(0, pyramid_cap - cur_w))
                if add_w <= 0:
                    continue
                add_alloc = pv2 * add_w
                add_alloc = min(add_alloc, cash * 0.99)
                if add_alloc <= 0:
                    continue
                add_sh = math.floor(add_alloc / (exec_price * (1 + slippage)))
                if add_sh < 1:
                    continue
                cost = add_sh * exec_price * (1 + slippage)
                if cost > cash:
                    continue
                holdings[sym] = holdings.get(sym, 0) + add_sh
                cost_basis[sym] = cost_basis.get(sym, 0) + cost
                cash -= cost
                meta = entry_meta.setdefault(sym, {})
                meta['pyramids'] = meta.get('pyramids', 0) + 1
                trade_records.append({
                    'date': date, 'symbol': sym, 'side': 'BUY',
                    'shares': add_sh, 'price': exec_price,
                    'notional': add_sh * exec_price,
                    'slippage': add_sh * exec_price * slippage,
                    'reason': 'pyramid',
                })

        # Entry rebalance
        if date in rebal_set:
            sd = entry_schedule[date]
            ranked = signals.get(sd, [])
            keep = set(ranked[:top_n + exit_buffer])

            # Sell rank-out
            for sym in list(holdings.keys()):
                if sym not in keep:
                    sh = holdings.pop(sym, 0)
                    if sh == 0:
                        continue
                    exec_price = (trade_panel.loc[date, sym]
                                  if sym in trade_panel.columns
                                  else cr.get(sym, np.nan))
                    if pd.isna(exec_price) or exec_price <= 0:
                        holdings[sym] = sh
                        continue
                    cash += sh * exec_price * (1 - slippage)
                    avg_cost = cost_basis.get(sym, 0) / sh if sh else 0
                    meta = entry_meta.pop(sym, {'date': date})
                    pnl_pct = ((exec_price / avg_cost - 1)
                               if avg_cost > 0 else None)
                    exit_records.append({
                        'symbol': sym, 'pnl_pct': pnl_pct, 'reason': 'rank',
                        'entry_date': meta.get('date'), 'exit_date': date,
                    })
                    cost_basis.pop(sym, None)
                    trade_records.append({
                        'date': date, 'symbol': sym, 'side': 'SELL',
                        'shares': sh, 'price': exec_price,
                        'notional': sh * exec_price,
                        'slippage': sh * exec_price * slippage,
                        'reason': 'rank',
                    })

            # Buy new entrants
            entrants = [s for s in ranked[:top_n] if s not in holdings]
            entrants = entrants[:max(0, top_n - len(holdings))]
            if entrants:
                pv2 = cash
                for sym, sh in holdings.items():
                    p = cr.get(sym, last_prices.get(sym, 0))
                    if pd.isna(p):
                        p = last_prices.get(sym, 0)
                    pv2 += sh * p
                n = len(holdings) + len(entrants)
                stock_w = min(1.0 / n if n > 0 else 0, max_weight)
                tgt = pv2 * stock_w
                for sym in entrants:
                    exec_price = (trade_panel.loc[date, sym]
                                  if sym in trade_panel.columns else np.nan)
                    if pd.isna(exec_price) or exec_price <= 0:
                        continue
                    alloc = min(tgt, cash * 0.99)
                    if alloc <= 0:
                        break
                    sh = math.floor(alloc / (exec_price * (1 + slippage)))
                    if sh < 1:
                        continue
                    cost = sh * exec_price * (1 + slippage)
                    if cost > cash:
                        continue
                    holdings[sym] = holdings.get(sym, 0) + sh
                    cost_basis[sym] = cost_basis.get(sym, 0) + cost
                    cash -= cost
                    entry_meta[sym] = {
                        'date': date, 'peak': cr.get(sym, exec_price),
                        'pyramids': 0,
                    }
                    trade_records.append({
                        'date': date, 'symbol': sym, 'side': 'BUY',
                        'shares': sh, 'price': exec_price,
                        'notional': sh * exec_price,
                        'slippage': sh * exec_price * slippage,
                        'reason': 'entry',
                    })

    eq_df = pd.DataFrame(eq_records)
    return {
        'equity': eq_df,
        'trades': pd.DataFrame(trade_records),
        'exits': pd.DataFrame(exit_records),
    }


weekly_fri = fridays(close_panel.index)
biweekly_fri = biweekly_fridays(close_panel.index)


def run(*, universe_path, label, **kwargs):
    universe = load_universe(Path(universe_path))
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    sma50_uni = sma_50_full[cols]
    sma100_uni = sma_100_full[cols]
    sma200_uni = sma_200_full[cols]
    min_date = close_uni.index[252]
    biweekly_filt = biweekly_fri[biweekly_fri >= min_date]
    weekly_filt = weekly_fri[weekly_fri >= min_date]
    score_args = {
        'close_panel_universe': close_uni,
        'sma_50': sma50_uni, 'sma_100': sma100_uni, 'sma_200': sma200_uni,
    }
    res = run_with_pyramid(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=biweekly_filt, weekly_signal_dates=weekly_filt,
        score_args=score_args,
        sma_200_panel=sma_200_full, atr_20_panel=atr_20_panel,
        top_n=25, exit_buffer=20,
        atr_mult=5.0, atr_min_floor=0.0,
        max_weight=0.075, slippage=0.002,
        **kwargs,
    )
    if res is None:
        return None
    return compute_metrics(res, label)


variants = [
    ('Baseline (no pyramid)',  dict(pyramid_threshold=None)),
    ('+15% / +50% / cap 10%',  dict(pyramid_threshold=0.15, pyramid_size_mult=0.5, pyramid_cap=0.10)),
    ('+25% / +50% / cap 10%',  dict(pyramid_threshold=0.25, pyramid_size_mult=0.5, pyramid_cap=0.10)),
    ('+40% / +50% / cap 10%',  dict(pyramid_threshold=0.40, pyramid_size_mult=0.5, pyramid_cap=0.10)),
    ('+25% / +100% / cap 12%', dict(pyramid_threshold=0.25, pyramid_size_mult=1.0, pyramid_cap=0.12)),
]

universes = [
    ('NSE 500',  'data/static/nse500_universe.csv'),
    ('Nifty 250','data/static/nifty250_universe.csv'),
    ('Nifty 100','data/static/nifty100_universe.csv'),
]

print(f"\n{'Universe':<12} {'Variant':<26} {'CAGR':>7} {'Max DD':>8} {'LongDD':>7} "
      f"{'Sharpe':>7} {'Sortino':>8} {'Calmar':>7}")
print('-' * 90)

for u_name, u_path in universes:
    for v_name, v_kwargs in variants:
        m = run(universe_path=u_path, label=f'{u_name} {v_name}', **v_kwargs)
        if m:
            print(f"{u_name:<12} {v_name:<26} "
                  f"{m['cagr']*100:>+6.1f}% {m['max_dd']*100:>+7.1f}% "
                  f"{m['longest_dd_days']:>6}d "
                  f"{m['sharpe']:>7.2f} {m['sortino']:>8.2f} "
                  f"{m['calmar']:>7.2f}")
    print()
