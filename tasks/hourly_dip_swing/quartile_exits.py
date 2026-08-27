"""Exit hysteresis for lower-quartile dip entries.

QUARTILE_STUDY.md showed the published exit (momentum rank < 0.35) is
incoherent for Q2/Q3 entries -- the floor sits inside the entry band, so
positions are ejected on entry-adjacent noise (q3_std: 90% momq exits,
6-day median hold, -53% DD). This grids the exit rule instead, holding
the entry and everything else fixed.

Exit families (all keep the 20% trail unless the trail itself is the
variable):

  trail        trailing stop only, no rank exit          -- trail 15/20/25%
  floor_f      absolute rank floor f, well below the band -- f = 0.10, 0.20
  rel_d        entry-relative: rank < entry_rank - d      -- d = 0.15, 0.25
  ratchet_d    peak-relative: rank < max_rank_since_entry - d (a trailing
               stop on momentum rank itself)             -- d = 0.20, 0.30

Held fixed from dd_optimization.py's dip_6m_ts20: 5-day return < -5%
trigger, 126d vol-scaled momentum rank, cap 25, rank-priority slots,
signal at close / fill next day at OHLC/4 +/- 20bps, 2010-06-01 ->
2026-08-21, nse500 merged less CLIFF_SYMBOLS.

Run:  .venv/bin/python tasks/hourly_dip_swing/quartile_exits.py
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
CAP = 25
BANDS = {"q1": (0.75, 1.01), "q2": (0.50, 0.75), "q3": (0.25, 0.50)}


def simulate_exit(close, trade, sig, mom_rank, *, cap, end, trail,
                  band_lo, band_hi, exit_mode, exit_param, start=None):
    """One dip engine, parametric exit rule.

    exit_mode: "none"    -- trail only
               "floor"   -- rank < exit_param
               "rel"     -- rank < entry_rank - exit_param
               "ratchet" -- rank < (peak rank since entry) - exit_param
               "promote" -- (target, grace): after `grace` trading days the
                            position must have reached rank >= target at some
                            point, else exit; once promoted, hold on the
                            trail alone
    """
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
            r = rk_v[i, j]
            if not np.isnan(r) and r > pos["peak_rank"]:
                pos["peak_rank"] = r
        exits = []
        for j, pos in active.items():
            c = cl_v[i, j]
            if np.isnan(c):
                continue
            r = rk_v[i, j]
            hit, reason = False, "momq"
            if not np.isnan(r):
                if exit_mode == "floor":
                    hit = r < exit_param
                elif exit_mode == "rel":
                    hit = r < pos["entry_rank"] - exit_param
                elif exit_mode == "ratchet":
                    hit = r < pos["peak_rank"] - exit_param
                elif exit_mode == "promote":
                    target, grace = exit_param
                    hit = (i - pos["entry_i"] >= grace
                           and pos["peak_rank"] < target)
            if not hit and trail is not None and c < pos["peak"] * (1 - trail):
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
                          "reason": reason, "entry_rank": round(pos["entry_rank"], 4),
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
                         "peak": cl_v[i, j], "entry_rank": r, "peak_rank": r}
        counts[i - start_i] = len(active)

    for j, pos in active.items():
        c = cl_v[end_i, j]
        calls.append({"symbol": cols[j], "signal_date": pos["signal_date"],
                      "entry_date": pos["entry_date"], "exit_date": cal[end_i],
                      "reason": "open", "entry_rank": round(pos["entry_rank"], 4),
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls), pd.Series(counts, index=cal[start_i:end_i + 1]), n_skipped


def run_arm(name, close, trade, sig, rank, *, band, trail, mode, param,
            rows, yearlies):
    lo, hi = band
    print(f"[qx] {name}: band [{lo},{hi}) trail={trail} exit={mode}({param})")
    calls, counts, skipped = simulate_exit(
        close, trade, sig, rank, cap=CAP, end=END, trail=trail,
        band_lo=lo, band_hi=hi, exit_mode=mode, exit_param=param)
    calls.to_csv(OUT_DIR / f"calls_qx_{name}.csv", index=False)
    pv = slot_curve(calls, close, CAP, END)
    tail = pv.loc[pv.index >= TAIL_START]
    tail = tail / tail.iloc[0]
    closed = calls[calls.status == "closed"]
    p = closed.pnl_pct
    rows[name] = {**cadence(calls, END), **group_stats(calls),
                  **curve_metrics(pv),
                  **{f"tail_{k}": v for k, v in curve_metrics(tail).items()},
                  "band": f"{lo}-{hi}", "trail": trail,
                  "exit_mode": mode, "exit_param": str(param),
                  "pct_momq_exits": round(float((closed.reason == "momq").mean()) * 100, 1),
                  "pct_loss_gt10": round(float((p < -0.10).mean()) * 100, 1),
                  "pct_gain_gt20": round(float((p > 0.20).mean()) * 100, 1),
                  "exit_mix": dict(closed.reason.value_counts()),
                  "mean_active": round(float(counts.mean()), 1),
                  "skipped": skipped}
    yearlies[name] = yearly(calls, pv)
    pv.to_csv(OUT_DIR / f"curve_qx_{name}.csv")


def main_promote():
    """Addendum: the 'prove it' exit -- hold only if momentum rebuilds."""
    print("[qx] loading panels (nse500 merged)")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    keep = [c for c in panels["close"].columns if c not in CLIFF_SYMBOLS]
    close, trade = panels["close"][keep], panels["trade"][keep]
    dip = ((close / close.shift(5) - 1.0) < -0.05).fillna(False)
    rank = build_score_rank(close, 126)

    rows, yearlies = {}, {}
    for bname in ("q2", "q3"):
        for tag, target, grace in [("p75g20", 0.75, 20), ("p75g40", 0.75, 40),
                                   ("p65g20", 0.65, 20), ("p50g20", 0.50, 20)]:
            run_arm(f"{bname}_{tag}", close, trade, dip, rank,
                    band=BANDS[bname], trail=0.20, mode="promote",
                    param=(target, grace), rows=rows, yearlies=yearlies)

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.drop(columns=["exit_mix"]).to_csv(OUT_DIR / "summary_quartile_promote.csv")
    (OUT_DIR / "report_quartile_promote.json").write_text(
        json.dumps({"arms": rows, "yearly": yearlies}, indent=2, default=str))
    pd.set_option("display.width", 340)
    show = ["calls_per_year", "n_closed", "win_rate_pct", "mean_pnl_pct",
            "median_pnl_pct", "median_hold_td", "pct_momq_exits",
            "pct_loss_gt10", "pct_gain_gt20", "cagr_pct", "sharpe",
            "max_dd_pct", "calmar", "tail_cagr_pct", "tail_sharpe"]
    print("\n=== 'prove it' promotion exit for lower-quartile entries ===")
    print(df[show].to_string())


def main():
    print("[qx] loading panels (nse500 merged)")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    keep = [c for c in panels["close"].columns if c not in CLIFF_SYMBOLS]
    close, trade = panels["close"][keep], panels["trade"][keep]
    dip = ((close / close.shift(5) - 1.0) < -0.05).fillna(False)
    rank = build_score_rank(close, 126)

    exits = [
        ("ts15",      0.15, "none",    None),
        ("ts20",      0.20, "none",    None),
        ("ts25",      0.25, "none",    None),
        ("f10",       0.20, "floor",   0.10),
        ("f20",       0.20, "floor",   0.20),
        ("rel15",     0.20, "rel",     0.15),
        ("rel25",     0.20, "rel",     0.25),
        ("ratchet20", 0.20, "ratchet", 0.20),
        ("ratchet30", 0.20, "ratchet", 0.30),
    ]

    rows, yearlies = {}, {}
    # reference: the published feed, unchanged
    run_arm("q1_published", close, trade, dip, rank, band=BANDS["q1"],
            trail=0.20, mode="floor", param=0.35, rows=rows, yearlies=yearlies)
    for bname in ("q2", "q3"):
        for ename, trail, mode, param in exits:
            run_arm(f"{bname}_{ename}", close, trade, dip, rank,
                    band=BANDS[bname], trail=trail, mode=mode, param=param,
                    rows=rows, yearlies=yearlies)
    # does the same hysteresis help the TOP sleeve too? if yes it is not a
    # lower-quartile fix, it is just a better exit
    for ename, trail, mode, param in [("ts20", 0.20, "none", None),
                                      ("ratchet20", 0.20, "ratchet", 0.20),
                                      ("rel25", 0.20, "rel", 0.25)]:
        run_arm(f"q1_{ename}", close, trade, dip, rank, band=BANDS["q1"],
                trail=trail, mode=mode, param=param, rows=rows, yearlies=yearlies)

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.drop(columns=["exit_mix"]).to_csv(OUT_DIR / "summary_quartile_exits.csv")
    (OUT_DIR / "report_quartile_exits.json").write_text(
        json.dumps({"arms": rows, "yearly": yearlies}, indent=2, default=str))
    pd.set_option("display.width", 340)
    show = ["calls_per_year", "n_closed", "win_rate_pct", "mean_pnl_pct",
            "median_pnl_pct", "p5_pnl_pct", "p95_pnl_pct", "median_hold_td",
            "pct_momq_exits", "pct_loss_gt10", "pct_gain_gt20",
            "cagr_pct", "sharpe", "max_dd_pct", "calmar",
            "tail_cagr_pct", "tail_sharpe", "mean_active"]
    print("\n=== exit hysteresis for lower-quartile dip entries ===")
    print(df[show].to_string())


if __name__ == "__main__":
    if "--promote" in sys.argv:
        main_promote()
    else:
        main()
