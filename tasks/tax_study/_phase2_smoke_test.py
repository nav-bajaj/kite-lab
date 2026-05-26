"""Smoke test for Phase 2: run tax_engine on all 4 strategies, verify
realized+unrealized P&L matches equity-curve total return (gate 2.8),
and print per-FY tax tables."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from tax_engine import (
    compute_tax_per_fy,
    fy_tax_to_dataframe,
    match_lots,
    sanity_check,
)

ROOT = Path(__file__).resolve().parents[2]
RUNS = Path(__file__).resolve().parent / "runs"
PRICES = ROOT / "nse500_data_merged"

STRATEGIES = {
    "OM25 v3":  ("om25_v3",         "om25_trades.csv",  "om25_equity.csv"),
    "TL25 v3":  ("tl25_v3",         "tl25_trades.csv",  "tl25_equity.csv"),
    "L6 v2":    ("l6_v2",           "l6_trades.csv",    "l6_equity.csv"),
    "COMBO":    ("combo_defensive", "combo_trades.csv", "combo_equity.csv"),
}


def main() -> None:
    print(f"Phase 2 smoke test — tax engine on 4 strategies\n")
    print(f"  Prices panel: {PRICES}")
    print(f"  Runs dir:     {RUNS}\n")

    all_ok = True
    for name, (sd, tr_file, eq_file) in STRATEGIES.items():
        print(f"\n{'=' * 70}\n{name}\n{'=' * 70}")
        trades = pd.read_csv(RUNS / sd / tr_file)
        equity = pd.read_csv(RUNS / sd / eq_file, parse_dates=["date"])

        realized, open_positions = match_lots(trades)
        print(f"  Realized lots:   {len(realized):,}")
        print(f"  Open positions:  {sum(len(v) for v in open_positions.values())} lots across "
              f"{len(open_positions)} symbols")

        sc = sanity_check(equity, realized, open_positions, PRICES)
        print(f"\n  Sanity check (P&L reconciliation):")
        print(f"    Initial PV:        ₹{sc['initial_pv']/1e6:>10.2f}M")
        print(f"    Final PV:          ₹{sc['final_pv']/1e6:>10.2f}M")
        print(f"    Expected ΔPV:      ₹{sc['expected_pnl']/1e6:>10.2f}M")
        print(f"    Realized P&L:      ₹{sc['realized_pnl']/1e6:>10.2f}M")
        print(f"    Unrealized P&L:    ₹{sc['unrealized_pnl']/1e6:>10.2f}M")
        print(f"    Sum:               ₹{sc['total_pnl']/1e6:>10.2f}M")
        print(f"    Diff:              ₹{sc['diff']/1e6:>+10.4f}M  ({sc['diff_pct']:+.4f}%)")

        gate_ok = abs(sc["diff_pct"]) < 0.5
        print(f"    Gate 2.8 (±0.5%): {'PASS ✓' if gate_ok else 'FAIL ✗'}")
        if not gate_ok:
            all_ok = False

        fy_results = compute_tax_per_fy(realized)
        df = fy_tax_to_dataframe(fy_results)
        # Render whole table in lakhs (₹1L = 100,000) for readability
        money_cols = ["st_gross", "lt_gross", "stcl_cf_in", "ltcl_cf_in",
                      "intra_stcl_used", "cf_stcl_used", "cf_ltcl_used",
                      "ltcg_exempt_used", "st_taxable", "lt_taxable",
                      "stcg_tax", "ltcg_tax", "total_tax",
                      "stcl_cf_out", "ltcl_cf_out"]
        for c in money_cols:
            df[c] = (df[c] / 1e5).round(2)
        print(f"\n  Per-FY tax (₹ lakhs):")
        print(df.to_string(index=False))

        total_tax = sum(x.total_tax for x in fy_results)
        total_stcg = sum(x.stcg_tax for x in fy_results)
        total_ltcg = sum(x.ltcg_tax for x in fy_results)
        print(f"\n  Totals:")
        print(f"    STCG tax paid:   ₹{total_stcg/1e6:>8.2f}M ({total_stcg/1e5:.1f}L)")
        print(f"    LTCG tax paid:   ₹{total_ltcg/1e6:>8.2f}M ({total_ltcg/1e5:.1f}L)")
        print(f"    TOTAL tax paid:  ₹{total_tax/1e6:>8.2f}M  ({total_tax/sc['final_pv']*100:.2f}% of final PV)")

    print(f"\n{'=' * 70}")
    print(f"OVERALL: {'all gates PASS ✓' if all_ok else 'some gates FAILED ✗'}")


if __name__ == "__main__":
    main()
