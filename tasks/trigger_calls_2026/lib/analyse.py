from __future__ import annotations
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
from daily_features import regime_gate
from tapes import dedupe

ERAS = [(2006, 2012, "2006-12"), (2013, 2019, "2013-19"), (2020, 2026, "2020-26")]
t = pd.read_parquet("tasks/trigger_calls_2026/data/tapes.parquet")
out = {}

# ---------- §1 regime ----------
g = regime_gate()
grp = (g != g.shift()).cumsum()
runs = g.groupby(grp).agg(v=("first"), n=("size"))
yrs = (g.index[-1] - g.index[0]).days / 365.25
out["regime"] = dict(
    flips=int((g.astype(int).diff().abs() == 1).sum()), years=round(yrs, 1),
    flips_yr=round((g.astype(int).diff().abs() == 1).sum() / yrs, 2),
    median_run=float(runs.n.median()), median_on=float(runs[runs.v].n.median()),
    median_off=float(runs[~runs.v].n.median()), time_on=round(g.mean() * 100, 1),
    n_on=int(runs.v.sum()))

def stats(x, lab):
    if not len(x):
        return dict(tag=lab, n=0)
    w, l = x.ret[x.ret > 0], x.ret[x.ret <= 0]
    return dict(tag=lab, n=len(x), win=round((x.ret > 0).mean() * 100, 1),
                avgw=round(w.mean() * 100, 1) if len(w) else np.nan,
                avgl=round(l.mean() * 100, 1) if len(l) else np.nan,
                ratio=round(w.mean() / abs(l.mean()), 2) if len(w) and len(l) and l.mean() != 0 else np.nan,
                exp=round(x.ret.mean() * 100, 2),
                alpha=round(x.alpha.mean() * 100, 2),
                med=round(x.ret.median() * 100, 1),
                medhold=int(x.hold.median()))

tapes = {}
for k in ("T1", "T2", "T3"):
    for gt in (True, False):
        d = t[t.kind == k]
        if gt:
            d = d[d.gate_on]
        tapes[(k, gt)] = dedupe(d)

rows = []
for (k, gt), d in tapes.items():
    lab = f"{k} {'gate' if gt else 'none'}"
    r = stats(d, lab)
    for lo, hi, el in ERAS:
        e = d[(d.trigger_date.dt.year >= lo) & (d.trigger_date.dt.year <= hi)]
        r[f"n_{el}"] = len(e)
        r[f"exp_{el}"] = round(e.ret.mean() * 100, 1) if len(e) else np.nan
        r[f"win_{el}"] = round((e.ret > 0).mean() * 100, 1) if len(e) else np.nan
    rows.append(r)
out["percall"] = rows

# ---------- A1 ----------
a1 = {}
d = tapes[("T3", True)]
for lab, m in [("trigger_year", d.trigger_date.dt.year >= 2014),
               ("entry_year", d.entry_date.dt.year >= 2014)]:
    x = d[m]
    a1[lab] = dict(n=len(x), win=round((x.ret > 0).mean() * 100, 1),
                   exp=round(x.ret.mean() * 100, 2))
raw = t[(t.kind == "T3") & t.gate_on]
raw = raw[raw.trigger_date.dt.year >= 2014]
a1["no_dedupe"] = dict(n=len(raw), win=round((raw.ret > 0).mean() * 100, 1),
                       exp=round(raw.ret.mean() * 100, 2))
out["a1"] = a1

# engine cross-check against the reference tape
ref = pd.read_csv("tasks/trend_screen_2026/data/calls_full_range_ohlc4.csv",
                  parse_dates=["entry_date", "exit_date"])
m = tapes[("T3", True)].merge(ref, on=["symbol", "entry_date"], suffixes=("", "_r"))
out["engine_check"] = dict(matched=len(m), of=len(tapes[("T3", True)]),
                           max_abs_ret_diff=float((m.ret - m.ret_r).abs().max()))

# ---------- cadence ----------
cad = []
for (k, gt), d in tapes.items():
    mth = d.trigger_date.dt.to_period("M").value_counts().sort_index()
    span = pd.period_range(t.trigger_date.min().to_period("M"),
                           t.trigger_date.max().to_period("M"), freq="M")
    mth = mth.reindex(span, fill_value=0)
    z = (mth == 0)
    longest = int((z * (z.groupby((~z).cumsum()).cumcount() + 1)).max())
    cad.append(dict(tag=f"{k} {'gate' if gt else 'none'}", n=len(d),
                    mean=round(mth.mean(), 1), median=float(mth.median()),
                    zero=round(z.mean() * 100, 1), busiest=str(mth.idxmax()),
                    busiest_n=int(mth.max()), empty_run=longest))
out["cadence"] = cad

# ---------- entry timing / overlap (no-gate, raw episodes) ----------
r1 = t[t.kind == "T1"].copy()
r3 = t[t.kind == "T3"].copy()
idx3 = {}
for s, gg in r3.groupby("symbol"):
    idx3[s] = gg.sort_values("trigger_date")
pairs, nofire = [], 0
for a in r1.itertuples():
    gg = idx3.get(a.symbol)
    hit = None
    if gg is not None:
        w = gg[(gg.trigger_date >= a.trigger_date) &
               (gg.trigger_date <= a.trigger_date + pd.Timedelta(days=31))]
        if len(w):
            hit = w.iloc[0]
    if hit is None:
        nofire += 1
        continue
    pairs.append(dict(symbol=a.symbol, d1=a.entry_date, d3=hit.entry_date,
                      days=(hit.entry_date - a.entry_date).days,
                      r1=a.ret, r3=hit.ret, h1=a.hold, h3=hit.hold))
p = pd.DataFrame(pairs)
out["timing"] = dict(
    t1_calls=len(r1), matched=len(p), never_fired=nofire,
    never_pct=round(nofire / len(r1) * 100, 1),
    mean_days=round(p.days.mean(), 1), median_days=float(p.days.median()),
    same_day=round((p.days == 0).mean() * 100, 1),
    mean_ret_t1=round(p.r1.mean() * 100, 2), mean_ret_t3=round(p.r3.mean() * 100, 2),
    med_ret_t1=round(p.r1.median() * 100, 2), med_ret_t3=round(p.r3.median() * 100, 2),
    mean_diff=round((p.r1 - p.r3).mean() * 100, 2),
    med_diff=round((p.r1 - p.r3).median() * 100, 2),
    win_t1=round((p.r1 > 0).mean() * 100, 1), win_t3=round((p.r3 > 0).mean() * 100, 1),
    t1_better=round((p.r1 > p.r3).mean() * 100, 1),
    mean_hold_t1=round(p.h1.mean(), 0), mean_hold_t3=round(p.h3.mean(), 0))
# lateness buckets
p["bucket"] = pd.cut(p.days, [-1, 0, 7, 14, 21, 400],
                     labels=["0", "1-7", "8-14", "15-21", "22+"])
out["timing_buckets"] = [dict(bucket=str(b), n=len(x),
                              diff=round((x.r1 - x.r3).mean() * 100, 2))
                         for b, x in p.groupby("bucket", observed=True)]
# gated variant of the never-fired share
g1 = t[(t.kind == "T1") & t.gate_on]
nf = 0
for a in g1.itertuples():
    gg = idx3.get(a.symbol)
    if gg is None or not len(gg[(gg.trigger_date >= a.trigger_date) &
                               (gg.trigger_date <= a.trigger_date + pd.Timedelta(days=31))]):
        nf += 1
out["timing"]["never_pct_gated"] = round(nf / len(g1) * 100, 1)
out["timing"]["t1_calls_gated"] = len(g1)

print(json.dumps(out, indent=1, default=str))
