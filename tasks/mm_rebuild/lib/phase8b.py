"""§8b — robustness of the two Nifty 250 winners: concentrate-N x regime x stop, both universes."""
import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
BASE = {"N250": dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None), "N500": dict(universe="nse500", kind="voladj", skip=21, lookback=126, min_obs=110, start="2010-01-01", end=None)}
REG = {"ROC31/c3": dict(regime_kind="roc", roc_n=31, confirm=3), "ROC21/c3": dict(regime_kind="roc", roc_n=21, confirm=3), "ROC42/c3": dict(regime_kind="roc", roc_n=42, confirm=3), "breadth200<30%": dict(regime_kind="strength", str_kind="breadth_ma", str_len=200, str_thresh=0.3, confirm=3)}
ms = pd.read_csv("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv", parse_dates=["date"]).set_index("date")["close"]; bm = ms.resample("M").last().pct_change().dropna()
def capture(p, b, a, z):
    p = p[(p.index >= a) & (p.index <= z)]; i = p.index.intersection(b.index); p, b = p[i], b[i]; up, dn = b > 0, b < 0
    return ((1 + p[up]).prod() ** (1 / up.sum()) - 1) / ((1 + b[up]).prod() ** (1 / up.sum()) - 1), ((1 + p[dn]).prod() ** (1 / dn.sum()) - 1) / ((1 + b[dn]).prod() ** (1 / dn.sum()) - 1)
rows = []
for uni, b in BASE.items():
    for n, (rn, r), stop in itertools.product([12, 15, 18, 20], REG.items(), [0.0, 0.2]):
        if uni == "N500" and (n not in (15, 18) or rn == "ROC42/c3"): continue
        cfg, _ = run_candidate(**b, dyn_n_bear=n, dyn_mode="concentrate", trailing_stop=stop, **r); e = W.equity(RUNS / cfg_id(cfg)); end = str(e.index[-1].date()); m = e.resample("M").last().pct_change().dropna()
        st_is = W.stats(e, "2010-01-01", "2015-12-31"); st_o = W.stats(e, "2016-01-01", end); st_w = W.stats(e, "2020-10-01", "2026-08-31"); W.register(cfg, cfg_id(cfg), st_is, "8b")
        subs = [W.stats(e, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]; up, dn = capture(m, bm, "2020-10-31", "2026-08-31")
        rows.append(dict(uni=uni, n_bear=n, regime=rn, stop=stop, is_sharpe=st_is["sharpe"], oos_cagr=100 * st_o["cagr"], oos_sharpe=st_o["sharpe"], oos_maxdd=100 * st_o["maxdd"], sub1=subs[0], sub2=subs[1], sub3=subs[2], w_cagr=100 * st_w["cagr"], w_sharpe=st_w["sharpe"], w_maxdd=100 * st_w["maxdd"], up_w=up, dn_w=dn))
        print(uni, n, rn, stop, f"OOS {100*st_o['cagr']:.1f}/{st_o['sharpe']:.2f}/{100*st_o['maxdd']:.0f} subs {subs[0]:.2f}/{subs[1]:.2f}/{subs[2]:.2f} | W {100*st_w['cagr']:.1f}/{st_w['sharpe']:.2f} up {up:.2f} dn {dn:.2f}", flush=True)
pd.DataFrame(rows).to_csv(RUNS / "8b_summary.csv", index=False); print("done")
