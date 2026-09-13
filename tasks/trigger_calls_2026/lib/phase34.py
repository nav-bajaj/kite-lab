"""A1 re-run under the corrected gate, the three-gate table, §3 and §4."""
from __future__ import annotations
import sys, json, time
import numpy as np, pandas as pd
sys.path.insert(0, "tasks/trend_screen_2026/lib")
sys.path.insert(0, "tasks/breakout_calls_2026/lib")
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
from exits import load_panel, simulate          # noqa: E402
from book import build_book, era_sharpe         # noqa: E402
from daily_features import regime_gate, benchmark  # noqa: E402
from tapes import dedupe, REF_CFG               # noqa: E402

ERAS = [(2006, 2012, "2006-12"), (2013, 2019, "2013-19"), (2020, 2026, "2020-26")]
t0 = time.time()
out = {}
t = pd.read_parquet("tasks/trigger_calls_2026/data/tapes.parquet")

def align(s, idx):
    s = s.sort_index()
    return s.reindex(s.index.union(pd.Index(idx.unique()))).ffill().reindex(idx)

# ---- gates ----
comp = pd.read_parquet("tasks/regime_allocation_2026/data/signals.parquet")["composite"].dropna()
g_dir = (comp.sort_index() > comp.sort_index().shift(63))
g_hys = regime_gate()
c4 = pd.read_parquet("tasks/regime_first_2026/data/candidate_labels.parquet")["C4 kmeans k=2"].dropna()
g_c4 = (c4 == "S0")                    # S0 is BROAD: higher mean pct_above_200 on the fit window
GATES = {"none": None, "hyst": g_hys, "c4": g_c4, "dir63": g_dir}
for k, g in GATES.items():
    if g is None:
        t[f"g_{k}"] = True
    else:
        t[f"g_{k}"] = align(g, t.trigger_date).fillna(False).to_numpy().astype(bool)
out["gate_meta"] = {k: (None if g is None else dict(
    time_on=round(g.mean() * 100, 1),
    flips_yr=round(g.astype(int).diff().abs().sum() / ((g.index[-1] - g.index[0]).days / 365.25), 2),
    median_run=float(pd.Series(g.groupby((g != g.shift()).cumsum()).size()).median())))
    for k, g in GATES.items()}
out["c4_map"] = "S0 = BROAD (fit-window mean pct_above_200 0.718 vs S1 0.275)"

# ---- A1 re-run ----
a1 = {}
t3d = dedupe(t[(t.kind == "T3") & t.g_dir63])
for lab, m in [("entry_year>=2014", t3d.entry_date.dt.year >= 2014),
               ("trigger_year>=2014", t3d.trigger_date.dt.year >= 2014)]:
    x = t3d[m]
    a1[lab] = dict(n=len(x), win=round((x.ret > 0).mean() * 100, 1),
                   exp=round(x.ret.mean() * 100, 2))
raw = t[(t.kind == "T3") & t.g_dir63]
raw = raw[raw.entry_date.dt.year >= 2014]
a1["no_dedupe"] = dict(n=len(raw), win=round((raw.ret > 0).mean() * 100, 1),
                       exp=round(raw.ret.mean() * 100, 2))
out["a1"] = a1

# ---- three-gate per-call + cadence ----
span = pd.period_range(t.trigger_date.min().to_period("M"),
                       t.trigger_date.max().to_period("M"), freq="M")
def stats(x):
    w, l = x.ret[x.ret > 0], x.ret[x.ret <= 0]
    mth = x.trigger_date.dt.to_period("M").value_counts().reindex(span, fill_value=0)
    return dict(n=len(x), win=round((x.ret > 0).mean() * 100, 1),
                avgw=round(w.mean() * 100, 1), avgl=round(l.mean() * 100, 1),
                ratio=round(w.mean() / abs(l.mean()), 2),
                exp=round(x.ret.mean() * 100, 1), alpha=round(x.alpha.mean() * 100, 1),
                med=round(x.ret.median() * 100, 1), medhold=int(x.hold.median()),
                permo=round(mth.mean(), 1), zero=round((mth == 0).mean() * 100, 1),
                eras={el: (len(e), round((e.ret > 0).mean() * 100, 1), round(e.ret.mean() * 100, 1))
                      for lo, hi, el in ERAS
                      for e in [x[(x.trigger_date.dt.year >= lo) & (x.trigger_date.dt.year <= hi)]]})
rows = {}
tapes = {}
for k in ("T1", "T2", "T3"):
    for gk in ("none", "hyst", "c4"):
        d = dedupe(t[(t.kind == k) & t[f"g_{gk}"]])
        tapes[(k, gk)] = d
        rows[f"{k}|{gk}"] = stats(d)
out["threegate"] = rows
print(json.dumps(out, indent=1, default=str), flush=True)

if a1["entry_year>=2014"]["n"] > 762 or a1["entry_year>=2014"]["n"] < 752:
    print("A1 FAIL — stopping"); sys.exit(0)

# ---- §3 exit sweep on the best gated expectancy trigger ----
best = max(("T1", "T2", "T3"), key=lambda k: rows[f"{k}|hyst"]["exp"])
out["best_trigger"] = best
tape = tapes[(best, "hyst")][["symbol", "trigger_date"]].drop_duplicates()
GRID = [("ma150", dict(trail="ma150")), ("ma100", dict(trail="ma100")),
        ("atr2", dict(trail="chandelier", atr_mult=2.0)),
        ("atr3", dict(trail="chandelier", atr_mult=3.0)),
        ("atr4", dict(trail="chandelier", atr_mult=4.0)),
        ("swing", dict(trail="swing"))]
res = {g: [] for g, _ in GRID}
for sym, gg in tape.groupby("symbol", sort=False):
    p = load_panel(sym)
    if p is None:
        continue
    n = len(p["c"])
    for td in gg.trigger_date:
        i = p["pos"].get(pd.Timestamp(td))
        if i is None or i + 1 >= n:
            continue
        e = i + 1
        entry = (p["o"][e] + p["h"][e] + p["l"][e] + p["c"][e]) / 4 * 1.002
        for gname, over in GRID:
            cfg = dict(REF_CFG); cfg.update(over)
            o = simulate(p, e, entry, entry * 0.01, cfg)
            if o is None:
                continue
            res[gname].append(dict(symbol=sym, trigger_date=pd.Timestamp(td),
                                   entry_date=p["dates"][e], entry=entry,
                                   exit_date=p["dates"][min(e + o[2], n - 1)],
                                   exit_px=entry * (1 + o[0]), ret=o[0],
                                   hold=o[2], reason=o[3]))
b = benchmark()
sweep = {}
grids = {}
for gname, rws in res.items():
    x = pd.DataFrame(rws)
    bi = b.reindex(b.index.union(pd.Index(x.entry_date.unique()).union(pd.Index(x.exit_date.unique())))).ffill()
    x["alpha"] = x.ret - (bi.reindex(x.exit_date).to_numpy() / bi.reindex(x.entry_date).to_numpy() - 1)
    grids[gname] = x
    sweep[gname] = stats(x)
out["sweep"] = sweep
e = np.array([sweep[g]["exp"] for g, _ in GRID])
mu, sd = e.mean(), e.std(ddof=1)
out["sweep_summary"] = dict(cells=len(e), median=round(float(np.median(e)), 1),
                            best=max(sweep, key=lambda k: sweep[k]["exp"]),
                            best_exp=round(float(e.max()), 1),
                            mean=round(float(mu), 1), sd=round(float(sd), 1),
                            gumbel_emax5=round(float(mu + sd * 1.16296), 1),
                            gumbel_emax6=round(float(mu + sd * 1.26721), 1))
print(json.dumps({k: out[k] for k in ("best_trigger", "sweep", "sweep_summary")},
                 indent=1, default=str), flush=True)

# ---- §4 portfolio ----
cal = pd.DatetimeIndex(sorted(pd.read_parquet(
    "tasks/trigger_calls_2026/data/daily.parquet", columns=["date"]).date.unique()))
adv = t[["symbol", "trigger_date", "adv"]].drop_duplicates()
tr = grids["ma150"].merge(adv, on=["symbol", "trigger_date"], how="left")
tr["adv"] = tr["adv"].fillna(1.0)
tr["stop"] = tr.entry * 0.01
syms = sorted(tr.symbol.unique())
panels = {}
for s in syms:
    p = load_panel(s)
    if p is not None:
        panels[s] = dict(close=pd.Series(p["c"], index=p["dates"]))
gh = align(g_hys, pd.Index(cal)); gh.index = cal; gh = gh.fillna(False)
book = {}
for lab, reg in (("gated", gh), ("always-on", None)):
    src = tr if reg is not None else grids["ma150"].merge(adv, on=["symbol", "trigger_date"], how="left")
    if reg is None:
        src["adv"] = src["adv"].fillna(1.0); src["stop"] = src.entry * 0.01
    for lo, hi, tag in ((2006, 2026, "full"), (2016, 2026, "oos")):
        c = cal[(cal.year >= lo) & (cal.year <= hi)]
        x = src[(src.entry_date >= c[0]) & (src.entry_date <= c[-1])]
        r = build_book(x, panels, c, slots=25, regime=reg)
        book[f"{lab}|{tag}"] = dict(
            cagr=round(r["cagr"] * 100, 1), maxdd=round(r["maxdd"] * 100, 1),
            sharpe=round(r["sharpe"], 2), vol=round(r["vol"] * 100, 1),
            exposure=round(r["exposure"] * 100, 1), avg_open=round(r["avg_open"], 1),
            taken=r["taken"], eras=({k: round(v, 2) for k, v in
                                     era_sharpe(r["equity"], ERAS).items()}))
# benchmark
for lo, hi, tag in ((2006, 2026, "full"), (2016, 2026, "oos")):
    c = cal[(cal.year >= lo) & (cal.year <= hi)]
    s = b.reindex(b.index.union(c)).ffill().reindex(c)
    y = (c[-1] - c[0]).days / 365.25
    rr = s.pct_change().dropna()
    cg = (s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1
    v = rr.std() * np.sqrt(252)
    book[f"NIFTY500|{tag}"] = dict(cagr=round(cg * 100, 1),
                                   maxdd=round((1 - s / s.cummax()).max() * 100, 1),
                                   sharpe=round((cg - 0.05) / v, 2), vol=round(v * 100, 1))
out["book"] = book
print(json.dumps({"book": book}, indent=1, default=str), flush=True)
print("elapsed", round(time.time() - t0), flush=True)
