"""§22 — chained refit for the single-book candidate: score {voladj, cr, mix40, mix50, mix60} x 6 binary switches = 320 configs, 2006 -> today, Nifty 250."""
import sys, json, itertools, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
import run as MM; import windows as W
BASE = dict(universe="nifty250", lookback=252, min_obs=220, top_n=25, cadence="monthly", exit_cadence="same", stop_check="monthly", fill_from_buffer=True, start="2006-02-01", end=None, regime_kind="roc", roc_n=31, confirm=3)
SCORES = {"voladj": dict(kind="voladj", skip=21), "cr": dict(kind="cr", skip=0), "mix40": dict(kind="mix", mix_w=0.4, skip=21), "mix50": dict(kind="mix", mix_w=0.5, skip=21), "mix60": dict(kind="mix", mix_w=0.6, skip=21)}
GRID = list(itertools.product(SCORES, [10, 20], [0.0, 0.2], ["equal", "invvol"], [0, 15], [0, 5]))
def cfg_of(k): sc, buf, stop, siz, nb, cap = k; return dict(**SCORES[sc], exit_buffer=buf, trailing_stop=stop, sizing=siz, max_weight=0.10 if siz == "invvol" else 1.0, dyn_n_bear=nb, dyn_mode="hold", bear_buffer=20 if nb else -1, sector_cap=cap)
eqs = {}
for i, k in enumerate(GRID):
    cfg, _ = MM.run_candidate(**BASE, **cfg_of(k)); rid = MM.cfg_id(cfg); eqs[k] = W.equity(MM.RUNS / rid); W.register(cfg, rid, W.stats(eqs[k], "2010-01-01", "2015-12-31"), "22"); print(i + 1, k, "ok", flush=True)
END = max(e.index[-1] for e in eqs.values()); end = str(END.date())
def chain(y0, trail, freq, margin):
    starts = pd.date_range(f"{y0}-01-01", END, freq="YS" if freq == "annual" else "QS"); segs, picks, cur = [], [], None
    for i, s in enumerate(starts):
        z = s - pd.Timedelta(days=1); a = pd.Timestamp(year=z.year - trail, month=z.month, day=1) + pd.offsets.MonthBegin(1) if freq == "quarterly" else pd.Timestamp(f"{s.year-trail}-01-01")
        sh = {k: W.stats(eqs[k], str(a.date()), str(z.date()))["sharpe"] for k in GRID}; best = max(sh, key=sh.get)
        if cur is None or sh[best] - sh[cur] > margin: cur = best
        nxt = starts[i + 1] - pd.Timedelta(days=1) if i + 1 < len(starts) else END; e = eqs[cur]
        segs.append(e[(e.index >= s) & (e.index <= nxt)].pct_change().dropna()); picks.append(cur)
    c = (1 + pd.concat(segs)).cumprod(); return c, sum(1 for i in range(1, len(picks)) if picks[i] != picks[i-1]), picks
out = {}
for label, y0, trail, freq, margin in [("5y annual", 2011, 5, "annual", 0.0), ("10y annual", 2016, 10, "annual", 0.0), ("10y quarterly", 2016, 10, "quarterly", 0.0), ("10y quarterly, margin 0.10 (adopted policy)", 2016, 10, "quarterly", 0.10)]:
    c, ch, picks = chain(y0, trail, freq, margin); so = W.stats(c, "2016-01-01", end); sw = W.stats(c, "2020-10-01", "2026-08-31"); subs = [W.stats(c, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]
    out[label] = dict(oos=f"{100*so['cagr']:.1f}% / {so['sharpe']:.2f} / {100*so['maxdd']:.0f}%", subs=[round(x, 2) for x in subs], wright=f"{100*sw['cagr']:.1f}% / {sw['sharpe']:.2f}", changes=ch, n=len(picks), picks=["/".join(map(str, p)) for p in picks], scores=[p[0] for p in picks])
    print(label, out[label]["oos"], out[label]["subs"], "W", out[label]["wright"], "changes", ch, "of", len(picks), "| scores by period:", out[label]["scores"], flush=True)
sh = pd.Series({k: W.stats(eqs[k], "2016-01-01", end)["sharpe"] for k in GRID}); hb = sh.idxmax()
print("hindsight best on OOS:", hb, f"{sh.max():.2f}", "| grid median", f"{sh.median():.2f}", "| mix50/20/0.2/invvol/15/5 rank", int((sh > sh[("mix50", 20, 0.2, "invvol", 15, 5)]).sum()) + 1, "of", len(sh), "| by score, median OOS Sharpe:", {s: round(sh[[k for k in GRID if k[0] == s]].median(), 2) for s in SCORES}, flush=True)
json.dump(out, open(MM.RUNS / "22_summary.json", "w"), indent=1); print("done", flush=True)
