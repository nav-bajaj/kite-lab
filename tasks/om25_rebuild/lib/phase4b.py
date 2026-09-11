"""§4b — full walk-forward: refit score / regimes / buffer / stop yearly on the trailing window, chained 2016 -> today.
Labelled: tuned with knowledge of 2016-2026 (OOS was opened in §4)."""
import sys, json, itertools, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats
BOOKS = {"A N250 monthly": dict(universe="nifty250", cadence="monthly", lookback=252, min_obs=220),
         "B N250 biweekly": dict(universe="nifty250", cadence="biweekly", lookback=252, min_obs=220),
         "C N500 monthly": dict(universe="nse500", cadence="monthly", lookback=126, min_obs=110),
         "D N500 biweekly": dict(universe="nse500", cadence="biweekly", lookback=126, min_obs=110)}
GRID = list(itertools.product(["cr", "5050", "uc"], [1, 2], [0, 10, 20], [0.0, 0.2]))
END = None
eqs = {}
for bname, b in BOOKS.items():
    for sc, rg, buf, stop in GRID:
        cfg, _ = run_candidate(score=sc, regimes=rg, top_n=25, exit_buffer=buf, return_filter=True, exit_cadence="same",
                               trailing_stop=stop, start="2006-02-01", end=END, **b)
        eqs[(bname, sc, rg, buf, stop)] = equity(RUNS / cfg_id(cfg))
        print(bname, sc, rg, buf, stop, "ok", flush=True)
end = str(max(e.index[-1] for e in eqs.values()).date())
out = []
for bname in BOOKS:
    keys = [k for k in eqs if k[0] == bname]
    for trail in (5, 10):
        chain, picks = [], []
        for y in range(2016, int(end[:4]) + 1):
            a, z = f"{y-trail}-01-01", f"{y-1}-12-31"
            best = max(keys, key=lambda k: stats(eqs[k], a, z)["sharpe"])
            seg = eqs[best][(eqs[best].index >= f"{y}-01-01") & (eqs[best].index <= f"{y}-12-31")].pct_change().dropna()
            chain.append(seg); picks.append((y, best[1:]))
        wf = (1 + pd.concat(chain)).cumprod()
        st = stats(wf, "2016-01-01", end); subs = [stats(wf, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]
        n_changes = sum(1 for i in range(1, len(picks)) if picks[i][1] != picks[i-1][1])
        out.append(dict(book=bname, trail=trail, cagr=st["cagr"], sharpe=st["sharpe"], maxdd=st["maxdd"], sub1=subs[0], sub2=subs[1], sub3=subs[2],
                        changes=n_changes, picks=json.dumps(picks)))
        print(bname, trail, {k: round(v, 3) for k, v in out[-1].items() if isinstance(v, float)}, "changes", n_changes, flush=True)
        print("   picks:", picks, flush=True)
# oracle and static references per book: best single config on the whole OOS (hindsight ceiling) and the §4 static pick
for bname in BOOKS:
    keys = [k for k in eqs if k[0] == bname]
    best = max(keys, key=lambda k: stats(eqs[k], "2016-01-01", end)["sharpe"]); st = stats(eqs[best], "2016-01-01", end)
    print(bname, "hindsight best single config on OOS:", best[1:], f"{100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
    st = stats(eqs[(bname, "cr", 1, 20, 0.0)], "2016-01-01", end); print(bname, "static §4 config (2006 start) OOS:", f"{100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
pd.DataFrame(out).to_csv(RUNS / "4b_summary.csv", index=False); print("done", flush=True)
