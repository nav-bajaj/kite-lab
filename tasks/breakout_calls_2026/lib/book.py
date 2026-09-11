"""§5 — the portfolio layer.

Turns the signal tape into a book with a finite number of slots, so we can
answer the two questions §3 cannot: how many calls a month the thing can
actually place, and what drawdown a client lives through.

Non-negotiable (TASKS.md §5): equity is marked to market EVERY DAY. The
competitor's headline −12.3% is a closed-trade drawdown, which is why their
book appears to lose a tenth of its value in 2022 while the same positions
were down half. Realised-only drawdown is not computed here at all.

Sizing: risk_pct of equity divided by the stop distance, capped both as a
share of equity and by participation in the name's ADV. Cash earns nothing —
an empty slot is a real cost and is carried as one.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_book(trades: pd.DataFrame, panels: dict, calendar: pd.DatetimeIndex,
               slots: int, risk_pct: float = 0.015, max_weight: float | None = None,
               adv_cap: float = 0.10, capital: float = 1_000_000.0,
               seed: int = 0, order: str = "random",
               regime: pd.Series | None = None) -> dict:
    """One book path. `trades` needs entry_date, exit_date, entry, exit_px,
    stop, symbol, adv (Rs cr). `order` breaks ties when more signals fire than
    slots: 'random' claims no skill, 'tight' takes the tightest final
    contraction first (the one anatomy feature §3 found predictive)."""
    # Position size must scale with slot count or the sweep is meaningless.
    # Risk sizing alone (1.5% risk / 8% stop) implies ~19% of equity per
    # position, so cash — not the slot parameter — binds at about five names
    # and every N above that returns an identical book. Capping each position
    # at an equal-weight 1/N share makes more slots mean smaller positions,
    # which is what a slot sweep is supposed to test.
    if max_weight is None:
        max_weight = 1.0 / slots
    rng = np.random.default_rng(seed)
    by_entry = {d: g for d, g in trades.groupby("entry_date", sort=False)}

    equity = capital
    cash = capital
    open_pos = []          # dicts: symbol, shares, entry, exit_date, exit_px
    eq_curve, expo_curve, n_open = [], [], []
    taken, passed_full, passed_adv, passed_cash = 0, 0, 0, 0

    for day in calendar:
        # --- exits first, so a slot freed today can be refilled today ---
        still = []
        for p in open_pos:
            if p["exit_date"] <= day:
                cash += p["shares"] * p["exit_px"]
            else:
                still.append(p)
        open_pos = still

        # --- mark to market on today's close ---
        mtm = cash
        for p in open_pos:
            s = panels[p["symbol"]]["close"]
            v = s.get(day)
            if v is None or np.isnan(v):
                v = p["last"]
            p["last"] = v
            mtm += p["shares"] * v
        equity = mtm

        # --- new entries ---
        cand = by_entry.get(day)
        if cand is not None and len(open_pos) < slots:
            if regime is not None and not bool(regime.get(day, True)):
                cand = cand.iloc[0:0]
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
                if t.symbol in held:          # no same-name double position
                    continue
                risk_per_share = t.entry - t.stop
                if risk_per_share <= 0:
                    continue
                want = min(risk_pct * equity / risk_per_share * t.entry,
                           max_weight * equity)
                want = min(want, adv_cap * t.adv * 1e7)   # ADV is in Rs crore
                if want < 1000:
                    passed_adv += 1
                    continue
                want = min(want, cash)
                if want < 1000:
                    passed_cash += 1          # a slot was free; the cash was not
                    continue
                sh = want / t.entry
                cash -= sh * t.entry
                open_pos.append(dict(symbol=t.symbol, shares=sh, entry=t.entry,
                                     exit_date=t.exit_date, exit_px=t.exit_px,
                                     last=t.entry))
                held.add(t.symbol)
                taken += 1

        eq_curve.append(equity)
        expo_curve.append(1 - cash / equity if equity > 0 else 0)
        n_open.append(len(open_pos))

    eq = pd.Series(eq_curve, index=calendar)
    dd = 1 - eq / eq.cummax()
    yrs = (calendar[-1] - calendar[0]).days / 365.25
    rets = eq.pct_change().dropna()
    ann_vol = rets.std() * np.sqrt(252)
    cagr = (eq.iloc[-1] / capital) ** (1 / yrs) - 1
    sharpe = (cagr - 0.05) / ann_vol if ann_vol > 0 else np.nan
    return dict(equity=eq, dd=dd, cagr=cagr, maxdd=dd.max(), sharpe=sharpe,
                vol=ann_vol, taken=taken, passed_full=passed_full,
                passed_adv=passed_adv, passed_cash=passed_cash,
                exposure=float(np.mean(expo_curve)),
                avg_open=float(np.mean(n_open)), end=float(eq.iloc[-1]))


def era_sharpe(eq: pd.Series, eras) -> dict:
    out = {}
    for lo, hi, lab in eras:
        s = eq.loc[f"{lo}-01-01":f"{hi}-12-31"]
        if len(s) < 60:
            out[lab] = np.nan
            continue
        r = s.pct_change().dropna()
        y = (s.index[-1] - s.index[0]).days / 365.25
        c = (s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1
        v = r.std() * np.sqrt(252)
        out[lab] = (c - 0.05) / v if v > 0 else np.nan
    return out
