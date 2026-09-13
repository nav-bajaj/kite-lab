from __future__ import annotations
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "tasks/breakout_calls_2026/lib")
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
sys.path.insert(0, "tasks/exit_asymmetry_2026/lib")
from exits import load_panel            # noqa: E402
from daily_features import benchmark    # noqa: E402
from tapes import dedupe                # noqa: E402
from exitsim import walk                # noqa: E402

ERAS = [(2006, 2012, "2006-12"), (2013, 2019, "2013-19"), (2020, 2026, "2020-26")]
CELLS = [("X9", f"N={N} Z={int(Z*100)} k={int(k*100)}", dict(N=N, Z=Z, k=k))
         for N in (21, 42) for Z in (0.10, 0.15) for k in (0.50, 0.65)]
tp = pd.read_parquet("tasks/trigger_calls_2026/data/tapes.parquet")
tape = dedupe(tp[(tp.kind == "T3") & (tp.rk <= 20)])[
    ["symbol", "entry_date", "entry"]].reset_index(drop=True)
rows = []
for sym, g in tape.groupby("symbol", sort=False):
    p = load_panel(sym)
    if p is None:
        continue
    aux = dict(state={}, rank={}, deter={})
    for r in g.itertuples():
        e = p["pos"].get(pd.Timestamp(r.entry_date))
        if e is None:
            continue
        for fam, pl, par in CELLS:
            ret, hold, why, pg, xb = walk(p, e, r.entry, fam, par, True, aux)
            rows.append((pl, sym, r.entry_date, p["dates"][xb], ret, hold, why, pg))
R = pd.DataFrame(rows, columns=["params", "symbol", "entry_date", "exit_date",
                                "ret", "hold", "why", "peak_gain"])
bm = benchmark()
bi = bm.reindex(bm.index.union(pd.Index(R.entry_date.unique())
                               .union(pd.Index(R.exit_date.unique())))).ffill()
R["alpha"] = R.ret - (bi.reindex(R.exit_date).to_numpy() / bi.reindex(R.entry_date).to_numpy() - 1)
R["closed"] = R.why != "open_at_end"
R["fam"] = "X9"; R["backstop"] = True
R.to_parquet("tasks/exit_asymmetry_2026/data/sims_x9.parquet", index=False)

old = pd.read_parquet("tasks/exit_asymmetry_2026/data/sims.parquet")
A = pd.concat([old, R], ignore_index=True)
A["yr"] = pd.to_datetime(A.entry_date).dt.year

def cell(x):
    w, l = x.ret[x.ret > 0], x.ret[x.ret <= 0]
    big = x[x.peak_gain >= 0.10]
    c21 = x[(x.yr >= 2021) & x.closed]
    o = dict(n=len(x), win=round((x.ret > 0).mean()*100, 1),
             avgw=round(w.mean()*100, 1), avgl=round(l.mean()*100, 1),
             exp=round(x.ret.mean()*100, 2), alpha=round(x.alpha.mean()*100, 2),
             meanhold=int(x.hold.mean()), medhold=int(x.hold.median()),
             openpct=round((~x.closed).mean()*100, 1),
             keep=round(float((big.ret/big.peak_gain).median()*100), 1),
             n21=len(c21), exp21=round(c21.ret.mean()*100, 2))
    for lo, hi, el in ERAS:
        e = x[(x.yr >= lo) & (x.yr <= hi)]
        o[el] = round(e.ret.mean()*100, 2)
    return o

res = {}
res["X0 ma150"] = cell(A[(A.fam == "X0")])
res["X1 A=25 k=50 +ma150"] = cell(A[(A.fam == "X1") & (A.params == "A=25 k=50") & A.backstop])
for _, pl, _ in CELLS:
    res[f"X9 {pl}"] = cell(A[(A.fam == "X9") & (A.params == pl)])
x0 = res["X0 ma150"]
e = np.array([res[f"X9 {pl}"]["exp"] for _, pl, _ in CELLS])
mu, sd = e.mean(), e.std(ddof=1)
ln = np.log(8)
zg = np.sqrt(2*ln) - (np.log(ln) + np.log(4*np.pi))/(2*np.sqrt(2*ln))
best = max((f"X9 {pl}" for _, pl, _ in CELLS), key=lambda k: res[k]["exp"])
v = res[best]
gates = dict(E1=v["exp"]-x0["exp"] >= 2.0, E2=v["keep"] >= 35.0,
             E3=v["avgw"] >= 0.85*x0["avgw"],
             E4=all(v[el] > 0 for _,_,el in ERAS) and all(v[el] >= 0.60*v["exp"] for _,_,el in ERAS),
             E5=v["exp21"]-x0["exp21"] >= 2.0,
             E7=v["meanhold"] <= 1.3*x0["meanhold"])
# where it comes from
bx = A[(A.fam == "X9") & (A.params == best[3:])].set_index(["symbol", "entry_date"])
zx = A[A.fam == "X0"].set_index(["symbol", "entry_date"])
j = bx[["ret", "why", "hold"]].join(zx[["ret", "hold"]], rsuffix="_x0")
j["earlystop"] = j.why == "early_stop"
brk = {}
for lab, m in [("early stop fired", j.earlystop), ("early stop did not fire", ~j.earlystop)]:
    g = j[m]
    brk[lab] = dict(n=len(g), x9=round(g.ret.mean()*100, 2), x0=round(g.ret_x0.mean()*100, 2),
                    diff=round((g.ret-g.ret_x0).mean()*100, 2),
                    x0_win=round((g.ret_x0 > 0).mean()*100, 1),
                    x0_recov=round((g.ret_x0 > 0).sum()), medhold=int(g.hold.median()),
                    medhold_x0=int(g.hold_x0.median()))
print(json.dumps(dict(res=res, gumbel=dict(mean=round(float(mu),2), sd=round(float(sd),2),
    z_gumbel=round(float(zg),3), emax_gumbel=round(float(mu+sd*zg),2),
    emax_exact=round(float(mu+sd*1.42360),2), best=best, best_exp=v["exp"]),
    gates=gates, breakdown=brk), indent=1, default=str))
A[A.fam == "X9"].to_csv("tasks/exit_asymmetry_2026/data/x9_grid_trades.csv", index=False)
