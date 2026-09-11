"""§10 — followability: rebalance cadence x stop-check cadence for the MM stack and OM25's current configuration. Post-OOS."""
import sys, importlib.util, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
import run as MM; import windows as W
sp = importlib.util.spec_from_file_location("om25_run", "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib/run.py"); OM = importlib.util.module_from_spec(sp); sp.loader.exec_module(OM)
sw_ = importlib.util.spec_from_file_location("om25_windows", "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib/windows.py"); OMW = importlib.util.module_from_spec(sw_); sw_.loader.exec_module(OMW)
ms = pd.read_csv("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv", parse_dates=["date"]).set_index("date")["close"]; bm = ms.resample("M").last().pct_change().dropna()
def capture(p, b, a, z):
    p = p[(p.index >= a) & (p.index <= z)]; i = p.index.intersection(b.index); p, b = p[i], b[i]; up, dn = b > 0, b < 0
    return ((1 + p[up]).prod() ** (1 / up.sum()) - 1) / ((1 + b[up]).prod() ** (1 / up.sum()) - 1), ((1 + p[dn]).prod() ** (1 / dn.sum()) - 1) / ((1 + b[dn]).prod() ** (1 / dn.sum()) - 1)
MMS = dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None, dyn_n_bear=15, dyn_mode="hold", bear_buffer=20, trailing_stop=0.2, sizing="invvol", max_weight=0.10, regime_kind="roc", roc_n=31, confirm=3, sector_cap=5)
OMC = dict(universe="nifty250", score="5050", regimes=1, top_n=25, exit_buffer=10, trailing_stop=0.2, return_filter=True, lookback=252, min_obs=220, exit_cadence="same", start="2010-01-01", end=None)
rows = []
def evaluate(book, mod, base, cad, chk):
    cfg, _ = mod.run_candidate(**base, cadence=cad, stop_check=chk); rid = mod.cfg_id(cfg); e = W.equity(mod.RUNS / rid); end = str(e.index[-1].date())
    if (cad, chk) != ("monthly", "weekly"): (W.register if mod is MM else OMW.register)(cfg, rid, W.stats(e, "2010-01-01", "2015-12-31"), "10")
    so = W.stats(e, "2016-01-01", end); sw = W.stats(e, "2020-10-01", "2026-08-31"); subs = [W.stats(e, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]
    m = e.resample("M").last().pct_change().dropna(); up, dn = capture(m, bm, "2020-10-31", "2026-08-31")
    t = pd.read_csv(mod.RUNS / rid / "trades.csv", parse_dates=["date"]); t = t[t.date >= "2016-01-01"]; x = pd.read_csv(mod.RUNS / rid / "exits.csv"); yrs = (e.index[-1] - pd.Timestamp("2016-01-01")).days / 365.25
    days = t.groupby(t.date.dt.to_period("M")).date.nunique(); mon = t.date.dt.to_period("M").nunique(); n_m = int((e.index[-1].to_period("M") - pd.Period("2016-01")).n) + 1
    rows.append(dict(book=book, rebalance=cad, stop_check=chk, oos_cagr=100 * so["cagr"], oos_sharpe=so["sharpe"], oos_maxdd=100 * so["maxdd"], sub1=subs[0], sub2=subs[1], sub3=subs[2], w_cagr=100 * sw["cagr"], w_sharpe=sw["sharpe"], up=up, dn=dn,
                     trades_py=len(t) / yrs, action_days_pm=len(t.date.unique()) / n_m, months_with_action=100 * mon / n_m, max_days_month=int(days.max()), med_hold=x.hold_days.median(), stop_share=100 * x.reason.str.contains("stop", case=False).mean()))
    r = rows[-1]; print(f"{book} {cad}/{chk}: OOS {r['oos_cagr']:.1f}/{r['oos_sharpe']:.2f}/{r['oos_maxdd']:.0f} subs {subs[0]:.2f}/{subs[1]:.2f}/{subs[2]:.2f} | W {r['w_cagr']:.1f}/{r['w_sharpe']:.2f} up {up:.2f} dn {dn:.2f} | {r['trades_py']:.0f} tr/yr, {r['action_days_pm']:.1f} action days/mo (max {r['max_days_month']}), {r['months_with_action']:.0f}% months active, hold {r['med_hold']:.0f}d, stops {r['stop_share']:.0f}%", flush=True)
for cad, chk in [("monthly", "weekly"), ("monthly", "biweekly"), ("monthly", "monthly"), ("biweekly", "weekly"), ("biweekly", "biweekly"), ("weekly", "weekly")]:
    evaluate("MM stack N250", MM, MMS, cad, chk)
for cad, chk in [("monthly", "weekly"), ("monthly", "biweekly"), ("biweekly", "weekly"), ("biweekly", "biweekly")]:
    evaluate("OM25 current pick N250", OM, OMC, cad, chk)
pd.DataFrame(rows).to_csv(MM.RUNS / "10_summary.csv", index=False); print("done")
