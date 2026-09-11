"""§17b — refit window {3,5,10}y x refit frequency {annual, quarterly} on the §17 grid (128 configs, Nifty 250)."""
import sys, json, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
import run as MM; import windows as W
BASE = dict(universe="nifty250", lookback=252, min_obs=219, top_n=25, cadence="monthly", exit_cadence="same", stop_check="monthly", start="2006-02-01", end=None, regime_kind="roc", roc_n=31, confirm=3)
GRID = list(itertools.product(["voladj", "blend"], [0, 21], [10, 20], [0.0, 0.2], ["equal", "invvol"], [0, 15], [0, 5]))
def cfg_of(k): kind, skip, buf, stop, siz, nb, sc = k; return dict(kind=kind, skip=skip, exit_buffer=buf, trailing_stop=stop, sizing=siz, max_weight=0.10 if siz == "invvol" else 1.0, dyn_n_bear=nb, dyn_mode="hold", bear_buffer=20 if nb else -1, sector_cap=sc)
eqs = {k: W.equity(MM.RUNS / MM.cfg_id(MM.run_candidate(**BASE, **cfg_of(k))[0])) for k in GRID}
END = max(e.index[-1] for e in eqs.values()); end = str(END.date())
def chain(y0, trail, freq):
    starts = pd.date_range(f"{y0}-01-01", END, freq="YS" if freq == "annual" else "QS")
    segs, picks = [], []
    for i, s in enumerate(starts):
        z = s - pd.Timedelta(days=1); a = pd.Timestamp(year=z.year - trail, month=z.month, day=1) + pd.offsets.MonthBegin(1) if freq == "quarterly" else f"{s.year-trail}-01-01"
        best = max(GRID, key=lambda k: W.stats(eqs[k], str(pd.Timestamp(a).date()), str(z.date()))["sharpe"]); e = eqs[best]
        nxt = starts[i + 1] - pd.Timedelta(days=1) if i + 1 < len(starts) else END
        segs.append(e[(e.index >= s) & (e.index <= nxt)].pct_change().dropna()); picks.append(best)
    c = (1 + pd.concat(segs)).cumprod(); ch = sum(1 for i in range(1, len(picks)) if picks[i] != picks[i-1])
    return c, ch, len(picks)
rows = []
for trail, freq, y0 in [(3, "annual", 2011), (5, "annual", 2011), (10, "annual", 2016), (3, "quarterly", 2011), (5, "quarterly", 2011), (10, "quarterly", 2016)]:
    c, ch, n = chain(y0, trail, freq); so = W.stats(c, "2016-01-01", end); sf = W.stats(c, c.index[0], end); sw = W.stats(c, "2020-10-01", "2026-08-31")
    subs = [W.stats(c, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]
    rows.append(dict(trail=trail, freq=freq, chain_from=y0, oos_cagr=100 * so["cagr"], oos_sharpe=so["sharpe"], oos_maxdd=100 * so["maxdd"], sub1=subs[0], sub2=subs[1], sub3=subs[2], full_cagr=100 * sf["cagr"], full_sharpe=sf["sharpe"], w_cagr=100 * sw["cagr"], w_sharpe=sw["sharpe"], changes=ch, refits=n))
    r = rows[-1]; print(f"{trail:2d}y {freq:9s} from {y0}: OOS {r['oos_cagr']:.1f}/{r['oos_sharpe']:.2f}/{r['oos_maxdd']:.0f} subs {subs[0]:.2f}/{subs[1]:.2f}/{subs[2]:.2f} | full {r['full_cagr']:.1f}/{r['full_sharpe']:.2f} | W {r['w_cagr']:.1f}/{r['w_sharpe']:.2f} | changes {ch}/{n}", flush=True)
pd.DataFrame(rows).to_csv(MM.RUNS / "17b_summary.csv", index=False); print("done")
