import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats, register
rows = []
for uni, cad in [("nifty250", "monthly"), ("nifty250", "biweekly"), ("nse500", "biweekly")]:
    for n, c, be in itertools.product([15, 21, 31, 42], [2, 3, 5], [0.0, 0.25]):
        cfg, _ = run_candidate(score="cr", regimes=1, universe=uni, top_n=25, exit_buffer=20, cadence=cad, return_filter=True,
                               overlay=True, roc_n=n, confirm=c, bear_exposure=be, reenter_on_flip=True)
        st = stats(equity(RUNS / cfg_id(cfg)), "2006-01-01", "2015-12-31"); register(cfg, cfg_id(cfg), st, "3g")
        rows.append((uni, cad, n, c, be, 100 * st["cagr"], st["sharpe"], 100 * st["maxdd"]))
        print(f"{uni} {cad} flip ROC{n}/c{c} exp{be}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
pd.DataFrame(rows, columns=["universe", "cadence", "roc_n", "confirm", "bear_exposure", "cagr", "sharpe", "maxdd"]).to_csv(RUNS / "3g_summary.csv", index=False)
print("done", flush=True)
