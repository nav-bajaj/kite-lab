"""§4 — OOS opened once (founder, 2026-09-10). Candidates fixed before any 2016+ statistic is computed."""
import sys, json, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats
IS = ("2010-01-01", "2015-12-31"); OOS_START = "2016-01-01"
SUBS = [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", "2030-12-31")]
BASE = dict(score="cr", regimes=1, top_n=25, exit_buffer=20, return_filter=True, exit_cadence="same")
OVL = dict(overlay=True, regime_kind="strength", str_kind="breadth_ma", str_len=200, str_thresh=0.3, str_mode="abs", confirm=3, bear_exposure=0.0, reenter_on_flip=True)
def lb(n): return dict(lookback=n, min_obs=int(round(0.87 * n)))
CANDS = {
    "A N250 monthly lb252":            dict(universe="nifty250", cadence="monthly",  **lb(252)),
    "B N250 biweekly lb252":           dict(universe="nifty250", cadence="biweekly", **lb(252)),
    "C N500 monthly lb126":            dict(universe="nse500",   cadence="monthly",  **lb(126)),
    "D N500 biweekly lb126":           dict(universe="nse500",   cadence="biweekly", **lb(126)),
    "E N250 monthly lb252 + breadth":  dict(universe="nifty250", cadence="monthly",  **lb(252), **OVL),
}
WF_LB = [63, 126, 189, 252]          # refit set: inside the 12-month cap
def turnover(rid, a, b):
    t = pd.read_csv(RUNS / rid / "trades.csv"); dc = [c for c in t.columns if "date" in c.lower()][0]
    t[dc] = pd.to_datetime(t[dc]); t = t[(t[dc] >= a) & (t[dc] <= b)]
    eq = equity(RUNS / rid); eq = eq[(eq.index >= a) & (eq.index <= b)]
    vc = [c for c in t.columns if "value" in c.lower() or "notional" in c.lower()]
    gross = t[vc[0]].abs().sum() if vc else np.nan
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return gross / eq.mean() / yrs if vc else np.nan, len(t) / yrs
rows = []; wf_rows = []
for name, c in CANDS.items():
    cfg, _ = run_candidate(**BASE, **c, start="2010-01-01", end=None); rid = cfg_id(cfg)
    eq = equity(RUNS / rid); end = str(eq.index[-1].date())
    st_is = stats(eq, *IS); st_oos = stats(eq, OOS_START, end); st_full = stats(eq, "2010-01-01", end)
    subs = [stats(eq, a, b) for a, b in SUBS]
    to, ntr = turnover(rid, OOS_START, end)
    # walk-forward: each OOS year, pick the lookback with the best Sharpe on the trailing ten years (2006-start runs), trade it that year
    wf_eq = {}
    for n in WF_LB:
        cw, _ = run_candidate(**BASE, **{k: v for k, v in c.items() if k not in ("lookback", "min_obs")}, **lb(n), start="2006-02-01", end=None)
        wf_eq[n] = equity(RUNS / cfg_id(cw))
    chain = []; picks = []
    for y in range(2016, int(end[:4]) + 1):
        a, b = f"{y-10}-01-01", f"{y-1}-12-31"
        best = max(WF_LB, key=lambda n: stats(wf_eq[n], a, b)["sharpe"])
        seg = wf_eq[best][(wf_eq[best].index >= f"{y}-01-01") & (wf_eq[best].index <= f"{y}-12-31")].pct_change().dropna()
        chain.append(seg); picks.append((y, best))
    wf = (1 + pd.concat(chain)).cumprod(); st_wf = stats(wf, OOS_START, end)
    rows.append(dict(cand=name, id=rid, is_cagr=st_is["cagr"], is_sharpe=st_is["sharpe"], is_maxdd=st_is["maxdd"],
                     oos_cagr=st_oos["cagr"], oos_sharpe=st_oos["sharpe"], oos_maxdd=st_oos["maxdd"],
                     sub1=subs[0]["sharpe"], sub2=subs[1]["sharpe"], sub3=subs[2]["sharpe"],
                     full_cagr=st_full["cagr"], wf_sharpe=st_wf["sharpe"], wf_cagr=st_wf["cagr"], wf_picks=json.dumps(picks),
                     turnover=to, trades_py=ntr, end=end))
    print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items() if k not in ("wf_picks", "id")}, flush=True)
pd.DataFrame(rows).to_csv(RUNS / "4_summary.csv", index=False); print("done", flush=True)
