from __future__ import annotations
import sys, json
import numpy as np, pandas as pd

ERAS = [(2006, 2012, "2006-12"), (2013, 2019, "2013-19"), (2020, 2026, "2020-26")]
R = pd.read_parquet("tasks/exit_asymmetry_2026/data/sims.parquet")
R["yr"] = pd.to_datetime(R.entry_date).dt.year


def cell(x):
    w, l = x.ret[x.ret > 0], x.ret[x.ret <= 0]
    big = x[x.peak_gain >= 0.10]
    keep = (big.ret / big.peak_gain).median() * 100 if len(big) else np.nan
    c21 = x[(x.yr >= 2021) & x.closed]
    out = dict(n=len(x), win=round((x.ret > 0).mean() * 100, 1),
               avgw=round(w.mean() * 100, 1), avgl=round(l.mean() * 100, 1),
               exp=round(x.ret.mean() * 100, 2), alpha=round(x.alpha.mean() * 100, 2),
               medhold=int(x.hold.median()), meanhold=int(x.hold.mean()),
               keep=round(float(keep), 1), n21=len(c21),
               win21=round((c21.ret > 0).mean() * 100, 1) if len(c21) else np.nan,
               exp21=round(c21.ret.mean() * 100, 2) if len(c21) else np.nan,
               openpct=round((~x.closed).mean() * 100, 1))
    for lo, hi, el in ERAS:
        e = x[(x.yr >= lo) & (x.yr <= hi)]
        out[el] = round(e.ret.mean() * 100, 2) if len(e) else np.nan
    return out


res = {}
for (f, p, bs), g in R.groupby(["fam", "params", "backstop"], sort=False):
    res[(f, p, bool(bs))] = cell(g)
x0 = res[("X0", "—", False)]

for k, v in res.items():
    v["E1"] = v["exp"] - x0["exp"] >= 2.0
    v["E2"] = v["keep"] >= 35.0
    v["E3"] = v["avgw"] >= 0.85 * x0["avgw"]
    eras = [v[el] for _, _, el in ERAS]
    v["E4"] = all(e > 0 for e in eras) and all(e >= 0.60 * v["exp"] for e in eras)
    v["E5"] = (v["exp21"] - x0["exp21"]) >= 2.0
    v["E15"] = all(v[f"E{i}"] for i in (1, 2, 3, 4, 5))

e = np.array([v["exp"] for k, v in res.items() if k[0] != "X0"])
ntr = len(res)
mu, sd = e.mean(), e.std(ddof=1)
ln = np.log(ntr)
z = np.sqrt(2 * ln) - (np.log(ln) + np.log(4 * np.pi)) / (2 * np.sqrt(2 * ln))
bound = mu + sd * z
best = max((k for k in res if k[0] != "X0"), key=lambda k: res[k]["exp"])
for k, v in res.items():
    v["E6"] = (k == best) and (v["exp"] > bound)

rows = []
for (f, p, bs), v in res.items():
    rows.append(dict(family=f, params=p, backstop=bs, **v))
df = pd.DataFrame(rows).sort_values("exp", ascending=False)
df.to_csv("tasks/exit_asymmetry_2026/data/exit_grid.csv", index=False)
print(json.dumps(dict(x0=x0, trials=ntr, mean=round(float(mu), 2),
                      sd=round(float(sd), 2), z=round(float(z), 3),
                      gumbel=round(float(bound), 2),
                      best=[best[0], best[1], best[2], res[best]["exp"]],
                      clears=bool(res[best]["exp"] > bound)), indent=1, default=str))
print(df.head(14).to_string(index=False))
print("--- passing E1-E5 ---")
print(df[df.E15].to_string(index=False))
