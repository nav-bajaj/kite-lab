"""§3a-c — skip-month, positive-momentum eligibility, trailing stop; each alone on the §2 base, IS 2010-2015."""
import sys, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
BASE = {"nifty250": dict(lookback=252, min_obs=219), "nse500": dict(lookback=126, min_obs=110)}
rows = []
for uni, b in BASE.items():
    for phase, kw in [("3a", dict(skip=5)), ("3a", dict(skip=21)), ("3b", dict(positive_only=True)), ("3c", dict(trailing_stop=0.10)), ("3c", dict(trailing_stop=0.15)), ("3c", dict(trailing_stop=0.20)), ("3c", dict(trailing_stop=0.25)), ("base", {})]:
        cfg, _ = run_candidate(universe=uni, kind="voladj", **b, **kw)
        st = W.stats(W.equity(RUNS / cfg_id(cfg)), "2010-01-01", "2015-12-31")
        if phase != "base": W.register(cfg, cfg_id(cfg), st, phase)
        x = pd.read_csv(RUNS / cfg_id(cfg) / "exits.csv"); t = pd.read_csv(RUNS / cfg_id(cfg) / "trades.csv")
        rows.append(dict(universe=uni, phase=phase, device=json.dumps(kw) if (json := __import__("json")) else "", cagr=100 * st["cagr"], sharpe=st["sharpe"], maxdd=100 * st["maxdd"], hit=(x.pnl_pct > 0).mean(), trades_py=len(t) / 6, stop_share=x.reason.str.contains("stop", case=False).mean()))
        print(f"{uni} {phase} {kw}: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}  hit {100*(x.pnl_pct>0).mean():.0f}% trades/yr {len(t)/6:.0f}", flush=True)
pd.DataFrame(rows).to_csv(RUNS / "3abc_summary.csv", index=False); print("done", flush=True)
