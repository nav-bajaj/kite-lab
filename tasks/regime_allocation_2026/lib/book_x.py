"""Instrumented book — `build_book` plus fills, and the two variants of
"where the rule acts" (PLAN §E) that cannot be expressed as a per-trade
weight.

`mode`:
  "entry"      — entry sizing only. Must reproduce `build_book` exactly.
  "force_exit" — entry sizing, and every open position is closed at the close
                 of any day the regime weight is zero.
  "rebal_down" — entry sizing, and open positions are scaled down (never up)
                 to the current regime weight, the shaved notional returning
                 to cash at that day's close.

The mark-to-market, sizing and slot logic is copied from
`tasks/breakout_calls_2026/lib/book.py` line for line so the "entry" mode is a
null change; §4 asserts that it is.

`fills` is the audit trail §5 needs: one row per closed leg with notional,
realised rupees and hold days, so turnover and the tax drag are measured
rather than estimated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_book_x(trades: pd.DataFrame, panels: dict, calendar: pd.DatetimeIndex,
                 slots: int, risk_pct: float = 1.0, max_weight: float | None = None,
                 adv_cap: float = 0.10, capital: float = 1e7, seed: int = 0,
                 order: str = "tight", wt_daily: pd.Series | None = None,
                 mode: str = "entry") -> dict:
    if max_weight is None:
        max_weight = 1.0 / slots
    rng = np.random.default_rng(seed)
    by_entry = {d: g for d, g in trades.groupby("entry_date", sort=False)}
    wd = None if wt_daily is None else wt_daily.reindex(calendar).ffill()

    equity, cash = capital, capital
    open_pos = []
    eq_curve, expo_curve, n_open = [], [], []
    taken, passed_full, passed_adv, passed_cash = 0, 0, 0, 0
    fills, entries = [], []

    def _close(p, day, px, reason):
        fills.append(dict(symbol=p["symbol"], entry_date=p["entry_date"],
                          exit_date=day, shares=p["shares"], entry=p["entry"],
                          exit_px=px, notional=p["shares"] * p["entry"],
                          pnl=p["shares"] * (px - p["entry"]),
                          hold=(day - p["entry_date"]).days, reason=reason))

    for day in calendar:
        w_today = 1.0 if wd is None else float(wd.get(day, 1.0))
        if not np.isfinite(w_today):
            w_today = 1.0

        still = []
        for p in open_pos:
            if p["exit_date"] <= day:
                cash += p["shares"] * p["exit_px"]
                _close(p, day, p["exit_px"], "trail")
            else:
                still.append(p)
        open_pos = still

        if mode in ("force_exit", "rebal_down") and open_pos:
            for p in list(open_pos):
                s = panels[p["symbol"]]["close"]
                v = s.get(day)
                if v is None or np.isnan(v):
                    v = p["last"]
                if mode == "force_exit":
                    if w_today <= 0:
                        cash += p["shares"] * v
                        _close(p, day, v, "regime")
                        open_pos.remove(p)
                else:
                    if w_today < p["applied"] - 1e-12:
                        frac = 0.0 if p["applied"] <= 0 else w_today / p["applied"]
                        shed = p["shares"] * (1 - frac)
                        cash += shed * v
                        fills.append(dict(symbol=p["symbol"],
                                          entry_date=p["entry_date"], exit_date=day,
                                          shares=shed, entry=p["entry"], exit_px=v,
                                          notional=shed * p["entry"],
                                          pnl=shed * (v - p["entry"]),
                                          hold=(day - p["entry_date"]).days,
                                          reason="rebal_down"))
                        p["shares"] -= shed
                        p["applied"] = w_today
                        if p["shares"] * v < 1000:
                            open_pos.remove(p)

        mtm = cash
        for p in open_pos:
            s = panels[p["symbol"]]["close"]
            v = s.get(day)
            if v is None or np.isnan(v):
                v = p["last"]
            p["last"] = v
            mtm += p["shares"] * v
        equity = mtm

        cand = by_entry.get(day)
        if cand is not None and len(open_pos) < slots:
            c = cand.copy()
            if order == "random":
                c = c.iloc[rng.permutation(len(c))]
            elif order == "tight":
                c = c.sort_values("final_depth")
            held = {p["symbol"] for p in open_pos}
            for t in c.itertuples():
                if len(open_pos) >= slots:
                    passed_full += 1
                    continue
                if t.symbol in held:
                    continue
                risk_per_share = t.entry - t.stop
                if risk_per_share <= 0:
                    continue
                wt = getattr(t, "wt", 1.0)
                if wt <= 0:
                    continue
                want = min(risk_pct * equity / risk_per_share * t.entry,
                           max_weight * equity) * wt
                want = min(want, adv_cap * t.adv * 1e7)
                if want < 1000:
                    passed_adv += 1
                    continue
                want = min(want, cash)
                if want < 1000:
                    passed_cash += 1
                    continue
                sh = want / t.entry
                cash -= sh * t.entry
                open_pos.append(dict(symbol=t.symbol, shares=sh, entry=t.entry,
                                     exit_date=t.exit_date, exit_px=t.exit_px,
                                     last=t.entry, entry_date=t.entry_date,
                                     applied=wt))
                entries.append(dict(symbol=t.symbol, date=t.entry_date,
                                    notional=sh * t.entry))
                held.add(t.symbol)
                taken += 1

        eq_curve.append(equity)
        expo_curve.append(1 - cash / equity if equity > 0 else 0)
        n_open.append(len(open_pos))

    eq = pd.Series(eq_curve, index=calendar)
    dd = 1 - eq / eq.cummax()
    yrs = (calendar[-1] - calendar[0]).days / 365.25
    rets = eq.pct_change().dropna()
    vol = rets.std() * np.sqrt(252)
    cagr = (eq.iloc[-1] / capital) ** (1 / yrs) - 1
    return dict(equity=eq, dd=dd, cagr=cagr, maxdd=float(dd.max()),
                sharpe=(cagr - 0.05) / vol if vol > 0 else np.nan, vol=vol,
                taken=taken, passed_full=passed_full, passed_adv=passed_adv,
                passed_cash=passed_cash, exposure=float(np.mean(expo_curve)),
                avg_open=float(np.mean(n_open)), end=float(eq.iloc[-1]),
                fills=pd.DataFrame(fills), entries=pd.DataFrame(entries))
