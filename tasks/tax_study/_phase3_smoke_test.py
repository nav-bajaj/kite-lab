"""Phase 3 smoke test: compute post-tax equity curve with forced-sale slippage,
verify (a) step-downs occur at each Apr 1 with tax owed and (b) the post-tax
CAGR is reasonable vs pre-tax."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from forced_sale import build_tax_events, post_tax_summary
from tax_engine import compute_tax_per_fy, match_lots

ROOT = Path(__file__).resolve().parents[2]
RUNS = Path(__file__).resolve().parent / "runs"

STRATEGIES = {
    "OM25 v3":  ("om25_v3",         "om25_trades.csv",  "om25_equity.csv"),
    "TL25 v3":  ("tl25_v3",         "tl25_trades.csv",  "tl25_equity.csv"),
    "L6 v2":    ("l6_v2",           "l6_trades.csv",    "l6_equity.csv"),
    "COMBO":    ("combo_defensive", "combo_trades.csv", "combo_equity.csv"),
}


def main() -> None:
    print("Phase 3 smoke test — forced-sale-for-tax + post-tax equity curve\n")
    print(f"  {'Strategy':<10} {'years':>6} "
          f"{'pretax':>10} {'posttax':>10} {'drag':>9} "
          f"{'tax/finalPV':>12} {'slip/tax':>11} {'n_events':>9}")
    print("  " + "-" * 80)

    all_step_down_checks_pass = True
    for name, (sd, tr_file, eq_file) in STRATEGIES.items():
        trades = pd.read_csv(RUNS / sd / tr_file)
        equity = pd.read_csv(RUNS / sd / eq_file, parse_dates=["date"])

        realized, _ = match_lots(trades)
        fy_results = compute_tax_per_fy(realized)
        events, scale = build_tax_events(fy_results, equity)
        summary = post_tax_summary(equity, events, scale)

        # Verify a step-down at each event date — the scale value at the event
        # date should be strictly less than the scale value on the previous
        # trading day.
        equity_sorted = equity.sort_values("date").reset_index(drop=True)
        step_downs_ok = True
        for ev in events:
            i = int(equity_sorted.index[equity_sorted["date"] == ev.pay_date][0])
            if i == 0:
                continue
            prev_scale = float(scale.iloc[i - 1])
            curr_scale = float(scale.iloc[i])
            if curr_scale >= prev_scale - 1e-12:
                step_downs_ok = False
                print(f"    ✗ {name} {ev.fy_label}: no step-down on {ev.pay_date.date()} "
                      f"({prev_scale:.6f} → {curr_scale:.6f})")
        if not step_downs_ok:
            all_step_down_checks_pass = False

        slip_ratio = (summary["total_forced_slippage"] / summary["total_tax_paid"]
                       if summary["total_tax_paid"] > 0 else 0)

        print(f"  {name:<10} {summary['years']:>5.1f}y "
              f"{summary['pretax_cagr']*100:>9.2f}% "
              f"{summary['posttax_cagr']*100:>9.2f}% "
              f"{summary['drag_bps']:>7.0f}bp "
              f"{summary['tax_as_pct_final_pretax_pv']:>10.2f}% "
              f"{slip_ratio*100:>9.3f}% "
              f"{summary['n_tax_events']:>9}")

    print("\n  step-down check (gate 3.6):", "PASS ✓" if all_step_down_checks_pass else "FAIL ✗")

    # Detail dump for one strategy — show each tax event
    print(f"\n  Detail — OM25 v3 tax events:")
    name, (sd, tr_file, eq_file) = "OM25 v3", STRATEGIES["OM25 v3"]
    trades = pd.read_csv(RUNS / sd / tr_file)
    equity = pd.read_csv(RUNS / sd / eq_file, parse_dates=["date"])
    realized, _ = match_lots(trades)
    fy_results = compute_tax_per_fy(realized)
    events, _ = build_tax_events(fy_results, equity)
    print(f"  {'FY':<10} {'pay_date':<12} {'pre_PV_₹L':>11} {'tax_₹L':>10} "
          f"{'slip_₹L':>10} {'drag_₹L':>10} {'post_PV_₹L':>12}")
    print("  " + "-" * 80)
    for e in events:
        print(f"  {e.fy_label:<10} {e.pay_date.date()!s:<12} "
              f"{e.pre_tax_pv/1e5:>10.2f} "
              f"{e.tax_paid/1e5:>9.2f} "
              f"{e.forced_sale_slippage/1e5:>9.3f} "
              f"{e.total_drag/1e5:>9.2f} "
              f"{e.post_tax_pv_post_event/1e5:>11.2f}")


if __name__ == "__main__":
    main()
