"""§3h — the same book started 2010-01-01: no crash, no recovery, muted returns."""
import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats, register
START, IS_END = "2010-01-01", "2015-12-31"
rows = []
def go(**kw):
    cfg, _ = run_candidate(score="cr", regimes=1, top_n=25, exit_buffer=20, return_filter=True, start=START, **kw)
    st = stats(equity(RUNS / cfg_id(cfg)), START, IS_END); register(cfg, cfg_id(cfg), st, "3h")
    rows.append({**{k: kw.get(k) for k in ["universe", "cadence", "overlay", "roc_n", "confirm", "bear_exposure", "reenter_on_flip"]},
                 "cagr": 100 * st["cagr"], "sharpe": st["sharpe"], "maxdd": 100 * st["maxdd"]})
    print(f"{kw}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
for uni, cad in [("nifty250", "monthly"), ("nse500", "biweekly")]:
    go(universe=uni, cadence=cad, overlay=False)
    for n, c, be in itertools.product([15, 21, 31, 42], [2, 3, 5], [0.75, 0.5, 0.25, 0.0]):
        go(universe=uni, cadence=cad, overlay=True, roc_n=n, confirm=c, bear_exposure=be)
    for n, c in itertools.product([15, 21, 31, 42], [2, 3, 5]):
        go(universe=uni, cadence=cad, overlay=True, roc_n=n, confirm=c, bear_exposure=0.0, reenter_on_flip=True)
pd.DataFrame(rows).to_csv(RUNS / "3h_summary.csv", index=False)
print("done", flush=True)
