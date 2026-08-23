"""Investor-level simulation of the dip25_ts20 feed.

Rs 20,00,000 starting 2023-01-01. NSE 500 (minus cliff artifacts),
entry = 5d return < -5% AND top-quartile 126d momentum score, slots by
momentum rank, cap 25, position = 4% of current equity (integer
shares), fill next day at OHLC/4 +/- 20bps, exit on momentum rank
< 0.35 or 20% trailing stop (close basis). Tax: 25% flat on net
realized gains each FY (Mar 31), losses carried forward. Cash earns 0.

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/investor_sim.py
"""

from __future__ import annotations

import json
import math
import os
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
from tasks.dip_vs_breakout_calls.experiment import CLIFF_SYMBOLS  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
CAPITAL0 = 2_000_000.0
POS_FRAC = 0.04
CAP = 25
SLIP = 0.002
EXIT_RANK = 0.35
TRAIL = 0.80
QUARTILE = 0.75
TAX_RATE = float(os.environ.get("TAX_RATE", "0.25"))
OUT_TAG = os.environ.get("OUT_TAG", "")
SIM_START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2026-08-19")
FY_ENDS = [pd.Timestamp(f"{y}-03-31") for y in (2023, 2024, 2025, 2026)]


def main():
    syms = [s for s in load_universe_symbols() if s not in CLIFF_SYMBOLS]
    panels = load_ohlc_panels(symbols=syms)
    close, trade = panels["close"], panels["trade"]
    rank = build_score_rank(close, 126)
    ret5 = close / close.shift(5) - 1.0
    sig = ((ret5 < -0.05) & (rank >= QUARTILE)).fillna(False)

    cal = close.index
    cl_v, tr_v = close.to_numpy(), trade.to_numpy()
    rk_v, sig_v = rank.to_numpy(), sig.to_numpy()
    cols = list(close.columns)
    start_i = int(np.searchsorted(cal, SIM_START))
    end_i = int(np.searchsorted(cal, END, side="right")) - 1

    fy_end_idx = set()
    for fy in FY_ENDS:
        j = int(np.searchsorted(cal, fy, side="right")) - 1
        if start_i <= j <= end_i:
            fy_end_idx.add(j)

    cash = CAPITAL0
    active = {}            # j(col) -> position
    ledger, curve = [], []
    fy_realized = 0.0
    loss_cf = 0.0
    tax_events = []

    def mtm(i):
        return cash + sum(p["shares"] * cl_v[i, j] for j, p in active.items()
                          if not np.isnan(cl_v[i, j]))

    for i in range(start_i, end_i + 1):
        d = cal[i]
        for j, pos in active.items():
            c = cl_v[i, j]
            if not np.isnan(c) and c > pos["peak"]:
                pos["peak"] = c
        # exits (signal today, fill tomorrow)
        for j in list(active):
            c = cl_v[i, j]
            if np.isnan(c) or i + 1 > end_i:
                continue
            r = rk_v[i, j]
            hit, reason = False, None
            if (not np.isnan(r)) and r < EXIT_RANK:
                hit, reason = True, "momentum_decay"
            elif c < active[j]["peak"] * TRAIL:
                hit, reason = True, "trailing_stop"
            if not hit:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            pos = active.pop(j)
            eff = px * (1 - SLIP)
            proceeds = pos["shares"] * eff
            pnl = proceeds - pos["cost"]
            cash += proceeds
            fy_realized += pnl
            ledger.append(dict(symbol=cols[j], entry_date=str(pos["entry_date"].date()),
                               exit_date=str(cal[i + 1].date()), shares=pos["shares"],
                               entry_px=round(pos["entry_px"], 2), exit_px=round(eff, 2),
                               pnl_rs=round(pnl, 0), pnl_pct=round(eff / pos["entry_px"] - 1, 4),
                               hold_td=i + 1 - pos["entry_i"], reason=reason,
                               status="closed"))
        # entries
        cand = [(j, rk_v[i, j]) for j in np.where(sig_v[i])[0]
                if j not in active and not np.isnan(rk_v[i, j])]
        cand.sort(key=lambda t: -t[1])
        eq_now = mtm(i)
        for j, r in cand:
            if len(active) >= CAP or i + 1 > end_i:
                break
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            eff = px * (1 + SLIP)
            invest = min(eq_now * POS_FRAC, cash)
            shares = int(invest // eff)
            if shares < 1:
                continue
            cost = shares * eff
            cash -= cost
            active[j] = dict(entry_date=cal[i + 1], entry_i=i + 1, shares=shares,
                             entry_px=eff, cost=cost, peak=cl_v[i, j])
        # FY-end tax on net realized gains
        if i in fy_end_idx:
            taxable = max(0.0, fy_realized - loss_cf)
            tax = taxable * TAX_RATE
            loss_cf = max(0.0, loss_cf - max(0.0, fy_realized)) + \
                max(0.0, -fy_realized)
            if tax > 0:
                cash -= tax
            tax_events.append(dict(fy_end=str(d.date()),
                                   realized=round(fy_realized, 0),
                                   loss_cf_after=round(loss_cf, 0),
                                   tax=round(tax, 0),
                                   equity_after=round(mtm(i), 0)))
            fy_realized = 0.0
        curve.append((d, mtm(i), len(active), cash))

    # open holdings at end
    holdings = []
    for j, pos in active.items():
        c = cl_v[end_i, j]
        holdings.append(dict(symbol=cols[j], entry_date=str(pos["entry_date"].date()),
                             shares=pos["shares"], entry_px=round(pos["entry_px"], 2),
                             last_close=round(float(c), 2),
                             value_rs=round(pos["shares"] * c, 0),
                             pnl_rs=round(pos["shares"] * c - pos["cost"], 0),
                             pnl_pct=round(c / pos["entry_px"] - 1, 4),
                             hold_td=end_i - pos["entry_i"],
                             peak_dist=round(c / pos["peak"] - 1, 4),
                             mom_rank=round(float(rk_v[end_i, j]), 2)))
    holdings.sort(key=lambda h: -h["pnl_pct"])

    cdf = pd.DataFrame(curve, columns=["date", "equity", "n_pos", "cash"]).set_index("date")
    ldf = pd.DataFrame(ledger)
    pd.DataFrame(holdings).to_csv(OUT_DIR / f"investor{OUT_TAG}_holdings.csv", index=False)
    ldf.to_csv(OUT_DIR / f"investor{OUT_TAG}_ledger.csv", index=False)
    cdf.to_csv(OUT_DIR / f"investor{OUT_TAG}_curve.csv")
    summary = dict(final_equity=round(float(cdf.equity.iloc[-1]), 0),
                   cash=round(float(cdf.cash.iloc[-1]), 0),
                   n_closed=len(ldf), n_open=len(holdings),
                   total_tax=round(sum(t["tax"] for t in tax_events), 0),
                   pending_fy_realized=round(fy_realized, 0),
                   loss_cf=round(loss_cf, 0),
                   tax_events=tax_events)
    (OUT_DIR / f"investor{OUT_TAG}_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nHoldings:", len(holdings))
    print(pd.DataFrame(holdings).to_string(index=False))


if __name__ == "__main__":
    main()
