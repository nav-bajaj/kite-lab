"""S2 backtest engine - clean-engine discipline plus two controls it lacks.

Mirrors scripts/_clean_engine.run_strategy's no-lookahead contract exactly:
every decision reads the signal-date close, every fill happens on the next
trading day at OHLC/4 with slippage. Production code is untouched.

What it adds, because the first S2 run showed both are load-bearing:

  weight_mode   The production books cap weight at ENTRY and then let winners
                drift. On a stage-2 book that concentrated the entire
                portfolio into one promoter group (Adani, 2021-22) and one
                theme (PSU/power, 2023-24), which is where the -68% came
                from. 'trim' sells positions back to max_weight at each
                weekly check; 'equal' fully re-equalises; 'drift' reproduces
                production behaviour for comparison.

  sector_cap    At most N names per sector in the entry ranking. Symbols with
                no sector mapping are each treated as their own group, i.e.
                never capped - permissive, and reported.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _exec_price(trade_panel, close_row, last_prices, date, sym):
    p = trade_panel.loc[date, sym] if sym in trade_panel.columns else np.nan
    if pd.isna(p) or p <= 0:
        p = close_row.get(sym, last_prices.get(sym, np.nan))
    if pd.isna(p) or p <= 0:
        return None
    return float(p)


def run_s2_strategy(*, close_panel, trade_panel, calendar, benchmark_aligned,
                    signal_dates, score_fn,
                    top_n=22, exit_buffer=10, max_weight=0.075,
                    slippage=0.002, stop=0.0,
                    weight_mode="trim",          # drift | trim | equal
                    sector_map=None, sector_cap=0,
                    min_hold_days=0,
                    exit_confirm_weeks=1,  # consecutive failed checks before a sell
                    membership_fn=None,
                    entry_gate=None,   # optional Date x Symbol bool: entrants only
                    initial_capital=1_000_000,
                    end=None):
    if end is not None:
        end = pd.Timestamp(end)
        calendar = calendar[calendar <= end]
        signal_dates = signal_dates[signal_dates <= end]

    # --- pre-compute rankings at every signal date -------------------------
    rankings: dict[pd.Timestamp, list[str]] = {}
    for sd in signal_dates:
        if sd not in close_panel.index:
            continue
        sc = score_fn(sd)
        if sc is None or len(sc) == 0:
            continue
        sc = sc.dropna()
        if sc.empty:
            continue
        rankings[pd.Timestamp(sd)] = sc.sort_values(ascending=False).index.tolist()

    exec_to_signal: dict[pd.Timestamp, pd.Timestamp] = {}
    for sd in sorted(rankings):
        nxt = calendar[calendar > sd]
        if len(nxt):
            exec_to_signal[pd.Timestamp(nxt[0])] = pd.Timestamp(sd)
    if not exec_to_signal:
        return None

    active = calendar[calendar >= min(exec_to_signal)]

    holdings: dict[str, int] = {}
    cost_basis: dict[str, float] = {}
    entry_meta: dict[str, dict] = {}
    last_prices: dict[str, float] = {}
    strikes: dict[str, int] = {}
    cash = float(initial_capital)
    eq_rows, trade_rows, exit_rows = [], [], []

    def sector_of(sym):
        if sector_map is None:
            return sym
        return sector_map.get(sym, f"__unmapped__{sym}")

    def sell(sym, shares, date, close_row, reason):
        nonlocal cash
        px = _exec_price(trade_panel, close_row, last_prices, date, sym)
        if px is None:
            return False
        proceeds = shares * px * (1 - slippage)
        cash += proceeds
        held = holdings.get(sym, 0)
        avg_cost = (cost_basis.get(sym, 0.0) / held) if held else 0.0
        holdings[sym] = held - shares
        cost_basis[sym] = cost_basis.get(sym, 0.0) - shares * avg_cost
        trade_rows.append({"date": date, "symbol": sym, "side": "SELL",
                           "shares": shares, "price": px,
                           "notional": shares * px,
                           "slippage": shares * px * slippage,
                           "reason": reason})
        if holdings[sym] <= 0:
            meta = entry_meta.pop(sym, {"date": date})
            pnl = (px * (1 - slippage) / avg_cost - 1) if avg_cost > 0 else None
            exit_rows.append({"symbol": sym, "pnl_pct": pnl, "reason": reason,
                              "entry_date": meta.get("date"), "exit_date": date,
                              "hold_days": ((date - meta["date"]).days
                                            if meta.get("date") else None),
                              "sector": sector_of(sym)})
            holdings.pop(sym, None)
            cost_basis.pop(sym, None)
        return True

    def buy(sym, budget, date, close_row, reason):
        nonlocal cash
        if budget <= 0:
            return 0.0
        px = _exec_price(trade_panel, close_row, last_prices, date, sym)
        if px is None:
            return 0.0
        sh = math.floor(budget / (px * (1 + slippage)))
        if sh < 1:
            return 0.0
        cost = sh * px * (1 + slippage)
        if cost > cash:
            return 0.0
        holdings[sym] = holdings.get(sym, 0) + sh
        cost_basis[sym] = cost_basis.get(sym, 0.0) + cost
        cash -= cost
        if sym not in entry_meta:
            entry_meta[sym] = {"date": date, "peak": px}
        trade_rows.append({"date": date, "symbol": sym, "side": "BUY",
                           "shares": sh, "price": px, "notional": sh * px,
                           "slippage": sh * px * slippage, "reason": reason})
        return cost

    for date in active:
        cr = close_panel.loc[date]
        for sym in holdings:
            p = cr.get(sym, np.nan)
            if not pd.isna(p):
                last_prices[sym] = float(p)
                if sym in entry_meta:
                    entry_meta[sym]["peak"] = max(
                        entry_meta[sym].get("peak", p), float(p))

        def mark():
            v = cash
            for s, sh in holdings.items():
                p = cr.get(s, last_prices.get(s, 0.0))
                if pd.isna(p):
                    p = last_prices.get(s, 0.0)
                v += sh * float(p)
            return v

        pv = mark()
        eq_rows.append({"date": date, "pv": pv, "cash": cash,
                        "cash_pct": cash / pv if pv > 0 else 1.0,
                        "holdings": len(holdings),
                        "benchmark": benchmark_aligned.get(date, np.nan)})

        if date not in exec_to_signal:
            continue
        sd = exec_to_signal[date]
        signal_close = close_panel.loc[sd]

        # --- 1. per-position trailing stop (signal-date decision) -----------
        if stop > 0:
            for sym in list(holdings.keys()):
                sc_px = signal_close.get(sym, np.nan)
                if pd.isna(sc_px):
                    continue
                pk = entry_meta.get(sym, {}).get("peak", sc_px)
                if pk > 0 and (sc_px / pk - 1.0) < -stop:
                    sell(sym, holdings[sym], date, cr, "stop")

        # --- 2. rank / gate exit -------------------------------------------
        ranked_raw = rankings.get(sd, [])
        if membership_fn is not None:
            mem = membership_fn(sd)
            ranked_raw = [s for s in ranked_raw if s in mem or s in holdings]
        keep = set(ranked_raw[:top_n + exit_buffer])
        for sym in list(holdings.keys()):
            if sym in keep:
                strikes.pop(sym, None)
                continue
            if min_hold_days > 0:
                ed = entry_meta.get(sym, {}).get("date")
                if ed is not None and (date - ed).days < min_hold_days:
                    continue
            # Exit confirmation, mirroring the entry stage-age rule: a single
            # failed check is noise, so require the name to stay out of the
            # keep set for N consecutive weekly checks before selling.
            strikes[sym] = strikes.get(sym, 0) + 1
            if strikes[sym] < exit_confirm_weeks:
                continue
            strikes.pop(sym, None)
            sell(sym, holdings[sym], date, cr, "rank")

        # --- 3. entrants, sector-capped ------------------------------------
        def entry_ok(sym):
            if entry_gate is None:
                return True
            try:
                return bool(entry_gate.loc[sd, sym])
            except Exception:
                return False

        # holdings already occupy their sector slots
        if sector_cap and sector_map is not None:
            used: dict[str, int] = {}
            for s in holdings:
                g = sector_of(s)
                used[g] = used.get(g, 0) + 1
            pool2, seen = [], dict(used)
            for s in ranked_raw:
                if s in holdings:
                    continue
                if membership_fn is not None and s not in membership_fn(sd):
                    continue
                if not entry_ok(s):
                    continue
                g = sector_of(s)
                if seen.get(g, 0) >= sector_cap:
                    continue
                seen[g] = seen.get(g, 0) + 1
                pool2.append(s)
            entry_pool = pool2
        else:
            entry_pool = [s for s in ranked_raw[:top_n]
                          if s not in holdings and entry_ok(s)]

        entrants = entry_pool[:max(0, top_n - len(holdings))]

        # --- 4. weight discipline ------------------------------------------
        pv2 = mark()
        n_final = len(holdings) + len(entrants)
        target_w = min(1.0 / n_final, max_weight) if n_final else 0.0
        tgt_value = pv2 * target_w

        if weight_mode in ("trim", "equal") and tgt_value > 0:
            cap_value = pv2 * max_weight if weight_mode == "trim" else tgt_value
            for sym in list(holdings.keys()):
                p = cr.get(sym, last_prices.get(sym, np.nan))
                if pd.isna(p) or p <= 0:
                    continue
                val = holdings[sym] * float(p)
                if val <= cap_value * 1.02:
                    continue
                shares_to_sell = int((val - cap_value) / float(p))
                if shares_to_sell >= 1:
                    sell(sym, min(shares_to_sell, holdings[sym]), date, cr,
                         "trim")

        # --- 5. buy entrants ------------------------------------------------
        if entrants:
            spent = {}
            fair = (cash * 0.99) / len(entrants)
            budget = min(tgt_value, fair)
            for sym in entrants:
                spent[sym] = buy(sym, budget, date, cr, "entry")
            leftover_min = tgt_value * 0.10
            if cash > leftover_min:
                for sym in entrants:
                    room = tgt_value - spent.get(sym, 0.0)
                    if room < leftover_min:
                        continue
                    spent[sym] = spent.get(sym, 0.0) + buy(
                        sym, min(room, cash * 0.99), date, cr, "entry")

        # --- 6. top existing holdings up toward target (equal mode only) ----
        if weight_mode == "equal" and tgt_value > 0 and cash > tgt_value * 0.10:
            for sym in list(holdings.keys()):
                p = cr.get(sym, last_prices.get(sym, np.nan))
                if pd.isna(p) or p <= 0:
                    continue
                room = tgt_value - holdings[sym] * float(p)
                if room < tgt_value * 0.10 or cash < tgt_value * 0.10:
                    continue
                buy(sym, min(room, cash * 0.99), date, cr, "rebal_topup")

    return {"equity": pd.DataFrame(eq_rows),
            "trades": pd.DataFrame(trade_rows),
            "exits": pd.DataFrame(exit_rows)}
