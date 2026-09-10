"""§2 — mechanics on the §1 winners: top-N (<= 25) x exit buffer x cadence (entry / exit), IS 2010-2015."""
import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
rows = []
for uni, lb in [("nifty250", 252), ("nse500", 126)]:
    for n, buf, (cad, ex) in itertools.product([15, 20, 25], [0, 10, 20], [("weekly", "same"), ("biweekly", "same"), ("biweekly", "weekly"), ("monthly", "same")]):
        cfg, _ = run_candidate(universe=uni, kind="voladj", lookback=lb, min_obs=int(round(0.87 * lb)), top_n=n, exit_buffer=buf, cadence=cad, exit_cadence=ex)
        st = W.stats(W.equity(RUNS / cfg_id(cfg)), "2010-01-01", "2015-12-31"); W.register(cfg, cfg_id(cfg), st, "2")
        t = pd.read_csv(RUNS / cfg_id(cfg) / "trades.csv")
        rows.append(dict(universe=uni, top_n=n, buffer=buf, entry=cad, exit=ex, cagr=100 * st["cagr"], sharpe=st["sharpe"], maxdd=100 * st["maxdd"], trades_py=len(t) / 6))
        print(f"{uni} n{n} b{buf} {cad}/{ex}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f} trades/yr {len(t)/6:.0f}", flush=True)
pd.DataFrame(rows).to_csv(RUNS / "2_summary.csv", index=False); print("done", flush=True)
