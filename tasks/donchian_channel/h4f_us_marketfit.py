"""H4f — US market-fit grid on the expanded universe (large + mid caps).

Universe: S&P 500 union Nasdaq 100 union S&P 400 (916 symbols, current
snapshots, yfinance adjusted prices). Entry unchanged (fresh 20-day-high
cross, top-quartile 126d momentum, rank-priority slots). Grid
(pre-registered, TASKS.md Phase 5f):

  cap        {50, 100}
  stop       {none, atr10 = close < peak * (1 - 10 * atr20_pct(signal))}
  exit rank  {0.50, 0.35}

Baseline arm = cap50/none/0.50 (the 5e winner rules) isolates the
universe effect. Overfit guard: every arm reports the full window AND
the 2023-07-01..2026-05-08 tail separately.

Run:
    python tasks/donchian_channel/h4f_us_marketfit.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, donchian_upper, breakout_cross,
)
from tasks.donchian_channel.h4c_combo_grid import (  # noqa: E402
    build_score_rank, curve_metrics, START, END,
)

QUARTILE = 0.75


def group_stats(calls):
    closed = calls[calls.status == "closed"]
    p = closed.pnl_pct
    return {"n_closed": int(len(closed)),
            "n_open": int((calls.status == "open").sum()),
            "win_rate_pct": round(float((p > 0).mean()) * 100, 1),
            "mean_pnl_pct": round(float(p.mean()) * 100, 2),
            "median_pnl_pct": round(float(p.median()) * 100, 2),
            "p5_pnl_pct": round(float(p.quantile(.05)) * 100, 1),
            "p95_pnl_pct": round(float(p.quantile(.95)) * 100, 1),
            "median_hold_td": int(closed.hold_td.median())}
SLIPPAGE = 0.002
TAIL_START = pd.Timestamp("2023-07-01")


def simulate(close, trade, cross, mom_rank, atr_pct, *,
             cap: int, stop: str, exit_rank: float):
    cal = close.index
    col = {s: j for j, s in enumerate(close.columns)}
    start_i = cal.get_loc(cal[cal >= START][0])
    end_i = cal.get_loc(cal[cal <= END][-1])
    active, calls, n_skipped = {}, [], 0
    counts = {}

    for i in range(start_i, end_i + 1):
        d = cal[i]
        for sym, pos in active.items():
            c = close.iat[i, col[sym]]
            if not pd.isna(c) and c > pos["peak"]:
                pos["peak"] = c
        exits = []
        for sym, pos in active.items():
            c = close.iat[i, col[sym]]
            if pd.isna(c):
                continue
            r = mom_rank.iat[i, col[sym]]
            hit = (not pd.isna(r)) and r < exit_rank
            if stop == "atr10" and not hit:
                a = atr_pct.iat[i, col[sym]]
                a = 0.02 if pd.isna(a) else a
                hit = c < pos["peak"] * (1 - 10 * a)
            if hit:
                exits.append(sym)
        for sym in exits:
            if i + 1 > end_i:
                continue
            px = trade.iat[i + 1, col[sym]]
            if pd.isna(px) or px <= 0:
                continue
            pos = active.pop(sym)
            eff = px * (1 - SLIPPAGE)
            calls.append({**{k: pos[k] for k in ("symbol", "signal_date",
                                                 "entry_date", "entry_px")},
                          "exit_date": cal[i + 1],
                          "pnl_pct": eff / pos["entry_px"] - 1.0,
                          "hold_td": i + 1 - pos["entry_i"],
                          "status": "closed"})
        row = cross.iloc[i]
        cands = []
        for sym in row.index[row.values]:
            if sym in active:
                continue
            r = mom_rank.iat[i, col[sym]]
            if pd.isna(r) or r < QUARTILE:
                continue
            cands.append((sym, r))
        cands.sort(key=lambda t: -t[1])
        for sym, r in cands:
            if len(active) >= cap:
                n_skipped += sum(1 for s, _ in cands if s not in active)
                break
            if i + 1 > end_i:
                continue
            px = trade.iat[i + 1, col[sym]]
            if pd.isna(px) or px <= 0:
                continue
            active[sym] = {"symbol": sym, "signal_date": d,
                           "entry_date": cal[i + 1], "entry_i": i + 1,
                           "entry_px": px * (1 + SLIPPAGE),
                           "peak": close.iat[i, col[sym]]}
        counts[d] = len(active)

    last = cal[end_i]
    for sym, pos in active.items():
        c = close.iat[end_i, col[sym]]
        calls.append({**{k: pos[k] for k in ("symbol", "signal_date",
                                             "entry_date", "entry_px")},
                      "exit_date": last,
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls), pd.Series(counts, dtype=float), n_skipped


def slot_curve(calls, close, slots):
    cal = close.loc[(close.index >= START) & (close.index <= END)].index
    rets = close.pct_change()
    tot = pd.Series(0.0, index=cal)
    for _, c in calls.iterrows():
        sl = rets.loc[c["entry_date"]:c["exit_date"], c["symbol"]].reindex(cal).dropna()
        if len(sl) <= 1:
            continue
        tot.loc[sl.index[1:]] += sl.iloc[1:]
    return (1 + tot / slots).cumprod()


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/donchian_channel/runs" / f"h4f_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[h4f] loading expanded US panels")
    uni = pd.read_csv(ROOT / "tasks/donchian_channel/us_expanded_universe.csv")
    symbols = sorted(uni["Symbol"].dropna().astype(str).unique())
    panels = load_ohlc_panels(prices_dir=ROOT / "us_equities_data",
                              symbols=symbols)
    close, trade, high = panels["close"], panels["trade"], panels["high"]
    print(f"  panel {close.shape}, {close.index.min().date()} .. {close.index.max().date()}")

    cross = breakout_cross(close, donchian_upper(high, 20)).fillna(False)
    rank = build_score_rank(close, 126)
    atr_pct = close.pct_change().rolling(20).std()

    rows = {}
    for cap in (50, 100):
        for stop in ("none", "atr10"):
            for xr in (0.50, 0.35):
                arm = f"cap{cap}_{stop}_xr{int(xr*100)}"
                print(f"  simulating {arm}")
                calls, counts, skipped = simulate(
                    close, trade, cross, rank, atr_pct,
                    cap=cap, stop=stop, exit_rank=xr)
                calls.to_csv(out_dir / f"calls_{arm}.csv", index=False)
                pv = slot_curve(calls, close, cap)
                tail_pv = pv.loc[pv.index >= TAIL_START]
                tail_pv = tail_pv / tail_pv.iloc[0]
                rows[arm] = {
                    "cap": cap, "stop": stop, "exit_rank": xr,
                    **group_stats(calls), **curve_metrics(pv),
                    **{f"tail_{k}": v for k, v in curve_metrics(tail_pv).items()},
                    "mean_active": round(float(counts.mean()), 1),
                    "pct_days_full": round(float((counts >= cap).mean()) * 100, 1),
                    "skipped": int(skipped),
                }

    summary = pd.DataFrame(rows).T
    summary.index.name = "arm"
    summary.to_csv(out_dir / "summary.csv")
    pd.set_option("display.width", 250)
    print("\n=== H4f expanded-universe grid ===")
    show = ["n_closed", "win_rate_pct", "mean_pnl_pct", "median_pnl_pct",
            "median_hold_td", "cagr_pct", "sharpe", "max_dd_pct", "calmar",
            "tail_cagr_pct", "tail_sharpe", "tail_max_dd_pct",
            "mean_active", "pct_days_full"]
    print(summary[show].to_string())
    (out_dir / "config.json").write_text(json.dumps({
        "universe": "SP500+NDX+SP400 (916 symbols, yfinance)",
        "grid": "cap{50,100} x stop{none,atr10} x exit_rank{0.50,0.35}",
        "lookback": 126, "tail_start": str(TAIL_START.date()),
    }, indent=2))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
