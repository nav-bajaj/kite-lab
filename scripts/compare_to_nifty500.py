"""
Generate short performance comparison report: Portfolio vs NIFTY 500

Usage:
    python scripts/compare_to_nifty500.py --backtest <backtest_dir>
    python scripts/compare_to_nifty500.py --backtest experiments/final_portfolio/final_portfolio_20260125230911/backtests/baseline
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def load_equity(path: Path) -> pd.DataFrame:
    """Load equity curve from backtest"""
    df = pd.read_csv(path, parse_dates=["date"])
    return df


def load_benchmark(path: Path) -> pd.DataFrame:
    """Load benchmark index data"""
    df = pd.read_csv(path, parse_dates=["date"])
    return df[["date", "close"]].rename(columns={"close": "benchmark"})


def annualized_return(values: pd.Series, dates: pd.Series) -> float:
    """Calculate CAGR"""
    if len(values) < 2:
        return 0.0
    start_val = values.iloc[0]
    end_val = values.iloc[-1]
    days = (dates.iloc[-1] - dates.iloc[0]).days
    years = days / 365.25
    if years <= 0 or start_val <= 0:
        return 0.0
    return (end_val / start_val) ** (1 / years) - 1


def annualized_vol(returns: pd.Series) -> float:
    """Calculate annualized volatility"""
    if len(returns) < 2:
        return 0.0
    return returns.std() * np.sqrt(252)


def max_drawdown(values: pd.Series) -> float:
    """Calculate maximum drawdown"""
    if len(values) < 2:
        return 0.0
    cummax = values.cummax()
    dd = (values - cummax) / cummax
    return dd.min()


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.05) -> float:
    """Calculate Sharpe ratio"""
    if len(returns) < 2:
        return 0.0
    excess = returns.mean() - risk_free / 252
    vol = returns.std()
    if vol == 0:
        return 0.0
    return (excess / vol) * np.sqrt(252)


def generate_report(backtest_dir: Path, benchmark_path: Path):
    """Generate comparison report"""

    # Load data
    equity_path = backtest_dir / "momentum_equity.csv"
    if not equity_path.exists():
        print(f"ERROR: Equity file not found at {equity_path}")
        return 1

    equity_df = load_equity(equity_path)

    # Load NIFTY 500 benchmark (will be named "benchmark" after rename in load_benchmark)
    nifty500_df = load_benchmark(benchmark_path)

    # Keep only portfolio columns we need, drop old benchmark column
    portfolio_cols = ["date", "portfolio_value", "cash", "invested"]
    equity_df = equity_df[portfolio_cols]

    # Merge with NIFTY 500
    merged = pd.merge(equity_df, nifty500_df, on="date", how="inner")

    if merged.empty:
        print("ERROR: No overlapping dates between portfolio and benchmark")
        return 1

    # Normalize both to start at 100
    merged["portfolio_norm"] = merged["portfolio_value"] / merged["portfolio_value"].iloc[0] * 100
    merged["benchmark_norm"] = merged["benchmark"] / merged["benchmark"].iloc[0] * 100

    # Calculate returns
    merged["portfolio_return"] = merged["portfolio_value"].pct_change()
    merged["benchmark_return"] = merged["benchmark"].pct_change()

    # Drop NaN from returns
    returns_df = merged[["portfolio_return", "benchmark_return"]].dropna()

    # Calculate metrics
    port_cagr = annualized_return(merged["portfolio_value"], merged["date"])
    bench_cagr = annualized_return(merged["benchmark"], merged["date"])

    port_vol = annualized_vol(returns_df["portfolio_return"])
    bench_vol = annualized_vol(returns_df["benchmark_return"])

    port_sharpe = sharpe_ratio(returns_df["portfolio_return"])
    bench_sharpe = sharpe_ratio(returns_df["benchmark_return"])

    port_dd = max_drawdown(merged["portfolio_value"])
    bench_dd = max_drawdown(merged["benchmark"])

    # Total returns
    port_total = (merged["portfolio_value"].iloc[-1] / merged["portfolio_value"].iloc[0] - 1) * 100
    bench_total = (merged["benchmark"].iloc[-1] / merged["benchmark"].iloc[0] - 1) * 100

    # Date range
    start_date = merged["date"].iloc[0].date()
    end_date = merged["date"].iloc[-1].date()
    days = (merged["date"].iloc[-1] - merged["date"].iloc[0]).days

    # Print report
    print("=" * 80)
    print("PORTFOLIO vs NIFTY 500 PERFORMANCE COMPARISON")
    print("=" * 80)
    print()
    print(f"Period: {start_date} to {end_date} ({days} days)")
    print(f"Backtest: {backtest_dir.parent.parent.name}")
    print()

    print("-" * 80)
    print(f"{'METRIC':<30} {'PORTFOLIO':>15} {'NIFTY 500':>15} {'DIFFERENCE':>15}")
    print("-" * 80)

    print(f"{'Total Return':<30} {port_total:>14.2f}% {bench_total:>14.2f}% {port_total - bench_total:>+14.2f}%")
    print(f"{'CAGR':<30} {port_cagr*100:>14.2f}% {bench_cagr*100:>14.2f}% {(port_cagr - bench_cagr)*100:>+14.2f}%")
    print(f"{'Volatility (Annual)':<30} {port_vol*100:>14.2f}% {bench_vol*100:>14.2f}% {(port_vol - bench_vol)*100:>+14.2f}%")
    print(f"{'Sharpe Ratio':<30} {port_sharpe:>14.2f} {bench_sharpe:>14.2f} {port_sharpe - bench_sharpe:>+14.2f}")
    print(f"{'Max Drawdown':<30} {port_dd*100:>14.2f}% {bench_dd*100:>14.2f}% {(port_dd - bench_dd)*100:>+14.2f}%")

    print("-" * 80)
    print()

    # Risk-adjusted metrics
    print("RISK-ADJUSTED PERFORMANCE:")
    print(f"  Return / Volatility:  {port_cagr / port_vol if port_vol > 0 else 0:.3f} vs {bench_cagr / bench_vol if bench_vol > 0 else 0:.3f}")
    print(f"  Return / Max DD:      {-port_cagr / port_dd if port_dd < 0 else 0:.3f} vs {-bench_cagr / bench_dd if bench_dd < 0 else 0:.3f}")
    print()

    # Outperformance
    outperf_days = (returns_df["portfolio_return"] > returns_df["benchmark_return"]).sum()
    total_days = len(returns_df)
    outperf_pct = outperf_days / total_days * 100

    print("DAILY OUTPERFORMANCE:")
    print(f"  Days beating NIFTY 500: {outperf_days}/{total_days} ({outperf_pct:.1f}%)")

    # Excess return stats
    excess_returns = returns_df["portfolio_return"] - returns_df["benchmark_return"]
    avg_excess = excess_returns.mean() * 252 * 100  # Annualized

    print(f"  Avg daily excess return: {excess_returns.mean()*100:.4f}%")
    print(f"  Annualized excess return: {avg_excess:.2f}%")
    print()

    # Final values
    print("FINAL VALUES (Starting from 100):")
    print(f"  Portfolio: {merged['portfolio_norm'].iloc[-1]:.2f}")
    print(f"  NIFTY 500: {merged['benchmark_norm'].iloc[-1]:.2f}")
    print(f"  Outperformance: {merged['portfolio_norm'].iloc[-1] - merged['benchmark_norm'].iloc[-1]:.2f} points")
    print()

    print("=" * 80)

    # Summary verdict
    if port_cagr > bench_cagr:
        alpha = (port_cagr - bench_cagr) * 100
        print(f"✓ Portfolio OUTPERFORMED NIFTY 500 by {alpha:.2f}% annualized")
    else:
        alpha = (bench_cagr - port_cagr) * 100
        print(f"✗ Portfolio UNDERPERFORMED NIFTY 500 by {alpha:.2f}% annualized")

    if port_sharpe > bench_sharpe:
        print(f"✓ Portfolio has BETTER risk-adjusted returns (Sharpe: {port_sharpe:.2f} vs {bench_sharpe:.2f})")
    else:
        print(f"✗ Portfolio has LOWER risk-adjusted returns (Sharpe: {port_sharpe:.2f} vs {bench_sharpe:.2f})")

    print("=" * 80)

    return 0


def main():
    parser = argparse.ArgumentParser(description="Compare portfolio to NIFTY 500 benchmark")
    parser.add_argument("--backtest", type=Path, required=True, help="Path to backtest directory (e.g., experiments/.../backtests/baseline)")
    parser.add_argument("--benchmark", type=Path, default=Path("indices_data/NIFTY_500.csv"), help="Path to NIFTY 500 benchmark data")
    args = parser.parse_args()

    if not args.backtest.exists():
        print(f"ERROR: Backtest directory not found: {args.backtest}")
        return 1

    if not args.benchmark.exists():
        print(f"ERROR: Benchmark file not found: {args.benchmark}")
        return 1

    return generate_report(args.backtest, args.benchmark)


if __name__ == "__main__":
    sys.exit(main())
