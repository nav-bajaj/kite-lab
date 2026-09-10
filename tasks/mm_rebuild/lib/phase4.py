"""§4 — OOS opened once (founder, 2026-09-10) + full walk-forward. Candidates fixed before any 2016+ statistic is computed."""
import sys, json, itertools, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
import windows as W
OOS = "2016-01-01"; SUBS = [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", "2030-12-31")]
BOOKS = {"A N250 monthly 12m": dict(universe="nifty250", lookback=252, min_obs=219), "B N500 monthly 6m": dict(universe="nse500", lookback=126, min_obs=110)}
STATIC = dict(kind="voladj", skip=21, exit_buffer=20, trailing_stop=0.0, cr_quantile=0.0)
GRID = list(itertools.product(["abs", "voladj", "blend"], [0, 21], [10, 20], [0.0, 0.2], [0.0, 0.25]))   # kind, skip, buffer, stop, cr_quantile
rows = []
for name, b in BOOKS.items():
    cfg, _ = run_candidate(**b, **STATIC, start="2010-01-01", end=None); rid = cfg_id(cfg); eq = W.equity(RUNS / rid); end = str(eq.index[-1].date())
    st_is, st_oos, st_full = W.stats(eq, "2010-01-01", "2015-12-31"), W.stats(eq, OOS, end), W.stats(eq, "2010-01-01", end); subs = [W.stats(eq, a, z)["sharpe"] for a, z in SUBS]
    t = pd.read_csv(RUNS / rid / "trades.csv", parse_dates=["date"]); t = t[t.date >= OOS]; yrs = (eq.index[-1] - pd.Timestamp(OOS)).days / 365.25
    eqs = {}
    for k, sk, buf, stop, cq in GRID:
        cw, _ = run_candidate(**b, kind=k, skip=sk, exit_buffer=buf, trailing_stop=stop, cr_quantile=cq, start="2006-02-01", end=None); eqs[(k, sk, buf, stop, cq)] = W.equity(RUNS / cfg_id(cw))
        print(name, k, sk, buf, stop, cq, "ok", flush=True)
    wf = {}
    for trail in (5, 10):
        chain, picks = [], []
        for y in range(2016, int(end[:4]) + 1):
            a, z = f"{y-trail}-01-01", f"{y-1}-12-31"; best = max(eqs, key=lambda kk: W.stats(eqs[kk], a, z)["sharpe"]); e = eqs[best]
            chain.append(e[(e.index >= f"{y}-01-01") & (e.index <= f"{y}-12-31")].pct_change().dropna()); picks.append((y, best))
        c = (1 + pd.concat(chain)).cumprod(); s = W.stats(c, OOS, end); wf[trail] = dict(sharpe=s["sharpe"], cagr=s["cagr"], maxdd=s["maxdd"], subs=[W.stats(c, a, z)["sharpe"] for a, z in SUBS], picks=picks, changes=sum(1 for i in range(1, len(picks)) if picks[i][1] != picks[i-1][1]))
    hb = max(eqs, key=lambda kk: W.stats(eqs[kk], OOS, end)["sharpe"]); hs = W.stats(eqs[hb], OOS, end)
    rows.append(dict(cand=name, id=rid, is_cagr=st_is["cagr"], is_sharpe=st_is["sharpe"], oos_cagr=st_oos["cagr"], oos_sharpe=st_oos["sharpe"], oos_maxdd=st_oos["maxdd"], sub1=subs[0], sub2=subs[1], sub3=subs[2], full_cagr=st_full["cagr"],
                     trades_py=len(t) / yrs, turnover=t.notional.sum() / (eq[eq.index >= OOS].mean() * 1e6) / yrs / 2,
                     wf5_sharpe=wf[5]["sharpe"], wf5_cagr=wf[5]["cagr"], wf5_maxdd=wf[5]["maxdd"], wf5_subs=json.dumps(wf[5]["subs"]), wf5_changes=wf[5]["changes"], wf5_picks=json.dumps(wf[5]["picks"]),
                     wf10_sharpe=wf[10]["sharpe"], wf10_cagr=wf[10]["cagr"], wf10_maxdd=wf[10]["maxdd"], wf10_subs=json.dumps(wf[10]["subs"]), wf10_changes=wf[10]["changes"], wf10_picks=json.dumps(wf[10]["picks"]),
                     hindsight_best=json.dumps(hb), hindsight_sharpe=hs["sharpe"], hindsight_cagr=hs["cagr"], end=end))
    print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items() if "picks" not in k and k != "id"}, flush=True)
pd.DataFrame(rows).to_csv(RUNS / "4_summary.csv", index=False); print("done", flush=True)
