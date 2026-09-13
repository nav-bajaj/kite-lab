"""§4 — the exit ladder.

`vcp_relook` found the exit, not the entry, is the binding constraint on this
pattern (0.32R -> 1.17R). §3 gives a clean 0.467R baseline on the E1 tape
under the reference exit, so this grid moves from a known point.

Grid axes, all applied with the same look-ahead discipline as §3: a decision
made on bar t uses only bar t's close and earlier; a stop gapped through fills
at the open, never at the stop price.

  stop      initial risk: fixed % below entry, or the final-contraction low
            capped at a fixed %
  trail     50DMA / 150DMA / chandelier (N x ATR20 below the running high) /
            none
  partial   sell half into +nR strength, stop to breakeven on the rest
  timestop  abandon after N bars if the trade has not made +1R

P7 caps the whole strategy at 10 parameters, so the grid is deliberately
coarse. Per the `mm_rebuild` precedent the GRID MEDIAN is the headline; the
best cell of a grid is a selection artifact, not a result.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

SLIPPAGE = 0.002
PANELS = "data/master/prices/adjusted_pr"


def load_panel(sym: str):
    f = os.path.join(PANELS, f"{sym}.csv")
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, parse_dates=["date"]).dropna(subset=["close"]).set_index("date")
    df = df[~df.index.duplicated()].sort_index()
    c = df.close
    tr = pd.concat([df.high - df.low,
                    (df.high - c.shift()).abs(),
                    (df.low - c.shift()).abs()], axis=1).max(axis=1)
    return dict(
        dates=df.index, pos={d: i for i, d in enumerate(df.index)},
        o=df.open.to_numpy(float), h=df.high.to_numpy(float),
        l=df.low.to_numpy(float), c=c.to_numpy(float),
        s50=c.rolling(50).mean().to_numpy(),
        s150=c.rolling(150).mean().to_numpy(),
        atr=tr.rolling(20).mean().to_numpy(),
    )


def simulate(p, e: int, entry: float, stop0: float, cfg: dict):
    """One trade. -> (ret, r_multiple, hold_bars, reason)"""
    n = len(p["c"])
    o, h, l, c = p["o"], p["h"], p["l"], p["c"]
    risk = entry - stop0
    if risk <= 0:
        return None
    stop = stop0
    realized = 0.0
    w = 1.0                      # open weight
    run_hi = h[e]
    partial_done = False

    for t in range(e, n):
        # --- stop first: it is the only intrabar event we model ---
        if l[t] <= stop:
            px = (min(o[t], stop) if t > e else stop) * (1 - SLIPPAGE)
            realized += w * (px / entry - 1)
            return realized, realized * entry / risk, t - e, "stop" if not partial_done else "be_stop"

        run_hi = max(run_hi, h[t])

        # --- partial into strength, on the close ---
        if cfg["partial_r"] and not partial_done and c[t] >= entry + cfg["partial_r"] * risk:
            realized += 0.5 * (c[t] * (1 - SLIPPAGE) / entry - 1)
            w = 0.5
            partial_done = True
            stop = max(stop, entry)          # breakeven on the remainder

        # --- time stop: dead money, on the close ---
        if cfg["timestop"] and (t - e) >= cfg["timestop"] and c[t] < entry + risk:
            realized += w * (c[t] * (1 - SLIPPAGE) / entry - 1)
            return realized, realized * entry / risk, t - e, "timestop"

        # --- trail, on the close, never on the entry bar ---
        if t > e:
            tr = cfg["trail"]
            hit = False
            if tr == "ma50":
                hit = not np.isnan(p["s50"][t]) and c[t] < p["s50"][t]
            elif tr == "ma150":
                hit = not np.isnan(p["s150"][t]) and c[t] < p["s150"][t]
            elif tr == "chandelier":
                a = p["atr"][t]
                hit = not np.isnan(a) and c[t] < run_hi - cfg["atr_mult"] * a
            if hit:
                # A close-based signal cannot be filled at that same close. When
                # exit_next_open is set the sale is at the following session's
                # open, which is what a person acting on the close can get.
                # Production convention (scripts/_clean_engine.py): fills at
                # OHLC/4 of the session after the signal. exec_ohlc4 applies it
                # to the trail exit; the caller applies it to the entry.
                if (cfg.get("exit_next_open") or cfg.get("exec_ohlc4")) and t + 1 < n:
                    px = ((o[t+1] + h[t+1] + l[t+1] + c[t+1]) / 4
                          if cfg.get("exec_ohlc4") else o[t + 1])
                    return (realized + w * (px * (1 - SLIPPAGE) / entry - 1),
                            (realized + w * (px * (1 - SLIPPAGE) / entry - 1)) * entry / risk,
                            t + 1 - e, "trail")
                realized += w * (c[t] * (1 - SLIPPAGE) / entry - 1)
                return realized, realized * entry / risk, t - e, "trail"

    realized += w * (c[n - 1] * (1 - SLIPPAGE) / entry - 1)
    return realized, realized * entry / risk, n - 1 - e, "open_at_end"


def run_config(tape: pd.DataFrame, panels: dict, cfg: dict) -> pd.DataFrame:
    rows = []
    for ev in tape.itertuples():
        p = panels.get(ev.symbol)
        if p is None:
            continue
        e = p["pos"].get(pd.Timestamp(ev.signal_date))
        if e is None:
            continue
        if ev.kind == "E2":
            e += 1
            if e >= len(p["c"]):
                continue
            entry = p["o"][e] * (1 + SLIPPAGE)
        else:
            entry = ev.entry * (1 + SLIPPAGE)

        if cfg["stop_mode"] == "fixed":
            stop0 = entry * (1 - cfg["stop_pct"])
        else:                                   # structure low, capped
            stop0 = max(ev.stop_ref, entry * (1 - cfg["stop_pct"]))
        out = simulate(p, e, entry, stop0, cfg)
        if out is None:
            continue
        ret, r, hold, reason = out
        rows.append(dict(symbol=ev.symbol, year=p["dates"][e].year,
                         ret=ret, r=r, hold=hold, reason=reason))
    return pd.DataFrame(rows)
