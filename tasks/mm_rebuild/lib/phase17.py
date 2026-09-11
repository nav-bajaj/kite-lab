"""§17 — full chained refit for MM (the OM25 §4b/§4d design): 7 binary design choices = 128 configs, each run 2006-02-01 -> today on Nifty 250;
each January the best trailing-window Sharpe config is traded for the year; chained 2011 -> today (5y) and 2016 -> today (10y)."""
import sys, json, itertools, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
import run as MM; import windows as W
BASE = dict(universe="nifty250", lookback=252, min_obs=219, top_n=25, cadence="monthly", exit_cadence="same", stop_check="monthly", start="2006-02-01", end=None, regime_kind="roc", roc_n=31, confirm=3)
GRID = list(itertools.product(["voladj", "blend"], [0, 21], [10, 20], [0.0, 0.2], ["equal", "invvol"], [0, 15], [0, 5]))   # kind, skip, buffer, stop, sizing, bear N, sector cap
def cfg_of(k): kind, skip, buf, stop, siz, nb, sc = k; return dict(kind=kind, skip=skip, exit_buffer=buf, trailing_stop=stop, sizing=siz, max_weight=0.10 if siz == "invvol" else 1.0, dyn_n_bear=nb, dyn_mode="hold", bear_buffer=20 if nb else -1, sector_cap=sc)
eqs = {}
for i, k in enumerate(GRID):
    cfg, _ = MM.run_candidate(**BASE, **cfg_of(k)); rid = MM.cfg_id(cfg); eqs[k] = W.equity(MM.RUNS / rid)
    W.register(cfg, rid, W.stats(eqs[k], "2010-01-01", "2015-12-31"), "17")
    print(i + 1, k, "ok", flush=True)
END = max(e.index[-1] for e in eqs.values()); end = str(END.date())
def chain(y0, trail):
    segs, picks = [], []
    for y in range(y0, END.year + 1):
        a, z = f"{y-trail}-01-01", f"{y-1}-12-31"; best = max(GRID, key=lambda k: W.stats(eqs[k], a, z)["sharpe"]); e = eqs[best]
        segs.append(e[(e.index >= f"{y}-01-01") & (e.index <= f"{y}-12-31")].pct_change().dropna()); picks.append((y, best))
    return (1 + pd.concat(segs)).cumprod(), picks
out = {}
for label, y0, trail in [("5y refit, chained 2011->", 2011, 5), ("10y refit, chained 2016->", 2016, 10), ("5y refit, chained 2016->", 2016, 5)]:
    c, picks = chain(y0, trail); so = W.stats(c, "2016-01-01", end); sf = W.stats(c, c.index[0], end)
    subs = [W.stats(c, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]; sw = W.stats(c, "2020-10-01", "2026-08-31")
    out[label] = dict(oos=f"{100*so['cagr']:.1f}% / {so['sharpe']:.2f} / {100*so['maxdd']:.0f}%", full=f"{c.index[0].year}-26 {100*sf['cagr']:.1f}% / {sf['sharpe']:.2f} / {100*sf['maxdd']:.0f}%", subs=[round(s, 2) for s in subs], wright=f"{100*sw['cagr']:.1f}% / {sw['sharpe']:.2f}", changes=sum(1 for i in range(1, len(picks)) if picks[i][1] != picks[i-1][1]), picks=[(y, "/".join(map(str, k))) for y, k in picks])
    print(label, out[label]["oos"], "subs", out[label]["subs"], "| full", out[label]["full"], "| W", out[label]["wright"], "| changes", out[label]["changes"], flush=True); print("   picks:", out[label]["picks"], flush=True)
static = eqs[("voladj", 21, 20, 0.2, "invvol", 15, 5)]; so = W.stats(static, "2016-01-01", end); print("static adopted stack (2006 start) OOS:", f"{100*so['cagr']:.1f}% / {so['sharpe']:.2f} / {100*so['maxdd']:.0f}%")
hb = max(GRID, key=lambda k: W.stats(eqs[k], "2016-01-01", end)["sharpe"]); hs = W.stats(eqs[hb], "2016-01-01", end); print("hindsight best single config on OOS:", hb, f"{100*hs['cagr']:.1f}% / {hs['sharpe']:.2f} / {100*hs['maxdd']:.0f}%")
sh = pd.Series({k: W.stats(eqs[k], "2016-01-01", end)["sharpe"] for k in GRID}); print("grid OOS Sharpe: min", round(sh.min(), 2), "median", round(sh.median(), 2), "max", round(sh.max(), 2), "| adopted stack rank", int((sh > sh[("voladj", 21, 20, 0.2, "invvol", 15, 5)]).sum()) + 1, "of", len(sh))
json.dump(out, open(MM.RUNS / "17_summary.json", "w"), indent=1); print("done", flush=True)
