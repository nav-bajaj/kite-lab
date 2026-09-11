"""§3j diagnostics (no engine): indicator distributions <= 2015-12-31 and how often each threshold reads weak
in the 2008 crash (2008-01-08 peak -> 2009-03-09 trough) versus 2010-2015. Decides the trial grid."""
import sys, time, itertools
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
import numpy as np, pandas as pd
from run import panels, MEMBERSHIP
from regime import membership_mask, strength_indicator, strength_regime
END = pd.Timestamp("2015-12-31")
CRASH, COST = ("2008-01-08", "2009-03-09"), ("2010-01-01", "2015-12-31")
GRID = {"breadth": [63, 126, 252], "breadth_ma": [100, 200], "disp": [126, 252], "factor": [21, 42, 63],
        "leaders": [21, 42, 63], "persist": [21, 63], "capture": [126, 252], "breadth_d": [21, 63], "capture_d": [21, 63], "leaders_d": [21, 63]}
ABS = {"breadth": [0.3, 0.4, 0.5, 0.6], "breadth_ma": [0.3, 0.4, 0.5, 0.6], "factor": [-0.10, -0.05, 0.0], "leaders": [-0.05, -0.02, 0.0],
       "breadth_d": [-0.2, -0.1, 0.0], "capture_d": [-0.2, -0.1, 0.0], "leaders_d": [-0.05, 0.0]}
PCT = [0.1, 0.2, 0.3]
close = panels()["close"]; close = close[close.index <= END]
rows = []
for uni in ["nifty250", "nse500"]:
    t = time.time(); mask = membership_mask(MEMBERSHIP[uni], close); print(uni, "mask", f"{time.time()-t:.1f}s", flush=True)
    for kind, lens in GRID.items():
        for L in lens:
            t = time.time(); ind = strength_indicator(close, mask, kind, L)
            s = ind[(ind.index >= "2006-01-01")]
            q = s.quantile([0.05, 0.25, 0.5, 0.75, 0.95]).round(3).tolist()
            print(f"{uni} {kind:10s} L={L:3d} first={ind.first_valid_index().date()} q05/25/50/75/95={q} crash-median={s[CRASH[0]:CRASH[1]].median():.3f} cost-median={s[COST[0]:COST[1]].median():.3f} {time.time()-t:.1f}s", flush=True)
            for mode, ths in [("abs", ABS.get(kind, [])), ("pct", PCT)]:
                for th in ths:
                    r = strength_regime(ind, th, mode, 3, close.index)
                    weak = ~r
                    fc, fk = weak[CRASH[0]:CRASH[1]].mean(), weak[COST[0]:COST[1]].mean()
                    flips = int((r != r.shift(1)).sum())
                    rows.append(dict(universe=uni, kind=kind, len=L, mode=mode, thresh=th, weak_crash=round(fc, 3), weak_cost=round(fk, 3), flips=flips))
df = pd.DataFrame(rows); df.to_csv("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/3j_diag.csv", index=False)
pd.set_option("display.width", 200, "display.max_rows", 500)
print(df.to_string(index=False))
