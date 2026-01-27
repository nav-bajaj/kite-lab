"""
Test impact of vol_floor parameter on portfolio composition and performance

Usage:
    python scripts/test_vol_floor_impact.py \
        --prices-dir nse500_data \
        --output experiments/vol_floor_test
"""

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def generate_signals(prices_dir: Path, output_path: Path, vol_floor: float):
    """Generate momentum signals with specified vol_floor"""
    cmd = [
        sys.executable,
        "scripts/build_momentum_signals_flexible.py",
        "--prices-dir", str(prices_dir),
        "--output", str(output_path),
        "--lookback-months", "6",
        "--rebalance-weeks", "1",
        "--skip-days", "0",
        "--top-n", "24",
        "--vol-floor", str(vol_floor),
        "--vol-power", "1.0",
    ]

    subprocess.run(cmd, check=True)


def run_backtest(signals_path: Path, prices_dir: Path, output_dir: Path):
    """Run backtest on generated signals"""
    cmd = [
        sys.executable,
        "scripts/backtest_momentum.py",
        "--signals", str(signals_path),
        "--prices-dir", str(prices_dir),
        "--output-dir", str(output_dir),
        "--top-n", "24",
        "--scenario", "baseline",
    ]

    subprocess.run(cmd, check=True)


def compare_stock_compositions(signal_files: dict, output_dir: Path):
    """Compare which stocks are selected across different vol_floor values"""

    # Load all signals
    signals = {}
    for name, path in signal_files.items():
        df = pd.read_csv(path, parse_dates=["date"])
        signals[name] = df

    # Get latest date from each
    latest_stocks = {}
    for name, df in signals.items():
        latest_date = df["date"].max()
        latest = df[df["date"] == latest_date].sort_values("rank")
        latest_stocks[name] = set(latest["symbol"].values)

    # Calculate overlaps
    print("\n" + "="*80)
    print("STOCK COMPOSITION COMPARISON (Latest Rebalance Date)")
    print("="*80 + "\n")

    vol_floors = sorted(signal_files.keys())

    for i, name1 in enumerate(vol_floors):
        for name2 in vol_floors[i+1:]:
            overlap = latest_stocks[name1] & latest_stocks[name2]
            unique_1 = latest_stocks[name1] - latest_stocks[name2]
            unique_2 = latest_stocks[name2] - latest_stocks[name1]

            overlap_pct = len(overlap) / 24 * 100

            print(f"{name1} vs {name2}:")
            print(f"  Overlap: {len(overlap)}/24 stocks ({overlap_pct:.1f}%)")
            if unique_1:
                print(f"  Only in {name1}: {sorted(unique_1)}")
            if unique_2:
                print(f"  Only in {name2}: {sorted(unique_2)}")
            print()

    # Show full latest portfolio for each
    print("\n" + "="*80)
    print("FULL PORTFOLIOS (Latest Date)")
    print("="*80 + "\n")

    for name in vol_floors:
        df = signals[name]
        latest_date = df["date"].max()
        latest = df[df["date"] == latest_date].sort_values("rank")

        print(f"\n{name}:")
        print(f"Date: {latest_date.date()}")
        print("\nRank | Symbol        | Score")
        print("-" * 40)
        for _, row in latest.iterrows():
            print(f"{row['rank']:4d} | {row['symbol']:13s} | {row['score']:6.2f}")

    # Calculate composition stability over time
    print("\n" + "="*80)
    print("COMPOSITION STABILITY OVER TIME")
    print("="*80 + "\n")

    for name, df in signals.items():
        # Get unique stocks that appear in top 24 over the entire period
        all_stocks = df["symbol"].unique()
        total_rebalances = len(df["date"].unique())

        # Calculate turnover (how often stocks change)
        turnover_events = 0
        prev_stocks = set()

        for date in sorted(df["date"].unique()):
            current_stocks = set(df[df["date"] == date]["symbol"].values)
            if prev_stocks:
                changes = len(prev_stocks.symmetric_difference(current_stocks))
                if changes > 0:
                    turnover_events += 1
            prev_stocks = current_stocks

        print(f"{name}:")
        print(f"  Unique stocks over time: {len(all_stocks)}")
        print(f"  Total rebalances: {total_rebalances}")
        print(f"  Rebalances with changes: {turnover_events} ({turnover_events/total_rebalances*100:.1f}%)")
        print()


def compare_performance(backtest_dirs: dict, output_dir: Path):
    """Compare performance metrics across different vol_floor values"""

    comparison_data = []

    for name, backtest_dir in backtest_dirs.items():
        equity_path = backtest_dir / "momentum_equity.csv"

        if not equity_path.exists():
            print(f"Warning: {equity_path} not found")
            continue

        df = pd.read_csv(equity_path, parse_dates=["date"])

        # Calculate metrics
        portfolio_values = df["portfolio_value"]
        returns = portfolio_values.pct_change().dropna()

        start_val = portfolio_values.iloc[0]
        end_val = portfolio_values.iloc[-1]
        total_return = (end_val / start_val - 1) * 100

        days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
        years = days / 365.25
        cagr = ((end_val / start_val) ** (1 / years) - 1) * 100

        vol = returns.std() * np.sqrt(252) * 100

        cummax = portfolio_values.cummax()
        drawdown = (portfolio_values - cummax) / cummax * 100
        max_dd = drawdown.min()

        sharpe = (returns.mean() * 252 - 0.05) / (returns.std() * np.sqrt(252))

        comparison_data.append({
            "Vol Floor": name,
            "CAGR (%)": f"{cagr:.2f}",
            "Total Return (%)": f"{total_return:.1f}",
            "Volatility (%)": f"{vol:.2f}",
            "Max DD (%)": f"{max_dd:.2f}",
            "Sharpe": f"{sharpe:.2f}",
            "Final Value": f"₹{end_val:,.0f}"
        })

    comparison_df = pd.DataFrame(comparison_data)

    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON")
    print("="*80 + "\n")
    print(comparison_df.to_string(index=False))
    print()

    # Save comparison
    comparison_csv = output_dir / "vol_floor_comparison.csv"
    comparison_df.to_csv(comparison_csv, index=False)
    print(f"Saved comparison to {comparison_csv}")

    # Generate chart
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # Extract vol_floor values for x-axis
        vol_floors = [float(name.replace("vol_floor_", "")) for name in backtest_dirs.keys()]
        cagrs = [float(row["CAGR (%)"]) for row in comparison_data]
        vols = [float(row["Volatility (%)"]) for row in comparison_data]
        dds = [float(row["Max DD (%)"]) for row in comparison_data]
        sharpes = [float(row["Sharpe"]) for row in comparison_data]

        # Plot 1: CAGR
        axes[0, 0].plot(vol_floors, cagrs, marker='o', linewidth=2, markersize=8)
        axes[0, 0].set_xlabel("Vol Floor", fontsize=12)
        axes[0, 0].set_ylabel("CAGR (%)", fontsize=12)
        axes[0, 0].set_title("CAGR vs Vol Floor", fontsize=14, fontweight="bold")
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axvline(0.2, color='red', linestyle='--', alpha=0.5, label='Current (0.2)')
        axes[0, 0].legend()

        # Plot 2: Volatility
        axes[0, 1].plot(vol_floors, vols, marker='o', linewidth=2, markersize=8, color='orange')
        axes[0, 1].set_xlabel("Vol Floor", fontsize=12)
        axes[0, 1].set_ylabel("Volatility (%)", fontsize=12)
        axes[0, 1].set_title("Volatility vs Vol Floor", fontsize=14, fontweight="bold")
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].axvline(0.2, color='red', linestyle='--', alpha=0.5, label='Current (0.2)')
        axes[0, 1].legend()

        # Plot 3: Max Drawdown
        axes[1, 0].plot(vol_floors, dds, marker='o', linewidth=2, markersize=8, color='red')
        axes[1, 0].set_xlabel("Vol Floor", fontsize=12)
        axes[1, 0].set_ylabel("Max Drawdown (%)", fontsize=12)
        axes[1, 0].set_title("Max Drawdown vs Vol Floor", fontsize=14, fontweight="bold")
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].axvline(0.2, color='red', linestyle='--', alpha=0.5, label='Current (0.2)')
        axes[1, 0].legend()

        # Plot 4: Sharpe Ratio
        axes[1, 1].plot(vol_floors, sharpes, marker='o', linewidth=2, markersize=8, color='green')
        axes[1, 1].set_xlabel("Vol Floor", fontsize=12)
        axes[1, 1].set_ylabel("Sharpe Ratio", fontsize=12)
        axes[1, 1].set_title("Sharpe Ratio vs Vol Floor", fontsize=14, fontweight="bold")
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].axvline(0.2, color='red', linestyle='--', alpha=0.5, label='Current (0.2)')
        axes[1, 1].legend()

        plt.tight_layout()
        chart_path = output_dir / "vol_floor_impact.png"
        plt.savefig(chart_path, dpi=150)
        print(f"Saved chart to {chart_path}")
        plt.close()
    except Exception as e:
        print(f"Warning: Could not generate chart: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test vol_floor impact on portfolio")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--output", type=Path, default=Path("experiments/vol_floor_test"))
    parser.add_argument("--vol-floors", type=float, nargs="+",
                       default=[0.10, 0.15, 0.20, 0.25, 0.30],
                       help="Vol floor values to test (default: 0.1 0.15 0.2 0.25 0.3)")

    args = parser.parse_args()

    if not args.prices_dir.exists():
        print(f"ERROR: Prices directory not found: {args.prices_dir}")
        return 1

    args.output.mkdir(parents=True, exist_ok=True)

    signal_files = {}
    backtest_dirs = {}

    # Generate signals and run backtests for each vol_floor
    for vol_floor in args.vol_floors:
        name = f"vol_floor_{vol_floor:.2f}"
        print(f"\n{'='*80}")
        print(f"Testing Vol Floor: {vol_floor:.2f}")
        print(f"{'='*80}\n")

        # Generate signals
        signals_path = args.output / f"signals_{name}.csv"
        print(f"Generating signals with vol_floor={vol_floor}...")
        generate_signals(args.prices_dir, signals_path, vol_floor)
        signal_files[name] = signals_path

        # Run backtest
        backtest_dir = args.output / name
        print(f"Running backtest...")
        run_backtest(signals_path, args.prices_dir, backtest_dir)
        backtest_dirs[name] = backtest_dir

    # Compare compositions
    compare_stock_compositions(signal_files, args.output)

    # Compare performance
    compare_performance(backtest_dirs, args.output)

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    print(f"Tested {len(args.vol_floors)} vol_floor values: {args.vol_floors}")
    print(f"Results saved to: {args.output}")
    print()
    print("Key Insights:")
    print("  - Higher vol_floor = more conservative (penalizes low-vol stocks less)")
    print("  - Lower vol_floor = more aggressive (allows low-vol stocks with high returns)")
    print("  - Stock composition shows which stocks are sensitive to vol_floor setting")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
