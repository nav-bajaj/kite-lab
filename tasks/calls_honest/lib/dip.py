"""Dip-timed momentum calls feed (dip25_ts20) on the master store: rules from tasks/dip_vs_breakout_calls/experiment.py.

Frozen rules, as coded there:
  score      (close / close[-126] - 1) / max(annualised 126-day vol, 5%), percentile rank across the universe each day
  entry      5-day return < -5% at the close, rank >= 0.75; slots filled by rank, descending; cap 25 concurrent;
             one call per symbol; fill next session at OHLC/4 * (1 + 20 bps)
  exit       rank < 0.35 at any close ('momq'), else close < 0.80 x peak close since the signal day ('ts20');
             fill next session at OHLC/4 * (1 - 20 bps)
  portfolio  25 equal slots, idle slots earn zero

Port to the honest store: the rank is taken across point-in-time members each day; a held name that has left the
index is ranked against that day's members (share of member scores below it), so its exit rule keeps working.
Two curves are produced: `slot_curve_net`, each slot's daily return from its actual fills (the headline), and the
branch's `slot_curve` on raw closes (gross of slippage, for comparison with the earlier 37.8%).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from common import panels, universe, SLIPPAGE

DIP = dict(lookback=126, vol_floor=0.05, quartile=0.75, exit_rank=0.35, dip_ret=-0.05, dip_days=5, cap=25, ts=0.20, slippage=SLIPPAGE)


def dip_panels(uni: str, close=None):
    cols, mfn, cfn, mask = universe(uni)
    c = (panels()["close"] if close is None else close)[cols]
    mask = mask.reindex(c.index)
    lb = DIP["lookback"]
    mom = c / c.shift(lb) - 1.0
    vol = (c.pct_change().rolling(lb, min_periods=lb // 2).std() * math.sqrt(252)).clip(lower=DIP["vol_floor"])
    score = mom / vol
    rank = score.where(mask).rank(axis=1, pct=True)          # percentile across point-in-time members
    ret5 = c / c.shift(DIP["dip_days"]) - 1.0
    sig = ((ret5 < DIP["dip_ret"]) & mask).fillna(False)
    return dict(close=c, score=score, rank=rank, sig=sig, mask=mask, cols=cols)


def simulate(uni: str, start="2010-01-01", end=None, use_ts=True, cap=None):
    P = panels(); D = dip_panels(uni)
    close, trade = D["close"], P["trade"][D["cols"]]
    cal = close.index
    cap = cap or DIP["cap"]; s = DIP["slippage"]
    cl_v, tr_v, rk_v, sc_v, sig_v, mk_v = (close.to_numpy(), trade.to_numpy(), D["rank"].to_numpy(), D["score"].to_numpy(),
                                           D["sig"].to_numpy(), D["mask"].to_numpy())
    cols = list(close.columns)
    start_i = int(np.searchsorted(cal, pd.Timestamp(start)))
    end_i = int(np.searchsorted(cal, pd.Timestamp(end), side="right")) - 1 if end else len(cal) - 1
    active, calls, n_skipped = {}, [], 0
    counts = np.zeros(end_i + 1 - start_i)
    # daily slot returns (net of fills) accumulate here; idle slots earn zero
    slot_ret = np.zeros(end_i + 1 - start_i)

    def rank_of(i, j):
        r = rk_v[i, j]
        if not np.isnan(r):
            return r
        sc = sc_v[i, j]
        if np.isnan(sc):
            return np.nan
        m = sc_v[i][mk_v[i]]; m = m[~np.isnan(m)]
        return (m < sc).sum() / len(m) if len(m) else np.nan

    for i in range(start_i, end_i + 1):
        k = i - start_i
        for j, pos in active.items():
            c = cl_v[i, j]
            if np.isnan(c):
                continue
            prev = pos["last_mark"]
            slot_ret[k] += (c / prev - 1.0) / cap
            pos["last_mark"] = c
            if c > pos["peak"]:
                pos["peak"] = c
        exits = []
        for j, pos in active.items():
            c = cl_v[i, j]
            if np.isnan(c):
                continue
            r = rank_of(i, j)
            hit = (not np.isnan(r)) and r < DIP["exit_rank"]
            reason = "momq"
            if use_ts and not hit and c < pos["peak"] * (1 - DIP["ts"]):
                hit, reason = True, "ts20"
            if hit:
                exits.append((j, reason))
        for j, reason in exits:
            if i + 1 > end_i:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            pos = active.pop(j)
            fill = px * (1 - s)
            slot_ret[k + 1] += (fill / pos["last_mark"] - 1.0) / cap
            pos["last_mark"] = None
            calls.append({"symbol": cols[j], "signal_date": pos["signal_date"], "entry_date": pos["entry_date"], "exit_date": cal[i + 1],
                          "reason": reason, "pnl": fill / pos["entry_px"] - 1.0, "hold_td": i + 1 - pos["entry_i"], "status": "closed",
                          "entry_rank": pos["entry_rank"]})
        cand_j = np.where(sig_v[i])[0]
        cands = [(j, rk_v[i, j]) for j in cand_j if j not in active and not np.isnan(rk_v[i, j]) and rk_v[i, j] >= DIP["quartile"]]
        cands.sort(key=lambda t: -t[1])
        for j, r in cands:
            if len(active) >= cap:
                n_skipped += sum(1 for jj, _ in cands if jj not in active)
                break
            if i + 1 > end_i:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            entry_px = px * (1 + s)
            active[j] = {"signal_date": cal[i], "entry_date": cal[i + 1], "entry_i": i + 1, "entry_px": entry_px, "peak": cl_v[i, j],
                         "last_mark": entry_px, "entry_rank": r}
            # the entry day's mark: from the fill to that day's close, booked when the loop reaches i+1 via last_mark
        counts[k] = len(active)
    for j, pos in active.items():
        c = cl_v[end_i, j]
        calls.append({"symbol": cols[j], "signal_date": pos["signal_date"], "entry_date": pos["entry_date"], "exit_date": cal[end_i],
                      "reason": "open", "pnl": c * (1 - s) / pos["entry_px"] - 1.0, "hold_td": end_i - pos["entry_i"], "status": "open",
                      "entry_rank": pos["entry_rank"]})
    idx = cal[start_i:end_i + 1]
    calls = pd.DataFrame(calls)
    eq_net = pd.Series((1 + slot_ret).cumprod() * 1_000_000, index=idx)
    eq_gross = slot_curve(calls, close, cap, idx)
    equity = pd.DataFrame({"date": idx, "pv": eq_net.values, "pv_gross_slot": eq_gross.reindex(idx).values, "holdings": counts})
    return calls, equity, n_skipped


def slot_curve(calls, close, slots, idx):
    """The branch's construction, verbatim: raw close-to-close returns of each call over its life, divided by the slot count."""
    rets = close.pct_change()
    tot = pd.Series(0.0, index=idx)
    for _, c in calls.iterrows():
        sl = rets.loc[c["entry_date"]:c["exit_date"], c["symbol"]].reindex(idx).dropna()
        if len(sl) <= 1:
            continue
        tot.loc[sl.index[1:]] += sl.iloc[1:]
    return (1 + tot / slots).cumprod() * 1_000_000
