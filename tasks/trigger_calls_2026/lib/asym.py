"""Asymmetric regime gates — slow OFF, fast ON — and forced liquidation.

§4 showed the symmetric 40/60 gate blocks entries and never closes anything,
so the book rides a decline down and is then still switched off through the
recovery. Two candidate fixes, tested separately so the table says which one
moves the book: make the gate asymmetric (G1-G3), or make it liquidate
(G4, G5). Nothing else changes.
"""
from __future__ import annotations
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "tasks/trend_screen_2026/lib")
sys.path.insert(0, "tasks/breakout_calls_2026/lib")
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
from exits import load_panel                       # noqa: E402
from book import build_book                        # noqa: E402
from daily_features import regime_gate, benchmark  # noqa: E402
from tapes import dedupe                           # noqa: E402

SLOTS = 25
BREADTH = "tasks/trend_screen_2026/data/breadth.parquet"
p200 = pd.read_parquet(BREADTH)["pct_above_200"].dropna().sort_index()


def asym(on_th: float, off_below: float, off_n: int) -> pd.Series:
    """ON the session breadth first exceeds on_th. OFF only after off_n
    CONSECUTIVE sessions below off_below — one bad week does not turn it off."""
    on, run, vals = False, 0, []
    for v in p200.to_numpy():
        run = run + 1 if v < off_below else 0
        if not on and v > on_th:
            on = True
        elif on and run >= off_n:
            on = False
        vals.append(on)
    return pd.Series(vals, index=p200.index)


GATES = {
    "G0 sym 40/60": (regime_gate(), False),
    "G1 off<40x21 / on>50": (asym(0.50, 0.40, 21), False),
    "G2 off<40x10 / on>50": (asym(0.50, 0.40, 10), False),
    "G3 off<40x21 / on>45": (asym(0.45, 0.40, 21), False),
    "G4 = G1 + forced exit": (asym(0.50, 0.40, 21), True),
    "G5 = G0 + forced exit": (regime_gate(), True),
}

t = pd.read_parquet("tasks/trigger_calls_2026/data/tapes.parquet")
t3 = t[t.kind == "T3"].copy()
cal = pd.DatetimeIndex(sorted(pd.read_parquet(
    "tasks/trigger_calls_2026/data/daily.parquet", columns=["date"]).date.unique()))
span = pd.period_range(t.trigger_date.min().to_period("M"),
                       t.trigger_date.max().to_period("M"), freq="M")
syms = sorted(t3.symbol.unique())
raw_close, ohlc4 = {}, {}
for s in syms:
    p = load_panel(s)
    if p is None:
        continue
    raw_close[s] = pd.Series(p["c"], index=p["dates"])
    ohlc4[s] = pd.Series((p["o"] + p["h"] + p["l"] + p["c"]) / 4, index=p["dates"])


def align(g, idx):
    u = g.reindex(g.index.union(pd.Index(pd.unique(idx)))).ffill()
    return u.reindex(idx)


def gate_stats(g):
    yrs = (g.index[-1] - g.index[0]).days / 365.25
    runs = g.groupby((g != g.shift()).cumsum()).size()
    return dict(flips_yr=round(g.astype(int).diff().abs().sum() / yrs, 2),
                median_run=int(runs.median()), time_on=round(g.mean() * 100, 1))


rows = {}
for name, (g, forced) in GATES.items():
    gt = align(g, t3.trigger_date).fillna(False).astype(bool).to_numpy()
    tape = dedupe(t3[gt]).copy()
    mth = tape.trigger_date.dt.to_period("M").value_counts().reindex(span, fill_value=0)
    r = dict(gate=gate_stats(g), n=len(tape),
             win=round((tape.ret > 0).mean() * 100, 1),
             exp=round(tape.ret.mean() * 100, 1),
             alpha=round(tape.alpha.mean() * 100, 1),
             empty=round((mth == 0).mean() * 100, 1), books={})
    gc = align(g, cal).fillna(False).astype(bool)
    gc.index = cal
    # Liquidate on the session AFTER the gate turns off, at that session's
    # OHLC/4 — the same fill convention as every other exit in this task.
    fx = (gc.shift(1).fillna(False) & ~gc) if forced else None
    if forced:
        fxdays = set(fx.index[fx])
        panels = {s: dict(close=raw_close[s].copy()) for s in raw_close}
        for s in panels:
            idx = panels[s]["close"].index.intersection(fxdays)
            panels[s]["close"].loc[idx] = ohlc4[s].loc[idx]
    else:
        panels = {s: dict(close=raw_close[s]) for s in raw_close}
    x = tape.copy()
    x["stop"] = x.entry * 0.01
    x["adv"] = x["adv"].fillna(1.0)
    for lo, hi, tag in ((2006, 2026, "full"), (2016, 2026, "oos")):
        c = cal[(cal.year >= lo) & (cal.year <= hi)]
        z = x[(x.entry_date >= c[0]) & (x.entry_date <= c[-1])]
        b = build_book(z, panels, c, slots=SLOTS, risk_pct=1.0,
                       max_weight=1.0 / SLOTS, regime=gc,
                       force_exit=(fx if forced else None))
        r["books"][tag] = dict(cagr=round(b["cagr"] * 100, 1),
                               maxdd=round(b["maxdd"] * 100, 1),
                               sharpe=round(b["sharpe"], 2),
                               exposure=round(b["exposure"] * 100, 1),
                               taken=b["taken"])
    rows[name] = r

sh = np.array([rows[k]["books"]["oos"]["sharpe"] for k in GATES])
mu, sd = sh.mean(), sh.std(ddof=1)
print(json.dumps(dict(rows=rows, gumbel=dict(
    n=6, mean=round(float(mu), 2), sd=round(float(sd), 2),
    emax6=round(float(mu + sd * 1.26721), 2),
    best=round(float(sh.max()), 2),
    best_cell=list(GATES)[int(sh.argmax())])), indent=1, default=str))
