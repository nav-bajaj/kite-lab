"""§3 — walk-forward, the verdict.

Top 5 candidates from §2 by OOS edge (Sharpe minus their own exposure-matched
control), each walked forward 2014-2026: trailing 8-year fit, apply one year,
chain. Two candidates sharing a (signal, shape) family walk identically, so
families are de-duplicated and the next-best families fill the slate to five.

What the trailing fit chooses each year: the direction window (and, for D3, the
lo/hi quantile pair), plus the level cut / quantile levels recomputed on the
fit window. That is the honest version of the question — standing in 2013 you
do not know that 63 sessions is the window that works.
"""
from __future__ import annotations

import ast
import os

import numpy as np
import pandas as pd

import harness as H

D3_QS = [(0.10, 0.90), (0.20, 0.80), (0.30, 0.70), (0.40, 0.60)]


def family_cells(shape):
    if shape == "D3_continuous":
        return [(w, lo, hi) for w in H.WINDOWS for (lo, hi) in D3_QS]
    return [(w,) for w in H.WINDOWS]


def make_grid_fn(sig, signal, shape):
    def fn(cell, fit_index):
        if shape == "D3_continuous":
            w, lo, hi = cell
            return H.regime_series(signal, w, shape, sig=sig, fit_index=fit_index,
                                   lo_q=lo, hi_q=hi)
        return H.regime_series(signal, cell[0], shape, sig=sig,
                               fit_index=fit_index, top_weight=0.5)
    return fn


def main():
    os.chdir(H.REPO)
    tr = H.load_tape("trend")
    pan = H.load_panels(tr)
    sig = H.raw_signals()
    g = pd.read_csv(f"{H.CACHE}/grid.csv")
    g = g[g.hyst == 0].sort_values("oos_edge", ascending=False)

    fams, seen = [], set()
    for _, r in g.iterrows():
        k = (r.signal, r["shape"])
        if k in seen:
            continue
        seen.add(k)
        fams.append(dict(signal=r.signal, shape=r["shape"],
                         best_window=int(r.window),
                         static_oos_sharpe=r.oos_sharpe,
                         static_oos_edge=r.oos_edge,
                         static_oos_cagr=r.oos_cagr, static_oos_maxdd=r.oos_maxdd))
        if len(fams) == 5:
            break
    print("families walked:", [(f["signal"], f["shape"]) for f in fams], flush=True)

    out, picks_all = [], {}
    # always-on, walked the same way
    ao = H.walk_forward(lambda c, fi: pd.Series(1.0, index=sig.index), [(0,)],
                        tr, pan, sig, mode="always")
    print(f"always-on WF  CAGR {ao['cagr']:.1%}  DD {ao['maxdd']:.1%}  "
          f"Sharpe {ao['sharpe']:.2f}", flush=True)
    out.append(dict(candidate="always on (control)", signal="-", shape="-",
                    params=0, wf_cagr=ao["cagr"], wf_maxdd=ao["maxdd"],
                    wf_sharpe=ao["sharpe"], ctl_sharpe=np.nan,
                    static_oos_sharpe=np.nan, distinct_cells=0, chg_yr=0.0,
                    cash=0.0))
    picks_all["always on (control)"] = ao["picks"]

    for f in fams:
        fn = make_grid_fn(sig, f["signal"], f["shape"])
        cells = family_cells(f["shape"])
        r = H.walk_forward(fn, cells, tr, pan, sig, mode="rule")
        c = H.walk_forward(fn, cells, tr, pan, sig, mode="control")
        name = f"{f['signal']}/{f['shape']}"
        # allocation churn of the walked rule: re-derive the chosen cell per year
        chg, cash = [], []
        for _, p in r["picks"].iterrows():
            cell = ast.literal_eval(p.cell) if isinstance(p.cell, str) else p.cell
            fit_cal = H.cal(f"{int(p.year) - 8}-01-01", f"{int(p.year) - 1}-12-31")
            w = fn(cell, fit_cal)
            yc = H.cal(f"{int(p.year)}-01-01", f"{int(p.year)}-12-31")
            chg.append(H.changes_per_year(w, yc))
            cash.append(H.time_in_cash(w, yc))
        row = dict(candidate=name, signal=f["signal"], shape=f["shape"],
                   params=H.PARAM_COUNT[f["shape"]],
                   wf_cagr=r["cagr"], wf_maxdd=r["maxdd"], wf_sharpe=r["sharpe"],
                   ctl_sharpe=c["sharpe"], ctl_cagr=c["cagr"], ctl_maxdd=c["maxdd"],
                   static_oos_sharpe=f["static_oos_sharpe"],
                   static_oos_edge=f["static_oos_edge"],
                   distinct_cells=int(r["picks"].cell.nunique()),
                   chg_yr=float(np.nanmean(chg)), cash=float(np.nanmean(cash)))
        row["g1"] = row["wf_sharpe"] - ao["sharpe"]
        row["g2"] = row["wf_sharpe"] - row["ctl_sharpe"]
        row["g3"] = abs(row["wf_sharpe"] - row["static_oos_sharpe"])
        out.append(row)
        picks_all[name] = r["picks"]
        print(f"{name:<32} WF {r['cagr']:>6.1%} {r['maxdd']:>6.1%} {r['sharpe']:>5.2f}"
              f"  ctl {c['sharpe']:>5.2f}  static {f['static_oos_sharpe']:>5.2f}"
              f"  cells {row['distinct_cells']}", flush=True)

    o = pd.DataFrame(out)
    o.to_csv(f"{H.CACHE}/wf.csv", index=False)
    pd.concat([p.assign(candidate=k) for k, p in picks_all.items()]
              ).to_csv(f"{H.CACHE}/wf_picks.csv", index=False)
    print("\n", o.to_string(index=False))


if __name__ == "__main__":
    main()
