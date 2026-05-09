"""
Analyze tax impact on portfolio returns using Indian financial year (April 1 - March 31).

This script:
1. Loads portfolio equity data from backtest
2. Applies 25% flat tax on gains at end of each financial year (April 1 - March 31)
3. Deducts tax from closing balance and continues with post-tax amount
4. Generates year-by-year comparison report
5. Shows total impact of taxation on performance

Usage:
    # Run on all three universes (default)
    python scripts/analyze_tax_impact.py

    # Run on a specific universe
    python scripts/analyze_tax_impact.py --universe nse500
    python scripts/analyze_tax_impact.py --universe nifty100
    python scripts/analyze_tax_impact.py --universe nifty250

    # Run with explicit equity file (overrides universe auto-discovery)
    python scripts/analyze_tax_impact.py --equity path/to/momentum_equity.csv

    # Custom tax rate and output
    python scripts/analyze_tax_impact.py --universe all --tax-rate 0.20 --output-dir reports/

Tax Model:
    - Indian Financial Year: April 1 to March 31
    - Tax applied on gains only (not on full balance)
    - Tax deducted at year-end from portfolio value
    - Continue investing with post-tax amount in next FY
    - 25% flat tax rate (default, configurable)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


UNIVERSE_CONFIGS = {
    "nse500": {
        "label": "NSE 500",
        "output_root": Path("experiments/final_portfolio"),
        "run_prefix": "final_portfolio",
        "fallback_equity": Path("data/backtests/momentum_equity.csv"),
    },
    "nifty100": {
        "label": "Nifty 100",
        "output_root": Path("nifty_100_tests"),
        "run_prefix": "nifty100_portfolio",
        "fallback_equity": None,
    },
    "nifty250": {
        "label": "Nifty 250",
        "output_root": Path("nifty_250_tests"),
        "run_prefix": "nifty250_portfolio",
        "fallback_equity": None,
    },
}


def find_latest_equity(universe: str) -> Path | None:
    """Find the latest momentum_equity.csv for a universe by picking the newest timestamped run."""
    cfg = UNIVERSE_CONFIGS[universe]
    root = cfg["output_root"]
    prefix = cfg["run_prefix"]

    if not root.exists():
        if cfg["fallback_equity"] and cfg["fallback_equity"].exists():
            return cfg["fallback_equity"]
        return None

    # Find timestamped run directories (prefix_YYYYMMDDHHMMSS)
    run_dirs = sorted(
        [d for d in root.iterdir() if d.is_dir() and d.name.startswith(prefix + "_") and d.name[len(prefix) + 1:].isdigit()],
        key=lambda d: d.name,
        reverse=True,
    )

    for run_dir in run_dirs:
        equity_path = run_dir / "backtests" / "baseline" / "momentum_equity.csv"
        if equity_path.exists():
            return equity_path

    # Fallback for NSE 500 which also has data/backtests/
    if cfg["fallback_equity"] and cfg["fallback_equity"].exists():
        return cfg["fallback_equity"]

    return None


def load_equity_data(equity_path: Path) -> pd.DataFrame:
    """Load portfolio equity data."""
    df = pd.read_csv(equity_path, parse_dates=["date"])
    if df.empty:
        raise RuntimeError(f"Equity file {equity_path} is empty")

    df = df.sort_values("date").reset_index(drop=True)

    if "portfolio_value" not in df.columns:
        raise ValueError(f"Missing 'portfolio_value' column in {equity_path}")

    return df


def get_financial_year(date: pd.Timestamp) -> str:
    """
    Get Indian financial year for a date.

    Indian FY runs April 1 to March 31.
    FY 2020-21 means April 1, 2020 to March 31, 2021.
    """
    if date.month >= 4:  # April to December
        return f"FY{date.year}-{date.year + 1}"
    else:  # January to March
        return f"FY{date.year - 1}-{date.year}"


def get_fy_end_date(date: pd.Timestamp) -> pd.Timestamp:
    """Get the end date (March 31) of the financial year for a given date."""
    if date.month >= 4:  # April to December
        return pd.Timestamp(f"{date.year + 1}-03-31")
    else:  # January to March
        return pd.Timestamp(f"{date.year}-03-31")


def apply_tax_on_gains(
    equity_df: pd.DataFrame,
    tax_rate: float = 0.25,
    initial_capital: float = 1000000,
) -> tuple:
    """
    Apply tax on gains at end of each financial year.

    Args:
        equity_df: DataFrame with date and portfolio_value columns
        tax_rate: Tax rate (default 25% = 0.25)
        initial_capital: Starting capital (default 1M)

    Returns:
        (post_tax_df, tax_events_df)
        - post_tax_df: DataFrame with post-tax portfolio values
        - tax_events_df: DataFrame with tax events by year
    """
    # Create copy with normalized values
    df = equity_df.copy()

    # Normalize portfolio values to start at initial_capital
    scale_factor = initial_capital / df["portfolio_value"].iloc[0]
    df["portfolio_value"] = df["portfolio_value"] * scale_factor

    # Add financial year column
    df["fy"] = df["date"].apply(get_financial_year)

    # Initialize post-tax tracking
    df["post_tax_value"] = df["portfolio_value"].copy()
    tax_events = []

    # Get unique financial years
    financial_years = df["fy"].unique()

    # Starting capital for tax calculation
    fy_start_capital = initial_capital

    for fy in financial_years:
        fy_data = df[df["fy"] == fy].copy()

        if fy_data.empty:
            continue

        # Get last day of this FY in our data
        last_day_idx = fy_data.index[-1]
        last_day_date = fy_data["date"].iloc[-1]

        # Portfolio value at end of FY (before tax)
        end_value_pretax = df.loc[last_day_idx, "post_tax_value"]

        # Calculate gain for this FY
        gain = end_value_pretax - fy_start_capital

        # Tax only on gains (not losses)
        if gain > 0:
            tax_amount = gain * tax_rate
            end_value_posttax = end_value_pretax - tax_amount

            # Record tax event
            tax_events.append({
                "fy": fy,
                "end_date": last_day_date,
                "start_capital": fy_start_capital,
                "end_value_pretax": end_value_pretax,
                "gain": gain,
                "tax_rate": tax_rate,
                "tax_amount": tax_amount,
                "end_value_posttax": end_value_posttax,
            })

            # Apply tax adjustment to all subsequent days
            tax_adjustment = tax_amount / end_value_pretax  # Proportional reduction

            # Apply adjustment to all future dates
            future_mask = df.index > last_day_idx
            df.loc[future_mask, "post_tax_value"] *= (1 - tax_adjustment)

            # Next FY starts with post-tax capital
            fy_start_capital = end_value_posttax
        else:
            # No tax on losses
            tax_events.append({
                "fy": fy,
                "end_date": last_day_date,
                "start_capital": fy_start_capital,
                "end_value_pretax": end_value_pretax,
                "gain": gain,
                "tax_rate": 0.0,
                "tax_amount": 0.0,
                "end_value_posttax": end_value_pretax,
            })

            # Next FY continues with same capital
            fy_start_capital = end_value_pretax

    tax_events_df = pd.DataFrame(tax_events)

    return df, tax_events_df


def compute_metrics(values: pd.Series, dates: pd.Series) -> dict:
    """Compute performance metrics."""
    if len(values) < 2:
        return {
            "cagr": np.nan,
            "total_return": np.nan,
            "final_value": np.nan,
            "volatility": np.nan,
        }

    returns = values.pct_change().fillna(0)
    total_return = values.iloc[-1] / values.iloc[0] - 1
    days = (dates.iloc[-1] - dates.iloc[0]).days
    cagr = (1 + total_return) ** (365.0 / days) - 1 if days > 0 else np.nan
    volatility = returns.std() * np.sqrt(252)

    return {
        "cagr": cagr,
        "total_return": total_return,
        "final_value": values.iloc[-1],
        "volatility": volatility,
    }


def generate_chart(
    equity_df: pd.DataFrame,
    output_path: Path,
) -> bool:
    """Generate comparison chart of pre-tax vs post-tax equity curves."""
    if not HAS_MATPLOTLIB:
        print("Warning: matplotlib not available, skipping chart generation")
        return False

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: Absolute values
    ax1.plot(equity_df["date"], equity_df["portfolio_value"], label="Pre-Tax", linewidth=2, color="blue")
    ax1.plot(equity_df["date"], equity_df["post_tax_value"], label="Post-Tax", linewidth=2, color="red")
    ax1.set_ylabel("Portfolio Value (₹)", fontsize=12)
    ax1.set_title("Pre-Tax vs Post-Tax Portfolio Value", fontsize=14, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # Add vertical lines for FY boundaries
    fy_boundaries = equity_df.groupby("fy")["date"].max()
    for fy_end in fy_boundaries:
        ax1.axvline(x=fy_end, color="gray", linestyle="--", alpha=0.5, linewidth=1)

    # Plot 2: Gap between pre-tax and post-tax
    equity_df["tax_drag"] = equity_df["portfolio_value"] - equity_df["post_tax_value"]
    ax2.fill_between(
        equity_df["date"],
        0,
        equity_df["tax_drag"],
        alpha=0.6,
        color="orange",
        label="Tax Drag (Cumulative)"
    )
    ax2.set_xlabel("Date", fontsize=12)
    ax2.set_ylabel("Cumulative Tax Impact (₹)", fontsize=12)
    ax2.set_title("Cumulative Tax Drag on Portfolio", fontsize=14, fontweight="bold")
    ax2.legend(loc="upper left", fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

    # Add vertical lines for FY boundaries
    for fy_end in fy_boundaries:
        ax2.axvline(x=fy_end, color="gray", linestyle="--", alpha=0.5, linewidth=1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return True


def generate_report(
    equity_df: pd.DataFrame,
    tax_events_df: pd.DataFrame,
    initial_capital: float,
    tax_rate: float,
) -> str:
    """Generate text report of tax impact."""
    lines = []
    lines.append("=" * 80)
    lines.append("TAX IMPACT ANALYSIS REPORT")
    lines.append("Indian Financial Year: April 1 - March 31")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"Initial Capital: ₹{initial_capital:,.0f}")
    lines.append(f"Tax Rate: {tax_rate:.1%}")
    lines.append(f"Analysis Period: {equity_df['date'].iloc[0].date()} to {equity_df['date'].iloc[-1].date()}")
    lines.append("")

    # Overall metrics
    lines.append("-" * 80)
    lines.append("OVERALL PERFORMANCE")
    lines.append("-" * 80)
    lines.append("")

    pre_tax_metrics = compute_metrics(equity_df["portfolio_value"], equity_df["date"])
    post_tax_metrics = compute_metrics(equity_df["post_tax_value"], equity_df["date"])

    lines.append(f"{'Metric':<30} {'Pre-Tax':<20} {'Post-Tax':<20} {'Impact':<15}")
    lines.append("-" * 80)

    # CAGR
    lines.append(
        f"{'CAGR':<30} "
        f"{pre_tax_metrics['cagr']:>18.2%}  "
        f"{post_tax_metrics['cagr']:>18.2%}  "
        f"{post_tax_metrics['cagr'] - pre_tax_metrics['cagr']:>13.2%}"
    )

    # Total Return
    lines.append(
        f"{'Total Return':<30} "
        f"{pre_tax_metrics['total_return']:>18.2%}  "
        f"{post_tax_metrics['total_return']:>18.2%}  "
        f"{post_tax_metrics['total_return'] - pre_tax_metrics['total_return']:>13.2%}"
    )

    # Final Value
    lines.append(
        f"{'Final Portfolio Value':<30} "
        f"₹{pre_tax_metrics['final_value']:>16,.0f}  "
        f"₹{post_tax_metrics['final_value']:>16,.0f}  "
        f"₹{post_tax_metrics['final_value'] - pre_tax_metrics['final_value']:>11,.0f}"
    )

    # Volatility
    lines.append(
        f"{'Volatility':<30} "
        f"{pre_tax_metrics['volatility']:>18.2%}  "
        f"{post_tax_metrics['volatility']:>18.2%}  "
        f"{post_tax_metrics['volatility'] - pre_tax_metrics['volatility']:>13.2%}"
    )

    lines.append("")

    # Total tax paid
    total_tax_paid = tax_events_df["tax_amount"].sum()
    lines.append(f"Total Tax Paid: ₹{total_tax_paid:,.0f}")
    lines.append(f"Tax as % of Final Pre-Tax Value: {total_tax_paid / pre_tax_metrics['final_value']:.2%}")
    lines.append("")

    # Year-by-year breakdown
    lines.append("-" * 80)
    lines.append("YEAR-BY-YEAR TAX BREAKDOWN")
    lines.append("-" * 80)
    lines.append("")

    header = f"{'FY':<12} {'End Date':<12} {'Start':<15} {'End (Pre-Tax)':<15} {'Gain':<15} {'Tax':<15} {'End (Post-Tax)':<15}"
    lines.append(header)
    lines.append("-" * 80)

    for _, row in tax_events_df.iterrows():
        lines.append(
            f"{row['fy']:<12} "
            f"{row['end_date'].date()!s:<12} "
            f"₹{row['start_capital']:>12,.0f}  "
            f"₹{row['end_value_pretax']:>12,.0f}  "
            f"₹{row['gain']:>12,.0f}  "
            f"₹{row['tax_amount']:>12,.0f}  "
            f"₹{row['end_value_posttax']:>12,.0f}"
        )

    lines.append("")
    lines.append("=" * 80)
    lines.append("KEY INSIGHTS")
    lines.append("=" * 80)
    lines.append("")

    # Calculate impact
    cagr_reduction = pre_tax_metrics['cagr'] - post_tax_metrics['cagr']
    final_value_reduction = pre_tax_metrics['final_value'] - post_tax_metrics['final_value']

    lines.append(f"1. Tax reduces CAGR by {cagr_reduction:.2%} (from {pre_tax_metrics['cagr']:.2%} to {post_tax_metrics['cagr']:.2%})")
    lines.append(f"2. Final portfolio value is ₹{final_value_reduction:,.0f} lower due to taxes")
    lines.append(f"3. Total taxes paid: ₹{total_tax_paid:,.0f} over {len(tax_events_df)} financial years")
    lines.append(f"4. Average annual tax: ₹{total_tax_paid / len(tax_events_df):,.0f}")

    # Compounding impact
    pre_multiplier = pre_tax_metrics['final_value'] / initial_capital
    post_multiplier = post_tax_metrics['final_value'] / initial_capital
    lines.append(f"5. Pre-tax: ₹1 becomes ₹{pre_multiplier:.2f}")
    lines.append(f"6. Post-tax: ₹1 becomes ₹{post_multiplier:.2f}")
    lines.append(f"7. Tax drag on compounding: {(pre_multiplier - post_multiplier) / pre_multiplier:.1%}")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def run_analysis(
    label: str,
    equity_path: Path,
    tax_rate: float,
    initial_capital: float,
    output_dir: Path | None,
) -> dict:
    """Run tax impact analysis for a single universe. Returns summary metrics."""
    print(f"\n{'=' * 80}")
    print(f"  {label}")
    print(f"  Equity: {equity_path}")
    print(f"{'=' * 80}")

    equity_df = load_equity_data(equity_path)

    print(f"Applying {tax_rate:.1%} tax on gains at end of each financial year...")
    post_tax_df, tax_events_df = apply_tax_on_gains(
        equity_df,
        tax_rate=tax_rate,
        initial_capital=initial_capital,
    )

    report = generate_report(post_tax_df, tax_events_df, initial_capital, tax_rate)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = label.lower().replace(" ", "_")

        report_path = output_dir / f"tax_impact_report_{slug}.txt"
        with open(report_path, "w") as f:
            f.write(report)
        print(f"✓ Report saved to {report_path}")

        chart_path = output_dir / f"tax_impact_chart_{slug}.png"
        if generate_chart(post_tax_df, chart_path):
            print(f"✓ Chart saved to {chart_path}")

        csv_path = output_dir / f"tax_impact_data_{slug}.csv"
        export_df = post_tax_df[["date", "fy", "portfolio_value", "post_tax_value"]].copy()
        export_df["tax_drag"] = export_df["portfolio_value"] - export_df["post_tax_value"]
        export_df.to_csv(csv_path, index=False)
        print(f"✓ CSV saved to {csv_path}")
    else:
        print(report)

    pre = compute_metrics(post_tax_df["portfolio_value"], post_tax_df["date"])
    post = compute_metrics(post_tax_df["post_tax_value"], post_tax_df["date"])
    return {
        "label": label,
        "pre_tax_cagr": pre["cagr"],
        "post_tax_cagr": post["cagr"],
        "cagr_drag": pre["cagr"] - post["cagr"],
        "pre_tax_final": pre["final_value"],
        "post_tax_final": post["final_value"],
        "total_tax_paid": tax_events_df["tax_amount"].sum(),
    }


def print_comparison_table(summaries: list[dict]) -> None:
    """Print a side-by-side comparison table across universes."""
    print(f"\n{'=' * 90}")
    print("  CROSS-UNIVERSE TAX IMPACT COMPARISON")
    print(f"{'=' * 90}\n")

    header = f"{'Universe':<15} {'Pre-Tax CAGR':>13} {'Post-Tax CAGR':>14} {'CAGR Drag':>10} {'Tax Paid':>15} {'Post-Tax Final':>16}"
    print(header)
    print("-" * 90)

    for s in summaries:
        print(
            f"{s['label']:<15} "
            f"{s['pre_tax_cagr']:>12.2%} "
            f"{s['post_tax_cagr']:>13.2%} "
            f"{s['cagr_drag']:>9.2%} "
            f"₹{s['total_tax_paid']:>13,.0f} "
            f"₹{s['post_tax_final']:>14,.0f}"
        )

    print(f"\n{'=' * 90}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze tax impact on portfolio returns using Indian FY (April-March)"
    )
    parser.add_argument(
        "--universe",
        choices=["nse500", "nifty100", "nifty250", "all"],
        default="all",
        help="Stock universe to analyze (default: all)",
    )
    parser.add_argument(
        "--equity",
        help="Explicit path to equity CSV (overrides --universe auto-discovery)",
    )
    parser.add_argument(
        "--tax-rate",
        type=float,
        default=0.25,
        help="Tax rate on gains (default: 0.25 = 25%%)",
    )
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=1000000,
        help="Initial capital in rupees (default: 1,000,000)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to save reports, charts, and CSVs (default: print to console)",
    )

    args = parser.parse_args()

    # If explicit equity path given, run single analysis
    if args.equity:
        summary = run_analysis(
            label="Custom",
            equity_path=Path(args.equity),
            tax_rate=args.tax_rate,
            initial_capital=args.initial_capital,
            output_dir=args.output_dir,
        )
        print_comparison_table([summary])
        return 0

    # Determine which universes to run
    universes = list(UNIVERSE_CONFIGS.keys()) if args.universe == "all" else [args.universe]

    summaries = []
    for universe in universes:
        equity_path = find_latest_equity(universe)
        if equity_path is None:
            print(f"\n⚠ Skipping {UNIVERSE_CONFIGS[universe]['label']}: no equity file found")
            continue

        summary = run_analysis(
            label=UNIVERSE_CONFIGS[universe]["label"],
            equity_path=equity_path,
            tax_rate=args.tax_rate,
            initial_capital=args.initial_capital,
            output_dir=args.output_dir,
        )
        summaries.append(summary)

    if len(summaries) > 1:
        print_comparison_table(summaries)

    return 0


if __name__ == "__main__":
    exit(main())
