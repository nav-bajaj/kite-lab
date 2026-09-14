"""Phase 8c -- announcement date instead of effective date (founder, 2026-09-11).

NSE publishes a reconstitution press release ahead of the effective date --
median 35 days for Nifty 250, 9 for NSE 500. Knowing on the publication date
that a stock joins is point-in-time legitimate information, so the universe can
admit it from `pub` rather than `eff`. Tests whether that lead is worth anything,
especially for MM, whose monthly cadence means 35 days is a full extra rebalance.

Coverage limit: the press-release corpus carries both dates only from 2020-08,
so this is a 2020-> test and cannot be run on IS or on 2016-19.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
sys.path.insert(0, "/Users/navdeep/kite-lab")
import run as MM, windows as W, buckets as B, run_ladder as L  # noqa: E402
from scripts.universe_membership import load_membership  # noqa: E402

MM.RUNS = TASK / "runs"; W.REG = TASK / "runs/registry.csv"; B.OUT = TASK / "runs/membership"
PR = Path("/Users/navdeep/kite-lab/tasks/index_reconstruction/data")


def build_announced(universe: str, pr_file: str) -> tuple[Path, dict]:
    df = load_membership(B.MASTER / f"membership/{universe}.csv")
    ev = json.load(open(PR / pr_file))
    known = set(df["symbol"])
    moved, unmatched, skipped = 0, 0, 0
    for e in ev:
        if not e.get("pub") or not e.get("eff"):
            continue
        pub, eff = pd.Timestamp(e["pub"]), pd.Timestamp(e["eff"])
        if pub >= eff:
            continue
        for _, sym in (e.get("included") or []):
            if sym not in known:
                unmatched += 1
                continue
            # the window this event opened: effective_from within a few days of eff
            m = (df["symbol"] == sym) & (df["effective_from"] >= eff - pd.Timedelta(days=5)) & (df["effective_from"] <= eff + pd.Timedelta(days=5))
            if not m.any():
                skipped += 1
                continue
            df.loc[m, "effective_from"] = pub
            moved += 1
    p = B.OUT / f"{universe}_announced.csv"
    df.to_csv(p, index=False, date_format="%Y-%m-%d")
    stats = dict(moved=moved, unmatched=unmatched, no_window=skipped)
    print(f"{universe}: {moved} inclusions pulled forward to their announcement date "
          f"({unmatched} symbols not in our membership file, {skipped} with no matching window)", flush=True)
    return p, stats


if __name__ == "__main__":
    MM.om.MEMBERSHIP["P_n250"] = B.MASTER / "membership/nifty250.csv"
    MM.om.MEMBERSHIP["P_n250_ann"], _ = build_announced("nifty250", "pr_nifty250_changes.json")
    MM.om.MEMBERSHIP["P_n500"] = B.MASTER / "membership/nse500.csv"
    MM.om.MEMBERSHIP["P_n500_ann"], _ = build_announced("nse500", "pr_nse500_changes.json")
    res = {}
    print(f"\n{'book / universe':<30}{'2020-> CAGR / Sharpe / DD':>28}{'trail 3y':>16}{'trail 1y':>16}")
    for book in ("MM", "OM25 v4"):
        spec = L.BOOKS[book]; res[book] = {}
        for lab, uni in [("nifty250 effective-date", "P_n250"), ("nifty250 ANNOUNCEMENT", "P_n250_ann"),
                         ("nse500 effective-date", "P_n500"), ("nse500 ANNOUNCEMENT", "P_n500_ann")]:
            cfg, _ = MM.run_candidate(universe=uni, start=spec["start"], end=None, **spec["cfg"])
            eq = W.equity(MM.RUNS / MM.cfg_id(cfg))
            o = W.stats(eq, "2020-09-01", "2099-12-31")
            t3 = W.stats(eq, "2023-09-11", "2099-12-31"); t1 = W.stats(eq, "2025-09-11", "2099-12-31")
            print(f"{book+' / '+lab:<30}{100*o['cagr']:11.1f}% /{o['sharpe']:5.2f} /{100*o['maxdd']:4.0f}%"
                  f"{100*t3['cagr']:9.1f}% /{t3['sharpe']:5.2f}{100*t1['cagr']:9.1f}% /{t1['sharpe']:5.2f}", flush=True)
            res[book][lab] = dict(w2020={m: float(o[m]) for m in ("cagr", "sharpe", "maxdd")},
                                  t3={m: float(t3[m]) for m in ("cagr", "sharpe")}, t1={m: float(t1[m]) for m in ("cagr", "sharpe")})
            W.register(cfg, MM.cfg_id(cfg), o, "announce")
    json.dump(res, open(TASK / "report/announce_summary.json", "w"), indent=1)
