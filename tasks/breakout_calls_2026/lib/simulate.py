"""§3 — per-trade measurement.

Attaches a FIXED reference exit to every event on the tape so that the only
thing separating the E1 and E2 results is the entry rule. The exit ladder is
§4's job; deliberately no partials here, because a partial interacts with the
entry price and would blur the comparison §3 exists to make.

Reference exit, inherited from `vcp_reference.simulate_trade`:
  hard stop at max(final-contraction low, entry x (1 - 8%))
  trail out on the first close below the 50-day average

Entry handling differs by rule, and the difference is the point:
  E1  filled INTRADAY on the signal bar at the pivot trigger. The stop can
      therefore be hit on that same bar — a poke that reverses hard stops out
      the day it fills. The exit scan starts at the signal bar.
  E2  filled at the NEXT open after a confirming close. The exit scan starts
      there.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

SLIPPAGE = 0.002
STOP_CAP = 0.08
PANELS = "data/master/prices/adjusted_pr"
BENCH = "data/master/benchmarks/NIFTY_500.csv"


def _bench():
    b = pd.read_csv(BENCH, parse_dates=["date"]).set_index("date")["close"]
    return b[~b.index.duplicated()].sort_index()


def simulate_symbol(sym: str, events: pd.DataFrame, bench: pd.Series) -> list[dict]:
    f = os.path.join(PANELS, f"{sym}.csv")
    if not os.path.exists(f):
        return []
    df = pd.read_csv(f, parse_dates=["date"]).dropna(subset=["close"]).set_index("date")
    df = df[~df.index.duplicated()].sort_index()
    o, h, l, cl = (df[c].to_numpy(float) for c in ("open", "high", "low", "close"))
    s50 = df.close.rolling(50).mean().to_numpy()
    dates = df.index
    pos = {d: i for i, d in enumerate(dates)}
    n = len(cl)
    out = []

    for ev in events.itertuples():
        bo = pos.get(pd.Timestamp(ev.signal_date))
        if bo is None:
            continue
        if ev.kind == "E1":
            e = bo                      # filled intraday on the signal bar
            entry = ev.entry * (1 + SLIPPAGE)
        else:
            e = bo + 1                  # filled at the next open
            if e >= n:
                continue
            entry = o[e] * (1 + SLIPPAGE)
        stop = max(ev.stop_ref, entry * (1 - STOP_CAP))
        risk = entry - stop
        if risk <= 0:
            continue

        ret, exit_i, reason, still_open = None, None, None, False
        for t in range(e, n):
            if l[t] <= stop:
                # a gap through the stop fills at the open, not at the stop
                px = min(o[t], stop) if t > e else stop
                ret = px * (1 - SLIPPAGE) / entry - 1
                exit_i, reason = t, "stop"
                break
            if t > e and not np.isnan(s50[t]) and cl[t] < s50[t]:
                ret = cl[t] * (1 - SLIPPAGE) / entry - 1
                exit_i, reason = t, "trail_50dma"
                break
        if ret is None:
            ret = cl[n - 1] * (1 - SLIPPAGE) / entry - 1
            exit_i, reason, still_open = n - 1, "open_at_end", True

        d0, d1 = dates[e], dates[exit_i]
        b0, b1 = bench.asof(d0), bench.asof(d1)
        bret = (b1 / b0 - 1) if pd.notna(b0) and pd.notna(b1) else np.nan
        out.append(dict(
            symbol=sym, kind=ev.kind, failed_poke=bool(ev.failed_poke),
            confirmed_same_bar=bool(ev.confirmed_same_bar),
            entry_date=d0.date().isoformat(), exit_date=d1.date().isoformat(),
            year=d0.year, entry=round(entry, 4), stop=round(stop, 4),
            stop_pct=round(risk / entry, 4),
            ret=round(ret, 5), r=round(ret * entry / risk, 3),
            hold_days=int(exit_i - e), exit_reason=reason, open_at_end=still_open,
            bench_ret=round(bret, 5) if pd.notna(bret) else None,
            alpha=round(ret - bret, 5) if pd.notna(bret) else None,
            base_len=int(ev.base_len), n_contractions=int(ev.n_contractions),
            final_depth=float(ev.final_depth),
        ))
    return out


def run(tape: str, out_csv: str) -> pd.DataFrame:
    ev = pd.read_csv(tape)
    bench = _bench()
    rows = []
    for sym, g in ev.groupby("symbol", sort=False):
        rows.extend(simulate_symbol(sym, g, bench))
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    return df
