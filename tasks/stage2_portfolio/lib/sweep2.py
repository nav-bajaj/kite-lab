"""S2 mechanics sweep: weight discipline x sector cap x scoring variant.

Windows follow the house convention so OOS is comparable to the published
v3 figures: IS 2009-09-01..2016-12-31, OOS 2017-01-01..panel end.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2]))

from lib.run_s2 import build_context, run_one, metrics

IS = ("2009-09-01", "2016-12-31")
OOS = ("2017-01-01", None)


def concentration(res, close, sector_map):
    """Peak single-name and single-sector weight actually reached."""
    tr = res["trades"].copy()
    if tr.empty:
        return {}
    tr["date"] = pd.to_datetime(tr["date"])
    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"]
    pos: dict[str, int] = {}
    max_name = 0.0
    max_sector = 0.0
    worst_sector = None
    # walk month-ends to keep it cheap
    month_ends = pv.resample("ME").last().index
    by_date = {d: g for d, g in tr.groupby("date")}
    dates = sorted(set(pv.index))
    checkpoints = set(month_ends)
    for d in dates:
        if d in by_date:
            for _, t in by_date[d].iterrows():
                s = t["symbol"]
                pos[s] = pos.get(s, 0) + (t["shares"] if t["side"] == "BUY"
                                          else -t["shares"])
                if pos[s] <= 0:
                    pos.pop(s, None)
        if d not in checkpoints or not pos:
            continue
        v = float(pv.loc[d])
        if v <= 0:
            continue
        vals = {}
        row = close.loc[d] if d in close.index else None
        if row is None:
            continue
        for s, sh in pos.items():
            p = row.get(s, np.nan)
            if not pd.isna(p):
                vals[s] = sh * float(p)
        if not vals:
            continue
        mn = max(vals.values()) / v
        max_name = max(max_name, mn)
        sect: dict[str, float] = {}
        for s, val in vals.items():
            g = sector_map.get(s, f"__u_{s}")
            sect[g] = sect.get(g, 0.0) + val
        g, gv = max(sect.items(), key=lambda kv: kv[1])
        if gv / v > max_sector:
            max_sector, worst_sector = gv / v, g
    return {"peak_name_wt_pct": round(max_name * 100, 1),
            "peak_sector_wt_pct": round(max_sector * 100, 1),
            "peak_sector": worst_sector}


def main():
    ctx = build_context()
    bench, close, sm = ctx["benchmark"], ctx["prices"]["close"], ctx["sector_map"]
    rows = []
    configs = []
    for wm in ["drift", "trim", "equal"]:
        for cap in [0, 4]:
            configs.append(("B_quality", wm, cap))
    for variant in ["A_rs", "C_nofresh", "D_blend"]:
        configs.append((variant, "trim", 4))

    for variant, wm, cap in configs:
        for win, (s, e) in (("IS", IS), ("OOS", OOS)):
            res = run_one(ctx, variant=variant, top_n=22, exit_buffer=10,
                          stop=0.0, weight_mode=wm, sector_cap=cap,
                          start=s, end=e)
            m = metrics(res, benchmark=bench)
            if m is None:
                continue
            m.update(variant=variant, weight_mode=wm, sector_cap=cap,
                     window=win)
            m.update(concentration(res, close, sm))
            rows.append(m)
            print(f"  {variant:11s} {wm:6s} cap{cap} {win:3s}  "
                  f"CAGR {m['cagr_pct']:6.2f}%  DD {m['max_dd_pct']:7.2f}%  "
                  f"Sh {m['sharpe']:.2f}  Cal {m['calmar']:.2f}  "
                  f"alpha {m.get('alpha_cagr_pp', float('nan')):+5.2f}pp  "
                  f"peakName {m.get('peak_name_wt_pct', 0):4.1f}%  "
                  f"peakSect {m.get('peak_sector_wt_pct', 0):4.1f}%  "
                  f"trades/y {m['buys_per_year']:.0f}")
    df = pd.DataFrame(rows)
    df.to_csv(HERE.parent / "data" / "sweep_mechanics.csv", index=False)
    print(f"\n[wrote] data/sweep_mechanics.csv ({len(df)} rows)")


if __name__ == "__main__":
    main()
