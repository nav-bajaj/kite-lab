"""§3j stage 0 — fully invested baselines on the two windows, end passed so nothing past it is simulated."""
import sys, time
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats, register, fmt
WIN = {"cost": ("2010-01-01", "2015-12-31"), "pre": ("2006-02-01", "2009-12-31")}
for uni, cad in [("nifty250", "monthly"), ("nse500", "biweekly")]:
    for w, (a, b) in WIN.items():
        t = time.time()
        cfg, res = run_candidate(score="cr", regimes=1, universe=uni, top_n=25, exit_buffer=20, return_filter=True, cadence=cad, start=a, end=b)
        eq = equity(RUNS / cfg_id(cfg))
        st = stats(eq, a, b); register(cfg, cfg_id(cfg), stats(eq, "2010-01-01", "2015-12-31"), "3j")
        print(f"{uni} {cad} {w} {a}->{b}: {fmt(st)}  id={cfg_id(cfg)} reused={res.get('reused', False)} last={eq.index[-1].date()} {time.time()-t:.1f}s", flush=True)
