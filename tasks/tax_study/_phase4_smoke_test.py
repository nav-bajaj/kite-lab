"""Phase 4 smoke test: NIFTY 50 B&H pre-tax vs post-tax over the full backtest
window, plus per-strategy comparison."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from benchmark import build_bh_equity, build_bh_trades, load_nifty50
from forced_sale import build_tax_events, post_tax_summary
from tax_engine import compute_tax_per_fy, fy_tax_to_dataframe, match_lots

ROOT = Path(__file__).resolve().parents[2]
RUNS = Path(__file__).resolve().parent / "runs"

STRATEGIES = {
    "OM25 v3":  ("om25_v3",         "om25_trades.csv",  "om25_equity.csv"),
    "TL25 v3":  ("tl25_v3",         "tl25_trades.csv",  "tl25_equity.csv"),
    "L6 v2":    ("l6_v2",           "l6_trades.csv",    "l6_equity.csv"),
    "COMBO":    ("combo_defensive", "combo_trades.csv", "combo_equity.csv"),
}


def run_one(name: str, equity: pd.DataFrame, trades: pd.DataFrame) -> dict:
    realized, _ = match_lots(trades)
    fy_results = compute_tax_per_fy(realized)
    events, scale = build_tax_events(fy_results, equity)
    summary = post_tax_summary(equity, events, scale)
    summary["name"] = name
    summary["n_realized"] = len(realized)
    summary["n_lt_events"] = sum(1 for r in realized if r.bucket == "LT")
    summary["n_st_events"] = sum(1 for r in realized if r.bucket == "ST")
    return summary


def main() -> None:
    print("Phase 4 smoke test — NIFTY 50 B&H benchmark vs active strategies\n")

    # Window — driven by what NIFTY 50 data we have, intersected with backtest start
    nifty = load_nifty50(start="2009-09-01", end="2026-05-12")
    bh_start = nifty.iloc[0]["date"].date()
    bh_end = nifty.iloc[-1]["date"].date()
    print(f"  NIFTY 50 window: {bh_start} → {bh_end}  ({len(nifty)} trading days)\n")

    # Build B&H synthetic trades + equity
    bh_trades = build_bh_trades(nifty)
    bh_equity = build_bh_equity(nifty, bh_trades)

    bh = run_one("NIFTY 50 B&H", bh_equity, bh_trades)
    # Compare against each strategy over the same window
    print(f"  {'Name':<14} {'years':>6} {'pre-CAGR':>10} {'post-CAGR':>11} {'drag':>9} "
          f"{'tax/finalPV':>12} {'n_events':>9} {'#ST':>5} {'#LT':>5}")
    print("  " + "-" * 90)
    print(f"  {bh['name']:<14} {bh['years']:>5.1f}y "
          f"{bh['pretax_cagr']*100:>9.2f}% {bh['posttax_cagr']*100:>10.2f}% "
          f"{bh['drag_bps']:>7.0f}bp {bh['tax_as_pct_final_pretax_pv']:>10.2f}% "
          f"{bh['n_tax_events']:>9} {bh['n_st_events']:>5} {bh['n_lt_events']:>5}")
    print()

    for sname, (sd, tr_file, eq_file) in STRATEGIES.items():
        trades = pd.read_csv(RUNS / sd / tr_file)
        equity = pd.read_csv(RUNS / sd / eq_file, parse_dates=["date"])
        s = run_one(sname, equity, trades)
        print(f"  {s['name']:<14} {s['years']:>5.1f}y "
              f"{s['pretax_cagr']*100:>9.2f}% {s['posttax_cagr']*100:>10.2f}% "
              f"{s['drag_bps']:>7.0f}bp {s['tax_as_pct_final_pretax_pv']:>10.2f}% "
              f"{s['n_tax_events']:>9} {s['n_st_events']:>5} {s['n_lt_events']:>5}")

    print(f"\n  B&H tax detail:")
    realized, _ = match_lots(bh_trades)
    fy = compute_tax_per_fy(realized)
    df = fy_tax_to_dataframe(fy)
    money_cols = [c for c in df.columns if c != "fy"]
    for c in money_cols:
        df[c] = (df[c] / 1e5).round(2)
    print(df.to_string(index=False))
    print(f"\n  Single realized lot:")
    r = realized[0]
    print(f"    {r.symbol}  shares={r.shares:.2f}  "
          f"buy_date={r.buy_date.date()}  sell_date={r.sell_date.date()}  "
          f"holding={r.holding_days}d  bucket={r.bucket}  "
          f"gross_pnl=₹{r.gross_pnl/1e6:.2f}M")


if __name__ == "__main__":
    main()
