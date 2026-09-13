"""Persistent DIRECTION gates.

`trend_screen_2026` found the three-month change in breadth separated
per-call expectancy 5.9x across quartiles against 1.6x for the level, but
raw direction flips 26 times a year, so every gate shipped since has been a
level rule. This gives direction the same persistence treatment the level
got, and puts the two in one table.
"""
from __future__ import annotations
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "tasks/trend_screen_2026/lib")
sys.path.insert(0, "tasks/breakout_calls_2026/lib")
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
from daily_features import regime_gate  # noqa: E402
from tapes import dedupe                # noqa: E402

ERAS = [(2006, 2012, "2006-12"), (2013, 2019, "2013-19"), (2020, 2026, "2020-26")]
p200 = pd.read_parquet("tasks/trend_screen_2026/data/breadth.parquet")["pct_above_200"].dropna().sort_index()
d = (p200 - p200.shift(63)).dropna()


def persist(up_n: int, dn_n: int) -> pd.Series:
    """ON after up_n consecutive d>0, OFF after dn_n consecutive d<0."""
    on, u, w, out = False, 0, 0, []
    for v in d.to_numpy():
        u = u + 1 if v > 0 else 0
        w = w + 1 if v < 0 else 0
        if not on and u >= up_n:
            on = True
        elif on and w >= dn_n:
            on = False
        out.append(on)
    return pd.Series(out, index=d.index)


def level_asym(on_th=0.50, off_below=0.40, off_n=21) -> pd.Series:
    on, run, out = False, 0, []
    for v in p200.to_numpy():
        run = run + 1 if v < off_below else 0
        if not on and v > on_th:
            on = True
        elif on and run >= off_n:
            on = False
        out.append(on)
    return pd.Series(out, index=p200.index)


G1 = level_asym()
D3 = persist(1, 21)
GATES = {
    "no gate": None,
    "G1 level off<40x21 / on>50": G1,
    "D0 raw d>0": (d > 0),
    "D1 10 up / 10 down": persist(10, 10),
    "D2 21 up / 21 down": persist(21, 21),
    "D3 asym: off d<0 x21 / on d>0": D3,
    "D4 21-session mean d > 0": (d.rolling(21).mean() > 0),
    "D5 G1 BROAD and D3 on": (G1.reindex(D3.index).ffill().fillna(False) & D3),
}

t = pd.read_parquet("tasks/trigger_calls_2026/data/tapes.parquet")
t3 = t[t.kind == "T3"].copy()
span = pd.period_range(t.trigger_date.min().to_period("M"),
                       t.trigger_date.max().to_period("M"), freq="M")


def align(g, idx):
    u = g.reindex(g.index.union(pd.Index(pd.unique(idx)))).ffill()
    return u.reindex(idx)


def gstats(g):
    if g is None:
        return dict(flips_yr=None, median_run=None, time_on=100.0)
    g = g.astype(bool)
    yrs = (g.index[-1] - g.index[0]).days / 365.25
    runs = g.groupby((g != g.shift()).cumsum()).size()
    return dict(flips_yr=round(g.astype(int).diff().abs().sum() / yrs, 2),
                median_run=int(runs.median()), time_on=round(g.mean() * 100, 1))


def pc(x, sp):
    w, l = x.ret[x.ret > 0], x.ret[x.ret <= 0]
    mth = x.trigger_date.dt.to_period("M").value_counts().reindex(sp, fill_value=0)
    return dict(n=len(x), win=round((x.ret > 0).mean() * 100, 1),
                avgw=round(w.mean() * 100, 1), avgl=round(l.mean() * 100, 1),
                exp=round(x.ret.mean() * 100, 1), alpha=round(x.alpha.mean() * 100, 1),
                empty=round((mth == 0).mean() * 100, 1))


rows = {}
for name, g in GATES.items():
    tape = t3 if g is None else t3[align(g.astype(bool), t3.trigger_date).fillna(False).astype(bool).to_numpy()]
    tape = dedupe(tape)
    sp14 = pd.period_range("2014-01", span[-1], freq="M")
    x14 = tape[tape.trigger_date.dt.year >= 2014]
    rows[name] = dict(gate=gstats(g), full=pc(tape, span), y14=pc(x14, sp14),
                      eras={el: (len(e), round(e.ret.mean() * 100, 1))
                            for lo, hi, el in ERAS
                            for e in [tape[(tape.trigger_date.dt.year >= lo) &
                                           (tape.trigger_date.dt.year <= hi)]]})

dcells = [k for k in GATES if k.startswith("D")]
gum = {}
for sp in ("full", "y14"):
    e = np.array([rows[k][sp]["exp"] for k in dcells])
    mu, sd = e.mean(), e.std(ddof=1)
    gum[sp] = dict(mean=round(float(mu), 1), sd=round(float(sd), 1),
                   emax6=round(float(mu + sd * 1.26721), 1),
                   best=round(float(e.max()), 1),
                   best_cell=dcells[int(e.argmax())])
print(json.dumps(dict(rows=rows, gumbel=gum), indent=1, default=str))
