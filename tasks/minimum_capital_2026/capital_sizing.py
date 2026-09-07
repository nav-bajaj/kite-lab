"""Minimum-capital and SIP sizing for the production portfolios.

Answers two product questions with repo data rather than rules of thumb:

  1. What capital does a client need before an equal-weight 24/25-stock
     book is actually replicable? Position size is capital/N, so a share
     priced above that position cannot be bought at all, and flat DP
     charges on a high-turnover book are a fixed cost that only capital
     dilutes.
  2. What lumpsum + monthly SIP should we suggest?

Everything is computed from the live price panel and the production
trade logs. Nothing here is a modelled assumption except the broker
tariff constants below, which are Zerodha delivery-equity rates.

Usage:
    python tasks/minimum_capital_2026/capital_sizing.py
    python tasks/minimum_capital_2026/capital_sizing.py --prices-dir nse500_data
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import math
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "runs"

# Zerodha delivery equity, 2026. Brokerage is zero; DP is the fixed cost
# that makes small accounts expensive, charged per scrip per sell day
# regardless of quantity.
DP_PER_SCRIP_SALE = 15.93        # Rs 13.5 + 18% GST
STT_SELL = 0.001
STAMP_BUY = 0.00015
TXN_GST_EACH_SIDE = 0.00004      # exchange txn + SEBI + GST, approx

PORTFOLIOS = {
    "Quality Momentum (OM25)": "data/om25_v3_portfolios/*/om25_trades.csv",
    "Trend Leaders (TL25)": "data/tl25_v3_portfolios/*/tl25_trades.csv",
    "Core Momentum (L6)": "data/l6_v2_portfolios/*/l6_trades.csv",
    "Defensive Blend (COMBO)": "data/combo_defensive_portfolios/*/combo_trades.csv",
}
CAPITALS = [100_000, 200_000, 300_000, 500_000, 750_000, 1_000_000, 2_000_000]


def latest_trades(pattern: str) -> Path:
    hits = [p for p in glob.glob(str(ROOT / pattern)) if "latest" not in p]
    if not hits:
        raise FileNotFoundError(pattern)
    return Path(sorted(hits)[-1])


def load_prices(prices_dir: Path) -> dict:
    px = {}
    for f in glob.glob(str(prices_dir / "*_day.csv")):
        rows = list(csv.DictReader(open(f)))
        if rows:
            px[os.path.basename(f)[:-8]] = float(rows[-1]["close"])
    return px


def open_book(trades_csv: Path) -> list:
    pos = collections.Counter()
    for r in csv.DictReader(open(trades_csv)):
        s = int(float(r["shares"]))
        pos[r["symbol"]] += s if r["side"] == "BUY" else -s
    return [k for k, v in pos.items() if v > 0]


def turnover_and_sale_events(trades_csv: Path, equity_csv: Path):
    """Median full-year sell-events and sell turnover as % of equity.

    Per-year rather than whole-period, because equity compounds hard over
    the sample and a single ratio against mean equity would understate
    early years and overstate late ones.
    """
    rows = list(csv.DictReader(open(trades_csv)))
    eq = list(csv.DictReader(open(equity_csv)))
    eq_by_year = collections.defaultdict(list)
    for r in eq:
        eq_by_year[r["date"][:4]].append(float(r["pv"]))
    sell_val = collections.defaultdict(float)
    sell_ev = collections.defaultdict(set)
    for r in rows:
        if r["side"] != "BUY":
            y = r["date"][:4]
            sell_val[y] += float(r["notional"])
            sell_ev[y].add((r["date"], r["symbol"]))
    years = [y for y in sorted(eq_by_year) if len(eq_by_year[y]) > 200]
    if not years:
        return 0.0, 0.0
    ev = statistics.median(len(sell_ev[y]) for y in years)
    turn = statistics.median(
        sell_val[y] / statistics.mean(eq_by_year[y]) * 100 for y in years)
    return ev, turn


def replication(px_book: dict, capital: float) -> dict:
    """Whole-share feasibility of an equal-weight book at a given capital."""
    n = len(px_book)
    target = capital / n
    shares = {s: math.floor(target / p) for s, p in px_book.items()}
    invested = sum(shares[s] * px_book[s] for s in px_book)
    errs = [(shares[s] * px_book[s] - target) / target for s in px_book]
    return {
        "unbuyable": sum(1 for s in px_book if shares[s] == 0),
        "cash_pct": round((capital - invested) / capital * 100, 1),
        "rms_wt_err_pct": round(math.sqrt(sum(e * e for e in errs) / n) * 100, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    prices = load_prices(args.prices_dir)
    vals = sorted(prices.values())
    n = len(vals)

    def pct_at_or_below(x):
        return 100 * sum(1 for p in vals if p <= x) / n

    report = {"universe": {
        "n": n,
        "median": round(statistics.median(vals)),
        "p90": round(vals[int(.90 * n)]), "p95": round(vals[int(.95 * n)]),
        "p99": round(vals[int(.99 * n)]), "max": round(max(vals)),
        "most_expensive": [[k, round(v)] for k, v in
                           sorted(prices.items(), key=lambda x: -x[1])[:10]],
    }}
    u = report["universe"]
    print(f"Universe: {u['n']} names, median Rs {u['median']:,}, "
          f"p95 Rs {u['p95']:,}, max Rs {u['max']:,} ({u['most_expensive'][0][0]})")

    # ---- cost drag -------------------------------------------------
    print("\n== Annual explicit cost drag by capital ==")
    print("   (DP per scrip-sale + STT/stamp/txn/GST on turnover;")
    print("    the 0.2% slippage is already inside the published CAGRs)")
    hdr = f"{'portfolio':26}" + "".join(f"{c/1e5:>8.0f}L" for c in CAPITALS)
    print(hdr + "   fixed Rs/yr  variable")
    report["cost_drag"] = {}
    for name, pat in PORTFOLIOS.items():
        tr = latest_trades(pat)
        eq = next(iter(glob.glob(str(tr.parent / "*equity*.csv"))), None)
        if eq is None:
            continue
        ev, turn = turnover_and_sale_events(tr, Path(eq))
        variable = turn / 100 * (STT_SELL + TXN_GST_EACH_SIDE
                                 + STAMP_BUY + TXN_GST_EACH_SIDE)
        fixed = ev * DP_PER_SCRIP_SALE
        line = f"{name:26}"
        row = {"sell_events_per_yr": ev, "sell_turnover_pct": round(turn),
               "fixed_rs_per_yr": round(fixed),
               "variable_pct": round(variable * 100, 2), "by_capital": {}}
        for c in CAPITALS:
            drag = (fixed / c + variable) * 100
            row["by_capital"][c] = round(drag, 2)
            line += f"{drag:7.2f}%"
        print(line + f"  {fixed:>10,.0f}   {variable*100:.2f}%")
        report["cost_drag"][name] = row

    # ---- replication ------------------------------------------------
    print("\n== Replication feasibility of the current books ==")
    report["replication"] = {}
    for name, pat in PORTFOLIOS.items():
        book = open_book(latest_trades(pat))
        px_book = {s: prices[s] for s in book if s in prices}
        if not px_book:
            continue
        print(f"\n{name}: {len(px_book)} holdings, "
              f"Rs {min(px_book.values()):,.0f}-{max(px_book.values()):,.0f}, "
              f"median Rs {statistics.median(px_book.values()):,.0f}")
        print(f"  {'capital':>8} {'unbuyable':>10} {'cash':>7} {'RMS wt err':>11}")
        report["replication"][name] = {}
        for c in CAPITALS:
            r = replication(px_book, c)
            report["replication"][name][c] = r
            print(f"  {c/1e5:>6.1f}L {r['unbuyable']:10d} "
                  f"{r['cash_pct']:6.1f}% {r['rms_wt_err_pct']:10.1f}%")

    # ---- share granularity across the universe ----------------------
    print("\n== Share granularity at a 1/25 position ==")
    print(f"{'capital':>8} {'position':>10} {'>=1 share':>10} {'>=5':>7} "
          f"{'>=10':>7} {'>=20':>7}")
    report["granularity"] = {}
    for c in CAPITALS:
        pos = c / 25
        g = {"position": round(pos),
             "ge1": round(pct_at_or_below(pos), 1),
             "ge5": round(pct_at_or_below(pos / 5), 1),
             "ge10": round(pct_at_or_below(pos / 10), 1),
             "ge20": round(pct_at_or_below(pos / 20), 1)}
        report["granularity"][c] = g
        print(f"{c/1e5:>6.1f}L {pos:10,.0f} {g['ge1']:9.1f}% {g['ge5']:6.1f}% "
              f"{g['ge10']:6.1f}% {g['ge20']:6.1f}%")

    # ---- SIP sizing --------------------------------------------------
    print("\n== SIP deployability ==")
    print("   A SIP is deployed into the 1-3 most underweight names at the")
    print("   next rebalance, never spread across all 25 (Rs 25,000/25 =")
    print("   Rs 1,000, below the price of ~30% of the universe).")
    print(f"{'SIP/month':>10} {'>=1 share':>10} {'>=3':>7} {'>=10':>7}")
    report["sip"] = {}
    for s in [5_000, 10_000, 15_000, 25_000, 40_000, 50_000]:
        g = {"ge1": round(pct_at_or_below(s), 1),
             "ge3": round(pct_at_or_below(s / 3), 1),
             "ge10": round(pct_at_or_below(s / 10), 1)}
        report["sip"][s] = g
        print(f"{s:>10,} {g['ge1']:9.1f}% {g['ge3']:6.1f}% {g['ge10']:6.1f}%")

    (OUT / "capital_sizing.json").write_text(json.dumps(report, indent=2))
    print(f"\n[wrote] {OUT/'capital_sizing.json'}")


if __name__ == "__main__":
    main()
