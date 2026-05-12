"""Clean (no-lookahead) backtest engine for OM25 / TL25 variants.

Strict signal/execution separation:
- All decisions (entry rank, exit triggers, peak tracking for trailing stop)
  use prior signal-date close and indicators.
- All executions happen on the next trading day at OHLC/4 with slippage.

This module provides:
- run_strategy(): generic engine
- compute_metrics(): clean metrics from equity / trades / exits
- score_*: signal scoring functions
- date helpers: derive_*_signal_dates()

Used by experiment scripts to test OM25 and TL25 variants without lookahead.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.backtest_momentum import (
    load_price_panels, load_benchmark, map_signal_to_trade
)
from scripts.build_om25_signals import load_close_panel, load_universe


# ============================================================
# Date helpers
# ============================================================

def fridays(index):
    cal = pd.Series(index=index, data=index)
    return pd.DatetimeIndex(cal.resample('W-FRI').last().dropna().values)


def biweekly_fridays(index):
    return pd.DatetimeIndex(fridays(index).values[::2])


def thursdays(index):
    cal = pd.Series(index=index, data=index)
    return pd.DatetimeIndex(cal.resample('W-THU').last().dropna().values)


def biweekly_thursdays(index):
    return pd.DatetimeIndex(thursdays(index).values[::2])


def monthly_first_trading_day(index):
    cal = pd.Series(index=index, data=index)
    return pd.DatetimeIndex(cal.resample('MS').first().dropna().values)


def monthly_last_trading_day(index):
    cal = pd.Series(index=index, data=index)
    return pd.DatetimeIndex(cal.resample('ME').last().dropna().values)


# ============================================================
# Scoring functions (return Series indexed by symbol)
# ============================================================

def score_om25_composite(signal_date, returns_universe=None, min_obs=220):
    """OM25 composite: 50% upside_capture pct rank + 50% capture_ratio pct rank.

    Uses 252-day window ending at signal_date (inclusive).
    """
    if signal_date not in returns_universe.index:
        return pd.Series()
    idx = returns_universe.index.get_loc(signal_date)
    if idx < 252:
        return pd.Series()
    window = returns_universe.iloc[idx - 251:idx + 1]
    return _score_om25_window(window, min_obs)


def _score_om25_window(window, min_obs=220):
    """OM25 composite scoring on a return window.

    Eligibility (locked-in May 2026, V2):
      - len(r) >= min_obs valid daily returns
      - >= 50 market-up days AND >= 50 market-down days
    No positive-return prefilter — composite score does the quality work.
    """
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
        dc = sr[dn].mean() / mr[dn].mean() if mr[dn].mean() < 0 else 1
        ratio = uc / dc if dc > 0 else uc
        results[sym] = {'up': uc, 'ratio': ratio}
    if not results:
        return pd.Series()
    df = pd.DataFrame(results).T
    up_pct = df['up'].rank(ascending=True, method='average') / len(df)
    cr_pct = df['ratio'].rank(ascending=True, method='average') / len(df)
    return 0.5 * up_pct + 0.5 * cr_pct


def score_tl25_composite(signal_date, close_panel_universe=None, sma_50=None,
                          sma_100=None, sma_200=None, mom_3m=None,
                          min_obs=220, weights=None):
    """TL25 composite: equal weight MA structure + persistence + drawdown + 3m momentum.

    All inputs should be panels (DataFrames) covering the full period;
    we extract the row at signal_date.
    """
    if weights is None:
        weights = (0.30, 0.30, 0.25, 0.15)
    w_ma, w_persist, w_dd, w_mom = weights

    # MA structure score: stacking + slope (binary subs * 0.25 each)
    if signal_date not in close_panel_universe.index:
        return pd.Series()
    if signal_date not in sma_200.index:
        return pd.Series()

    close_t = close_panel_universe.loc[signal_date]
    s50_t = sma_50.loc[signal_date]
    s100_t = sma_100.loc[signal_date]
    s200_t = sma_200.loc[signal_date]
    s200_20ago = (sma_200.shift(20).loc[signal_date]
                  if signal_date in sma_200.shift(20).index else None)

    # Eligibility
    eligible = (close_t > s200_t) & (s50_t > s200_t)
    if s200_20ago is not None:
        eligible = eligible & (s200_t > s200_20ago)

    if eligible.sum() == 0:
        return pd.Series()

    # MA structure
    ma = pd.Series(0.0, index=close_t.index)
    ma += (close_t > s50_t).astype(float) * 0.25
    ma += (s50_t > s100_t).astype(float) * 0.25
    ma += (s100_t > s200_t).astype(float) * 0.25
    if s200_20ago is not None:
        ma += (s200_t > s200_20ago).astype(float) * 0.25

    # Persistence: % of last 63 days where Close > 100 DMA
    above_100 = (close_panel_universe > sma_100).astype(float)
    persist_panel = above_100.rolling(63, min_periods=63).mean()
    persistence = persist_panel.loc[signal_date]

    # Drawdown control: close / 126-day rolling max
    rolling_high = close_panel_universe.rolling(126, min_periods=126).max()
    drawdown_ctrl = (close_panel_universe / rolling_high).clip(0, 1)
    dd_score = drawdown_ctrl.loc[signal_date]

    # 3m momentum (percentile-ranked among eligible)
    mom_t = mom_3m.loc[signal_date]

    # Compose
    weighted = (w_ma * ma.fillna(0)
                + w_persist * persistence.fillna(0)
                + w_dd * dd_score.fillna(0))

    # Add momentum if weight > 0
    if w_mom > 0:
        mom_eligible = mom_t.where(eligible).dropna()
        if len(mom_eligible) > 1:
            mom_ranked = mom_eligible.rank(method='average', ascending=True)
            mom_pct = (mom_ranked - 1) / (len(mom_ranked) - 1)
            weighted = weighted + w_mom * mom_pct.reindex(close_t.index).fillna(0)

    weighted = weighted.where(eligible)
    return weighted


# ============================================================
# Generic backtest engine
# ============================================================

def run_strategy(*,
                 close_panel,
                 trade_panel,
                 calendar,
                 benchmark_aligned,
                 entry_signal_dates,        # signal dates (e.g. Fridays)
                 weekly_signal_dates,        # signal dates for weekly exits
                 signal_function,            # callable(window or context, signal_date) -> Series
                 signal_function_args,       # dict of extra kwargs to pass
                 sma_200_panel,
                 atr_20_panel,
                 top_n=25,
                 exit_buffer=15,
                 atr_mult=4.0,
                 atr_min_floor=0.0,          # 0 = no floor
                 max_weight=0.075,
                 slippage=0.002,
                 initial_capital=1_000_000,
                 use_trailing_stop=True,    # ATR trailing stop on/off
                 use_dma_exit=True,          # weekly 200 DMA exit on/off (independent)
                 donchian_low_panel=None,    # optional Date×Symbol N-day low panel; exit if close < low
                 weekly_rank_check=False,    # if True, fire rank-exit at every weekly_signal_date
                 regime_panel=None,         # optional pd.Series[date]->bool, True=bull
                 bear_exposure=0.0,          # gross exposure cap during bear (0..1)
                 ):
    """Generic clean (no-lookahead) backtest.

    signal_function(signal_date, **signal_function_args) → pd.Series of scores
    keyed by symbol. Higher score = more attractive. NaN means ineligible.
    """
    # Pre-compute signals at entry dates (and weekly dates if weekly_rank_check).
    # Weekly rank check needs scores at every Friday so we can rank-out holdings
    # without waiting for the next biweekly rebalance.
    score_dates = set(entry_signal_dates)
    if weekly_rank_check:
        score_dates |= set(weekly_signal_dates)
    signals = {}
    for date in score_dates:
        if date not in close_panel.index:
            continue
        scores = signal_function(date, **signal_function_args)
        if scores is None or scores.empty:
            continue
        ranked = scores.dropna().nlargest(top_n + exit_buffer)
        if len(ranked) == 0:
            continue
        signals[date] = ranked.index.tolist()

    # Map signal dates → execution dates.
    # Entry schedule is built from entry_signal_dates ONLY (the biweekly set
    # the caller passed). When weekly_rank_check is True, `signals` also has
    # weekly Friday scores — but those are for the rank-exit-only block below,
    # not new entries. Mixing them in here would turn every Friday into a
    # rebalance day and the weekly-rank-exit block (guarded by
    # `date not in rebal_set`) would never fire.
    entry_set = set(pd.Timestamp(d) for d in entry_signal_dates)
    entry_schedule = {}
    for sd in sorted(signals.keys()):
        if sd not in entry_set:
            continue
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
    entry_meta = {}
    cash = initial_capital
    last_prices = {}
    eq_records = []
    trade_records = []
    exit_records = []

    for date in active_cal:
        cr = close_panel.loc[date]
        # Update last prices for held names
        for sym in holdings:
            p = cr.get(sym, np.nan)
            if not pd.isna(p):
                last_prices[sym] = p

        # Daily peak update: peak = max of (entry exec price, all closes from
        # entry to today inclusive). Uses today's close — backward-looking
        # since `date` is the current iteration day; no future info.
        for sym in holdings:
            p = cr.get(sym, np.nan)
            if not pd.isna(p) and sym in entry_meta:
                entry_meta[sym]['peak'] = max(
                    entry_meta[sym].get('peak', p), p
                )

        # Mark-to-market
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
            'benchmark': benchmark_aligned.get(date, np.nan)
        })

        # Regime filter: if bear regime, scale exposure down to bear_exposure
        # by selling pro-rata across holdings. Lookahead-safe: regime_panel is
        # expected to already be lagged by the caller (using prior day's
        # close-vs-200DMA decision).
        is_bear = False
        if regime_panel is not None:
            try:
                rv = regime_panel.get(date, True)
                is_bear = not bool(rv) if rv is not None else False
            except Exception:
                is_bear = False
            if is_bear and holdings:
                invested = pv - cash
                target_invested = pv * bear_exposure
                excess = invested - target_invested
                if excess > 0 and invested > 0:
                    scale = min(1.0, excess / invested)
                    for sym in list(holdings.keys()):
                        sh = holdings[sym]
                        shares_to_sell = int(sh * scale)
                        if shares_to_sell < 1:
                            if scale >= 0.999:
                                shares_to_sell = sh  # sell all if scaling to ~0
                            else:
                                continue
                        exec_price = (trade_panel.loc[date, sym]
                                      if sym in trade_panel.columns else np.nan)
                        if pd.isna(exec_price) or exec_price <= 0:
                            exec_price = cr.get(sym, last_prices.get(sym, np.nan))
                        if pd.isna(exec_price) or exec_price <= 0:
                            continue
                        cash += shares_to_sell * exec_price * (1 - slippage)
                        holdings[sym] -= shares_to_sell
                        if holdings[sym] <= 0:
                            meta = entry_meta.pop(sym, {'date': date})
                            avg_cost = (cost_basis.pop(sym, 0) / sh
                                        if sh else 0)
                            pnl_pct = ((exec_price / avg_cost - 1)
                                       if avg_cost > 0 else None)
                            exit_records.append({
                                'symbol': sym, 'pnl_pct': pnl_pct,
                                'reason': 'regime_bear',
                                'entry_date': meta.get('date'),
                                'exit_date': date,
                                'hold_days': ((date - meta['date']).days
                                              if meta.get('date') else None)
                            })
                            holdings.pop(sym, None)
                        trade_records.append({
                            'date': date, 'symbol': sym, 'side': 'SELL',
                            'shares': shares_to_sell, 'price': exec_price,
                            'notional': shares_to_sell * exec_price,
                            'slippage': shares_to_sell * exec_price * slippage,
                            'reason': 'regime_bear'
                        })

        # Weekly exit check: signal date close + indicators, execute today.
        # Peak already reflects all closes through signal_date (updated daily
        # above) so we don't redo the peak update here.
        # 200 DMA, ATR stop, and Donchian low are independent toggles.
        use_donchian = donchian_low_panel is not None
        if (use_trailing_stop or use_dma_exit or use_donchian) and date in weekly_exec_to_signal:
            signal_date = weekly_exec_to_signal[date]
            if signal_date in close_panel.index:
                signal_close_row = close_panel.loc[signal_date]
                # Now check exits using signal date data
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

                    hit_dma = use_dma_exit and (sc < s200)
                    hit_atr = use_trailing_stop and (op < -trail)
                    hit_donchian = False
                    if use_donchian and sym in donchian_low_panel.columns:
                        don_low = donchian_low_panel.loc[signal_date, sym] \
                                  if signal_date in donchian_low_panel.index else None
                        if don_low is not None and not pd.isna(don_low):
                            hit_donchian = sc < don_low

                    if hit_dma or hit_atr or hit_donchian:
                        if hit_donchian:
                            reason = 'donchian'
                        elif hit_dma:
                            reason = '200dma'
                        else:
                            reason = 'atr_stop'
                        exits_now.append((sym, reason))

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
                        'symbol': sym, 'pnl_pct': pnl_pct,
                        'reason': reason,
                        'entry_date': meta.get('date'),
                        'exit_date': date,
                        'hold_days': ((date - meta['date']).days
                                      if meta.get('date') else None)
                    })
                    cost_basis.pop(sym, None)
                    trade_records.append({
                        'date': date, 'symbol': sym, 'side': 'SELL',
                        'shares': sh, 'price': exec_price,
                        'notional': sh * exec_price,
                        'slippage': sh * exec_price * slippage,
                        'reason': reason
                    })

        # Weekly rank-exit check (NEW, optional): fires at every
        # weekly_signal_date so a stock that loses rank doesn't sit in the
        # portfolio for up to 2 weeks until the next biweekly rebalance.
        # Skipped on rebal_set dates (the entry block below handles it).
        # No new entries here — just exit-only.
        if (weekly_rank_check and date in weekly_exec_to_signal
                and date not in rebal_set):
            sd_w = weekly_exec_to_signal[date]
            ranked_w = signals.get(sd_w, [])
            if ranked_w:
                keep_w = set(ranked_w[:top_n + exit_buffer])
                for sym in list(holdings.keys()):
                    if sym not in keep_w:
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
                            'symbol': sym, 'pnl_pct': pnl_pct,
                            'reason': 'rank_weekly',
                            'entry_date': meta.get('date'),
                            'exit_date': date,
                            'hold_days': ((date - meta['date']).days
                                          if meta.get('date') else None)
                        })
                        cost_basis.pop(sym, None)
                        trade_records.append({
                            'date': date, 'symbol': sym, 'side': 'SELL',
                            'shares': sh, 'price': exec_price,
                            'notional': sh * exec_price,
                            'slippage': sh * exec_price * slippage,
                            'reason': 'rank_weekly'
                        })

        # Entry rebalance: signal date list, execute today.
        # Skip entries during bear regime (existing positions handled above);
        # exits via rank still run so we keep churn control during bear.
        if date in rebal_set:
            sd = entry_schedule[date]
            ranked = signals.get(sd, [])
            keep = set(ranked[:top_n + exit_buffer])

            # Sell out-of-rank holdings
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
                        'symbol': sym, 'pnl_pct': pnl_pct,
                        'reason': 'rank',
                        'entry_date': meta.get('date'),
                        'exit_date': date,
                        'hold_days': ((date - meta['date']).days
                                      if meta.get('date') else None)
                    })
                    cost_basis.pop(sym, None)
                    trade_records.append({
                        'date': date, 'symbol': sym, 'side': 'SELL',
                        'shares': sh, 'price': exec_price,
                        'notional': sh * exec_price,
                        'slippage': sh * exec_price * slippage,
                        'reason': 'rank'
                    })

            # Buy new entrants — skipped if bear regime (no fresh exposure)
            if is_bear:
                continue
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

                # Order-independent allocation: divide available cash
                # equally across entrants, capped at target weight. Earlier
                # version was greedy/sequential — when cash ran out, late
                # entrants got fractional or zero allocations purely due
                # to iteration order. Two-pass strategy: pass 1 buys the
                # fair per-entrant budget; pass 2 redistributes any cash
                # left over (from share-rounding or zero-price symbols) to
                # entrants that still have headroom to tgt.
                n_entrants = len(entrants)
                fair_share = (cash * 0.99) / n_entrants
                per_entrant_budget = min(tgt, fair_share)

                spent = {sym: 0.0 for sym in entrants}
                # Pass 1: each entrant gets its fair share
                for sym in entrants:
                    exec_price = (trade_panel.loc[date, sym]
                                  if sym in trade_panel.columns else np.nan)
                    if pd.isna(exec_price) or exec_price <= 0:
                        continue
                    if per_entrant_budget <= 0:
                        break
                    sh = math.floor(per_entrant_budget / (exec_price * (1 + slippage)))
                    if sh < 1:
                        continue
                    cost = sh * exec_price * (1 + slippage)
                    if cost > cash:
                        continue
                    holdings[sym] = holdings.get(sym, 0) + sh
                    cost_basis[sym] = cost_basis.get(sym, 0) + cost
                    entry_meta[sym] = {'date': date, 'peak': exec_price}
                    cash -= cost
                    spent[sym] += cost
                    trade_records.append({
                        'date': date, 'symbol': sym, 'side': 'BUY',
                        'shares': sh, 'price': exec_price,
                        'notional': sh * exec_price,
                        'slippage': sh * exec_price * slippage,
                        'reason': 'entry'
                    })

                # Pass 2: redistribute leftover cash to entrants that
                # haven't yet hit their target. Bound by remaining cash.
                # Skip dust-sized fills: only top up if room is meaningful
                # (>=10% of tgt) to avoid generating dozens of 1-share dust
                # trades from rounding leftovers.
                min_topup = tgt * 0.10
                if cash > min_topup:
                    for sym in entrants:
                        room_to_target = tgt - spent.get(sym, 0)
                        if room_to_target < min_topup:
                            continue
                        exec_price = (trade_panel.loc[date, sym]
                                      if sym in trade_panel.columns else np.nan)
                        if pd.isna(exec_price) or exec_price <= 0:
                            continue
                        alloc = min(room_to_target, cash * 0.99)
                        if alloc < min_topup:
                            continue
                        sh = math.floor(alloc / (exec_price * (1 + slippage)))
                        if sh < 1:
                            continue
                        cost = sh * exec_price * (1 + slippage)
                        if cost > cash:
                            continue
                        holdings[sym] = holdings.get(sym, 0) + sh
                        cost_basis[sym] = cost_basis.get(sym, 0) + cost
                        # Don't overwrite entry_meta if already set by pass 1
                        if sym not in entry_meta:
                            entry_meta[sym] = {'date': date, 'peak': exec_price}
                        cash -= cost
                        spent[sym] += cost
                        trade_records.append({
                            'date': date, 'symbol': sym, 'side': 'BUY',
                            'shares': sh, 'price': exec_price,
                            'notional': sh * exec_price,
                            'slippage': sh * exec_price * slippage,
                            'reason': 'entry'
                        })

    return {
        'equity': pd.DataFrame(eq_records),
        'trades': pd.DataFrame(trade_records),
        'exits': pd.DataFrame(exit_records)
    }


# ============================================================
# Metrics
# ============================================================

def compute_metrics(result, label='', initial_capital=1_000_000):
    eq = result['equity']
    trades = result['trades']
    exits = result['exits']
    pv = eq['pv']
    dates = eq['date']
    ret = pv.pct_change().dropna()
    bm_ret = eq['benchmark'].pct_change().dropna()

    total = pv.iloc[-1] / pv.iloc[0] - 1
    years = (dates.iloc[-1] - dates.iloc[0]).days / 365.25
    cagr = (1 + total) ** (1 / years) - 1
    vol = ret.std() * np.sqrt(252)
    sharpe = cagr / vol if vol > 0 else 0
    downside = ret[ret < 0].std() * np.sqrt(252)
    sortino = cagr / downside if downside > 0 else 0

    peak = pv.cummax()
    dd_series = pv / peak - 1
    max_dd = dd_series.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0

    common = ret.index.intersection(bm_ret.index)
    rp = ret.loc[common]
    rb = bm_ret.loc[common]
    beta = rp.cov(rb) / rb.var() if rb.var() > 0 else 0
    corr = rp.corr(rb)

    avg_cash = eq['cash_pct'].mean()
    avg_holdings = eq['holdings'].mean()

    # DD duration
    cur = 0
    longest = 0
    for v in dd_series.values:
        if v < 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0

    cost_drag = (trades['slippage'].sum() / initial_capital
                 if not trades.empty else 0)
    yearly = eq.set_index('date')['pv'].resample('YE').last().pct_change().dropna()

    if not exits.empty and 'pnl_pct' in exits.columns:
        hit_rate = (exits['pnl_pct'].dropna() > 0).mean()
    else:
        hit_rate = np.nan

    return {
        'label': label,
        'cagr': cagr, 'max_dd': max_dd, 'longest_dd_days': longest,
        'sharpe': sharpe, 'sortino': sortino, 'calmar': calmar,
        'vol': vol, 'beta': beta, 'corr': corr,
        'avg_cash': avg_cash, 'avg_holdings': avg_holdings,
        'trades': len(trades),
        'cost_drag': cost_drag, 'hit_rate': hit_rate,
        'final_pv': pv.iloc[-1],
        'yearly': yearly,
    }
