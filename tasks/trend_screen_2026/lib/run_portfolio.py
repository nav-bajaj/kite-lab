"""§7 — could the trend screen be a portfolio?

Reuses `breakout_calls_2026`'s book simulator unchanged, so the answer is
directly comparable to that task's: same daily mark-to-market, same ADV
participation cap, same no-same-name-twice rule, same pre-committed gates.

One deliberate difference in sizing. The breakout book sized by risk
(risk_pct / stop distance) because it had a hard stop. The trend entry's best
exit is the 150-day trail with no hard stop, so risk-based sizing is
undefined — positions are equal-weight at 1/N instead. That is also the
frame the expectancy work pointed at: a subscriber buys similar amounts per
name, so money-per-trade is the relevant measure, not return-per-unit-risk.
"""
from __future__ import annotations

import os
import sys
import numpy as np
import pandas as pd

REPO = "/Users/navdeep/kite-lab"
sys.path.insert(0, f"{REPO}/tasks/breakout_calls_2026/lib")
from exits import load_panel, simulate  # noqa: E402
from book import build_book, era_sharpe  # noqa: E402

TASK = f"{REPO}/tasks/trend_screen_2026"
SLIP = 0.002
ERAS = [(2006, 2012, "06-12"), (2013, 2019, "13-19"), (2020, 2026, "20-26")]


def build_trades(sel, panels, stop_pct):
    cfg = dict(stop_mode="fixed", stop_pct=stop_pct, trail="ma150",
               partial_r=None, timestop=None, atr_mult=3.0)
    rows = []
    for sym, g in sel.groupby("symbol"):
        p = panels.get(sym)
        if p is None:
            continue
        n = len(p["c"])
        busy = -1
        for dt, rk in zip(g.date, g.rk):
            i = p["pos"].get(pd.Timestamp(dt))
            if i is None or i + 1 >= n or i <= busy:
                continue
            e = i + 1
            entry = p["o"][e] * (1 + SLIP)
            out = simulate(p, e, entry, entry * (1 - stop_pct), cfg)
            if out is None:
                continue
            ret, r, hold, why = out
            busy = e + hold
            rows.append(dict(symbol=sym, entry_date=p["dates"][e],
                             exit_date=p["dates"][min(e + hold, n - 1)],
                             entry=entry, stop=entry * (1 - stop_pct),
                             exit_px=entry * (1 + ret), ret=ret, r=r,
                             final_depth=float(rk)))   # sort key: best rank first
    return pd.DataFrame(rows)


def main():
    os.chdir(REPO)
    F = pd.read_parquet(f"{TASK}/data/features_ranked.parquet")
    B = F[F.state.isin(["LEADING", "EXTENDED"])].dropna(subset=["above_low"]).copy()
    B["rk"] = B.groupby("ym")["above_low"].rank(ascending=False, method="first")
    panels = {s: p for s in sorted(B.symbol.unique()) if (p := load_panel(s)) is not None}
    print(f"{len(panels)} panels", flush=True)

    pit = pd.read_parquet("tasks/breakout_calls_2026/data/pit_universe.parquet",
                          columns=["date", "symbol", "adv"]).drop_duplicates(["symbol", "date"])
    pan = {s: {"close": pd.Series(panels[s]["c"], index=panels[s]["dates"])} for s in panels}
    bench = pd.read_csv("data/master/benchmarks/NIFTY_500.csv", parse_dates=["date"])
    cal = pd.DatetimeIndex(sorted(bench.date.unique()))
    cal = cal[(cal >= "2006-01-01") & (cal <= "2026-09-09")]

    for stop_pct, slab in [(0.99, "trail only"), (0.15, "15% stop")]:
        for cap, clab in [(200, "whole list"), (50, "top 50"), (20, "top 20")]:
            tr = build_trades(B[B.rk <= cap], panels, stop_pct)
            tr = tr.merge(pit, left_on=["symbol", "entry_date"],
                          right_on=["symbol", "date"], how="left")
            tr["adv"] = tr.adv.fillna(tr.adv.median())
            tr = tr.drop(columns=["date"]).sort_values("entry_date").reset_index(drop=True)
            print(f"\n=== {clab}, {slab} — {len(tr):,} candidate trades ===", flush=True)
            print(f"{'slots':>6}{'CAGR':>8}{'maxDD':>8}{'Sharpe':>8}{'taken':>7}{'expo':>6}   era Sharpes")
            for slots in [10, 15, 20, 25]:
                res = [build_book(tr, pan, cal, slots=slots, risk_pct=1.0,
                                  capital=1e7, seed=s, order="tight") for s in range(3)]
                cg = np.median([r["cagr"] for r in res])
                dd = np.median([r["maxdd"] for r in res])
                sh = np.median([r["sharpe"] for r in res])
                tk = np.median([r["taken"] for r in res])
                ex = np.median([r["exposure"] for r in res])
                e = era_sharpe(res[0]["equity"], ERAS)
                print(f"{slots:>6}{cg:>7.1%}{dd:>7.1%}{sh:>8.2f}{tk:>7.0f}{ex:>6.0%}   "
                      + "  ".join(f"{k} {v:.2f}" for k, v in e.items()), flush=True)


if __name__ == "__main__":
    main()
