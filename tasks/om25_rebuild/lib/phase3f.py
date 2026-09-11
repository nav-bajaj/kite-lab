import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats, register
rows = []
for uni, cad, rf in [("nifty250", "biweekly", True), ("nifty250", "weekly", True), ("nse500", "weekly", True), ("nse500", "biweekly", True)]:
    for redeploy in [False, True]:
        for n, c, be in itertools.product([15, 21, 31, 42], [2, 3, 5], [0.5, 0.25, 0.0]):
            if uni == "nse500" and cad == "biweekly" and not redeploy:
                continue      # already in §3e
            cfg, _ = run_candidate(score="cr", regimes=1, universe=uni, top_n=25, exit_buffer=20, cadence=cad, return_filter=rf,
                                   overlay=True, roc_n=n, confirm=c, bear_exposure=be, redeploy=redeploy)
            st = stats(equity(RUNS / cfg_id(cfg)), "2006-01-01", "2015-12-31"); register(cfg, cfg_id(cfg), st, "3f")
            rows.append((uni, cad, redeploy, n, c, be, 100 * st["cagr"], st["sharpe"], 100 * st["maxdd"]))
            print(f"{uni} {cad} redeploy={redeploy} ROC{n}/c{c} exp{be}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
pd.DataFrame(rows, columns=["universe", "cadence", "redeploy", "roc_n", "confirm", "bear_exposure", "cagr", "sharpe", "maxdd"]).to_csv(RUNS / "3f_summary.csv", index=False)
print("done", flush=True)
