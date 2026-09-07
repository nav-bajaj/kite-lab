"""Does a price cap force winners out? Audit per strategy.

A cap must gate ENTRY only: a name bought under the cap that appreciates
through it should be held, not sold. Whether that actually happens is a
property of each strategy's architecture, not of the cap:

  OM25  -- score covers the whole universe, exit_buffer 20, so the
           engine's grandfather rule retains an appreciated holding.
  L6    -- same mechanism but exit_buffer 0, so retention is partial.
  COMBO -- make_combo_score_fn truncates each component to its top-12 and
           emits exactly 24 names at exit_buffer 0. A holding that
           appreciates through the cap drops out of the composite and is
           sold at the next rebalance. COMBO structurally cannot
           grandfather.

Two measurements per arm:
  1. Days a position survives after its price first crosses the cap.
     Short = the cap is forcing the exit.
  2. Realised P&L earned after crossing, i.e. what a forced-exit rule
     would have surrendered.

Usage:
    python tasks/minimum_capital_2026/forced_exit_audit.py --cap 4000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "runs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.loaders import load_price_panels

ARMS = {
    "OM25 cap": "om25_trades_cap4000.csv",
    "OM25 baseline": "om25_trades_baseline.csv",
    "L6 cap": "trades_l6_cap.csv",
    "L6 baseline": "trades_l6_baseline.csv",
    "COMBO cap": "trades_combo_cap.csv",
    "COMBO baseline": "trades_combo_baseline.csv",
}


def round_trips(path: Path) -> pd.DataFrame:
    """FIFO-average round trips from a trade log."""
    tr = pd.read_csv(path, parse_dates=["date"])
    pos, rows = {}, []
    for _, t in tr.sort_values("date").iterrows():
        s = t["symbol"]
        if t["side"] == "BUY":
            q = pos.setdefault(s, {"sh": 0, "cost": 0.0, "entry": t["date"]})
            q["sh"] += t["shares"]
            q["cost"] += t["shares"] * t["price"]
        else:
            q = pos.get(s)
            if not q or q["sh"] <= 0:
                continue
            cps = q["cost"] / q["sh"]
            n = min(t["shares"], q["sh"])
            rows.append({"symbol": s, "entry": q["entry"], "exit": t["date"],
                         "entry_px": cps, "exit_px": t["price"], "shares": n,
                         "pnl": n * (t["price"] - cps)})
            q["sh"] -= n
            q["cost"] -= n * cps
            if q["sh"] <= 0:
                pos.pop(s, None)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, default=4000)
    args = ap.parse_args()
    CAP = args.cap
    OUT.mkdir(exist_ok=True)

    close_panel, _ = load_price_panels(ROOT / "nse500_data")
    report = {"cap": CAP, "arms": {}}

    print(f"Cap Rs {CAP:,.0f}\n")
    print("Days a position survives AFTER its price first crosses the cap")
    print("(short = the cap forces the exit; long = the winner is kept)\n")
    print(f"{'arm':<16} {'n':>4} {'median':>8} {'mean':>7} {'max':>7} "
          f"{'<=21d':>7} {'P&L above cap':>16} {'% of realised':>14}")

    for arm, fname in ARMS.items():
        p = OUT / fname
        if not p.exists():
            print(f"{arm:<16}  [missing {fname} — run the cap studies first]")
            continue
        rt = round_trips(p)
        total_pnl = rt["pnl"].sum()
        days, pnl_above = [], 0.0
        for _, r in rt.iterrows():
            if r["symbol"] not in close_panel.columns:
                continue
            seg = close_panel.loc[r["entry"]:r["exit"], r["symbol"]]
            above = seg[seg > CAP]
            if above.empty:
                continue
            first = above.index[0]
            days.append((r["exit"] - first).days)
            pnl_above += r["shares"] * (r["exit_px"] - float(seg.loc[first]))
        if not days:
            continue
        a = np.array(days)
        row = {"n_crossed": int(len(a)), "n_round_trips": int(len(rt)),
               "median_days": float(np.median(a)), "mean_days": float(a.mean()),
               "max_days": int(a.max()),
               "pct_exit_within_21d": round((a <= 21).mean() * 100, 1),
               "pnl_above_cap": round(pnl_above, 2),
               "total_realised_pnl": round(float(total_pnl), 2),
               "pnl_above_pct_of_total": round(pnl_above / total_pnl * 100, 2)}
        report["arms"][arm] = row
        print(f"{arm:<16} {len(a):4d} {np.median(a):7.0f}d {a.mean():6.0f}d "
              f"{a.max():6.0f}d {(a<=21).mean()*100:6.0f}% "
              f"{pnl_above:15,.0f} {row['pnl_above_pct_of_total']:13.1f}%")

    (OUT / f"forced_exit_audit_cap{int(CAP)}.json").write_text(
        json.dumps(report, indent=2))
    print(f"\n[wrote] {OUT}/forced_exit_audit_cap{int(CAP)}.json")
    print("\nReading: OM25 keeps appreciated winners for months and never")
    print("force-exits. COMBO sells them within days. The in-sample cost")
    print("was negative for L6/COMBO only because their above-cap holdings")
    print("happened to be losers — a sample accident, not a safeguard.")


if __name__ == "__main__":
    main()
