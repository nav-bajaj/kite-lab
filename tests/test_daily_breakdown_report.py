#!/usr/bin/env python3
"""
Test daily breakdown table calculations in portfolio report

Verifies that the daily breakdown table in the HTML report shows
correct computed values for portfolio return, PnL, benchmark return,
and outperformance.
"""

import pandas as pd
from pathlib import Path
import sys
import re

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def compute_trailing_performance(equity: pd.DataFrame, days: int = 10) -> dict:
    """
    Compute trailing N-day performance for portfolio and benchmark

    This replicates the logic from scripts/report_backtests.py
    """
    if len(equity) < days:
        return {
            "portfolio_return_pct": 0,
            "portfolio_pnl": 0,
            "benchmark_return_pct": 0,
            "days": 0,
            "daily_data": pd.DataFrame()
        }

    # Get last N+1 days (need extra day for computing returns)
    trailing_equity = equity.tail(days + 1).copy()

    # Compute daily returns for each day
    daily_data = []
    for i in range(1, len(trailing_equity)):
        date = trailing_equity["date"].iloc[i]
        port_prev = trailing_equity["portfolio_value"].iloc[i - 1]
        port_curr = trailing_equity["portfolio_value"].iloc[i]
        bench_prev = trailing_equity["benchmark"].iloc[i - 1]
        bench_curr = trailing_equity["benchmark"].iloc[i]

        port_daily_return = (port_curr / port_prev - 1) if port_prev > 0 else 0
        port_daily_pnl = port_curr - port_prev
        bench_daily_return = (bench_curr / bench_prev - 1) if bench_prev > 0 else 0
        outperformance = port_daily_return - bench_daily_return

        daily_data.append({
            "date": date,
            "portfolio_return": port_daily_return,
            "portfolio_pnl": port_daily_pnl,
            "benchmark_return": bench_daily_return,
            "outperformance": outperformance
        })

    return pd.DataFrame(daily_data)


def parse_daily_breakdown_from_html(html_path: Path) -> pd.DataFrame:
    """Extract daily breakdown table from HTML report using regex"""
    with open(html_path, 'r') as f:
        html_content = f.read()

    # Find the Daily Breakdown section
    if 'Daily Breakdown' not in html_content:
        raise ValueError("Daily Breakdown table not found in HTML")

    # Extract table rows after "Daily Breakdown" header
    # Pattern: <tr><td>DATE</td><td>PORT_RET%</td><td>PORT_PNL</td><td>BENCH_RET%</td><td>OUTPERF%</td></tr>
    pattern = r'<tr>\s*<td[^>]*>(\d{4}-\d{2}-\d{2})</td>\s*<td[^>]*>([+-]?\d+\.\d+)%</td>\s*<td[^>]*>([+-]?\d+)</td>\s*<td[^>]*>([+-]?\d+\.\d+)%</td>\s*<td[^>]*>([+-]?\d+\.\d+)%</td>\s*</tr>'

    matches = re.findall(pattern, html_content)

    if not matches:
        raise ValueError("Could not parse daily breakdown table rows")

    rows = []
    for match in matches:
        date_str, port_ret_str, port_pnl_str, bench_ret_str, outperf_str = match
        rows.append({
            'date': pd.to_datetime(date_str),
            'portfolio_return': float(port_ret_str) / 100,
            'portfolio_pnl': float(port_pnl_str),
            'benchmark_return': float(bench_ret_str) / 100,
            'outperformance': float(outperf_str) / 100
        })

    return pd.DataFrame(rows)


def test_daily_breakdown(portfolio_dir: Path):
    """
    Test that daily breakdown table values are computed correctly

    Args:
        portfolio_dir: Path to portfolio experiment directory
                      (e.g., experiments/final_portfolio/final_portfolio_20260123165312)
    """
    print(f"Testing daily breakdown for: {portfolio_dir.name}")
    print("=" * 80)

    # Load equity data
    equity_path = portfolio_dir / "backtests" / "baseline" / "momentum_equity.csv"
    if not equity_path.exists():
        raise FileNotFoundError(f"Equity file not found: {equity_path}")

    equity = pd.read_csv(equity_path, parse_dates=["date"])
    print(f"✓ Loaded equity data: {len(equity)} rows")

    # Compute expected daily breakdown
    expected = compute_trailing_performance(equity, days=10)
    print(f"✓ Computed trailing 10-day performance: {len(expected)} days")

    # Parse actual values from HTML report
    report_path = portfolio_dir / "report.html"
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    actual = parse_daily_breakdown_from_html(report_path)
    print(f"✓ Parsed daily breakdown from HTML: {len(actual)} rows")

    # Compare expected vs actual
    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)

    if len(expected) != len(actual):
        print(f"✗ Row count mismatch: expected {len(expected)}, got {len(actual)}")
        return False

    # Merge on date for comparison
    comparison = expected.merge(
        actual,
        on='date',
        suffixes=('_expected', '_actual')
    )

    # Define tolerance for floating point comparison
    # HTML displays percentages with 2 decimal places (e.g., "1.23%")
    # So tolerance should be ±0.005pp to account for rounding
    TOLERANCE = 0.00005  # 0.005 percentage points
    PNL_TOLERANCE = 1.0  # For PnL (allow ±1 rupee due to rounding)

    all_tests_passed = True

    for idx, row in comparison.iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        print(f"\n{date_str}:")

        # Test Portfolio Return
        port_ret_diff = abs(row['portfolio_return_expected'] - row['portfolio_return_actual'])
        if port_ret_diff > TOLERANCE:
            print(f"  ✗ Portfolio Return mismatch:")
            print(f"    Expected: {row['portfolio_return_expected']*100:.2f}%")
            print(f"    Actual:   {row['portfolio_return_actual']*100:.2f}%")
            print(f"    Diff:     {port_ret_diff*100:.4f}pp")
            all_tests_passed = False
        else:
            print(f"  ✓ Portfolio Return: {row['portfolio_return_actual']*100:.2f}%")

        # Test Portfolio PnL
        pnl_diff = abs(row['portfolio_pnl_expected'] - row['portfolio_pnl_actual'])
        if pnl_diff > PNL_TOLERANCE:
            print(f"  ✗ Portfolio PnL mismatch:")
            print(f"    Expected: {row['portfolio_pnl_expected']:.2f}")
            print(f"    Actual:   {row['portfolio_pnl_actual']:.2f}")
            print(f"    Diff:     {pnl_diff:.2f}")
            all_tests_passed = False
        else:
            print(f"  ✓ Portfolio PnL: {row['portfolio_pnl_actual']:.0f}")

        # Test Benchmark Return
        bench_ret_diff = abs(row['benchmark_return_expected'] - row['benchmark_return_actual'])
        if bench_ret_diff > TOLERANCE:
            print(f"  ✗ Benchmark Return mismatch:")
            print(f"    Expected: {row['benchmark_return_expected']*100:.2f}%")
            print(f"    Actual:   {row['benchmark_return_actual']*100:.2f}%")
            print(f"    Diff:     {bench_ret_diff*100:.4f}pp")
            all_tests_passed = False
        else:
            print(f"  ✓ Benchmark Return: {row['benchmark_return_actual']*100:.2f}%")

        # Test Outperformance
        outperf_diff = abs(row['outperformance_expected'] - row['outperformance_actual'])
        if outperf_diff > TOLERANCE:
            print(f"  ✗ Outperformance mismatch:")
            print(f"    Expected: {row['outperformance_expected']*100:.2f}%")
            print(f"    Actual:   {row['outperformance_actual']*100:.2f}%")
            print(f"    Diff:     {outperf_diff*100:.4f}pp")
            all_tests_passed = False
        else:
            print(f"  ✓ Outperformance: {row['outperformance_actual']*100:.2f}%")

    print("\n" + "=" * 80)
    if all_tests_passed:
        print("✅ ALL TESTS PASSED - Daily breakdown calculations are correct!")
    else:
        print("❌ SOME TESTS FAILED - Review mismatches above")
    print("=" * 80)

    return all_tests_passed


def main():
    """Run tests on specified portfolio directory"""
    import argparse

    parser = argparse.ArgumentParser(description="Test daily breakdown report calculations")
    parser.add_argument(
        "--portfolio-dir",
        type=Path,
        default=Path("experiments/final_portfolio/final_portfolio_20260123165312"),
        help="Path to portfolio experiment directory"
    )
    args = parser.parse_args()

    if not args.portfolio_dir.exists():
        print(f"Error: Portfolio directory not found: {args.portfolio_dir}")
        sys.exit(1)

    success = test_daily_breakdown(args.portfolio_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
