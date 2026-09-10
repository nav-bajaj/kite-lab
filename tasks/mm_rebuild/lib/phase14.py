"""§14 — the mid-small universe as a book in its own right (founder question, 2026-09-10). Post-OOS.

The MidSmall 400 has only ever been a BENCHMARK here (om25_rebuild §4f). This
runs the stack on it as a universe: NSE 500 members that are not Nifty 250
members at each signal date — the same point-in-time construction §4f used for
the synthetic index before 2019, which tracked the real Smallcap 250 at 0.986
daily correlation. Judged against the MidSmall 400, which is its benchmark.
"""
import sys, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W

STACK = dict(kind="voladj", skip=21, start="2010-01-01", end=None, dyn_n_bear=15, dyn_mode="hold", bear_buffer=20,
             trailing_stop=0.2, sizing="invvol", max_weight=0.10, regime_kind="roc", roc_n=31, confirm=3,
             sector_cap=5, cadence="monthly", stop_check="monthly", top_n=25, exit_buffer=20)
SUBS = [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", "2030-12-31")]
def load(p):
    d = pd.read_csv(p, parse_dates=["date"]).set_index("date")["close"].sort_index(); return d[~d.index.duplicated()]
BM = {"MidSmall 400": load("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv"),
      "Nifty 500": load("/Users/navdeep/kite-lab/data/master/benchmarks/NIFTY_500.csv")}
def capture(p, b, a, z):
    p = p[(p.index >= a) & (p.index <= z)]; i = p.index.intersection(b.index); p, b = p[i], b[i]; up, dn = b > 0, b < 0
    return (((1 + p[up]).prod() ** (1 / up.sum()) - 1) / ((1 + b[up]).prod() ** (1 / up.sum()) - 1),
            ((1 + p[dn]).prod() ** (1 / dn.sum()) - 1) / ((1 + b[dn]).prod() ** (1 / dn.sum()) - 1))
bm_m = BM["MidSmall 400"].resample("ME").last().pct_change().dropna()
rows = []
def ev(label, **kw):
    cfg, _ = run_candidate(**kw); rid = cfg_id(cfg); e = W.equity(RUNS / rid); end = str(e.index[-1].date())
    W.register(cfg, rid, W.stats(e, "2010-01-01", "2015-12-31"), "14")
    st_is = W.stats(e, "2010-01-01", "2015-12-31"); so = W.stats(e, "2016-01-01", end); s3 = W.stats(e, "2023-01-01", end)
    subs = [W.stats(e, a, z)["sharpe"] for a, z in SUBS]
    m = e.resample("ME").last().pct_change().dropna(); up, dn = capture(m, bm_m, "2020-10-01", "2026-08-31")
    t = pd.read_csv(RUNS / rid / "trades.csv", parse_dates=["date"]); yrs = (e.index[-1] - pd.Timestamp("2016-01-01")).days / 365.25
    x = pd.read_csv(RUNS / rid / "exits.csv")
    x["b"] = pd.cut(x.hold_days, [0, 30, 60, 120, 250, 10000], labels=["0-30", "31-60", "61-120", "121-250", "251+"])
    mid = x[x.b.isin(["31-60", "61-120"])]
    rows.append(dict(cell=label, is_sharpe=st_is["sharpe"], oos_cagr=100 * so["cagr"], oos_sharpe=so["sharpe"], oos_maxdd=100 * so["maxdd"],
                     sub1=subs[0], sub2=subs[1], sub3=subs[2], y3_cagr=100 * s3["cagr"], y3_sharpe=s3["sharpe"], y3_dd=100 * s3["maxdd"],
                     up=up, dn=dn, trades_py=len(t[t.date >= "2016-01-01"]) / yrs, mid_avg=100 * mid.pnl_pct.mean(), id=rid))
    print(f"{label:44s} IS {st_is['sharpe']:.2f} | OOS {100*so['cagr']:5.1f}%/{so['sharpe']:.2f}/{100*so['maxdd']:.0f}% "
          f"subs {subs[0]:.2f}/{subs[1]:.2f}/{subs[2]:.2f} | 3y {100*s3['cagr']:5.1f}%/{s3['sharpe']:.2f}/{100*s3['maxdd']:.0f}% | "
          f"vs MS400 up {up:.2f} dn {dn:.2f} | {len(t[t.date>='2016-01-01'])/yrs:.0f} tr/yr | mid-hold {100*mid.pnl_pct.mean():+.1f}%", flush=True)
print("=" * 145)
print("§14  MID-SMALL AS A UNIVERSE (NSE 500 members not in Nifty 250, point-in-time). Capture is vs the MidSmall 400.")
print("=" * 145)
ev("Nifty 250 (adopted stack) [control]", universe="nifty250", lookback=252, min_obs=219, **STACK)
ev("NSE 500 (whole panel) [control]", universe="nse500", lookback=252, min_obs=219, **STACK)
ev("MID-SMALL, 12m lookback", universe="nse500", satellite_slots=25, lookback=252, min_obs=219, **STACK)
ev("MID-SMALL, 6m lookback", universe="nse500", satellite_slots=25, lookback=126, min_obs=110, **STACK)
ev("MID-SMALL, 12m, no bear rule, no stop", universe="nse500", satellite_slots=25, lookback=252, min_obs=219,
   **{**STACK, "dyn_n_bear": 0, "trailing_stop": 0.0})
print()
for n, b in BM.items():
    s = b[(b.index >= "2016-01-01")]; r = s.pct_change().dropna(); yrs = (s.index[-1] - s.index[0]).days / 365.25
    c = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1; v = r.std() * (252 ** 0.5)
    s3 = b[b.index >= "2023-01-01"]; r3 = s3.pct_change().dropna(); y3 = (s3.index[-1] - s3.index[0]).days / 365.25
    c3 = (s3.iloc[-1] / s3.iloc[0]) ** (1 / y3) - 1
    print(f"BENCHMARK {n:16s} OOS {100*c:5.1f}%/{(c-0.05)/v:.2f}/{100*((s/s.cummax()).min()-1):.0f}%   3y {100*c3:5.1f}%")
pd.DataFrame(rows).to_csv(RUNS / "14_summary.csv", index=False); print("\ndone")
