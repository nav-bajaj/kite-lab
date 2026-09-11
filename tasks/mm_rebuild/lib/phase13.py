"""§13 — two founder questions, 2026-09-10. Post-OOS by construction.

A. The stop and the medium-term hold. §12 showed the 31-120 day buckets are
   negative only because of stop exits (rank exits in those buckets average
   +1.0 to +1.3%). Sweep the stop level, including off, on the adopted stack.

B. Multi-cap slots. Reserve K of the 25 slots for the strongest names outside
   the Nifty 250 but inside the NSE 500 (the 251-500 band), majority core.
   K = 0 is the same stack run on the NSE 500 panel with the core mask, which
   is the control for the mechanism rather than for the universe.
"""
import sys, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W

STACK = dict(kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None,
             dyn_n_bear=15, dyn_mode="hold", bear_buffer=20, sizing="invvol", max_weight=0.10,
             regime_kind="roc", roc_n=31, confirm=3, sector_cap=5, cadence="monthly", stop_check="monthly")
SUBS = [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", "2030-12-31")]
ms = pd.read_csv("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv", parse_dates=["date"]).set_index("date")["close"]
bm = ms.resample("ME").last().pct_change().dropna()

def capture(p, b, a, z):
    p = p[(p.index >= a) & (p.index <= z)]; i = p.index.intersection(b.index); p, b = p[i], b[i]; up, dn = b > 0, b < 0
    return (((1 + p[up]).prod() ** (1 / up.sum()) - 1) / ((1 + b[up]).prod() ** (1 / up.sum()) - 1),
            ((1 + p[dn]).prod() ** (1 / dn.sum()) - 1) / ((1 + b[dn]).prod() ** (1 / dn.sum()) - 1))

def evaluate(label, phase, **kw):
    cfg, _ = run_candidate(**kw); rid = cfg_id(cfg); e = W.equity(RUNS / rid); end = str(e.index[-1].date())
    st_is = W.stats(e, "2010-01-01", "2015-12-31"); so = W.stats(e, "2016-01-01", end); s3 = W.stats(e, "2023-01-01", end)
    W.register(cfg, rid, st_is, phase)
    subs = [W.stats(e, a, z)["sharpe"] for a, z in SUBS]
    m = e.resample("ME").last().pct_change().dropna(); up, dn = capture(m, bm, "2020-10-01", "2026-08-31")
    x = pd.read_csv(RUNS / rid / "exits.csv"); t = pd.read_csv(RUNS / rid / "trades.csv", parse_dates=["date"])
    yrs = (e.index[-1] - pd.Timestamp("2016-01-01")).days / 365.25
    x["bucket"] = pd.cut(x.hold_days, [0, 30, 60, 120, 250, 10000], labels=["0-30", "31-60", "61-120", "121-250", "251+"])
    mid = x[x.bucket.isin(["31-60", "61-120"])]
    row = dict(cell=label, is_sharpe=st_is["sharpe"], oos_cagr=100 * so["cagr"], oos_sharpe=so["sharpe"], oos_maxdd=100 * so["maxdd"],
               sub1=subs[0], sub2=subs[1], sub3=subs[2], y3_cagr=100 * s3["cagr"], y3_sharpe=s3["sharpe"],
               up=up, dn=dn, trades_py=len(t[t.date >= "2016-01-01"]) / yrs,
               mid_avg=100 * mid.pnl_pct.mean(), mid_share=100 * len(mid) / len(x),
               stop_share=100 * x.reason.str.contains("stop", case=False).mean(), id=rid)
    print(f"{label:38s} IS {st_is['sharpe']:.2f} | OOS {100*so['cagr']:5.1f}%/{so['sharpe']:.2f}/{100*so['maxdd']:.0f}% "
          f"subs {subs[0]:.2f}/{subs[1]:.2f}/{subs[2]:.2f} | 3y {100*s3['cagr']:5.1f}%/{s3['sharpe']:.2f} | "
          f"up {up:.2f} dn {dn:.2f} | mid-hold avg {100*mid.pnl_pct.mean():+.1f}% | {len(t[t.date>='2016-01-01'])/yrs:.0f} tr/yr", flush=True)
    return row

print("=" * 130)
print("A. STOP LEVEL — does the 20% stop pay for the medium-term losses it causes?  (Nifty 250, adopted stack otherwise)")
print("=" * 130)
A = [evaluate(f"stop {'off' if s == 0 else f'{int(100*s)}%'}", "13a", universe="nifty250", trailing_stop=s, **STACK)
     for s in [0.0, 0.15, 0.20, 0.25, 0.30]]
pd.DataFrame(A).to_csv(RUNS / "13a_summary.csv", index=False)

print()
print("=" * 130)
print("B. MULTI-CAP SLOTS — K of 25 reserved for the strongest names outside the Nifty 250, inside the NSE 500")
print("=" * 130)
B = [evaluate("Nifty 250 only (the adopted stack)", "13b", universe="nifty250", trailing_stop=0.2, **STACK)]
for k in [0, 3, 5, 8]:
    lab = "NSE 500 panel, no quota (control)" if k == 0 else f"multi-cap: {25-k} core + {k} satellite"
    B.append(evaluate(lab, "13b", universe="nse500", trailing_stop=0.2, satellite_slots=k, **STACK))
pd.DataFrame(B).to_csv(RUNS / "13b_summary.csv", index=False)
print("\ndone")
