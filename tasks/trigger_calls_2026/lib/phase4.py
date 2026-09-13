"""§4 — 25-slot equal-weight book, gated vs always-on.

Equal weight is forced: with no hard stop (stop = 1% of entry) risk sizing
alone puts 1.5% of equity in each name and the book never invests, so
risk_pct is set above the level where the 1/N weight cap binds.
"""
from __future__ import annotations
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "tasks/trend_screen_2026/lib")
sys.path.insert(0, "tasks/breakout_calls_2026/lib")
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
from exits import load_panel                    # noqa: E402
from book import build_book, era_sharpe         # noqa: E402
from daily_features import regime_gate, benchmark  # noqa: E402
from tapes import dedupe                        # noqa: E402

ERAS = [(2006, 2012, "2006-12"), (2013, 2019, "2013-19"), (2020, 2026, "2020-26")]
SLOTS = 25
t = pd.read_parquet("tasks/trigger_calls_2026/data/tapes.parquet")
g = regime_gate()
ga = g.reindex(g.index.union(pd.Index(t.trigger_date.unique()))).ffill()
t["gate_on"] = t.trigger_date.map(ga).fillna(False).astype(bool)
cal = pd.DatetimeIndex(sorted(pd.read_parquet(
    "tasks/trigger_calls_2026/data/daily.parquet", columns=["date"]).date.unique()))

tapes = {"gated": dedupe(t[(t.kind == "T3") & t.gate_on]),
         "always-on": dedupe(t[t.kind == "T3"])}
syms = sorted(set(tapes["always-on"].symbol))
panels = {}
for s in syms:
    p = load_panel(s)
    if p is not None:
        panels[s] = dict(close=pd.Series(p["c"], index=p["dates"]))
b = benchmark()
out = {}
for lab, x in tapes.items():
    x = x.copy()
    x["stop"] = x.entry * 0.01
    x["adv"] = x["adv"].fillna(1.0)
    for lo, hi, tag in ((2006, 2026, "full"), (2016, 2026, "oos")):
        c = cal[(cal.year >= lo) & (cal.year <= hi)]
        z = x[(x.entry_date >= c[0]) & (x.entry_date <= c[-1])]
        r = build_book(z, panels, c, slots=SLOTS, risk_pct=1.0,
                       max_weight=1.0 / SLOTS)
        out[f"{lab}|{tag}"] = dict(
            n=len(z), taken=r["taken"], cagr=round(r["cagr"] * 100, 1),
            maxdd=round(r["maxdd"] * 100, 1), sharpe=round(r["sharpe"], 2),
            vol=round(r["vol"] * 100, 1), exposure=round(r["exposure"] * 100, 1),
            avg_open=round(r["avg_open"], 1),
            eras={k: (None if np.isnan(v) else round(v, 2))
                  for k, v in era_sharpe(r["equity"], ERAS).items()})
for lo, hi, tag in ((2006, 2026, "full"), (2016, 2026, "oos")):
    c = cal[(cal.year >= lo) & (cal.year <= hi)]
    s = b.reindex(b.index.union(c)).ffill().reindex(c)
    y = (c[-1] - c[0]).days / 365.25
    cg = (s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1
    v = s.pct_change().dropna().std() * np.sqrt(252)
    out[f"NIFTY500|{tag}"] = dict(cagr=round(cg * 100, 1),
                                  maxdd=round((1 - s / s.cummax()).max() * 100, 1),
                                  sharpe=round((cg - 0.05) / v, 2), vol=round(v * 100, 1))
print(json.dumps(out, indent=1, default=str))
