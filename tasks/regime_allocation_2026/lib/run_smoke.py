"""§1 smoke test — reproduce trend_screen_2026 §8's OOS numbers.

Reference (BRIEF): founder's rule 21.6% / 36.7% / 0.92; always-on
19.1% / 41.0% / 0.66; half-everywhere 13.5% / 26.4% / 0.64.

Also checks the two things the rest of the task leans on: that order="tight"
makes the book seed-independent, and that regime_series() reproduces the tape's
own `phase` column.
"""
from __future__ import annotations

import os
import time


import harness as H


def main():
    os.chdir(H.REPO)
    t0 = time.time()
    tr = H.load_tape("trend")
    pan = H.load_panels(tr)
    print(f"tape {tr.shape} panels {len(pan)} in {time.time() - t0:.0f}s", flush=True)
    sig = H.raw_signals()
    print("signals:", {c: int(sig[c].notna().sum()) for c in sig.columns}, flush=True)

    oos = H.cal("2016-01-01")
    sub = tr[tr.entry_date >= "2016-01-01"]

    founder = {"EXPANSION": 1.0, "RECOVERY": 1.0, "TOPPING": 0.5, "CONTRACTION": 0.0}

    # (a) tape phase column, exactly as run_isos.py does it
    t = sub.copy()
    t["wt"] = t.phase.map(founder).fillna(1.0)
    t0 = time.time()
    r = H.build_book(t, pan, oos, slots=25, risk_pct=1.0, capital=1e7, seed=0,
                     order="tight")
    dt = time.time() - t0
    print(f"\none build_book call: {dt:.1f}s", flush=True)
    print(f"founder (tape phase)    {r['cagr']:>7.1%}{r['maxdd']:>8.1%}{r['sharpe']:>7.2f}")

    # seed independence
    r1 = H.build_book(t, pan, oos, slots=25, risk_pct=1.0, capital=1e7, seed=1,
                      order="tight")
    r2 = H.build_book(t, pan, oos, slots=25, risk_pct=1.0, capital=1e7, seed=7,
                      order="tight")
    same = (abs(r1["sharpe"] - r["sharpe"]) < 1e-12
            and abs(r2["sharpe"] - r["sharpe"]) < 1e-12)
    print(f"seed-independent (order='tight'): {same}")

    # (b) my own regime_series reconstruction of the same rule
    ph = H.phase_labels("pct_above_200", 63, sig)
    ov = ph.reindex(sub.entry_date.values)
    agree = float((ov.to_numpy() == sub.phase.to_numpy()).mean())
    print(f"phase_labels vs tape phase agreement (OOS entries): {agree:.4f}")

    w = H.regime_series("pct_above_200", 63, "D1_four_bucket", sig=sig)
    rw = H.run_book(sub, pan, oos, w)
    print(f"founder (regime_series) {rw['cagr']:>7.1%}{rw['maxdd']:>8.1%}{rw['sharpe']:>7.2f}")

    ra = H.run_book(sub, pan, oos, 1.0)
    print(f"always on               {ra['cagr']:>7.1%}{ra['maxdd']:>8.1%}{ra['sharpe']:>7.2f}")
    rh = H.run_book(sub, pan, oos, 0.5)
    print(f"half everywhere         {rh['cagr']:>7.1%}{rh['maxdd']:>8.1%}{rh['sharpe']:>7.2f}")

    ref = {"founder": (0.216, 0.367, 0.92), "always": (0.191, 0.410, 0.66),
           "half": (0.135, 0.264, 0.64)}
    got = {"founder": (r["cagr"], r["maxdd"], r["sharpe"]),
           "always": (ra["cagr"], ra["maxdd"], ra["sharpe"]),
           "half": (rh["cagr"], rh["maxdd"], rh["sharpe"])}
    print("\ntolerance check (0.3pp CAGR / 0.5pp maxDD / 0.02 Sharpe):")
    ok = True
    for k in ref:
        d = [abs(got[k][i] - ref[k][i]) for i in range(3)]
        p = d[0] <= 0.003 + 1e-9 and d[1] <= 0.005 + 1e-9 and d[2] <= 0.02 + 1e-9
        ok &= p
        print(f"  {k:<10} d_cagr {d[0]*100:>5.2f}pp  d_dd {d[1]*100:>5.2f}pp  "
              f"d_sharpe {d[2]:>5.3f}  {'PASS' if p else 'FAIL'}")
    print(f"\nSMOKE: {'PASS' if ok else 'FAIL'}")

    # mean weight of the founder rule, for the record
    wts = sub.entry_date.map(w).fillna(1.0)
    print(f"founder rule mean weight (all OOS tape rows): {wts.mean():.3f}")
    print(f"changes/yr {H.changes_per_year(w, oos):.1f}  "
          f"time in cash {H.time_in_cash(w, oos):.1%}")


if __name__ == "__main__":
    main()
