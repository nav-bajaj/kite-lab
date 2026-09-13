"""§5 — what the rule costs to run.

Best §3 survivor, primary OOS span, against always-on:
  time in cash, turnover (measured from the book's own fills, not estimated),
  allocation changes per year, the ten worst whipsaws, and the tax drag.

Whipsaw: the allocation changes on day t and changes back to the prior level
within 21 sessions. Its cost is (interim weight - prior weight) x the always-on
book's return over the round trip: negative means the deviation gave up return,
positive means it happened to dodge a fall. A whipsaw is not automatically
expensive; the question the table answers is what the churn actually cost.

Tax: Indian financial years (Apr-Mar) on realised legs only, losses set off
inside their own holding-period bucket, STCG 20% under 365 days, LTCG 12.5%
at or over. Paid out of the book at each year end.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import harness as H
from book_x import build_book_x


def fy(d):
    return d.year if d.month >= 4 else d.year - 1


def tax_bill(fills: pd.DataFrame) -> pd.DataFrame:
    f = fills.copy()
    f["fy"] = f.exit_date.map(fy)
    f["bucket"] = np.where(f.hold < 365, "stcg", "ltcg")
    p = f.pivot_table(index="fy", columns="bucket", values="pnl", aggfunc="sum"
                      ).fillna(0.0)
    for b in ("stcg", "ltcg"):
        if b not in p:
            p[b] = 0.0
    p["tax"] = 0.20 * p.stcg.clip(lower=0) + 0.125 * p.ltcg.clip(lower=0)
    return p


def after_tax_cagr(eq: pd.Series, tax: pd.DataFrame) -> float:
    """Pay each year's bill out of the book on the last session of the FY."""
    e = eq.copy()
    mult = 1.0
    out = []
    for _d, v in e.items():
        out.append(v * mult)
    e2 = pd.Series(out, index=e.index)
    for y, row in tax.iterrows():
        end = e2.index[(e2.index >= f"{y + 1}-03-01") & (e2.index <= f"{y + 1}-03-31")]
        if len(end) == 0 or row.tax <= 0:
            continue
        d = end[-1]
        frac = 1 - row.tax / e2.loc[d]
        e2.loc[e2.index > d] = e2.loc[e2.index > d] * max(frac, 0.0)
    yrs = (e2.index[-1] - e2.index[0]).days / 365.25
    return (e2.iloc[-1] / e2.iloc[0]) ** (1 / yrs) - 1


def main():
    os.chdir(H.REPO)
    tr = H.load_tape("trend")
    pan = H.load_panels(tr)
    sig = H.raw_signals()
    b = pd.read_csv(f"{H.CACHE}/best_survivor.csv", index_col=0).iloc[:, 0]
    signal, shape, window = b.best_signal, b.best_shape, int(b.best_window)
    print(f"best survivor: {signal} / {shape} / window {window}", flush=True)

    c_is, c_oos = H.cal("2006-01-01", "2015-12-31"), H.cal("2016-01-01")
    w = H.regime_series(signal, window, shape, sig=sig, fit_index=c_is,
                        lo_q=0.20, hi_q=0.80)
    sub = tr[tr.entry_date >= c_oos[0]]
    t = sub.copy()
    t["wt"] = t.entry_date.map(w).fillna(1.0)
    t1 = sub.copy()
    t1["wt"] = 1.0

    rule = build_book_x(t, pan, c_oos, slots=25, wt_daily=w, mode="entry")
    allon = build_book_x(t1, pan, c_oos, slots=25, mode="entry")

    rows = []
    for lab, r, ws in (("rule", rule, w), ("always on", allon, None)):
        ent = r["entries"]
        yrs = (c_oos[-1] - c_oos[0]).days / 365.25
        turn = float(ent.notional.sum() / r["equity"].mean() / yrs)
        tx = tax_bill(r["fills"])
        atc = after_tax_cagr(r["equity"], tx)
        rows.append(dict(book=lab, cagr=r["cagr"], maxdd=r["maxdd"],
                         sharpe=r["sharpe"], taken=r["taken"],
                         expo=r["exposure"],
                         cash=(H.time_in_cash(ws, c_oos) if ws is not None else 0.0),
                         mean_w=(float(t.wt.mean()) if ws is not None else 1.0),
                         chg_yr=(H.changes_per_year(ws, c_oos) if ws is not None else 0.0),
                         turnover_x=turn,
                         median_hold=float(r["fills"].hold.median()),
                         pct_stcg=float((r["fills"].hold < 365).mean()),
                         tax=float(tx.tax.sum()),
                         tax_pct_end=float(tx.tax.sum() / r["equity"].iloc[-1]),
                         cagr_after_tax=atc,
                         tax_drag_pp=(r["cagr"] - atc) * 100))
    cost = pd.DataFrame(rows)
    cost.to_csv(f"{H.CACHE}/cost.csv", index=False)
    print(cost.to_string(index=False))

    # ---- whipsaws ----------------------------------------------------------
    s = w.reindex(c_oos).ffill().dropna()
    ch = s[s.diff().fillna(0) != 0]
    aeq = allon["equity"]
    wp = []
    for i in range(len(ch) - 1):
        d0, d1 = ch.index[i], ch.index[i + 1]
        gap = len(c_oos[(c_oos > d0) & (c_oos <= d1)])
        prev = s.shift(1).loc[d0]
        if gap <= 21 and abs(ch.iloc[i + 1] - prev) < 1e-12:
            r = float(aeq.loc[d1] / aeq.loc[d0] - 1)
            wp.append(dict(flip=d0.date(), back=d1.date(), sessions=gap,
                           w_from=float(prev), w_to=float(ch.iloc[i]),
                           always_on_ret=r,
                           cost=(ch.iloc[i] - prev) * r))
    wpd = pd.DataFrame(wp)
    if len(wpd):
        wpd["abs"] = wpd.cost.abs()
        wpd = wpd.sort_values("cost")
        wpd.to_csv(f"{H.CACHE}/whipsaws.csv", index=False)
        print(f"\nwhipsaws (<=21 sessions, flip and back): {len(wpd)} over "
              f"{(c_oos[-1] - c_oos[0]).days / 365.25:.1f}y")
        print("ten worst (most negative = the flip gave up return):")
        print(wpd.head(10).drop(columns=["abs"]).to_string(index=False))
        print(f"\nnet effect of all {len(wpd)} sub-21-session round trips, summed: "
              f"{wpd.cost.sum():+.1%}; harmful {int((wpd.cost < 0).sum())}, "
              f"helpful {int((wpd.cost > 0).sum())}; "
              f"sum of harmful {wpd.cost[wpd.cost < 0].sum():+.1%}")
    else:
        print("\nno whipsaws under 21 sessions")


if __name__ == "__main__":
    main()
