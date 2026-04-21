"""
Track trailing 12-month rolling returns for all stock universes.

Computes daily rolling 252-trading-day returns for each universe's equity curve
and the Nifty 100 TRI benchmark, then outputs a CSV time series and comparison chart.

Usage:
    # Run on all three universes + benchmark (default)
    python scripts/trailing_12m_returns.py

    # Run on a specific universe
    python scripts/trailing_12m_returns.py --universe nse500

    # Custom window and output directory
    python scripts/trailing_12m_returns.py --window 126 --output-dir reports/6m/

    # Explicit equity file (single universe)
    python scripts/trailing_12m_returns.py --equity path/to/momentum_equity.csv
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

UNIVERSE_COLORS = {
    "NSE 500": "#1f77b4",
    "Nifty 100": "#2ca02c",
    "Nifty 250": "#ff7f0e",
    "Benchmark": "#d62728",
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

    run_dirs = sorted(
        [d for d in root.iterdir() if d.is_dir() and d.name.startswith(prefix + "_") and d.name[len(prefix) + 1:].isdigit()],
        key=lambda d: d.name,
        reverse=True,
    )

    for run_dir in run_dirs:
        equity_path = run_dir / "backtests" / "baseline" / "momentum_equity.csv"
        if equity_path.exists():
            return equity_path

    if cfg["fallback_equity"] and cfg["fallback_equity"].exists():
        return cfg["fallback_equity"]

    return None


def load_equity(path: Path) -> pd.DataFrame:
    """Load equity CSV and return date-indexed portfolio_value series."""
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    if "portfolio_value" not in df.columns:
        raise ValueError(f"Missing 'portfolio_value' column in {path}")
    return df[["date", "portfolio_value"]]


def load_benchmark(path: Path) -> pd.DataFrame:
    """Load benchmark CSV and return date-indexed close series."""
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    if "close" not in df.columns:
        raise ValueError(f"Missing 'close' column in {path}")
    return df[["date", "close"]].rename(columns={"close": "portfolio_value"})


def compute_trailing_returns(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Compute rolling trailing return over a window of trading days."""
    df = df.copy()
    df["trailing_return"] = df["portfolio_value"] / df["portfolio_value"].shift(window) - 1
    return df[["date", "trailing_return"]].dropna()


def generate_chart(merged: pd.DataFrame, output_path: Path, window: int) -> bool:
    """Generate trailing returns comparison chart."""
    if not HAS_MATPLOTLIB:
        print("Warning: matplotlib not available, skipping chart generation")
        return False

    cols = [c for c in merged.columns if c != "date"]
    fig, ax = plt.subplots(figsize=(14, 7))

    for col in cols:
        color = UNIVERSE_COLORS.get(col, None)
        ax.plot(merged["date"], merged[col] * 100, label=col, linewidth=1.8, color=color)

    ax.axhline(y=0, color="black", linewidth=0.8, linestyle="-", alpha=0.5)
    ax.set_ylabel("Trailing Return (%)", fontsize=12)
    ax.set_title(f"Trailing {window}-Day Rolling Returns", fontsize=14, fontweight="bold")
    ax.legend(loc="best", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return True


def _heatmap_color(value: float) -> str:
    """Return background CSS color for a trailing return value. Red < 0 < Green."""
    if np.isnan(value):
        return "#f5f5f5"
    # Clamp to [-50%, +150%] for color scaling
    clamped = max(-0.50, min(1.50, value))
    if clamped < 0:
        # Red scale: 0% → white, -50% → saturated red
        intensity = min(abs(clamped) / 0.50, 1.0)
        r, g, b = 255, int(255 * (1 - intensity * 0.6)), int(255 * (1 - intensity * 0.6))
    else:
        # Green scale: 0% → white, +150% → saturated green
        intensity = min(clamped / 1.50, 1.0)
        r, g, b = int(255 * (1 - intensity * 0.55)), 255, int(255 * (1 - intensity * 0.55))
    return f"rgb({r},{g},{b})"


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def generate_heatmap_html(merged: pd.DataFrame, output_path: Path, window: int) -> None:
    """Generate an HTML report with monthly heatmap tables for each universe."""
    cols = [c for c in merged.columns if c != "date"]

    # Sample to end-of-month values
    df = merged.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    monthly = df.resample("ME").last().reset_index()
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month

    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        f"<title>Trailing {window}-Day Returns Heatmap</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 30px; margin-bottom: 8px; color: #555; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 60px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        f"<h1>Trailing {window}-Day Returns Heatmap</h1>",
        f"<div class='subtitle'>Generated from monthly end-of-period values. "
        f"Green = positive, Red = negative.</div>",
    ]

    years = sorted(monthly["year"].unique())

    for col in cols:
        html_parts.append(f"<h2>{col}</h2>")
        html_parts.append("<table>")

        # Header row
        html_parts.append("<tr><th>Year</th>")
        for m in MONTH_NAMES:
            html_parts.append(f"<th>{m}</th>")
        html_parts.append("</tr>")

        for year in years:
            html_parts.append("<tr>")
            html_parts.append(f"<td class='year-col'>{year}</td>")
            for month in range(1, 13):
                row = monthly[(monthly["year"] == year) & (monthly["month"] == month)]
                if row.empty or pd.isna(row[col].iloc[0]):
                    html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                else:
                    val = row[col].iloc[0]
                    bg = _heatmap_color(val)
                    html_parts.append(
                        f"<td style='background:{bg};'>{val:+.1%}</td>"
                    )
            html_parts.append("</tr>")

        html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def print_summary(merged: pd.DataFrame, window: int) -> None:
    """Print summary statistics table."""
    cols = [c for c in merged.columns if c != "date"]

    print(f"\n{'=' * 80}")
    print(f"  TRAILING {window}-DAY RETURN SUMMARY")
    print(f"{'=' * 80}\n")

    header = f"{'Universe':<15} {'Current':>10} {'Min':>10} {'Max':>10} {'Median':>10} {'Avg':>10}"
    print(header)
    print("-" * 70)

    for col in cols:
        s = merged[col].dropna()
        if s.empty:
            continue
        print(
            f"{col:<15} "
            f"{s.iloc[-1]:>9.1%} "
            f"{s.min():>9.1%} "
            f"{s.max():>9.1%} "
            f"{s.median():>9.1%} "
            f"{s.mean():>9.1%}"
        )

    print(f"\n{'=' * 80}")


def main():
    parser = argparse.ArgumentParser(
        description="Track trailing 12-month rolling returns across stock universes"
    )
    parser.add_argument(
        "--universe",
        choices=["nse500", "nifty100", "nifty250", "all"],
        default="all",
        help="Stock universe to analyze (default: all)",
    )
    parser.add_argument(
        "--equity",
        help="Explicit path to equity CSV (overrides --universe, single series)",
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("data/benchmarks/nifty100.csv"),
        help="Benchmark CSV path (default: data/benchmarks/nifty100.csv)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=252,
        help="Rolling window in trading days (default: 252 = ~12 months)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/trailing_returns"),
        help="Directory to save CSV and chart (default: reports/trailing_returns/)",
    )

    args = parser.parse_args()

    # Collect series to process: list of (label, equity_df)
    series = []

    if args.equity:
        print(f"Loading equity from {args.equity}...")
        series.append(("Custom", load_equity(Path(args.equity))))
    else:
        universes = list(UNIVERSE_CONFIGS.keys()) if args.universe == "all" else [args.universe]
        for universe in universes:
            equity_path = find_latest_equity(universe)
            if equity_path is None:
                print(f"⚠ Skipping {UNIVERSE_CONFIGS[universe]['label']}: no equity file found")
                continue
            label = UNIVERSE_CONFIGS[universe]["label"]
            print(f"Loading {label} from {equity_path}")
            series.append((label, load_equity(equity_path)))

    if not series:
        print("No equity data found. Nothing to do.")
        return 1

    # Load benchmark
    if args.benchmark.exists():
        print(f"Loading benchmark from {args.benchmark}")
        series.append(("Benchmark", load_benchmark(args.benchmark)))
    else:
        print(f"⚠ Benchmark file not found: {args.benchmark}")

    # Compute trailing returns and merge
    trailing_dfs = []
    for label, df in series:
        tr = compute_trailing_returns(df, args.window)
        tr = tr.rename(columns={"trailing_return": label})
        trailing_dfs.append(tr)

    merged = trailing_dfs[0]
    for tr in trailing_dfs[1:]:
        merged = pd.merge(merged, tr, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    # Print summary
    print_summary(merged, args.window)

    # Save outputs
    args.output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = args.output_dir / "trailing_12m_returns.csv"
    merged.to_csv(csv_path, index=False)
    print(f"\n✓ CSV saved to {csv_path}")

    chart_path = args.output_dir / "trailing_12m_returns.png"
    if generate_chart(merged, chart_path, args.window):
        print(f"✓ Chart saved to {chart_path}")

    heatmap_path = args.output_dir / "trailing_12m_heatmap.html"
    generate_heatmap_html(merged, heatmap_path, args.window)
    print(f"✓ Heatmap saved to {heatmap_path}")

    return 0


if __name__ == "__main__":
    exit(main())
