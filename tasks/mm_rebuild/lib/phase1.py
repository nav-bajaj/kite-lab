"""§1 — score x lookback x universe, monthly, 25/20, IS 2010-2015."""
import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
rows = []
for uni, kind, lb in itertools.product(["nifty250", "nse500"], ["abs", "voladj"], [126, 189, 252]):
    cfg, _ = run_candidate(universe=uni, kind=kind, lookback=lb, min_obs=int(round(0.87 * lb)))
    st = W.stats(W.equity(RUNS / cfg_id(cfg)), "2010-01-01", "2015-12-31"); W.register(cfg, cfg_id(cfg), st, "1")
    t = pd.read_csv(RUNS / cfg_id(cfg) / "trades.csv"); x = pd.read_csv(RUNS / cfg_id(cfg) / "exits.csv")
    rows.append(dict(universe=uni, kind=kind, lookback=lb, cagr=100 * st["cagr"], sharpe=st["sharpe"], maxdd=100 * st["maxdd"], trades_py=len(t) / 6, hit=(x.pnl_pct > 0).mean(), hold=x.hold_days.mean()))
    print(f"{uni:9s} {kind:7s} {lb}: {100*st['cagr']:5.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}  trades/yr {len(t)/6:.0f} hit {100*(x.pnl_pct>0).mean():.0f}% hold {x.hold_days.mean():.0f}d", flush=True)
pd.DataFrame(rows).to_csv(RUNS / "1_summary.csv", index=False); print("done")
