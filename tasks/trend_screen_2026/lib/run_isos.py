"""§8 — in-sample / out-of-sample test of phase-conditioned allocation.

The founder's proposal: full allocation in EXPANSION and RECOVERY, nothing in
CONTRACTION, something smaller in TOPPING.

**The trap, stated before any number.** The phase effect was discovered on the
whole 2006-2026 sample. Splitting that sample afterwards and calling the later
half "out of sample" does not make it so — the taxonomy (four phases, breadth
as % above the 200-day, a 63-session change window, the median as the level
cut) was all chosen knowing how the full period behaved. A genuinely clean
test would have required freezing those choices in 2015.

What can still be learned, and is worth the run:

1. Whether the allocation WEIGHTS, fitted only on 2006-2015, survive on
   2016-2026. That part is honest — the weights are the only thing refit.
2. Whether the founder's intuition matches what the in-sample decade actually
   said. It may not: in 2006-2012 TOPPING was the best bucket on alpha.
3. How much of the gain is just lower exposure rather than better timing,
   which the always-on and cash-matched controls isolate.

Anything the OOS half shows is therefore an upper bound on what a real
forward test would have delivered, and is labelled that way.
"""
from __future__ import annotations

import os
import sys
import numpy as np
import pandas as pd

REPO = "/Users/navdeep/kite-lab"
sys.path.insert(0, f"{REPO}/tasks/breakout_calls_2026/lib")
from exits import load_panel  # noqa: E402
from book import build_book  # noqa: E402

TASK = f"{REPO}/tasks/trend_screen_2026"
IS_END = "2015-12-31"
OOS_START = "2016-01-01"
PHASES = ["RECOVERY", "EXPANSION", "TOPPING", "CONTRACTION"]


def book(tr, pan, cal, weights, slots=25, capital=1e7, seeds=3):
    t = tr.copy()
    t["wt"] = t.phase.map(weights).fillna(1.0)
    out = []
    for s in range(seeds):
        r = build_book(t, pan, cal, slots=slots, risk_pct=1.0,
                       capital=capital, seed=s, order="tight")
        out.append(r)
    eq = out[0]["equity"]
    return dict(cagr=np.median([r["cagr"] for r in out]),
                maxdd=np.median([r["maxdd"] for r in out]),
                sharpe=np.median([r["sharpe"] for r in out]),
                taken=np.median([r["taken"] for r in out]),
                expo=np.median([r["exposure"] for r in out]), equity=eq)


def main():
    os.chdir(REPO)
    tr = pd.read_csv(f"{TASK}/data/calls_full_range.csv",
                     parse_dates=["entry_date", "exit_date"])
    tr = tr.rename(columns={"rnk": "rank"})
    tr["exit_px"] = tr.entry * (1 + tr.ret)
    tr["stop"] = tr.entry * 0.01
    tr["final_depth"] = tr["rank"]
    pit = pd.read_parquet(f"{REPO}/tasks/breakout_calls_2026/data/pit_universe.parquet",
                          columns=["date", "symbol", "adv"]).drop_duplicates(["symbol", "date"])
    tr = tr.merge(pit, left_on=["symbol", "entry_date"], right_on=["symbol", "date"], how="left")
    tr["adv"] = tr.adv.fillna(tr.adv.median())
    tr = tr.drop(columns=["date"]).sort_values("entry_date").reset_index(drop=True)

    panels = {s: p for s in sorted(tr.symbol.unique()) if (p := load_panel(s)) is not None}
    pan = {s: {"close": pd.Series(panels[s]["c"], index=panels[s]["dates"])} for s in panels}
    bench = pd.read_csv("data/master/benchmarks/NIFTY_500.csv", parse_dates=["date"])
    full = pd.DatetimeIndex(sorted(bench.date.unique()))
    cal_is = full[(full >= "2006-01-01") & (full <= IS_END)]
    cal_oos = full[(full >= OOS_START) & (full <= "2026-09-09")]

    ins = tr[tr.entry_date <= IS_END]
    print("=== what the IN-SAMPLE decade (2006-2015) actually said ===")
    print(f"  {'phase':<13}{'calls':>7}{'raw':>9}{'alpha':>9}")
    isstats = {}
    for p in PHASES:
        g = ins[ins.phase == p]
        isstats[p] = g.alpha.mean()
        print(f"  {p:<13}{len(g):>7}{g.ret.mean():>+9.2%}{g.alpha.mean():>+9.2%}")
    best = max(isstats, key=isstats.get)
    print(f"  -> best bucket in-sample: {best}")

    # weights fitted on IS only: rank phases by IS alpha, allocate 1 / 1 / 0.5 / 0
    order = sorted(PHASES, key=lambda p: -isstats[p])
    fitted = {order[0]: 1.0, order[1]: 1.0, order[2]: 0.5, order[3]: 0.0}
    founder = {"EXPANSION": 1.0, "RECOVERY": 1.0, "TOPPING": 0.5, "CONTRACTION": 0.0}
    schemes = {
        "always on (control)": {p: 1.0 for p in PHASES},
        "founder's rule": founder,
        "IS-fitted weights": fitted,
        "skip contraction only": {**{p: 1.0 for p in PHASES}, "CONTRACTION": 0.0},
        "half everywhere (control)": {p: 0.5 for p in PHASES},
    }
    print(f"\n  IS-fitted weights: {fitted}")
    print(f"  founder's weights: {founder}")

    for lab, cal, sub in [("IN-SAMPLE 2006-2015", cal_is, tr[tr.entry_date <= IS_END]),
                          ("OUT-OF-SAMPLE 2016-2026", cal_oos, tr[tr.entry_date >= OOS_START])]:
        print(f"\n=== {lab} ===")
        print(f"  {'scheme':<28}{'CAGR':>8}{'maxDD':>8}{'Sharpe':>8}{'taken':>7}{'expo':>7}")
        for name, w in schemes.items():
            r = book(sub, pan, cal, w)
            print(f"  {name:<28}{r['cagr']:>7.1%}{r['maxdd']:>7.1%}{r['sharpe']:>8.2f}"
                  f"{r['taken']:>7.0f}{r['expo']:>7.0%}", flush=True)


if __name__ == "__main__":
    main()
