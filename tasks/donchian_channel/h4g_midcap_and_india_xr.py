"""H4g — (A) US mid-caps-only stats, (B) exit-rank 0.35 test on India.

A: SP400-only symbols (expanded universe minus SP500/NDX), 20d breakout,
   top-quartile 126d momentum, cap 50, no stop, exit rank {0.50, 0.35}.
B: NSE 500, same entry, cap 50, grid exit rank {0.50, 0.35} x stop
   {none, fixed 20% trail} -- the 0.50 arms replicate h4c baselines and
   add tail metrics so all four cells are comparable.

Both report full window and the 2023-07..2026-05 tail.

Run:
    python tasks/donchian_channel/h4g_midcap_and_india_xr.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols, donchian_upper, breakout_cross,
)
from tasks.donchian_channel.h4c_combo_grid import (  # noqa: E402
    build_score_rank, curve_metrics, START, END,
)
from tasks.donchian_channel.h4f_us_marketfit import (  # noqa: E402
    group_stats, slot_curve, TAIL_START, QUARTILE, SLIPPAGE,
)

CAP = 50


def simulate(close, trade, cross, mom_rank, *, stop: str, exit_rank: float):
    cal = close.index
    col = {s: j for j, s in enumerate(close.columns)}
    start_i = cal.get_loc(cal[cal >= START][0])
    end_i = cal.get_loc(cal[cal <= END][-1])
    active, calls = {}, []
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
            if stop == "pct20" and not hit:
                hit = c < pos["peak"] * 0.80
            if hit:
                exits.append(sym)
        for sym in exits:
            if i + 1 > end_i:
                continue
            px = trade.iat[i + 1, col[sym]]
            if pd.isna(px) or px <= 0:
                continue
            pos = active.pop(sym)
            calls.append({"symbol": sym, "signal_date": d,
                          "entry_date": pos["entry_date"],
                          "entry_px": pos["entry_px"],
                          "exit_date": cal[i + 1],
                          "pnl_pct": px * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
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
            if len(active) >= CAP or i + 1 > end_i:
                break
            px = trade.iat[i + 1, col[sym]]
            if pd.isna(px) or px <= 0:
                continue
            active[sym] = {"entry_date": cal[i + 1], "entry_i": i + 1,
                           "entry_px": px * (1 + SLIPPAGE),
                           "peak": close.iat[i, col[sym]]}
        counts[d] = len(active)
    last = cal[end_i]
    for sym, pos in active.items():
        c = close.iat[end_i, col[sym]]
        calls.append({"symbol": sym, "signal_date": None,
                      "entry_date": pos["entry_date"],
                      "entry_px": pos["entry_px"], "exit_date": last,
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls), pd.Series(counts, dtype=float)


def run_block(name, close, trade, high, arms):
    cross = breakout_cross(close, donchian_upper(high, 20)).fillna(False)
    rank = build_score_rank(close, 126)
    rows = {}
    for arm, stop, xr in arms:
        print(f"  {name}: {arm}")
        calls, counts = simulate(close, trade, cross, rank,
                                 stop=stop, exit_rank=xr)
        pv = slot_curve(calls, close, CAP)
        tail = pv.loc[pv.index >= TAIL_START]
        tail = tail / tail.iloc[0]
        rows[arm] = {**group_stats(calls), **curve_metrics(pv),
                     **{f"tail_{k}": v for k, v in curve_metrics(tail).items()},
                     "mean_active": round(float(counts.mean()), 1)}
    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    pd.set_option("display.width", 250)
    show = ["n_closed", "win_rate_pct", "mean_pnl_pct", "median_pnl_pct",
            "median_hold_td", "cagr_pct", "sharpe", "max_dd_pct", "calmar",
            "tail_cagr_pct", "tail_sharpe", "tail_max_dd_pct", "mean_active"]
    print(f"\n=== {name} ===")
    print(df[show].to_string())
    return df


def main():
    out_dir = ROOT / "tasks/donchian_channel/runs" / \
        f"h4g_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[h4g] A: US mid caps only")
    old = set(pd.read_csv(ROOT / "data/static/us_equities_universe.csv")
              ["Symbol"].astype(str))
    exp = pd.read_csv(ROOT / "tasks/donchian_channel/us_expanded_universe.csv")
    mid = sorted(s for s in exp["Symbol"].astype(str) if s not in old)
    print(f"  {len(mid)} SP400-only symbols")
    p = load_ohlc_panels(prices_dir=ROOT / "us_equities_data", symbols=mid)
    a = run_block("US mid caps only (cap 50, no stop)",
                  p["close"], p["trade"], p["high"],
                  [("mid_xr50", "none", 0.50), ("mid_xr35", "none", 0.35)])
    a.to_csv(out_dir / "summary_us_midonly.csv")

    print("\n[h4g] B: India exit-rank grid")
    nse = load_universe_symbols()
    p = load_ohlc_panels(symbols=nse)
    b = run_block("India NSE 500 (cap 50)",
                  p["close"], p["trade"], p["high"],
                  [("in_xr50_nostop", "none", 0.50),
                   ("in_xr35_nostop", "none", 0.35),
                   ("in_xr50_ts20", "pct20", 0.50),
                   ("in_xr35_ts20", "pct20", 0.35)])
    b.to_csv(out_dir / "summary_india_xr.csv")
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
