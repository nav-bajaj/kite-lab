"""Stage-2 (S2-v2) on the master store: the signal and engine from branch stage2_portfolio, unchanged in rule.

Ported pieces (git show stage2_portfolio:tasks/stage2_portfolio/lib/{stage2,s2_engine,run_s2}.py):
  build_stage2_panels  - the seven-condition gate, tiered hold gate, extension and RS inputs. Volume legs are
                         optional because the frozen S2-v2 score (RS + un-extension) does not use them.
  make_s2_score        - verbatim.
  run_s2_strategy      - verbatim, plus two reporting-only additions: the sell reason records whether the name
                         had also left the hold gate ('gate') or only the keep set ('rank'), and open positions at
                         the end are returned so the call ledger is complete.

Two interpretations, both stated in RESULTS.md:
  - RS percentile is ranked across point-in-time members (the rule as RESULTS.md states it); the branch code ranked
    across every alive column of its own survivorship-free panel.
  - The master store forward-fills delisted names flat (delist at LTP), so the gate's strict inequalities fail
    on a flat series and the name is sold at its last price.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from common import panels, universe, save_run, om, SLIPPAGE

S2V2 = dict(variant="E_rs_unext", top_n=20, exit_buffer=40, stop=0.0, weight_mode="drift", sector_cap=0,
            hold_mode="tiered", exit_confirm_weeks=3, max_weight=0.075, min_stage_age=0, slippage=SLIPPAGE)

VARIANTS = {
    "A_rs": dict(w_freshness=0.0, w_unextended=0.0, w_contraction=0.0, w_accumulation=0.0, w_rs=1.0),
    "D_blend": dict(w_freshness=0.125, w_unextended=0.125, w_contraction=0.125, w_accumulation=0.125, w_rs=0.5),
    "E_rs_unext": dict(w_freshness=0.0, w_unextended=0.5, w_contraction=0.0, w_accumulation=0.0, w_rs=0.5),
}


def _mp(window: int, frac: float = 0.8) -> int:
    return max(2, int(window * frac))


def _consecutive_true(mask: pd.DataFrame) -> pd.DataFrame:
    m = mask.astype(int)
    csum = m.cumsum()
    reset = csum.where(~mask.astype(bool)).ffill().fillna(0)
    return (csum - reset).where(mask.astype(bool), 0.0)


def build_stage2_panels(close: pd.DataFrame, member_mask: pd.DataFrame, volume: pd.DataFrame | None = None, *,
                        sma_fast=50, sma_mid=150, sma_slow=200, slope_lookback=20, range_window=252,
                        off_low_min=0.30, off_high_max=0.25, rs_window=126, rs_min_pct=0.70,
                        vol_contraction_short=21, vol_contraction_long=126, accumulation_window=50,
                        min_stage_age=21) -> dict:
    sma_f = close.rolling(sma_fast, min_periods=_mp(sma_fast)).mean()
    sma_m = close.rolling(sma_mid, min_periods=_mp(sma_mid)).mean()
    sma_s = close.rolling(sma_slow, min_periods=_mp(sma_slow)).mean()
    hi = close.rolling(range_window, min_periods=_mp(range_window)).max()
    lo = close.rolling(range_window, min_periods=_mp(range_window)).min()

    c1 = (close > sma_m) & (close > sma_s)
    c2 = sma_m > sma_s
    c3 = sma_s > sma_s.shift(slope_lookback)
    c4 = sma_f > sma_m
    c5 = close > sma_f
    c6 = close >= lo * (1.0 + off_low_min)
    c7 = close >= hi * (1.0 - off_high_max)
    core_gate = c1 & c2 & c3 & c4 & c5 & c6 & c7
    stage_age = _consecutive_true(core_gate.fillna(False))

    ret_rs = close / close.shift(rs_window) - 1.0
    rs_pct = ret_rs.where(member_mask).rank(axis=1, pct=True)     # percentile across point-in-time members

    gate = core_gate & (rs_pct >= rs_min_pct) & (stage_age >= min_stage_age)
    hold_gate = (close > sma_m) & (sma_m >= sma_s)
    hold_gate_tiered = c1 & c2 & c3 & c4

    rets = close.pct_change(fill_method=None)
    vol_s = rets.rolling(vol_contraction_short, min_periods=_mp(vol_contraction_short)).std()
    vol_l = rets.rolling(vol_contraction_long, min_periods=_mp(vol_contraction_long)).std()
    contraction = vol_s / vol_l
    if volume is not None:
        up_sum = volume.where(rets > 0, 0.0).rolling(accumulation_window, min_periods=_mp(accumulation_window)).sum()
        dn_sum = volume.where(rets < 0, 0.0).rolling(accumulation_window, min_periods=_mp(accumulation_window)).sum()
        accumulation = up_sum / dn_sum.replace(0.0, np.nan)
    else:
        accumulation = None
    extension = close / sma_f - 1.0
    return {"gate": gate.fillna(False), "hold_gate": hold_gate.fillna(False), "hold_gate_tiered": hold_gate_tiered.fillna(False),
            "core_gate": core_gate.fillna(False), "stage_age": stage_age, "rs_pct": rs_pct, "ret_rs": ret_rs,
            "contraction": contraction, "accumulation": accumulation, "extension": extension}


def _pct(series: pd.Series) -> pd.Series:
    s = series.dropna()
    if len(s) < 2:
        return pd.Series(0.5, index=series.index)
    r = s.rank(method="average", ascending=True)
    out = (r - 1) / (len(r) - 1)
    return out.reindex(series.index).fillna(0.5)


def make_s2_score(p: dict, *, w_freshness=0.25, w_unextended=0.25, w_contraction=0.25, w_accumulation=0.25, w_rs=0.0,
                  candidate_fn=None, asymmetric_gate=False, hold_mode="strict"):
    gate = p["gate"]
    if asymmetric_gate or hold_mode != "strict":
        hold_gate = p.get({"tiered": "hold_gate_tiered", "loose": "hold_gate"}.get(hold_mode, "hold_gate"))
    else:
        hold_gate = None
    weights = dict(freshness=w_freshness, unextended=w_unextended, contraction=w_contraction, accumulation=w_accumulation, rs=w_rs)
    wsum = sum(weights.values()); weights = {k: v / wsum for k, v in weights.items()}

    def score_fn(signal_date, **_):
        if signal_date not in gate.index:
            return pd.Series(dtype=float)
        elig = gate.loc[signal_date]
        if hold_gate is not None:
            elig = elig | hold_gate.loc[signal_date]
        if candidate_fn is not None:
            elig = elig & elig.index.isin(candidate_fn(signal_date))
        if not elig.any():
            return pd.Series(dtype=float)
        cols = elig[elig].index
        total = pd.Series(0.0, index=cols)
        if weights["freshness"]:
            total += weights["freshness"] * (1.0 - _pct(p["stage_age"].loc[signal_date, cols]))
        if weights["unextended"]:
            total += weights["unextended"] * (1.0 - _pct(p["extension"].loc[signal_date, cols]))
        if weights["contraction"]:
            total += weights["contraction"] * (1.0 - _pct(p["contraction"].loc[signal_date, cols]))
        if weights["accumulation"]:
            total += weights["accumulation"] * _pct(p["accumulation"].loc[signal_date, cols])
        if weights["rs"]:
            total += weights["rs"] * _pct(p["rs_pct"].loc[signal_date, cols])
        return total.reindex(gate.columns)
    return score_fn


def _exec_price(trade_panel, close_row, last_prices, date, sym):
    p = trade_panel.loc[date, sym] if sym in trade_panel.columns else np.nan
    if pd.isna(p) or p <= 0:
        p = close_row.get(sym, last_prices.get(sym, np.nan))
    if pd.isna(p) or p <= 0:
        return None
    return float(p)


def run_s2_strategy(*, close_panel, trade_panel, calendar, benchmark_aligned, signal_dates, score_fn,
                    top_n=22, exit_buffer=10, max_weight=0.075, slippage=0.002, stop=0.0, weight_mode="trim",
                    sector_map=None, sector_cap=0, min_hold_days=0, exit_confirm_weeks=1, membership_fn=None,
                    entry_gate=None, hold_gate=None, initial_capital=1_000_000, end=None):
    if end is not None:
        end = pd.Timestamp(end); calendar = calendar[calendar <= end]; signal_dates = signal_dates[signal_dates <= end]
    rankings = {}
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
    exec_to_signal = {}
    for sd in sorted(rankings):
        nxt = calendar[calendar > sd]
        if len(nxt):
            exec_to_signal[pd.Timestamp(nxt[0])] = pd.Timestamp(sd)
    if not exec_to_signal:
        return None
    active = calendar[calendar >= min(exec_to_signal)]
    holdings, cost_basis, entry_meta, last_prices, strikes = {}, {}, {}, {}, {}
    cash = float(initial_capital)
    eq_rows, trade_rows, exit_rows = [], [], []

    def sector_of(sym):
        return sym if sector_map is None else sector_map.get(sym, f"__unmapped__{sym}")

    def sell(sym, shares, date, close_row, reason):
        nonlocal cash
        px = _exec_price(trade_panel, close_row, last_prices, date, sym)
        if px is None:
            return False
        cash += shares * px * (1 - slippage)
        held = holdings.get(sym, 0)
        avg_cost = (cost_basis.get(sym, 0.0) / held) if held else 0.0
        holdings[sym] = held - shares
        cost_basis[sym] = cost_basis.get(sym, 0.0) - shares * avg_cost
        trade_rows.append({"date": date, "symbol": sym, "side": "SELL", "shares": shares, "price": px, "notional": shares * px,
                           "slippage": shares * px * slippage, "reason": reason})
        if holdings[sym] <= 0:
            meta = entry_meta.pop(sym, {"date": date})
            pnl = (px * (1 - slippage) / avg_cost - 1) if avg_cost > 0 else None
            exit_rows.append({"symbol": sym, "pnl_pct": pnl, "reason": reason, "entry_date": meta.get("date"), "exit_date": date,
                              "hold_days": ((date - meta["date"]).days if meta.get("date") else None), "sector": sector_of(sym)})
            holdings.pop(sym, None); cost_basis.pop(sym, None)
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
        trade_rows.append({"date": date, "symbol": sym, "side": "BUY", "shares": sh, "price": px, "notional": sh * px,
                           "slippage": sh * px * slippage, "reason": reason})
        return cost

    for date in active:
        cr = close_panel.loc[date]
        for sym in holdings:
            p = cr.get(sym, np.nan)
            if not pd.isna(p):
                last_prices[sym] = float(p)
                if sym in entry_meta:
                    entry_meta[sym]["peak"] = max(entry_meta[sym].get("peak", p), float(p))

        def mark():
            v = cash
            for s, sh in holdings.items():
                p = cr.get(s, last_prices.get(s, 0.0))
                if pd.isna(p):
                    p = last_prices.get(s, 0.0)
                v += sh * float(p)
            return v

        pv = mark()
        eq_rows.append({"date": date, "pv": pv, "cash": cash, "cash_pct": cash / pv if pv > 0 else 1.0, "holdings": len(holdings),
                        "benchmark": benchmark_aligned.get(date, np.nan)})
        if date not in exec_to_signal:
            continue
        sd = exec_to_signal[date]
        signal_close = close_panel.loc[sd]

        if stop > 0:
            for sym in list(holdings.keys()):
                sc_px = signal_close.get(sym, np.nan)
                if pd.isna(sc_px):
                    continue
                pk = entry_meta.get(sym, {}).get("peak", sc_px)
                if pk > 0 and (sc_px / pk - 1.0) < -stop:
                    sell(sym, holdings[sym], date, cr, "stop")

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
            strikes[sym] = strikes.get(sym, 0) + 1
            if strikes[sym] < exit_confirm_weeks:
                continue
            strikes.pop(sym, None)
            # reporting only: did the name also leave the hold gate on the signal date, or only the keep set
            in_hold = bool(hold_gate.loc[sd, sym]) if (hold_gate is not None and sym in hold_gate.columns) else True
            sell(sym, holdings[sym], date, cr, "rank" if in_hold else "gate")

        def entry_ok(sym):
            if entry_gate is None:
                return True
            try:
                return bool(entry_gate.loc[sd, sym])
            except Exception:
                return False

        if sector_cap and sector_map is not None:
            used = {}
            for s in holdings:
                g = sector_of(s); used[g] = used.get(g, 0) + 1
            pool2, seen = [], dict(used)
            for s in ranked_raw:
                if s in holdings or (membership_fn is not None and s not in membership_fn(sd)) or not entry_ok(s):
                    continue
                g = sector_of(s)
                if seen.get(g, 0) >= sector_cap:
                    continue
                seen[g] = seen.get(g, 0) + 1; pool2.append(s)
            entry_pool = pool2
        else:
            entry_pool = [s for s in ranked_raw[:top_n] if s not in holdings and entry_ok(s)]
        entrants = entry_pool[:max(0, top_n - len(holdings))]

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
                    sell(sym, min(shares_to_sell, holdings[sym]), date, cr, "trim")
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
                    spent[sym] = spent.get(sym, 0.0) + buy(sym, min(room, cash * 0.99), date, cr, "entry")
        if weight_mode == "equal" and tgt_value > 0 and cash > tgt_value * 0.10:
            for sym in list(holdings.keys()):
                p = cr.get(sym, last_prices.get(sym, np.nan))
                if pd.isna(p) or p <= 0:
                    continue
                room = tgt_value - holdings[sym] * float(p)
                if room < tgt_value * 0.10 or cash < tgt_value * 0.10:
                    continue
                buy(sym, min(room, cash * 0.99), date, cr, "rebal_topup")

    last = active[-1]; lc = close_panel.loc[last]
    open_rows = []
    for sym, sh in holdings.items():
        avg_cost = cost_basis.get(sym, 0.0) / sh if sh else 0.0
        p = lc.get(sym, last_prices.get(sym, np.nan))
        open_rows.append({"symbol": sym, "pnl_pct": (float(p) * (1 - slippage) / avg_cost - 1) if avg_cost > 0 and not pd.isna(p) else None,
                          "reason": "open", "entry_date": entry_meta.get(sym, {}).get("date"), "exit_date": last,
                          "hold_days": (last - entry_meta[sym]["date"]).days if sym in entry_meta else None, "sector": sector_of(sym)})
    return {"equity": pd.DataFrame(eq_rows), "trades": pd.DataFrame(trade_rows), "exits": pd.DataFrame(exit_rows), "open": pd.DataFrame(open_rows)}


_s2_cache: dict = {}


def s2_context(uni: str, close=None):
    """Gate/score panels for one universe; `close` lets the self-check pass a truncated panel."""
    key = (uni, None if close is None else str(close.index[-1]))
    if key not in _s2_cache:
        cols, mfn, cfn, mask = universe(uni)
        c = (panels()["close"] if close is None else close)[cols]
        _s2_cache[key] = (build_stage2_panels(c, mask.reindex(c.index), None, min_stage_age=S2V2["min_stage_age"]), mfn, cfn)
    return _s2_cache[key]


def run_s2(uni: str, start="2010-01-01", end=None, **overrides):
    cfg = {**S2V2, **overrides}
    P = panels(); close, trade = P["close"], P["trade"]
    sp, mfn, cfn = s2_context(uni)
    cols = sp["gate"].columns
    cal = close.index
    end_ts = pd.Timestamp(end) if end else cal[-1]
    weekly = om.fridays(cal); weekly = weekly[(weekly >= pd.Timestamp(start)) & (weekly <= end_ts)]
    score_fn = make_s2_score(sp, candidate_fn=cfn, hold_mode=cfg["hold_mode"], **VARIANTS[cfg["variant"]])
    hold = {"tiered": "hold_gate_tiered", "loose": "hold_gate"}.get(cfg["hold_mode"])
    res = run_s2_strategy(close_panel=close[cols], trade_panel=trade[cols], calendar=cal, benchmark_aligned=P["bench"],
                          signal_dates=weekly, score_fn=score_fn, top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
                          max_weight=cfg["max_weight"], slippage=cfg["slippage"], stop=cfg["stop"], weight_mode=cfg["weight_mode"],
                          sector_map=None, sector_cap=cfg["sector_cap"], exit_confirm_weeks=cfg["exit_confirm_weeks"],
                          membership_fn=mfn, entry_gate=sp["gate"] if cfg["hold_mode"] != "strict" else None,
                          hold_gate=sp[hold] if hold else None, initial_capital=1_000_000, end=end_ts)
    ex = pd.concat([res["exits"], res["open"]], ignore_index=True)
    calls = pd.DataFrame({"symbol": ex["symbol"], "entry_date": ex["entry_date"], "exit_date": ex["exit_date"], "pnl": ex["pnl_pct"],
                          "reason": ex["reason"], "status": np.where(ex["reason"] == "open", "open", "closed")})
    return cfg, res, calls
