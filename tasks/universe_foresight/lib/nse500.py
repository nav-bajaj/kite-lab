"""Phase 6 -- the founder's actual question: NSE 500 point-in-time as the product
universe. Curated, liquidity-screened and governance-vetted by NSE, survivorship-
free in our store, and not the open pool Phase 4 rejected.

Four ways to take NSE 500 reach inside a real index:
  nifty250        the locked books, as shipped
  nse500          straight swap of the universe
  nse500 + floor  NSE 500 minus its own illiquid tail (a turnover floor INSIDE
                  the index -- narrows, never widens; untested before now)
  satellite K     Nifty 250 core + K slots for the strongest 251-500 names
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
import run as MM            # noqa: E402
import windows as W         # noqa: E402
import buckets as B         # noqa: E402
import run_ladder as L      # noqa: E402
sys.path.insert(0, "/Users/navdeep/kite-lab")
from scripts.universe_membership import load_membership, members_asof  # noqa: E402

MM.RUNS = TASK / "runs"; W.REG = TASK / "runs/registry.csv"
SUB = [("2016-19", "2016-01-01", "2019-12-31"), ("2020-22", "2020-01-01", "2022-12-31"), ("2023-26", "2023-01-01", "2099-12-31")]


def nse500_floor(floor: float, window: int = 63) -> Path:
    """NSE 500 point-in-time INTERSECTED with a turnover floor: the index minus
    its own illiquid tail. Strictly a subset of the index, so it can only remove
    names the product would already have been allowed to hold."""
    df = load_membership(B.MASTER / "membership/nse500.csv")
    tv = B.turnover_panel()
    med = tv.rolling(window, min_periods=window // 2).median()
    idx = med.index
    months = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).first()
    picks = {d: (members_asof(df, d) & set(med.columns[med.loc[d] >= floor])) for d in months}
    rows = []
    for sym in {s for p in picks.values() for s in p}:
        start = None
        for d in months:
            inn = sym in picks[d]
            if inn and start is None:
                start = d
            elif not inn and start is not None:
                rows.append((sym, start, d)); start = None
        if start is not None:
            rows.append((sym, start, pd.NaT))
    out = pd.DataFrame(rows, columns=["symbol", "effective_from", "effective_to"])
    out["note"] = f"NSE 500 PIT, turnover >= Rs {floor/1e7:.0f} cr"
    p = B.OUT / f"nse500_floor{int(floor/1e7)}.csv"
    out.to_csv(p, index=False, date_format="%Y-%m-%d")
    n = pd.Series({d: len(v) for d, v in picks.items()})
    print(f"nse500 + Rs {floor/1e7:.0f} cr floor: {out.symbol.nunique()} ever-members | breadth "
          f"{n[n.index >= '2016'].min()}-{n[n.index >= '2016'].max()} (2016+, median {int(n[n.index >= '2016'].median())})", flush=True)
    return p


def line(tag, eq, is_a):
    w = {k: W.stats(eq, a, z) for k, (a, z) in {"IS": (is_a, "2015-12-31"), "OOS": ("2016-01-01", "2099-12-31")}.items()}
    sub = [W.stats(eq, a, z)["sharpe"] for _, a, z in SUB]
    g3 = "PASS" if min(sub) >= 0.6 else "FAIL"
    g4 = "PASS" if w["OOS"]["maxdd"] >= -0.40 else "FAIL"
    print(f"  {tag:<26} OOS {100*w['OOS']['cagr']:5.1f}% / {w['OOS']['sharpe']:4.2f} / {100*w['OOS']['maxdd']:4.0f}%"
          f"  | IS {100*w['IS']['cagr']:5.1f}% / {w['IS']['sharpe']:4.2f}"
          f"  | subs " + "/".join(f"{x:.2f}" for x in sub) + f"  G3 {g3}  G4 {g4}", flush=True)
    return dict(windows={k: {m: float(v[m]) for m in ("cagr", "sharpe", "maxdd")} for k, v in w.items()},
                subs=[float(x) for x in sub], g3=g3, g4=g4)


if __name__ == "__main__":
    L.register_universes()
    for f in (2e7, 5e7):
        MM.om.MEMBERSHIP[f"nse500_f{int(f/1e7)}"] = nse500_floor(f)
    res = {}
    for name in ("MM", "OM25 v4"):
        spec = L.BOOKS[name]; is_a = spec["start"][:4] + "-01-01"
        print(f"\n{name} (locked rules, universe varied)", flush=True)
        res[name] = {}
        cases = [("nifty250 (as shipped)", "nifty250_b0", {}),
                 ("nse500 straight swap", "nse500_b0", {}),
                 ("nse500 + Rs 2 cr floor", "nse500_f2", {}),
                 ("nse500 + Rs 5 cr floor", "nse500_f5", {}),
                 ("nifty250 core + 3 sat", "nse500_b0", dict(satellite_slots=3)),
                 ("nifty250 core + 5 sat", "nse500_b0", dict(satellite_slots=5))]
        for tag, uni, extra in cases:
            cfg, _ = MM.run_candidate(universe=uni, start=spec["start"], end=None, **{**spec["cfg"], **extra})
            rid = MM.cfg_id(cfg); eq = W.equity(MM.RUNS / rid)
            res[name][tag] = line(tag, eq, is_a)
            W.register(cfg, rid, W.stats(eq, is_a, "2015-12-31"), "nse500")
    json.dump(res, open(TASK / "report/nse500_summary.json", "w"), indent=1)
    print(f"\ntrials: {W.n_trials()}", flush=True)
