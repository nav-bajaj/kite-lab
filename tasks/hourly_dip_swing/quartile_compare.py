"""Quartile study: the daily dip feed on the TOP vs THIRD momentum quartile.

Changes exactly one thing versus the daily arm from dd_optimization.py
(dip_6m_ts20): the momentum sleeve the dip entry is allowed to buy.

  Q1 (top)    rank >= 0.75          -- the published feed
  Q2 (second) 0.50 <= rank < 0.75   -- context row
  Q3 (third)  0.25 <= rank < 0.50   -- the founder's question

Everything else is the dip_vs_breakout_calls engine untouched: 5-day
return < -5% dip trigger, 126d vol-scaled momentum rank, cap 25,
rank-priority slots, signal at close / fill next day at OHLC/4 +/-
20bps, 20% trailing stop, window 2010-06-01 -> 2026-08-21, nse500
merged universe with CLIFF_SYMBOLS excluded.

One wrinkle the swap forces: the momentum-decay exit fires at rank <
0.35, which sits INSIDE the Q3 band (0.25-0.50), so a literal one-thing
change makes Q3 positions exit the moment they drift below 0.35. Both
readings are run:
  *_std   exit rank 0.35 unchanged (literal one-thing-changed)
  *_band  exit rank shifted with the sleeve (lo - 0.40, floored at 0),
          i.e. the same 0.40 of rank slack the top-quartile arm gets

Run:  .venv/bin/python tasks/hourly_dip_swing/quartile_compare.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols,
)
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402
from tasks.dip_vs_breakout_calls.experiment import (  # noqa: E402
    slot_curve, curve_metrics, group_stats, cadence, yearly,
    CLIFF_SYMBOLS, TAIL_START, SLIPPAGE, START,
)

OUT_DIR = Path(__file__).resolve().parent
END = pd.Timestamp("2026-08-21")
TRAIL = 0.20
CAP = 25
SLEEVE_LB = 126


def simulate_band(close, trade, sig, mom_rank, *, cap, end, trail,
                  band_lo, band_hi, exit_rank, start=None):
    """dd_optimization.simulate_trail with the sleeve as a band, not a floor."""
    cal = close.index
    cl_v, tr_v = close.to_numpy(), trade.to_numpy()
    rk_v, sig_v = mom_rank.to_numpy(), sig.to_numpy()
    cols = close.columns
    start_i = int(np.searchsorted(cal, start if start is not None else START))
    end_i = int(np.searchsorted(cal, end, side="right")) - 1
    active, calls, n_skipped = {}, [], 0
    counts = np.zeros(end_i + 1 - start_i)

    for i in range(start_i, end_i + 1):
        for j, pos in active.items():
            c = cl_v[i, j]
            if not np.isnan(c) and c > pos["peak"]:
                pos["peak"] = c
        exits = []
        for j, pos in active.items():
            c = cl_v[i, j]
            if np.isnan(c):
                continue
            r = rk_v[i, j]
            hit = (not np.isnan(r)) and r < exit_rank
            reason = "momq"
            if trail is not None and not hit and c < pos["peak"] * (1 - trail):
                hit, reason = True, "trail"
            if hit:
                exits.append((j, reason))
        for j, reason in exits:
            if i + 1 > end_i:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            pos = active.pop(j)
            calls.append({"symbol": cols[j], "signal_date": pos["signal_date"],
                          "entry_date": pos["entry_date"], "exit_date": cal[i + 1],
                          "reason": reason,
                          "pnl_pct": px * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                          "hold_td": i + 1 - pos["entry_i"], "status": "closed"})
        cand_j = np.where(sig_v[i])[0]
        cands = [(j, rk_v[i, j]) for j in cand_j
                 if j not in active and not np.isnan(rk_v[i, j])
                 and band_lo <= rk_v[i, j] < band_hi]
        cands.sort(key=lambda t: -t[1])
        for j, r in cands:
            if len(active) >= cap:
                n_skipped += sum(1 for jj, _ in cands if jj not in active)
                break
            if i + 1 > end_i:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            active[j] = {"signal_date": cal[i], "entry_date": cal[i + 1],
                         "entry_i": i + 1, "entry_px": px * (1 + SLIPPAGE),
                         "peak": cl_v[i, j]}
        counts[i - start_i] = len(active)

    for j, pos in active.items():
        c = cl_v[end_i, j]
        calls.append({"symbol": cols[j], "signal_date": pos["signal_date"],
                      "entry_date": pos["entry_date"], "exit_date": cal[end_i],
                      "reason": "open",
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls), pd.Series(counts, index=cal[start_i:end_i + 1]), n_skipped


def run_arm(name, close, trade, sig, rank, *, band, exit_rank, rows, yearlies):
    lo, hi = band
    print(f"[q] simulating {name}: band [{lo}, {hi}), exit rank < {exit_rank}")
    calls, counts, skipped = simulate_band(
        close, trade, sig, rank, cap=CAP, end=END, trail=TRAIL,
        band_lo=lo, band_hi=hi, exit_rank=exit_rank)
    calls.to_csv(OUT_DIR / f"calls_q_{name}.csv", index=False)
    pv = slot_curve(calls, close, CAP, END)
    tail = pv.loc[pv.index >= TAIL_START]
    tail = tail / tail.iloc[0]
    closed = calls[calls.status == "closed"]
    mix = dict(closed.reason.value_counts()) if len(closed) else {}
    rows[name] = {**cadence(calls, END), **group_stats(calls),
                  **curve_metrics(pv),
                  **{f"tail_{k}": v for k, v in curve_metrics(tail).items()},
                  "band_lo": lo, "band_hi": hi, "exit_rank": exit_rank,
                  "pct_trail_exits": round(
                      float((closed.reason == "trail").mean()) * 100, 1) if len(closed) else None,
                  "exit_mix": mix,
                  "mean_active": round(float(counts.mean()), 1),
                  "skipped": skipped}
    yearlies[name] = yearly(calls, pv)
    pv.to_csv(OUT_DIR / f"curve_q_{name}.csv")
    return rows[name]


def main():
    print("[q] loading panels (nse500 merged)")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    keep = [c for c in panels["close"].columns if c not in CLIFF_SYMBOLS]
    close, trade = panels["close"][keep], panels["trade"][keep]
    print(f"[q] {len(keep)} symbols, {close.index[0].date()} -> {close.index[-1].date()}")

    dip = ((close / close.shift(5) - 1.0) < -0.05).fillna(False)
    rank = build_score_rank(close, SLEEVE_LB)

    # candidate supply per band: how many dip signals each sleeve sees
    r_at_sig = rank.where(dip)
    supply = {}
    for name, (lo, hi) in {"q1": (0.75, 1.01), "q2": (0.50, 0.75),
                           "q3": (0.25, 0.50)}.items():
        supply[name] = int(((r_at_sig >= lo) & (r_at_sig < hi)).to_numpy().sum())
    print(f"[q] dip signals by sleeve: {supply}")

    rows, yearlies = {}, {}
    arms = [
        ("q1_top",   (0.75, 1.01), 0.35),
        ("q2_std",   (0.50, 0.75), 0.35),
        ("q2_band",  (0.50, 0.75), 0.10),
        ("q3_std",   (0.25, 0.50), 0.35),
        ("q3_band",  (0.25, 0.50), 0.00),
    ]
    for name, band, xr in arms:
        run_arm(name, close, trade, dip, rank, band=band, exit_rank=xr,
                rows=rows, yearlies=yearlies)

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.drop(columns=["exit_mix"]).to_csv(OUT_DIR / "summary_quartile.csv")
    (OUT_DIR / "report_quartile.json").write_text(json.dumps(
        {"supply": supply, "arms": rows, "yearly": yearlies},
        indent=2, default=str))

    pd.set_option("display.width", 320)
    show = ["calls_per_year", "n_closed", "win_rate_pct", "mean_pnl_pct",
            "median_pnl_pct", "p5_pnl_pct", "p95_pnl_pct", "median_hold_td",
            "pct_trail_exits", "cagr_pct", "sharpe", "max_dd_pct", "calmar",
            "tail_cagr_pct", "tail_sharpe", "tail_max_dd_pct", "mean_active"]
    print("\n=== dip feed: top quartile vs third quartile momentum sleeve ===")
    print(df[show].to_string())


if __name__ == "__main__":
    main()
