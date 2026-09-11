"""§3k — lookback re-check on the 2010 window, monthly/monthly, fully invested."""
import sys, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats, register
START, IS_END = "2010-01-01", "2015-12-31"
rows = []
for uni in ["nifty250", "nse500"]:
    for lb in [63, 126, 189, 252, 378]:
        cfg, _ = run_candidate(score="cr", regimes=1, universe=uni, top_n=25, exit_buffer=20, return_filter=True, cadence="monthly",
                               lookback=lb, min_obs=int(round(0.87 * lb)), start=START)
        st = stats(equity(RUNS / cfg_id(cfg)), START, IS_END); register(cfg, cfg_id(cfg), st, "3k")
        rows.append((uni, lb, 100 * st["cagr"], st["sharpe"], 100 * st["maxdd"]))
        print(f"{uni} lookback={lb}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", flush=True)
pd.DataFrame(rows, columns=["universe", "lookback", "cagr", "sharpe", "maxdd"]).to_csv(RUNS / "3k_summary.csv", index=False)
print("done")
