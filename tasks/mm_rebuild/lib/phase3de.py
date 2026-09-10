"""§3d ROC regime tilt (bull: absolute momentum, bear: vol-adjusted) and §3e exposure overlay, on the §3a base (skip 21), IS 2010-2015."""
import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
BASE = {"nifty250": dict(lookback=252, min_obs=219), "nse500": dict(lookback=126, min_obs=110)}
rows = []
for uni, b in BASE.items():
    cfg, _ = run_candidate(universe=uni, kind="voladj", skip=21, **b); st = W.stats(W.equity(RUNS / cfg_id(cfg)), "2010-01-01", "2015-12-31")
    rows.append(dict(universe=uni, phase="base", roc_n=None, confirm=None, bear_exposure=None, cagr=100 * st["cagr"], sharpe=st["sharpe"], maxdd=100 * st["maxdd"]))
    for n, c in itertools.product([15, 21, 31, 42], [2, 3, 5]):
        cfg, _ = run_candidate(universe=uni, kind="voladj", skip=21, regimes=2, bull_kind="abs", roc_n=n, confirm=c, **b)
        st = W.stats(W.equity(RUNS / cfg_id(cfg)), "2010-01-01", "2015-12-31"); W.register(cfg, cfg_id(cfg), st, "3d")
        rows.append(dict(universe=uni, phase="3d", roc_n=n, confirm=c, bear_exposure=None, cagr=100 * st["cagr"], sharpe=st["sharpe"], maxdd=100 * st["maxdd"]))
        print(f"{uni} 3d tilt ROC{n}/c{c}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
        for be in [0.5, 0.0]:
            cfg, _ = run_candidate(universe=uni, kind="voladj", skip=21, overlay=True, roc_n=n, confirm=c, bear_exposure=be, reenter_on_flip=True, **b)
            st = W.stats(W.equity(RUNS / cfg_id(cfg)), "2010-01-01", "2015-12-31"); W.register(cfg, cfg_id(cfg), st, "3e")
            rows.append(dict(universe=uni, phase="3e", roc_n=n, confirm=c, bear_exposure=be, cagr=100 * st["cagr"], sharpe=st["sharpe"], maxdd=100 * st["maxdd"]))
            print(f"{uni} 3e overlay ROC{n}/c{c} bear{be}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
pd.DataFrame(rows).to_csv(RUNS / "3de_summary.csv", index=False); print("done", flush=True)
