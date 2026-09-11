"""§9c — robustness of hold-N-in-bear (true mechanism): N x bear buffer x regime, inv-vol 10%, stop 20%, Nifty 250."""
import sys, itertools, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
N250 = dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None)
REG = {"ROC31/c3": dict(regime_kind="roc", roc_n=31, confirm=3), "breadth200<30%": dict(regime_kind="strength", str_kind="breadth_ma", str_len=200, str_thresh=0.3, confirm=3)}
rows = []
for n, bb, (rn, r) in itertools.product([12, 15, 18, 20], [10, 20], REG.items()):
    cfg, _ = run_candidate(**N250, dyn_n_bear=n, dyn_mode="hold", bear_buffer=bb, trailing_stop=0.2, sizing="invvol", max_weight=0.10, **r); e = W.equity(RUNS / cfg_id(cfg)); end = str(e.index[-1].date())
    st_is = W.stats(e, "2010-01-01", "2015-12-31"); so = W.stats(e, "2016-01-01", end); W.register(cfg, cfg_id(cfg), st_is, "9c")
    subs = [W.stats(e, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]
    rows.append(dict(n=n, bear_buffer=bb, regime=rn, is_sharpe=st_is["sharpe"], oos_cagr=100 * so["cagr"], oos_sharpe=so["sharpe"], oos_maxdd=100 * so["maxdd"], sub1=subs[0], sub2=subs[1], sub3=subs[2]))
    print(n, bb, rn, f"IS {st_is['sharpe']:.2f} OOS {100*so['cagr']:.1f}/{so['sharpe']:.2f}/{100*so['maxdd']:.0f} subs {subs[0]:.2f}/{subs[1]:.2f}/{subs[2]:.2f}", flush=True)
d = pd.DataFrame(rows); d.to_csv(RUNS / "9c_summary.csv", index=False)
print(); print(d.pivot_table(index=["n"], columns=["regime", "bear_buffer"], values="oos_sharpe").round(2).to_string())
