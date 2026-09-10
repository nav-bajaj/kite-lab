"""§8 — bear-month behaviour: every exposure device on the MM base, judged by leg. Post-OOS by construction; every run registered."""
import sys, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
BASE = {"N250": dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None), "N500": dict(universe="nse500", kind="voladj", skip=21, lookback=126, min_obs=110, start="2010-01-01", end=None)}
ROC = dict(regime_kind="roc", roc_n=31, confirm=3); BR = dict(regime_kind="strength", str_kind="breadth_ma", str_len=200, str_thresh=0.3, confirm=3)
DEV = {"base": {}, "stop 20%": dict(trailing_stop=0.2),
       "ROC overlay 50%": dict(overlay=True, bear_exposure=0.5, reenter_on_flip=True, **ROC), "ROC overlay 0%": dict(overlay=True, bear_exposure=0.0, reenter_on_flip=True, **ROC),
       "breadth overlay 50%": dict(overlay=True, bear_exposure=0.5, reenter_on_flip=True, **BR), "breadth overlay 0%": dict(overlay=True, bear_exposure=0.0, reenter_on_flip=True, **BR),
       "dyn N 18 lever (ROC)": dict(dyn_n_bear=18, dyn_mode="lever", **ROC), "dyn N 15 lever (ROC)": dict(dyn_n_bear=15, dyn_mode="lever", **ROC),
       "dyn N 15 concentrate (ROC)": dict(dyn_n_bear=15, dyn_mode="concentrate", **ROC), "dyn N 15 lever (breadth)": dict(dyn_n_bear=15, dyn_mode="lever", **BR),
       "vol target 20%": dict(vol_target=0.20), "vol target 15%": dict(vol_target=0.15), "vol target 15% + stop 20%": dict(vol_target=0.15, trailing_stop=0.2)}
ms = pd.read_csv("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv", parse_dates=["date"]).set_index("date")["close"]; bm = ms.resample("M").last().pct_change().dropna()
LEGS = [("bull20-21", "2020-04-30", "2021-10-31"), ("bear21-22", "2021-10-31", "2022-06-30"), ("bull22-24", "2022-06-30", "2024-09-30"), ("bear24-25", "2024-09-30", "2025-02-28"), ("bull25-26", "2025-02-28", "2026-08-31")]
def capture(p, b, a=None, z=None):
    if a: p = p[(p.index >= a) & (p.index <= z)]
    i = p.index.intersection(b.index); p, b = p[i], b[i]; up, dn = b > 0, b < 0
    return ((1 + p[up]).prod() ** (1 / up.sum()) - 1) / ((1 + b[up]).prod() ** (1 / up.sum()) - 1), ((1 + p[dn]).prod() ** (1 / dn.sum()) - 1) / ((1 + b[dn]).prod() ** (1 / dn.sum()) - 1)
rows = []
for uni, b in BASE.items():
    for dname, kw in DEV.items():
        cfg, _ = run_candidate(**b, **kw); e = W.equity(RUNS / cfg_id(cfg)); end = str(e.index[-1].date()); m = e.resample("M").last().pct_change().dropna()
        st_is = W.stats(e, "2010-01-01", "2015-12-31"); st_o = W.stats(e, "2016-01-01", end); st_w = W.stats(e, "2020-10-01", "2026-08-31")
        if dname != "base": W.register(cfg, cfg_id(cfg), st_is, "8")
        legs = {lab: 100 * ((1 + m[(m.index > a) & (m.index <= z)]).prod() - 1) for lab, a, z in LEGS}
        ucw, dcw = capture(m, bm, "2020-10-31", "2026-08-31"); ucl, dcl = capture(m, bm)
        eqd = pd.read_csv(RUNS / cfg_id(cfg) / "equity.csv", parse_dates=["date"]).set_index("date"); exp = 100 * (1 - eqd["cash_pct"][eqd.index >= "2016-01-01"]).mean()
        rows.append(dict(uni=uni, device=dname, is_sharpe=st_is["sharpe"], is_cagr=100 * st_is["cagr"], oos_cagr=100 * st_o["cagr"], oos_sharpe=st_o["sharpe"], oos_maxdd=100 * st_o["maxdd"], w_cagr=100 * st_w["cagr"], w_sharpe=st_w["sharpe"], w_maxdd=100 * st_w["maxdd"], up_w=ucw, dn_w=dcw, up_l=ucl, dn_l=dcl, avg_exp=exp, **legs))
        print(uni, dname, f"OOS {100*st_o['cagr']:.1f}/{st_o['sharpe']:.2f}/{100*st_o['maxdd']:.0f} | Wright-window up {ucw:.2f} dn {dcw:.2f} | legs", {k: round(v) for k, v in legs.items()}, flush=True)
d = pd.DataFrame(rows); d.to_csv(RUNS / "8_summary.csv", index=False); print("done")
