"""§4c — the Nifty 250 monthly adaptive process run on the NSE 500 universe, judged on Wright's window."""
import sys, json, itertools, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats
GRID = list(itertools.product(["cr", "5050", "uc"], [1, 2], [0, 10, 20], [0.0, 0.2]))
def book(uni):
    return dict(universe=uni, cadence="monthly", lookback=252, min_obs=220, top_n=25, return_filter=True, exit_cadence="same", start="2006-02-01", end=None)
eqs = {}
for uni in ["nse500", "nifty250"]:
    for sc, rg, buf, stop in GRID:
        cfg, _ = run_candidate(**book(uni), score=sc, regimes=rg, exit_buffer=buf, trailing_stop=stop)
        eqs[(uni, sc, rg, buf, stop)] = equity(RUNS / cfg_id(cfg))
end = str(max(e.index[-1] for e in eqs.values()).date())
def chain(uni, pick_uni, trail=5):
    keys = [k for k in eqs if k[0] == pick_uni]; segs, picks = [], []
    for y in range(2016, int(end[:4]) + 1):
        a, z = f"{y-trail}-01-01", f"{y-1}-12-31"
        best = max(keys, key=lambda k: stats(eqs[k], a, z)["sharpe"])[1:]
        e = eqs[(uni,) + best]; segs.append(e[(e.index >= f"{y}-01-01") & (e.index <= f"{y}-12-31")].pct_change().dropna()); picks.append((y, best))
    return (1 + pd.concat(segs)).cumprod(), picks
series = {"Adaptive on NSE 500 (own refit)": chain("nse500", "nse500"), "Nifty 250 picks applied to NSE 500": chain("nse500", "nifty250"), "Adaptive on Nifty 250 (§4b)": chain("nifty250", "nifty250")}
W = [[0,0,0,0,0,0,0,0,0,1.7,5.2,8.3],[2.6,15.6,6.2,8.3,7.7,3.7,6.0,0.6,6.3,2.0,0.5,8.1],[1.1,-7.3,9.1,-2.2,-8.9,-2.4,11.6,8.4,-2.2,-0.6,1.8,-0.6],
     [-3.4,-2.2,-1.4,6.0,5.3,8.2,8.6,4.6,3.0,-2.1,10.4,4.6],[11.6,-4.6,-0.1,5.5,-0.5,6.5,8.6,4.0,2.5,1.6,-4.4,0.3],[-10.3,-9.0,7.1,2.6,4.9,4.5,0.3,-5.6,4.0,2.7,-0.4,-1.5],[-5.9,1.9,-10.6,17.2,4.6,-0.6,-3.7,8.3]]
wr = pd.Series({pd.Timestamp(2020+i, m+1, 1) + pd.offsets.MonthEnd(0): v/100 for i, row in enumerate(W) for m, v in enumerate(row)}); wr = wr[wr.index >= '2020-10-31']
def monthly(e):
    m = e.resample('M').last().pct_change().dropna(); return m[(m.index >= '2020-10-31') & (m.index <= '2026-08-31')]
def summ(m):
    g = (1 + m).cumprod(); cagr = g.iloc[-1] ** (12 / len(m)) - 1; dd = (g / g.cummax()).min() - 1
    tr = lambda n: (1 + m.iloc[-n:]).prod() ** (12 / n) - 1
    return dict(cagr=100*cagr, maxdd=100*dd, ytd=100*((1 + m[m.index >= '2026-01-31']).prod() - 1), y1=100*tr(12), y2=100*tr(24), y3=100*tr(36), vol=100*m.std()*np.sqrt(12), corr_wright=m.corr(wr))
rows = {"Wright Momentum (ex-costs)": summ(wr)}
for n, (e, p) in series.items(): rows[n] = summ(monthly(e))
print(pd.DataFrame(rows).T.round(2).to_string())
yy = pd.DataFrame({"Wright": wr.groupby(wr.index.year).apply(lambda x: 100*((1+x).prod()-1)), **{n: monthly(e).groupby(monthly(e).index.year).apply(lambda x: 100*((1+x).prod()-1)) for n, (e, p) in series.items()}})
print("\ncalendar years:"); print(yy.round(1).to_string())
print("\nNSE 500 own-refit picks:", [(y, "/".join(map(str, p))) for y, p in series["Adaptive on NSE 500 (own refit)"][1] if y >= 2020])
e = series["Adaptive on NSE 500 (own refit)"][0]; st = stats(e, "2016-01-01", end); print(f"\nNSE 500 own-refit full OOS 2016-26: {100*st['cagr']:.1f} / {st['sharpe']:.2f} / {100*st['maxdd']:.1f}", [round(stats(e,a,z)['sharpe'],2) for a,z in [("2016-01-01","2019-12-31"),("2020-01-01","2022-12-31"),("2023-01-01",end)]])
