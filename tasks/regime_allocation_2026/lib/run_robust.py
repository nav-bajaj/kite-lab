"""§4 — robustness for the §3 slate.

Four checks, each on the same harness:
  1. alternate splits — IS 2006-2012 / OOS 2013-2026 and IS 2006-2018 /
     OOS 2019-2026. Every fitted constant is refit on the alternate IS window;
     the direction window is the one §2 picked on the primary split, which is
     a known contamination of this check and is labelled as one.
  2. where the rule acts — entry only / entry + forced exit / entry +
     rebalance-down, best §3 survivor only.
  3. slot count 15 / 25 / 35, best survivor.
  4. cross-signal — the same rule on the breakout tape.
"""
from __future__ import annotations

import os

import pandas as pd

import harness as H
from book_x import build_book_x

SPLITS = [("primary", "2006-01-01", "2015-12-31", "2016-01-01"),
          ("alt_2013", "2006-01-01", "2012-12-31", "2013-01-01"),
          ("alt_2019", "2006-01-01", "2018-12-31", "2019-01-01")]


def main():
    os.chdir(H.REPO)
    tr = H.load_tape("trend")
    pan = H.load_panels(tr)
    sig = H.raw_signals()
    g = pd.read_csv(f"{H.CACHE}/grid.csv")
    g = g[g.hyst == 0]
    wf = pd.read_csv(f"{H.CACHE}/wf.csv")
    fams = wf[wf.candidate != "always on (control)"].copy()
    fams["key"] = fams.candidate
    best = fams.sort_values("wf_sharpe", ascending=False).iloc[0]
    print(f"best §3 survivor by WF Sharpe: {best.candidate}", flush=True)

    # ---- 1. alternate splits -------------------------------------------------
    rows = []
    for _, f in fams.iterrows():
        cell = g[(g.signal == f.signal) & (g["shape"] == f["shape"])
                 ].sort_values("oos_edge", ascending=False).iloc[0]
        for lab, is_lo, is_hi, oos_lo in SPLITS:
            c_is, c_oos = H.cal(is_lo, is_hi), H.cal(oos_lo)
            w = H.regime_series(f.signal, int(cell.window), f["shape"], sig=sig,
                                fit_index=c_is, lo_q=0.20, hi_q=0.80)
            r = H.evaluate(w, tr, pan, c_oos)
            sub = tr[(tr.entry_date >= c_oos[0]) & (tr.entry_date <= c_oos[-1])]
            a = H.run_book(sub, pan, c_oos, 1.0)
            rows.append(dict(candidate=f.candidate, window=int(cell.window),
                             split=lab, oos_cagr=r["cagr"], oos_maxdd=r["maxdd"],
                             oos_sharpe=r["sharpe"], ctl_sharpe=r["c_sharpe"],
                             always_sharpe=a["sharpe"],
                             beats_always=bool(r["sharpe"] > a["sharpe"]),
                             beats_ctl=bool(r["sharpe"] > r["c_sharpe"])))
            print(f"  {f.candidate:<34}{lab:<10} rule {r['sharpe']:>5.2f}  "
                  f"always {a['sharpe']:>5.2f}  ctl {r['c_sharpe']:>5.2f}", flush=True)
    alt = pd.DataFrame(rows)
    alt.to_csv(f"{H.CACHE}/robust_splits.csv", index=False)

    # ---- best survivor's fixed cell, primary OOS ----------------------------
    bcell = g[(g.signal == best.signal) & (g["shape"] == best["shape"])
              ].sort_values("oos_edge", ascending=False).iloc[0]
    c_is, c_oos = H.cal("2006-01-01", "2015-12-31"), H.cal("2016-01-01")
    wb = H.regime_series(best.signal, int(bcell.window), best["shape"], sig=sig,
                         fit_index=c_is, lo_q=0.20, hi_q=0.80)
    sub = tr[tr.entry_date >= c_oos[0]]

    # ---- 2. where the rule acts --------------------------------------------
    t = sub.copy()
    t["wt"] = t.entry_date.map(wb).fillna(1.0)
    ref = H.build_book(t, pan, c_oos, slots=25, risk_pct=1.0, capital=1e7,
                       seed=0, order="tight")
    acts = []
    for mode in ("entry", "force_exit", "rebal_down"):
        r = build_book_x(t, pan, c_oos, slots=25, wt_daily=wb, mode=mode)
        acts.append(dict(mode=mode, cagr=r["cagr"], maxdd=r["maxdd"],
                         sharpe=r["sharpe"], taken=r["taken"],
                         expo=r["exposure"], fills=len(r["fills"])))
        if mode == "entry":
            ok = (abs(r["sharpe"] - ref["sharpe"]) < 1e-9
                  and abs(r["cagr"] - ref["cagr"]) < 1e-9)
            print(f"  book_x 'entry' reproduces build_book exactly: {ok}", flush=True)
        print(f"  {mode:<12}{r['cagr']:>7.1%}{r['maxdd']:>8.1%}{r['sharpe']:>6.2f}",
              flush=True)
    pd.DataFrame(acts).to_csv(f"{H.CACHE}/robust_acts.csv", index=False)

    # ---- 3. slots ------------------------------------------------------------
    srows = []
    for s in (15, 25, 35):
        r = H.evaluate(wb, tr, pan, c_oos, slots=s)
        a = H.run_book(sub, pan, c_oos, 1.0, slots=s)
        srows.append(dict(slots=s, rule_cagr=r["cagr"], rule_maxdd=r["maxdd"],
                          rule_sharpe=r["sharpe"], ctl_sharpe=r["c_sharpe"],
                          always_cagr=a["cagr"], always_maxdd=a["maxdd"],
                          always_sharpe=a["sharpe"]))
        print(f"  slots {s:<4} rule {r['sharpe']:>5.2f}  always {a['sharpe']:>5.2f}"
              f"  ctl {r['c_sharpe']:>5.2f}", flush=True)
    pd.DataFrame(srows).to_csv(f"{H.CACHE}/robust_slots.csv", index=False)

    # ---- 4. cross-signal: the breakout tape ---------------------------------
    trb = H.load_tape("breakout")
    panb = H.load_panels(trb, "brk")
    subb = trb[trb.entry_date >= c_oos[0]]
    xr = H.evaluate(wb, trb, panb, c_oos)
    xa = H.run_book(subb, panb, c_oos, 1.0)
    xrows = [dict(tape="breakout", rule_cagr=xr["cagr"], rule_maxdd=xr["maxdd"],
                  rule_sharpe=xr["sharpe"], ctl_sharpe=xr["c_sharpe"],
                  always_cagr=xa["cagr"], always_maxdd=xa["maxdd"],
                  always_sharpe=xa["sharpe"], taken=xr["taken"])]
    print(f"  breakout tape: rule {xr['sharpe']:.2f}  always {xa['sharpe']:.2f}"
          f"  ctl {xr['c_sharpe']:.2f}", flush=True)
    pd.DataFrame(xrows).to_csv(f"{H.CACHE}/robust_cross.csv", index=False)

    # G6 per candidate: sign holds in BOTH alternates
    g6 = (alt[alt.split != "primary"].groupby("candidate").beats_always.all())
    g6.to_csv(f"{H.CACHE}/robust_g6.csv")
    print("\nG6 (beats always-on in both alternates):")
    print(g6.to_string())
    pd.Series({"best_candidate": best.candidate,
               "best_window": int(bcell.window),
               "best_shape": best["shape"],
               "best_signal": best.signal}).to_csv(f"{H.CACHE}/best_survivor.csv")


if __name__ == "__main__":
    main()
