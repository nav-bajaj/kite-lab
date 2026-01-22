"""
Test to verify benchmark returns in the trailing 10-day report section.

This test validates that the benchmark returns displayed in the HTML report's
daily breakdown table match the actual calculations from the equity data.

Run with: python tests/test_report_benchmark_returns.py
"""

import re
import sys
from pathlib import Path

import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_equity_data(equity_path: Path) -> pd.DataFrame:
    """Load equity data from CSV."""
    df = pd.read_csv(equity_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def compute_benchmark_returns(equity_df: pd.DataFrame, days: int = 10) -> pd.DataFrame:
    """
    Compute benchmark returns for the last N trading days.

    Args:
        equity_df: DataFrame with date and benchmark columns
        days: Number of trailing days to compute

    Returns:
        DataFrame with date and benchmark_return columns
    """
    # Get last N+1 days (need N+1 to compute N returns)
    trailing_data = equity_df.tail(days + 1).copy()

    if len(trailing_data) < 2:
        return pd.DataFrame()

    # Compute daily returns
    trailing_data["benchmark_return"] = trailing_data["benchmark"].pct_change()

    # Drop the first row (no return for it) and keep last N days
    trailing_data = trailing_data.iloc[1:].reset_index(drop=True)

    return trailing_data[["date", "benchmark", "benchmark_return"]]


def extract_benchmark_returns_from_html(html_path: Path) -> dict:
    """
    Extract benchmark returns from HTML report's daily breakdown table.

    Returns:
        dict: {date_str: benchmark_return_pct}
    """
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Find the Daily Breakdown table
    # Pattern: <td>DATE</td>...<td>BENCHMARK_RETURN</td>
    pattern = r'<td style="padding: 5px; text-align: center;">(\d{4}-\d{2}-\d{2})</td>.*?' \
              r'<td style="padding: 5px; text-align: right; color: \w+;">([+-]?\d+\.\d+)%</td>.*?' \
              r'<td style="padding: 5px; text-align: right; color: \w+;">([+-]?\d+)</td>.*?' \
              r'<td style="padding: 5px; text-align: right; color: \w+;">([+-]?\d+\.\d+)%</td>'

    matches = re.findall(pattern, html_content, re.DOTALL)

    benchmark_returns = {}
    for date_str, portfolio_ret, portfolio_pnl, benchmark_ret in matches:
        # benchmark_ret is the 4th captured group
        benchmark_returns[date_str] = float(benchmark_ret) / 100.0  # Convert from % to decimal

    return benchmark_returns


def test_benchmark_returns(equity_path: Path, html_path: Path, tolerance: float = 0.0001):
    """
    Test that benchmark returns in HTML match actual calculations.

    Args:
        equity_path: Path to momentum_equity.csv
        html_path: Path to report.html
        tolerance: Tolerance for floating point comparison
    """
    print("=" * 80)
    print("Testing Benchmark Returns in Trailing 10-Day Report")
    print("=" * 80)
    print()

    # Load equity data
    print(f"Loading equity data from {equity_path}...")
    equity_df = load_equity_data(equity_path)
    print(f"  ✓ Loaded {len(equity_df)} days of data")
    print(f"  Date range: {equity_df['date'].iloc[0].date()} to {equity_df['date'].iloc[-1].date()}")
    print()

    # Compute actual benchmark returns
    print("Computing actual benchmark returns for last 10 days...")
    actual_returns = compute_benchmark_returns(equity_df, days=10)
    print(f"  ✓ Computed returns for {len(actual_returns)} days")
    print()

    # Extract reported returns from HTML
    print(f"Extracting benchmark returns from {html_path}...")
    reported_returns = extract_benchmark_returns_from_html(html_path)
    print(f"  ✓ Extracted {len(reported_returns)} days from HTML")
    print()

    # Compare
    print("-" * 80)
    print("Comparing Actual vs Reported Benchmark Returns")
    print("-" * 80)
    print()

    errors = []
    matches = 0

    for _, row in actual_returns.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d")
        actual_return = row["benchmark_return"]

        if date_str in reported_returns:
            reported_return = reported_returns[date_str]
            diff = abs(actual_return - reported_return)

            status = "✓" if diff < tolerance else "✗"
            color = "green" if diff < tolerance else "red"

            print(f"{status} {date_str}")
            print(f"    Actual:   {actual_return:>10.4%}")
            print(f"    Reported: {reported_return:>10.4%}")
            print(f"    Diff:     {diff:>10.6%}")
            print()

            if diff < tolerance:
                matches += 1
            else:
                errors.append({
                    "date": date_str,
                    "actual": actual_return,
                    "reported": reported_return,
                    "diff": diff,
                })
        else:
            print(f"✗ {date_str}: Missing from HTML report")
            print()
            errors.append({
                "date": date_str,
                "actual": actual_return,
                "reported": None,
                "diff": None,
            })

    # Check for extra dates in HTML
    for date_str in reported_returns:
        if date_str not in actual_returns["date"].dt.strftime("%Y-%m-%d").values:
            print(f"⚠️  {date_str}: Found in HTML but not in last 10 days of equity data")
            print()

    # Summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print()
    print(f"Total days checked: {len(actual_returns)}")
    print(f"Matches: {matches}")
    print(f"Errors: {len(errors)}")
    print()

    if errors:
        print("❌ TEST FAILED")
        print()
        print("Errors found:")
        for err in errors:
            if err["reported"] is None:
                print(f"  - {err['date']}: Missing from HTML")
            else:
                print(f"  - {err['date']}: Diff = {err['diff']:.6%} (tolerance = {tolerance:.6%})")
        print()
        return False
    else:
        print("✅ TEST PASSED")
        print()
        print("All benchmark returns in the HTML report match the actual calculations!")
        print()
        return True


def main():
    """Main entry point."""
    # Default paths - adjust as needed
    equity_path = Path("experiments/final_portfolio/final_portfolio_20260122141402/backtests/baseline/momentum_equity.csv")
    html_path = Path("experiments/final_portfolio/final_portfolio_20260122141402/report.html")

    # Check if files exist
    if not equity_path.exists():
        print(f"Error: Equity file not found at {equity_path}")
        print("Please provide the correct path to momentum_equity.csv")
        return 1

    if not html_path.exists():
        print(f"Error: HTML report not found at {html_path}")
        print("Please provide the correct path to report.html")
        return 1

    # Run test
    success = test_benchmark_returns(equity_path, html_path, tolerance=0.0001)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
