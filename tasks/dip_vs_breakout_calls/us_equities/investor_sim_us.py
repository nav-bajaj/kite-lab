"""Investor-level simulation of the dip25_trend feed on US equities.

$100,000 starting 2023-01-01. SP500 union Nasdaq 100 universe, entry =
5d return < -5% AND close > 200DMA AND top-quartile 126d momentum
score, slots by momentum rank, cap 25, position = 4% of current equity
(integer shares), fill next day at OHLC/4 +/- 20bps, exit on momentum
rank < 0.35 only (no trailing stop -- the trail subtracts on US, see
RESULTS_US.md). Tax: 25% flat on net realized gains each calendar year
(Dec 31), losses carried forward. Cash earns 0.

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/us_equities/investor_sim_us.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import load_ohlc_panels  # noqa: E402
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
PRICES_DIR = ROOT / "us_equities_data"
UNIVERSE_CSV = ROOT / "data/static/us_equities_universe.csv"
CAPITAL0 = 100_000.0
POS_FRAC = 0.04
CAP = 25
SLIP = 0.002
EXIT_RANK = 0.35
QUARTILE = 0.75
TAX_RATE = 0.25
SIM_START = pd.Timestamp(os.environ.get("SIM_START", "2023-01-01"))
END = pd.Timestamp(os.environ.get("SIM_END", "2026-07-23"))
OUT_TAG = os.environ.get("OUT_TAG", "")
YEAR_ENDS = [pd.Timestamp(f"{y}-12-31")
             for y in range(SIM_START.year, END.year + 1)
             if pd.Timestamp(f"{y}-12-31") <= END + pd.Timedelta(days=3)]


def main():
    syms = sorted(pd.read_csv(UNIVERSE_CSV)["Symbol"].dropna().astype(str).unique())
    panels = load_ohlc_panels(prices_dir=PRICES_DIR, symbols=syms)
    close, trade = panels["close"], panels["trade"]
    rank = build_score_rank(close, 126)
    ret5 = close / close.shift(5) - 1.0
    s200 = close.rolling(200).mean()
    sig = ((ret5 < -0.05) & (close > s200) & (rank >= QUARTILE)).fillna(False)

    cal = close.index
    cl_v, tr_v = close.to_numpy(), trade.to_numpy()
    rk_v, sig_v = rank.to_numpy(), sig.to_numpy()
    cols = list(close.columns)
    start_i = int(np.searchsorted(cal, SIM_START))
    end_i = int(np.searchsorted(cal, END, side="right")) - 1

    ye_idx = set()
    for ye in YEAR_ENDS:
        j = int(np.searchsorted(cal, ye, side="right")) - 1
        if start_i <= j <= end_i:
            ye_idx.add(j)

    cash = CAPITAL0
    active = {}
    ledger, curve = [], []
    yr_realized = 0.0
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
        for j in list(active):
            c = cl_v[i, j]
            if np.isnan(c) or i + 1 > end_i:
                continue
            r = rk_v[i, j]
            if np.isnan(r) or r >= EXIT_RANK:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            pos = active.pop(j)
            eff = px * (1 - SLIP)
            proceeds = pos["shares"] * eff
            pnl = proceeds - pos["cost"]
            cash += proceeds
            yr_realized += pnl
            ledger.append(dict(symbol=cols[j], entry_date=str(pos["entry_date"].date()),
                               exit_date=str(cal[i + 1].date()), shares=pos["shares"],
                               entry_px=round(pos["entry_px"], 2), exit_px=round(eff, 2),
                               pnl_usd=round(pnl, 0), pnl_pct=round(eff / pos["entry_px"] - 1, 4),
                               hold_td=i + 1 - pos["entry_i"], reason="momentum_decay",
                               status="closed"))
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
        if i in ye_idx:
            taxable = max(0.0, yr_realized - loss_cf)
            tax = taxable * TAX_RATE
            loss_cf = max(0.0, loss_cf - max(0.0, yr_realized)) + \
                max(0.0, -yr_realized)
            if tax > 0:
                cash -= tax
            tax_events.append(dict(year_end=str(d.date()),
                                   realized=round(yr_realized, 0),
                                   loss_cf_after=round(loss_cf, 0),
                                   tax=round(tax, 0),
                                   equity_after=round(mtm(i), 0)))
            yr_realized = 0.0
        curve.append((d, mtm(i), len(active), cash))

    holdings = []
    for j, pos in active.items():
        c = cl_v[end_i, j]
        holdings.append(dict(symbol=cols[j], entry_date=str(pos["entry_date"].date()),
                             shares=pos["shares"], entry_px=round(pos["entry_px"], 2),
                             last_close=round(float(c), 2),
                             value_usd=round(pos["shares"] * c, 0),
                             pnl_usd=round(pos["shares"] * c - pos["cost"], 0),
                             pnl_pct=round(c / pos["entry_px"] - 1, 4),
                             hold_td=end_i - pos["entry_i"],
                             peak_dist=round(c / pos["peak"] - 1, 4),
                             mom_rank=round(float(rk_v[end_i, j]), 2)))
    holdings.sort(key=lambda h: -h["pnl_pct"])

    cdf = pd.DataFrame(curve, columns=["date", "equity", "n_pos", "cash"]).set_index("date")
    ldf = pd.DataFrame(ledger)
    pd.DataFrame(holdings).to_csv(OUT_DIR / f"investor_us{OUT_TAG}_holdings.csv", index=False)
    ldf.to_csv(OUT_DIR / f"investor_us{OUT_TAG}_ledger.csv", index=False)
    cdf.to_csv(OUT_DIR / f"investor_us{OUT_TAG}_curve.csv")
    summary = dict(final_equity=round(float(cdf.equity.iloc[-1]), 0),
                   cash=round(float(cdf.cash.iloc[-1]), 0),
                   n_closed=len(ldf), n_open=len(holdings),
                   total_tax=round(sum(t["tax"] for t in tax_events), 0),
                   pending_yr_realized=round(yr_realized, 0),
                   loss_cf=round(loss_cf, 0),
                   tax_events=tax_events)
    (OUT_DIR / f"investor_us{OUT_TAG}_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nHoldings:", len(holdings))
    print(pd.DataFrame(holdings).to_string(index=False))


if __name__ == "__main__":
    main()
