"""§2 — the candidate grid, IS 2006-2015 / OOS 2016-2026.

5 signals x 4 windows x 3 shapes = 60 candidates, each with its own
exposure-matched control on both spans. Every fitted constant (the D1 level
cut, the D3 lo/hi quantiles) is taken from the IS window only, so the OOS
column carries no look-ahead. D4 hysteresis is then applied to the top 3 by
OOS edge, N in {5, 10, 21} -> 9 further trials.
"""
from __future__ import annotations

import os

import pandas as pd

import harness as H

IS_LO, IS_HI = "2006-01-01", "2015-12-31"
OOS_LO = "2016-01-01"
LO_Q, HI_Q = 0.20, 0.80


def make_w(sig, signal, window, shape, fit_index, hyst=0):
    return H.regime_series(signal, window, shape, sig=sig, fit_index=fit_index,
                           lo_q=LO_Q, hi_q=HI_Q, top_weight=0.5, hysteresis=hyst)


def main():
    os.chdir(H.REPO)
    tr = H.load_tape("trend")
    pan = H.load_panels(tr)
    sig = H.raw_signals()
    cal_is, cal_oos = H.cal(IS_LO, IS_HI), H.cal(OOS_LO)
    cc = {}

    rows = []
    for signal in H.SIGNALS:
        for window in H.WINDOWS:
            for shape in H.SHAPES:
                w = make_w(sig, signal, window, shape, cal_is)
                a = H.evaluate(w, tr, pan, cal_is, control_cache=cc)
                b = H.evaluate(w, tr, pan, cal_oos, control_cache=cc)
                rows.append(dict(signal=signal, window=window, shape=shape,
                                 hyst=0, params=H.PARAM_COUNT[shape],
                                 **{f"is_{k}": v for k, v in a.items()},
                                 **{f"oos_{k}": v for k, v in b.items()}))
                print(f"  {signal:<14}{window:>4} {shape:<15} "
                      f"IS {a['sharpe']:>5.2f}/{a['c_sharpe']:>5.2f}  "
                      f"OOS {b['sharpe']:>5.2f}/{b['c_sharpe']:>5.2f}", flush=True)
    g = pd.DataFrame(rows)

    top3 = g.sort_values("oos_edge", ascending=False).head(3)
    hrows = []
    for _, r in top3.iterrows():
        for n in (5, 10, 21):
            w = make_w(sig, r.signal, int(r.window), r["shape"], cal_is, hyst=n)
            a = H.evaluate(w, tr, pan, cal_is, control_cache=cc)
            b = H.evaluate(w, tr, pan, cal_oos, control_cache=cc)
            hrows.append(dict(signal=r.signal, window=int(r.window),
                              shape=r["shape"], hyst=n,
                              params=H.PARAM_COUNT[r["shape"]] + 1,
                              **{f"is_{k}": v for k, v in a.items()},
                              **{f"oos_{k}": v for k, v in b.items()}))
            print(f"  HYST{n:>3} {r.signal:<14}{r.window:>4} {r['shape']:<15} "
                  f"OOS {b['sharpe']:>5.2f}/{b['c_sharpe']:>5.2f}", flush=True)
    allg = pd.concat([g, pd.DataFrame(hrows)], ignore_index=True)

    # always-on reference on both spans
    ref = []
    for lab, c in (("is", cal_is), ("oos", cal_oos)):
        sub = tr[(tr.entry_date >= c[0]) & (tr.entry_date <= c[-1])]
        r = H.run_book(sub, pan, c, 1.0)
        ref.append(dict(span=lab, cagr=r["cagr"], maxdd=r["maxdd"],
                        sharpe=r["sharpe"], taken=r["taken"], expo=r["exposure"]))
    refd = pd.DataFrame(ref)
    refd.to_csv(f"{H.CACHE}/grid_alwayson.csv", index=False)
    allg.to_csv(f"{H.CACHE}/grid.csv", index=False)

    n = len(allg)
    sd_e, med_e = allg.oos_edge.std(ddof=1), allg.oos_edge.median()
    sd_s, med_s = allg.oos_sharpe.std(ddof=1), allg.oos_sharpe.median()
    ao = float(refd.loc[refd.span == "oos", "sharpe"].iloc[0])
    print("\n=== §2 summary ===")
    print(f"trials                       {n}")
    print(f"always-on OOS Sharpe         {ao:.2f}")
    print(f"grid median OOS Sharpe       {med_s:.2f}   sd {sd_s:.3f}")
    print(f"grid median OOS edge         {med_e:.2f}   sd {sd_e:.3f}")
    print(f"best OOS Sharpe              {allg.oos_sharpe.max():.2f}")
    print(f"best OOS edge                {allg.oos_edge.max():.2f}")
    print(f"Gumbel E[max] edge           {med_e + H.gumbel_expected_max(n, sd_e):.2f}")
    print(f"Gumbel E[max] sharpe         {med_s + H.gumbel_expected_max(n, sd_s):.2f}")
    print(f"beating always-on OOS        {int((allg.oos_sharpe > ao).sum())} of {n}")
    print(f"beating own control OOS      {int((allg.oos_edge > 0).sum())} of {n}")
    print("\ntop 10 by OOS edge:")
    cols = ["signal", "window", "shape", "hyst", "is_sharpe", "is_c_sharpe",
            "oos_cagr", "oos_maxdd", "oos_sharpe", "oos_c_sharpe", "oos_edge",
            "oos_mean_w", "oos_chg_yr"]
    print(allg.sort_values("oos_edge", ascending=False).head(10)[cols].to_string(index=False))


if __name__ == "__main__":
    main()
