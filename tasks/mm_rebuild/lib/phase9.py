"""§9 — Wright-review hypotheses 1 (universe) and 2 (inverse-vol sizing), judged by leg. Post-OOS; every run registered."""
import sys, pandas as pd
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
N500 = dict(universe="nse500", kind="voladj", skip=21, lookback=126, min_obs=110, start="2010-01-01", end=None)
N250 = dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None)
CR = 1e7
CELLS = [("N500 base", N500, {}), ("N500 floor 2cr/day", N500, dict(turnover_floor=2 * CR)), ("N500 floor 5cr/day", N500, dict(turnover_floor=5 * CR)),
         ("top-300 (6m)", N500, dict(universe_cap=300)), ("top-300 (12m)", {**N500, "lookback": 252, "min_obs": 219}, dict(universe_cap=300)), ("top-300 + floor 2cr", N500, dict(universe_cap=300, turnover_floor=2 * CR)),
         ("N500 inv-vol cap 10%", N500, dict(sizing="invvol", max_weight=0.10)), ("N500 inv-vol cap 10% + floor 2cr", N500, dict(sizing="invvol", max_weight=0.10, turnover_floor=2 * CR)),
         ("top-300 inv-vol cap 10%", N500, dict(universe_cap=300, sizing="invvol", max_weight=0.10)), ("N250 base", N250, {}), ("N250 inv-vol cap 10%", N250, dict(sizing="invvol", max_weight=0.10)),
         ("N250 inv-vol cap 10% + concentrate 15 + stop", N250, dict(sizing="invvol", max_weight=0.10, dyn_n_bear=15, dyn_mode="concentrate", regime_kind="roc", roc_n=31, confirm=3, trailing_stop=0.2))]
ms = pd.read_csv("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv", parse_dates=["date"]).set_index("date")["close"]; bm = ms.resample("M").last().pct_change().dropna()
LEGS = [("bull20-21", "2020-04-30", "2021-10-31"), ("bear21-22", "2021-10-31", "2022-06-30"), ("bull22-24", "2022-06-30", "2024-09-30"), ("bear24-25", "2024-09-30", "2025-02-28"), ("bull25-26", "2025-02-28", "2026-08-31")]
def capture(p, b, a=None, z=None):
    if a: p = p[(p.index >= a) & (p.index <= z)]
    i = p.index.intersection(b.index); p, b = p[i], b[i]; up, dn = b > 0, b < 0
    return ((1 + p[up]).prod() ** (1 / up.sum()) - 1) / ((1 + b[up]).prod() ** (1 / up.sum()) - 1), ((1 + p[dn]).prod() ** (1 / dn.sum()) - 1) / ((1 + b[dn]).prod() ** (1 / dn.sum()) - 1)
rows = []
for name, base, kw in CELLS:
    cfg, _ = run_candidate(**base, **kw); e = W.equity(RUNS / cfg_id(cfg)); end = str(e.index[-1].date()); m = e.resample("M").last().pct_change().dropna()
    st_is = W.stats(e, "2010-01-01", "2015-12-31"); st_o = W.stats(e, "2016-01-01", end); st_w = W.stats(e, "2020-10-01", "2026-08-31")
    if kw: W.register(cfg, cfg_id(cfg), st_is, "9")
    subs = [W.stats(e, a, z)["sharpe"] for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", end)]]
    legs = {lab: 100 * ((1 + m[(m.index > a) & (m.index <= z)]).prod() - 1) for lab, a, z in LEGS}; ucw, dcw = capture(m, bm, "2020-10-31", "2026-08-31"); ucl, dcl = capture(m, bm)
    t = pd.read_csv(RUNS / cfg_id(cfg) / "trades.csv", parse_dates=["date"]); yrs = (e.index[-1] - e.index[0]).days / 365.25
    rows.append(dict(cell=name, is_sharpe=st_is["sharpe"], is_cagr=100 * st_is["cagr"], oos_cagr=100 * st_o["cagr"], oos_sharpe=st_o["sharpe"], oos_maxdd=100 * st_o["maxdd"], sub1=subs[0], sub2=subs[1], sub3=subs[2], w_cagr=100 * st_w["cagr"], w_sharpe=st_w["sharpe"], w_maxdd=100 * st_w["maxdd"], up_w=ucw, dn_w=dcw, up_l=ucl, dn_l=dcl, trades_py=len(t) / yrs, **legs))
    print(name, f"OOS {100*st_o['cagr']:.1f}/{st_o['sharpe']:.2f}/{100*st_o['maxdd']:.0f} | W {100*st_w['cagr']:.1f}/{st_w['sharpe']:.2f}/{100*st_w['maxdd']:.0f} up {ucw:.2f} dn {dcw:.2f}", flush=True)
d = pd.DataFrame(rows); d.to_csv(RUNS / "9_summary.csv", index=False); pd.set_option("display.width", 250)
print(); print(d[["cell", "is_sharpe", "oos_cagr", "oos_sharpe", "oos_maxdd", "sub1", "sub2", "sub3", "w_cagr", "w_sharpe", "w_maxdd", "up_w", "dn_w", "up_l", "dn_l", "trades_py", "bull20-21", "bear21-22", "bull22-24", "bear24-25", "bull25-26"]].round(2).to_string(index=False))
