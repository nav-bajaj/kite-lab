"""§3i — cadence grid from 2010: entry cadence x exit cadence, fully invested, no overlay."""
import sys, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats, register
START, IS_END = "2010-01-01", "2015-12-31"
rows = []
for uni in ["nifty250", "nse500"]:
    for cad, ex in [("weekly", "same"), ("biweekly", "same"), ("biweekly", "weekly"), ("monthly", "same"), ("monthly", "weekly")]:
        cfg, res = run_candidate(score="cr", regimes=1, universe=uni, top_n=25, exit_buffer=20, return_filter=True, cadence=cad, exit_cadence=ex, start=START)
        st = stats(equity(RUNS / cfg_id(cfg)), START, IS_END); register(cfg, cfg_id(cfg), st, "3i")
        tr = pd.read_csv(RUNS / cfg_id(cfg) / "trades.csv"); n_tr = len(tr)
        rows.append((uni, cad, ex, 100 * st["cagr"], st["sharpe"], 100 * st["maxdd"], n_tr))
        print(f"{uni} entry={cad} exit={ex}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}  trades={n_tr}", flush=True)
pd.DataFrame(rows, columns=["universe", "entry", "exit", "cagr", "sharpe", "maxdd", "trades"]).to_csv(RUNS / "3i_summary.csv", index=False)
print("done", flush=True)
