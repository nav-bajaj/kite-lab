"""§11 — rebalance day of month, both books, everything on one day a month. Post-OOS."""
import sys, importlib.util, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
import run as MM; import windows as W
sp = importlib.util.spec_from_file_location("om25_run", "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib/run.py"); OM = importlib.util.module_from_spec(sp); sp.loader.exec_module(OM)
sw_ = importlib.util.spec_from_file_location("om25_windows", "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib/windows.py"); OMW = importlib.util.module_from_spec(sw_); sw_.loader.exec_module(OMW)
MMS = dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None, dyn_n_bear=15, dyn_mode="hold", bear_buffer=20, trailing_stop=0.2, sizing="invvol", max_weight=0.10, regime_kind="roc", roc_n=31, confirm=3, sector_cap=5, cadence="monthly", stop_check="monthly")
OMC = dict(universe="nifty250", score="5050", regimes=1, top_n=25, exit_buffer=10, trailing_stop=0.2, return_filter=True, lookback=252, min_obs=220, exit_cadence="same", start="2010-01-01", end=None, cadence="monthly", stop_check="monthly")
rows = []
for book, mod, base, reg in [("MM stack", MM, MMS, W.register), ("OM25 pick", OM, OMC, OMW.register)]:
    for day in [1, 5, 10, 15, 20, 25]:
        cfg, _ = mod.run_candidate(**base, rebalance_day=day); rid = mod.cfg_id(cfg); e = W.equity(mod.RUNS / rid); end = str(e.index[-1].date())
        st_is = W.stats(e, "2010-01-01", "2015-12-31"); reg(cfg, rid, st_is, "11") if not (day == 1 and book == "MM stack") else None
        so = W.stats(e, "2016-01-01", end); sw = W.stats(e, "2020-10-01", "2026-08-31"); subs = [W.stats(e, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]
        sf = W.stats(e, "2010-01-01", end)
        rows.append(dict(book=book, day=day, is_sharpe=st_is["sharpe"], is_cagr=100 * st_is["cagr"], oos_cagr=100 * so["cagr"], oos_sharpe=so["sharpe"], oos_maxdd=100 * so["maxdd"], sub1=subs[0], sub2=subs[1], sub3=subs[2], w_cagr=100 * sw["cagr"], w_sharpe=sw["sharpe"], full_cagr=100 * sf["cagr"], full_sharpe=sf["sharpe"]))
        r = rows[-1]; print(f"{book} day {day:2d}: IS {r['is_cagr']:.1f}/{r['is_sharpe']:.2f} | OOS {r['oos_cagr']:.1f}/{r['oos_sharpe']:.2f}/{r['oos_maxdd']:.0f} subs {subs[0]:.2f}/{subs[1]:.2f}/{subs[2]:.2f} | W {r['w_cagr']:.1f}/{r['w_sharpe']:.2f} | 2010-26 {r['full_cagr']:.1f}/{r['full_sharpe']:.2f}", flush=True)
pd.DataFrame(rows).to_csv(MM.RUNS / "11_summary.csv", index=False); print("done")
