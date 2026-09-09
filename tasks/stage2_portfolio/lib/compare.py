"""Head-to-head: S2 vs the production momentum signals on IDENTICAL data.

The published TL25 v3 / L6 v2 figures were produced on a current-snapshot
universe. Comparing S2 (which runs survivorship-free here) against those
numbers would be a data-basis comparison, not a signal comparison. So every
signal below is re-run on the same panel, calendar, membership, benchmark and
cost assumptions.

Two runs per production signal:
  native    its own cadence and exits, on honest data
  s2_mech   its signal inside S2's mechanics (weekly, top-22, sector cap 4)
            - isolates the signal from the plumbing
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2]))

from scripts._clean_engine import fridays, biweekly_fridays
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score, V3_LOCKED
from scripts._momentum_engine import build_momentum_panels, make_momentum_score

from lib.run_s2 import build_context, run_one, metrics
from lib.s2_engine import run_s2_strategy
from lib.stage2 import make_s2_score, VARIANTS

IS = ("2009-09-01", "2016-12-31")
OOS = ("2017-01-01", None)


def run_signal(ctx, score_fn, *, cadence="weekly", top_n=22, exit_buffer=10,
               stop=0.0, weight_mode="trim", sector_cap=4,
               start="2009-09-01", end=None):
    P = ctx["prices"]
    cal = P["calendar"]
    sig = fridays(cal) if cadence == "weekly" else biweekly_fridays(cal)
    s_ts, e_ts = pd.Timestamp(start), (pd.Timestamp(end) if end else cal[-1])
    sig = sig[(sig >= s_ts) & (sig <= e_ts)]
    return run_s2_strategy(
        close_panel=P["close"], trade_panel=P["trade"], calendar=cal,
        benchmark_aligned=ctx["benchmark"], signal_dates=sig, score_fn=score_fn,
        top_n=top_n, exit_buffer=exit_buffer, max_weight=0.075,
        slippage=0.002, stop=stop, weight_mode=weight_mode,
        sector_map=ctx["sector_map"], sector_cap=sector_cap,
        membership_fn=ctx["membership_fn"], end=e_ts)


def build_signals(ctx):
    close = ctx["prices"]["close"]
    cf = ctx["candidate_fn"]

    tl_panels = build_tl25_panels(
        close, dma_short=V3_LOCKED["dma_short"], dma_long=V3_LOCKED["dma_long"],
        dma_persist_ref=V3_LOCKED["dma_persist_ref"],
        persistence_window=V3_LOCKED["persistence_window"],
        drawdown_window=V3_LOCKED["drawdown_window"],
        drawdown_concavity=V3_LOCKED["drawdown_concavity"],
        momentum_window=V3_LOCKED["momentum_window"])
    tl_score = make_tl25_score(
        tl_panels, w_persistence=V3_LOCKED["w_persistence"],
        w_drawdown=V3_LOCKED["w_drawdown"], w_momentum=V3_LOCKED["w_momentum"],
        candidate_fn=cf)

    mom_panels = build_momentum_panels(close, lookback_days=126)
    mom_score = make_momentum_score(mom_panels, vol_floor=0.05)

    return {"TL25v3": tl_score, "L6like": mom_score,
            "S2_D": make_s2_score(ctx["panels"], candidate_fn=cf,
                                  **VARIANTS["D_blend"]),
            "S2_B": make_s2_score(ctx["panels"], candidate_fn=cf,
                                  **VARIANTS["B_quality"])}


def main():
    ctx = build_context()
    sigs = build_signals(ctx)
    bench = ctx["benchmark"]
    rows, curves, books = [], {}, {}

    plans = [
        ("TL25v3", "native",  dict(cadence="biweekly", top_n=25, exit_buffer=20,
                                   stop=0.20, weight_mode="drift", sector_cap=0)),
        ("TL25v3", "s2_mech", dict(cadence="weekly", top_n=22, exit_buffer=10,
                                   stop=0.0, weight_mode="trim", sector_cap=4)),
        ("L6like", "native",  dict(cadence="weekly", top_n=24, exit_buffer=0,
                                   stop=0.0, weight_mode="drift", sector_cap=0)),
        ("L6like", "s2_mech", dict(cadence="weekly", top_n=22, exit_buffer=10,
                                   stop=0.0, weight_mode="trim", sector_cap=4)),
        ("S2_D",   "s2_mech", dict(cadence="weekly", top_n=22, exit_buffer=10,
                                   stop=0.0, weight_mode="trim", sector_cap=4)),
        ("S2_B",   "s2_mech", dict(cadence="weekly", top_n=22, exit_buffer=10,
                                   stop=0.0, weight_mode="trim", sector_cap=4)),
    ]

    for name, mode, kw in plans:
        for win, (s, e) in (("IS", IS), ("OOS", OOS)):
            res = run_signal(ctx, sigs[name], start=s, end=e, **kw)
            m = metrics(res, benchmark=bench)
            if m is None:
                continue
            m.update(signal=name, mode=mode, window=win)
            rows.append(m)
            print(f"  {name:7s} {mode:8s} {win:3s}  CAGR {m['cagr_pct']:6.2f}%  "
                  f"DD {m['max_dd_pct']:7.2f}%  Sh {m['sharpe']:.2f}  "
                  f"Cal {m['calmar']:.2f}  alpha {m.get('alpha_cagr_pp', np.nan):+5.2f}pp "
                  f" trades/y {m['buys_per_year']:.0f}")
            if win == "OOS":
                eq = res["equity"].copy()
                eq["date"] = pd.to_datetime(eq["date"])
                curves[f"{name}_{mode}"] = eq.set_index("date")["pv"]
                books[f"{name}_{mode}"] = res

    pd.DataFrame(rows).to_csv(HERE.parent / "data" / "compare_signals.csv",
                              index=False)

    # ---- differentiation: return correlation + holdings overlap (OOS) ------
    keys = ["S2_D_s2_mech", "S2_B_s2_mech", "TL25v3_s2_mech", "L6like_s2_mech",
            "TL25v3_native", "L6like_native"]
    keys = [k for k in keys if k in curves]
    wk = pd.DataFrame({k: curves[k] for k in keys}).resample("W-FRI").last()
    corr = wk.pct_change(fill_method=None).corr()
    print("\n--- OOS weekly return correlation ---")
    print(corr.round(3).to_string())
    corr.to_csv(HERE.parent / "data" / "oos_return_correlation.csv")

    def holdings_series(res):
        tr = res["trades"].copy()
        tr["date"] = pd.to_datetime(tr["date"])
        pos, snaps = {}, {}
        for d, g in tr.groupby("date"):
            for _, t in g.iterrows():
                s = t["symbol"]
                pos[s] = pos.get(s, 0) + (t["shares"] if t["side"] == "BUY"
                                          else -t["shares"])
                if pos[s] <= 0:
                    pos.pop(s, None)
            snaps[d] = set(pos)
        return snaps

    print("\n--- OOS holdings overlap (mean Jaccard, month-end) ---")
    snaps = {k: holdings_series(books[k]) for k in keys}
    all_d = sorted(set().union(*[set(v) for v in snaps.values()]))
    me = pd.DatetimeIndex(all_d).to_period("M").to_timestamp("M")
    pick = {}
    for d, m in zip(all_d, me):
        pick[m] = d
    ov = pd.DataFrame(index=keys, columns=keys, dtype=float)
    for a in keys:
        for b in keys:
            vals = []
            pa = pb = set()
            for d in all_d:
                pa = snaps[a].get(d, pa)
                pb = snaps[b].get(d, pb)
                if d in pick.values() and (pa or pb):
                    vals.append(len(pa & pb) / max(1, len(pa | pb)))
            ov.loc[a, b] = round(float(np.mean(vals)) if vals else np.nan, 3)
    print(ov.to_string())
    ov.to_csv(HERE.parent / "data" / "oos_holdings_overlap.csv")


if __name__ == "__main__":
    main()
