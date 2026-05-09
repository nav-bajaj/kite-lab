"""
Test volatility targeting feature and compare to baseline

Usage:
    python scripts/test_volatility_targeting.py \
        --signals data/final_portfolio/final_top24_signals.csv \
        --prices-dir nse500_data \
        --output experiments/vol_targeting_test
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def run_comparison(signals_path: Path, prices_dir: Path, output_dir: Path):
    """Run baseline vs volatility-targeted backtests"""

    output_dir.mkdir(parents=True, exist_ok=True)

    # Scenario configurations
    scenarios = {
        "baseline": {
            "scenario": "baseline",
            "description": "Baseline (100% exposure)"
        },
        "vol_target_20_weekly_cash": {
            "scenario": "vol_trigger_weekly_cash_buffer",
            "target_vol": 0.20,
            "vol_lookback": 63,
            "description": "Vol Target 20% (Weekly, Cash Buffer - preserve positions)"
        },
        "vol_target_20_bands_cash": {
            "scenario": "vol_trigger_bands_cash_buffer",
            "target_vol": 0.20,
            "vol_lookback": 63,
            "description": "Vol Target 20% (Bands, Cash Buffer - preserve positions)"
        },
        "vol_target_20_weekly_reduce": {
            "scenario": "vol_trigger_weekly",
            "target_vol": 0.20,
            "vol_lookback": 63,
            "description": "Vol Target 20% (Weekly, Position Reduction)"
        },
    }

    # Run backtests
    import subprocess

    results = {}
    for name, config in scenarios.items():
        print(f"\n{'='*80}")
        print(f"Running: {config['description']}")
        print(f"{'='*80}\n")

        run_dir = output_dir / name
        run_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "scripts/backtest_momentum.py",
            "--signals", str(signals_path),
            "--prices-dir", str(prices_dir),
            "--output-dir", str(run_dir),
            "--scenario", config["scenario"],
            "--top-n", "24",
        ]

        if "target_vol" in config:
            cmd.extend(["--target-vol", str(config["target_vol"])])
        if "vol_lookback" in config:
            cmd.extend(["--vol-lookback", str(config["vol_lookback"])])

        try:
            subprocess.run(cmd, check=True)
            results[name] = {
                "config": config,
                "equity_path": run_dir / "momentum_equity.csv"
            }
        except subprocess.CalledProcessError as e:
            print(f"Error running {name}: {e}")
            continue

    # Compare results
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY")
    print(f"{'='*80}\n")

    import pandas as pd
    import numpy as np

    comparison_data = []

    for name, result in results.items():
        equity_path = result["equity_path"]
        if not equity_path.exists():
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

        # Exposure stats
        avg_exposure = df["exposure"].mean() * 100 if "exposure" in df.columns else 100.0

        comparison_data.append({
            "Scenario": result["config"]["description"],
            "CAGR (%)": f"{cagr:.2f}",
            "Total Return (%)": f"{total_return:.1f}",
            "Volatility (%)": f"{vol:.2f}",
            "Max DD (%)": f"{max_dd:.2f}",
            "Sharpe": f"{sharpe:.2f}",
            "Avg Exposure (%)": f"{avg_exposure:.1f}",
            "Final Value": f"₹{end_val:,.0f}"
        })

    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df.to_string(index=False))
    print()

    # Save comparison
    comparison_csv = output_dir / "comparison_summary.csv"
    comparison_df.to_csv(comparison_csv, index=False)
    print(f"Saved comparison to {comparison_csv}")

    # Generate chart
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

        # Plot 1: Portfolio value
        ax1 = axes[0]
        for name, result in results.items():
            equity_path = result["equity_path"]
            if not equity_path.exists():
                continue
            df = pd.read_csv(equity_path, parse_dates=["date"])
            ax1.plot(df["date"], df["portfolio_value"], label=result["config"]["description"], linewidth=2)

        ax1.set_ylabel("Portfolio Value (₹)", fontsize=12)
        ax1.set_title("Volatility Targeting Comparison: Portfolio Value", fontsize=14, fontweight="bold")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)
        ax1.set_yscale("log")

        # Plot 2: Exposure over time (for vol-targeted strategies)
        ax2 = axes[1]
        for name, result in results.items():
            if result["config"]["scenario"] != "vol_trigger":
                continue
            equity_path = result["equity_path"]
            if not equity_path.exists():
                continue
            df = pd.read_csv(equity_path, parse_dates=["date"])
            if "exposure" in df.columns:
                ax2.plot(df["date"], df["exposure"] * 100, label=result["config"]["description"], linewidth=2)

        ax2.set_xlabel("Date", fontsize=12)
        ax2.set_ylabel("Exposure (%)", fontsize=12)
        ax2.set_title("Portfolio Exposure Over Time", fontsize=14, fontweight="bold")
        ax2.legend(loc="upper left")
        ax2.grid(True, alpha=0.3)
        ax2.axhline(100, color='gray', linestyle='--', alpha=0.5)
        ax2.set_ylim(0, 110)

        plt.tight_layout()
        chart_path = output_dir / "volatility_targeting_comparison.png"
        plt.savefig(chart_path, dpi=150)
        print(f"Saved chart to {chart_path}")
        plt.close()
    except Exception as e:
        print(f"Warning: Could not generate chart: {e}")

    print(f"\n{'='*80}")
    print("KEY INSIGHTS")
    print(f"{'='*80}\n")

    # Parse metrics for insights
    baseline = comparison_data[0] if comparison_data else None
    vol_weekly_cash = comparison_data[1] if len(comparison_data) > 1 else None
    vol_bands_cash = comparison_data[2] if len(comparison_data) > 2 else None
    vol_weekly_reduce = comparison_data[3] if len(comparison_data) > 3 else None

    if baseline and vol_weekly_cash:
        print("Comparing Baseline vs Vol Target 20% (Weekly, Cash Buffer):")
        print(f"  CAGR: {baseline['CAGR (%)']} → {vol_weekly_cash['CAGR (%)']}")
        print(f"  Max Drawdown: {baseline['Max DD (%)']} → {vol_weekly_cash['Max DD (%)']}")
        print(f"  Volatility: {baseline['Volatility (%)']} → {vol_weekly_cash['Volatility (%)']}")
        print(f"  Sharpe: {baseline['Sharpe']} → {vol_weekly_cash['Sharpe']}")
        print(f"  Avg Exposure: {baseline['Avg Exposure (%)']} → {vol_weekly_cash['Avg Exposure (%)']}")
        print()

    if baseline and vol_bands_cash:
        print("Comparing Baseline vs Vol Target 20% (Bands, Cash Buffer):")
        print(f"  CAGR: {baseline['CAGR (%)']} → {vol_bands_cash['CAGR (%)']}")
        print(f"  Max Drawdown: {baseline['Max DD (%)']} → {vol_bands_cash['Max DD (%)']}")
        print(f"  Volatility: {baseline['Volatility (%)']} → {vol_bands_cash['Volatility (%)']}")
        print(f"  Sharpe: {baseline['Sharpe']} → {vol_bands_cash['Sharpe']}")
        print(f"  Avg Exposure: {baseline['Avg Exposure (%)']} → {vol_bands_cash['Avg Exposure (%)']}")

    print()
    print("VOLATILITY TARGETING BENEFITS:")
    print("  ✓ Reduces exposure during high-volatility periods")
    print("  ✓ Can reduce maximum drawdowns")
    print("  ✓ Smooths equity curve")
    print("  ✓ May improve risk-adjusted returns (Sharpe ratio)")
    print()
    print("TRADE-OFFS:")
    print("  ✗ Lower CAGR due to reduced exposure")
    print("  ✗ Misses some upside during volatile rallies")
    print("  ✗ Adds complexity to portfolio management")
    print()


def main():
    parser = argparse.ArgumentParser(description="Test volatility targeting vs baseline")
    parser.add_argument("--signals", type=Path, default=Path("data/final_portfolio/final_top24_signals.csv"))
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--output", type=Path, default=Path("experiments/vol_targeting_test"))

    args = parser.parse_args()

    if not args.signals.exists():
        print(f"ERROR: Signals file not found: {args.signals}")
        return 1

    if not args.prices_dir.exists():
        print(f"ERROR: Prices directory not found: {args.prices_dir}")
        return 1

    run_comparison(args.signals, args.prices_dir, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
