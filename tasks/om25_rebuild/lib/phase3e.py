import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats, register
rows = []
for uni, cad in [("nifty250", "monthly"), ("nse500", "biweekly")]:
    for rf in [True, False]:
        cfg, _ = run_candidate(score="cr", regimes=1, universe=uni, top_n=25, exit_buffer=20, cadence=cad, return_filter=rf)
        st = stats(equity(RUNS / cfg_id(cfg)), "2006-01-01", "2015-12-31"); register(cfg, cfg_id(cfg), st, "3e-base")
        rows.append((uni, cad, rf, None, None, None, 100 * st["cagr"], st["sharpe"], 100 * st["maxdd"]))
        for n, c, be in itertools.product([15, 21, 31, 42], [2, 3, 5], [0.75, 0.5, 0.25, 0.0]):
            cfg, _ = run_candidate(score="cr", regimes=1, universe=uni, top_n=25, exit_buffer=20, cadence=cad, return_filter=rf,
                                   overlay=True, roc_n=n, confirm=c, bear_exposure=be)
            st = stats(equity(RUNS / cfg_id(cfg)), "2006-01-01", "2015-12-31"); register(cfg, cfg_id(cfg), st, "3e")
            rows.append((uni, cad, rf, n, c, be, 100 * st["cagr"], st["sharpe"], 100 * st["maxdd"]))
            print(f"{uni} rf={rf} ROC{n}/c{c} exp{be}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
pd.DataFrame(rows, columns=["universe", "cadence", "return_filter", "roc_n", "confirm", "bear_exposure", "cagr", "sharpe", "maxdd"]).to_csv(RUNS / "3e_summary.csv", index=False)
print("done", flush=True)
