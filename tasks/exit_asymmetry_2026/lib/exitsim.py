"""Eight pre-registered exit families, one walker.

Every family is a complete exit and every one is evaluated with and without
the 150-day as a backstop. The families are heterogeneous — a ratchet, a
time-box, a non-price state rule — so they are expressed as conditions inside
one forward walk rather than as branches in `exits.simulate`, which only
knows level trails. The fill convention is identical: a condition met on the
close of t is filled at OHLC/4 of t+1, less 0.2%.
"""
from __future__ import annotations
import numpy as np

SLIP = 0.002


def walk(p, e, entry, fam, par, backstop, aux):
    """-> (ret, hold, reason, peak_gain, exit_bar)"""
    o, h, l, c = p["o"], p["h"], p["l"], p["c"]
    s50, s150, atr = p["s50"], p["s150"], p["atr"]
    n = len(c)
    peak = c[e]
    floor = -np.inf
    reason = None
    A = par.get("A"); k = par.get("k"); m = par.get("m")
    N = par.get("N"); Y = par.get("Y"); R = par.get("R")

    for t in range(e, n):
        if c[t] > peak:
            peak = c[t]
        if t == e:
            continue
        age = t - e
        hit = None

        if backstop and not np.isnan(s150[t]) and c[t] < s150[t]:
            hit = "ma150_backstop"

        if hit is None:
            if fam == "X0":
                if not np.isnan(s150[t]) and c[t] < s150[t]:
                    hit = "ma150"
            elif fam in ("X1", "X8"):
                kk = k
                if fam == "X8" and aux["deter"].get(p["dates"][t], False):
                    kk = 0.75
                if peak >= entry * (1 + A):
                    floor = max(floor, entry + kk * (peak - entry))
                if floor > -np.inf and c[t] < floor:
                    hit = "ratchet"
            elif fam == "X2":
                if peak >= entry * (1 + A) and not np.isnan(atr[t]) and c[t] < peak - m * atr[t]:
                    hit = "armed_chandelier"
            elif fam == "X3":
                ma = s150[t] if age < N else s50[t]
                if not np.isnan(ma) and c[t] < ma:
                    hit = "ma150" if age < N else "ma50"
            elif fam == "X4":
                if age >= N and c[t] < entry * (1 + Y):
                    hit = "timebox"
                elif not np.isnan(s150[t]) and c[t] < s150[t]:
                    hit = "ma150"
            elif fam == "X5":
                st = aux["state"].get((p["dates"][t]))
                if st is not None and st not in ("LEADING", "EXTENDED"):
                    hit = "left_state"
            elif fam == "X6":
                rk = aux["rank"].get(p["dates"][t])
                if rk is not None and (np.isnan(rk) or rk > R):
                    hit = "lost_rank"
            elif fam == "X7":
                if age >= 42 and c[t] < entry * 1.05:
                    hit = "timebox"
                else:
                    if peak >= entry * 1.25:
                        floor = max(floor, entry + 0.60 * (peak - entry))
                    if floor > -np.inf and c[t] < floor:
                        hit = "ratchet"

        if hit is not None:
            if t + 1 < n:
                px = (o[t+1] + h[t+1] + l[t+1] + c[t+1]) / 4
                xb = t + 1
            else:
                px = c[t]
                xb = t
            return (px * (1 - SLIP) / entry - 1, xb - e, hit,
                    peak / entry - 1, xb)
    return (c[n-1] * (1 - SLIP) / entry - 1, n - 1 - e, "open_at_end",
            peak / entry - 1, n - 1)
