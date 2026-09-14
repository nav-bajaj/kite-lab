"""Random-exclusion placebo for b4 (the method from tasks/minimum_capital).

b4 beats b0, but b4 also reaches further down the cap scale than the index does.
The control asks whether the turnover RULE earned that or whether any point-in-time
universe of the same breadth, drawn from investable names, would have. Each draw
rebuilds a random N-name universe monthly from names that clear a bare investability
floor, and runs the same book on it.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
import run as MM            # noqa: E402
import windows as W         # noqa: E402
import buckets as B         # noqa: E402
import run_ladder as L      # noqa: E402

MM.RUNS = TASK / "runs"
FLOOR = 1e7      # Rs 1 cr median daily turnover: below this the name is not investable at all
N_DRAWS = 20


def eligible_by_month(window=63, min_hist=252, min_price=10.0):
    tv = B.turnover_panel()
    close = pd.DataFrame({f.name[:-8]: pd.read_csv(f, usecols=["date", "close"], parse_dates=["date"]).set_index("date")["close"]
                          for f in sorted(B.PANEL.glob("*_day.csv"))}).reindex(tv.index)
    med = tv.rolling(window, min_periods=window // 2).median()
    hist = close.notna().cumsum()
    idx = tv.index
    months = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).first()
    return {d: sorted(med.columns[(med.loc[d] >= FLOOR) & (hist.loc[d] >= min_hist) & (close.loc[d] >= min_price)])
            for d in months}


def draw(elig: dict, top_n: int, seed: int) -> Path:
    rng = np.random.default_rng(seed)
    picks = {d: set(rng.choice(names, size=min(top_n, len(names)), replace=False)) for d, names in elig.items()}
    dates = sorted(picks)
    rows = []
    for sym in {s for p in picks.values() for s in p}:
        start = None
        for d in dates:
            inn = sym in picks[d]
            if inn and start is None:
                start = d
            elif not inn and start is not None:
                rows.append((sym, start, d)); start = None
        if start is not None:
            rows.append((sym, start, pd.NaT))
    out = pd.DataFrame(rows, columns=["symbol", "effective_from", "effective_to"])
    out["note"] = f"placebo draw {seed}"
    p = B.OUT / f"placebo_{top_n}_{seed:02d}.csv"
    out.to_csv(p, index=False, date_format="%Y-%m-%d")
    return p


if __name__ == "__main__":
    book = sys.argv[1] if len(sys.argv) > 1 else "MM"
    spec = L.BOOKS[book]; top_n = L.BREADTH[spec["base"]]
    elig = eligible_by_month()
    print(f"eligible pool: {min(len(v) for v in elig.values())}-{max(len(v) for v in elig.values())} names a month "
          f"(>= Rs {FLOOR/1e7:.0f} cr median turnover)", flush=True)
    for tag in ("b0", "b4"):
        MM.om.MEMBERSHIP[f"{spec['base']}_{tag}"] = (B.MASTER / f"membership/{spec['base']}.csv") if tag == "b0" else B.OUT / f"{spec['base']}_b4.csv"
    ref = {}
    for tag in ("b0", "b4"):
        cfg, _ = MM.run_candidate(universe=f"{spec['base']}_{tag}", start=spec["start"], end=None, **spec["cfg"])
        ref[tag] = W.stats(W.equity(MM.RUNS / MM.cfg_id(cfg)), "2016-01-01", "2099-12-31")
    got = []
    for seed in range(N_DRAWS):
        key = f"placebo{top_n}_{seed:02d}"
        MM.om.MEMBERSHIP[key] = draw(elig, top_n, seed)
        cfg, _ = MM.run_candidate(universe=key, start=spec["start"], end=None, **spec["cfg"])
        s = W.stats(W.equity(MM.RUNS / MM.cfg_id(cfg)), "2016-01-01", "2099-12-31")
        got.append(s); print(f"  draw {seed:02d}  {100*s['cagr']:5.1f}% / {s['sharpe']:4.2f} / {100*s['maxdd']:4.0f}%", flush=True)
    c = np.array([g["cagr"] for g in got]) * 100
    sh = np.array([g["sharpe"] for g in got])
    b0c, b4c = 100 * ref["b0"]["cagr"], 100 * ref["b4"]["cagr"]
    print(f"\n{book}: b0 {b0c:.1f}% (Sharpe {ref['b0']['sharpe']:.2f}) | b4 {b4c:.1f}% (Sharpe {ref['b4']['sharpe']:.2f})")
    print(f"placebo {N_DRAWS} draws: CAGR mean {c.mean():.1f}% sd {c.std():.1f} range {c.min():.1f}-{c.max():.1f} "
          f"| Sharpe mean {sh.mean():.2f} sd {sh.std():.2f}")
    print(f"b4 percentile among placebos: CAGR {100*(c < b4c).mean():.0f}th, Sharpe {100*(sh < ref['b4']['sharpe']).mean():.0f}th")
    print(f"how much of b4-minus-b0 ({b4c-b0c:+.1f}pp) a random universe of the same breadth also gets: {c.mean()-b0c:+.1f}pp")
    dd = np.array([g["maxdd"] for g in got]) * 100
    print(f"max drawdown: b0 {100*ref['b0']['maxdd']:.0f}%  b4 {100*ref['b4']['maxdd']:.0f}%  placebo mean {dd.mean():.0f}% (worst {dd.min():.0f}%)")
    json.dump(dict(book=book, b0=b0c, b4=b4c, b0_dd=100 * ref["b0"]["maxdd"], b4_dd=100 * ref["b4"]["maxdd"],
                   placebo_cagr=list(c), placebo_sharpe=list(sh), placebo_maxdd=list(dd)),
              open(TASK / f"report/placebo_{book.replace(' ', '')}.json", "w"), indent=1)
