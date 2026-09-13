from __future__ import annotations
import sys, json, time
import numpy as np, pandas as pd
sys.path.insert(0, "tasks/breakout_calls_2026/lib")
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
sys.path.insert(0, "tasks/exit_asymmetry_2026/lib")
from exits import load_panel                # noqa: E402
from daily_features import benchmark        # noqa: E402
from tapes import dedupe                    # noqa: E402
from exitsim import walk                    # noqa: E402

ERAS = [(2006, 2012, "2006-12"), (2013, 2019, "2013-19"), (2020, 2026, "2020-26")]
t0 = time.time()

CELLS = [("X0", "—", {})]
for A in (0.15, 0.25):
    for k in (0.50, 0.65):
        CELLS.append(("X1", f"A={int(A*100)} k={int(k*100)}", dict(A=A, k=k)))
for A in (0.15, 0.25):
    for m in (3, 5):
        CELLS.append(("X2", f"A={int(A*100)} m={m}", dict(A=A, m=float(m))))
for N in (42, 63):
    CELLS.append(("X3", f"N={N}", dict(N=N)))
for Y in (0.05, 0.10):
    for N in (42, 63):
        CELLS.append(("X4", f"Y={int(Y*100)} N={N}", dict(Y=Y, N=N)))
CELLS.append(("X5", "—", {}))
for R in (50, 100):
    CELLS.append(("X6", f"R={R}", dict(R=R)))
CELLS.append(("X7", "N=42 Y=5 / A=25 k=60", {}))
CELLS.append(("X8", "A=25 k=60/75", dict(A=0.25, k=0.60)))

GRID = [(f, p, pr, False) for f, p, pr in CELLS]
GRID += [(f, p, pr, True) for f, p, pr in CELLS if f != "X0"]

tp = pd.read_parquet("tasks/trigger_calls_2026/data/tapes.parquet")
tape = dedupe(tp[(tp.kind == "T3") & (tp.rk <= 20)])[
    ["symbol", "trigger_date", "entry_date", "entry", "rk"]].reset_index(drop=True)
print("tape", len(tape), flush=True)

d = pd.read_parquet("tasks/trigger_calls_2026/data/daily.parquet",
                    columns=["date", "symbol", "state", "rk"])
st = {s: dict(zip(g.date, g.state)) for s, g in d.groupby("symbol")}
rkm = {s: dict(zip(g.date, g.rk)) for s, g in d.groupby("symbol")}
b200 = pd.read_parquet("tasks/trend_screen_2026/data/breadth.parquet")["pct_above_200"].dropna().sort_index()
dd = (b200 - b200.shift(63)).rolling(21).mean()
deter = (dd <= 0)
deter_map = deter.to_dict()

rows = []
for sym, g in tape.groupby("symbol", sort=False):
    p = load_panel(sym)
    if p is None:
        continue
    n = len(p["c"])
    # forward-fill state / rank onto this panel's calendar
    smap, rmap = {}, {}
    last_s, last_r = None, None
    ss, rr = st.get(sym, {}), rkm.get(sym, {})
    for dt in p["dates"]:
        if dt in ss:
            last_s = ss[dt]
            last_r = rr.get(dt, np.nan)
        smap[dt] = last_s
        rmap[dt] = last_r
    aux = dict(state=smap, rank=rmap, deter=deter_map)
    for r in g.itertuples():
        e = p["pos"].get(pd.Timestamp(r.entry_date))
        if e is None:
            continue
        entry = r.entry
        for fam, pl, par, bs in GRID:
            ret, hold, why, pg, xb = walk(p, e, entry, fam, par, bs, aux)
            rows.append((fam, pl, bs, sym, r.entry_date, p["dates"][xb],
                         ret, hold, why, pg))
    if len(rows) > 4_000_000:
        break
R = pd.DataFrame(rows, columns=["fam", "params", "backstop", "symbol",
                                "entry_date", "exit_date", "ret", "hold",
                                "why", "peak_gain"])
print("sims", len(R), round(time.time() - t0), flush=True)
bm = benchmark()
bi = bm.reindex(bm.index.union(pd.Index(R.entry_date.unique())
                               .union(pd.Index(R.exit_date.unique())))).ffill()
R["alpha"] = R.ret - (bi.reindex(R.exit_date).to_numpy() / bi.reindex(R.entry_date).to_numpy() - 1)
R["closed"] = R.why != "open_at_end"
R.to_parquet("tasks/exit_asymmetry_2026/data/sims.parquet", index=False)
print("saved", round(time.time() - t0), flush=True)
