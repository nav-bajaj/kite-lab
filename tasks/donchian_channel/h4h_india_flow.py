"""H4h — India call-flow grid: more calls/year for xr35 / no-stop.

Fixed: NSE 500, 126d momentum, exit rank 0.35, no stop, next-day OHLC/4
+/- 20bps. Varied per TASKS.md Phase 5g:

  cap50 (baseline) / cap75 / cap100 / cap150   entry 20d, floor 0.75
  cap100_e10                                    entry 10d channel
  cap100_q60                                    momentum floor 0.60

Adds product-cadence stats: closed calls/yr, mean new calls per week,
share of weeks with at least one new call.

Run:
    python tasks/donchian_channel/h4h_india_flow.py
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
    group_stats, slot_curve, TAIL_START, SLIPPAGE,
)

EXIT_RANK = 0.35


def simulate(close, trade, cross, mom_rank, *, cap: int, floor: float):
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
            if (not pd.isna(r)) and r < EXIT_RANK:
                exits.append(sym)
        for sym in exits:
            if i + 1 > end_i:
                continue
            px = trade.iat[i + 1, col[sym]]
            if pd.isna(px) or px <= 0:
                continue
            pos = active.pop(sym)
            calls.append({"symbol": sym, "entry_date": pos["entry_date"],
                          "entry_px": pos["entry_px"], "exit_date": cal[i + 1],
                          "pnl_pct": px * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                          "hold_td": i + 1 - pos["entry_i"],
                          "status": "closed"})
        row = cross.iloc[i]
        cands = []
        for sym in row.index[row.values]:
            if sym in active:
                continue
            r = mom_rank.iat[i, col[sym]]
            if pd.isna(r) or r < floor:
                continue
            cands.append((sym, r))
        cands.sort(key=lambda t: -t[1])
        for sym, r in cands:
            if len(active) >= cap or i + 1 > end_i:
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
        calls.append({"symbol": sym, "entry_date": pos["entry_date"],
                      "entry_px": pos["entry_px"], "exit_date": last,
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls), pd.Series(counts, dtype=float)


def cadence(calls) -> dict:
    e = pd.to_datetime(calls["entry_date"])
    wk = e.groupby(e.dt.to_period("W")).size()
    all_weeks = pd.period_range(START, END, freq="W")
    wk = wk.reindex(all_weeks, fill_value=0)
    return {"calls_per_year": round(len(calls[calls.status == "closed"]) /
                                    ((pd.Timestamp(END) - pd.Timestamp(START)).days / 365.25), 1),
            "new_per_week": round(float(wk.mean()), 2),
            "pct_weeks_with_call": round(float((wk > 0).mean()) * 100, 1)}


def main():
    out_dir = ROOT / "tasks/donchian_channel/runs" / \
        f"h4h_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[h4h] loading India panels")
    p = load_ohlc_panels(symbols=load_universe_symbols())
    close, trade, high = p["close"], p["trade"], p["high"]
    cross20 = breakout_cross(close, donchian_upper(high, 20)).fillna(False)
    cross10 = breakout_cross(close, donchian_upper(high, 10)).fillna(False)
    rank = build_score_rank(close, 126)

    arms = [
        ("cap50",      cross20, 50,  0.75),
        ("cap75",      cross20, 75,  0.75),
        ("cap100",     cross20, 100, 0.75),
        ("cap150",     cross20, 150, 0.75),
        ("cap100_e10", cross10, 100, 0.75),
        ("cap100_q60", cross20, 100, 0.60),
    ]
    rows = {}
    for arm, cross, cap, floor in arms:
        print(f"  simulating {arm}")
        calls, counts = simulate(close, trade, cross, rank, cap=cap, floor=floor)
        calls.to_csv(out_dir / f"calls_{arm}.csv", index=False)
        pv = slot_curve(calls, close, cap)
        tail = pv.loc[pv.index >= TAIL_START]
        tail = tail / tail.iloc[0]
        rows[arm] = {**cadence(calls), **group_stats(calls),
                     **curve_metrics(pv),
                     **{f"tail_{k}": v for k, v in curve_metrics(tail).items()},
                     "mean_active": round(float(counts.mean()), 1),
                     "pct_days_full": round(float((counts >= cap).mean()) * 100, 1)}

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.to_csv(out_dir / "summary.csv")
    pd.set_option("display.width", 260)
    show = ["calls_per_year", "new_per_week", "pct_weeks_with_call",
            "n_closed", "win_rate_pct", "mean_pnl_pct", "median_pnl_pct",
            "median_hold_td", "cagr_pct", "sharpe", "max_dd_pct",
            "tail_cagr_pct", "tail_sharpe", "pct_days_full"]
    print("\n=== H4h India flow grid (xr35, no stop) ===")
    print(df[show].to_string())
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
