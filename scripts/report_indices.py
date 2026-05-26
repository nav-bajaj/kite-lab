"""
Generate comprehensive HTML report comparing portfolio performance against tracked indices.

This script:
1. Loads portfolio equity data from backtest runs
2. Loads all tracked indices from indices_data/ directory
3. Computes performance metrics for portfolio and all indices
4. Groups indices by category (broad market, sectoral, factor, global, commodity)
5. Generates HTML report with:
   - Summary table with key metrics
   - Equity curves comparison
   - Category-wise comparison tables
   - Correlation matrix
   - Rolling metrics charts

Usage:
    # Compare portfolio against all indices
    python scripts/report_indices.py --portfolio data/backtests/run1/momentum_equity.csv --output indices_report.html

    # Compare specific portfolio run
    python scripts/report_indices.py --portfolio data/final_portfolio/final_equity.csv --output indices_report.html

Requirements:
    - Portfolio equity CSV with columns: date, portfolio_value, benchmark
    - Indices data in indices_data/ directory
    - data/static/tracked_indices.csv for index metadata
"""

import argparse
import base64
import io
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
    print("Warning: matplotlib not available, charts will be skipped")


# ===========================
# Data Loading
# ===========================


def load_portfolio_equity(path: Path) -> pd.DataFrame:
    """Load portfolio equity curve."""
    df = pd.read_csv(path, parse_dates=["date"])
    if df.empty:
        raise RuntimeError(f"Portfolio equity file {path} is empty")
    df = df.sort_values("date").reset_index(drop=True)
    if "portfolio_value" not in df.columns:
        raise ValueError(f"Missing 'portfolio_value' column in {path}")
    return df


def load_index_data(index_dir: Path) -> dict:
    """
    Load all index data from directory.

    Returns:
        dict: {index_name: DataFrame with date, close columns}
    """
    index_dir = Path(index_dir)
    if not index_dir.exists():
        raise FileNotFoundError(f"Index data directory not found: {index_dir}")

    indices = {}
    for csv_file in index_dir.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file, parse_dates=["date"])
            if df.empty or "close" not in df.columns:
                print(f"Warning: Skipping {csv_file.name} - empty or missing 'close' column")
                continue
            df = df.sort_values("date").reset_index(drop=True)
            index_name = csv_file.stem  # Filename without extension
            indices[index_name] = df[["date", "close"]].copy()
        except Exception as e:
            print(f"Warning: Failed to load {csv_file.name}: {e}")

    return indices


def load_index_metadata(metadata_path: Path) -> pd.DataFrame:
    """Load index metadata (categories, descriptions)."""
    if not metadata_path.exists():
        print(f"Warning: Index metadata not found at {metadata_path}")
        return pd.DataFrame()

    df = pd.read_csv(metadata_path)
    # Create mapping from tradingsymbol to metadata
    df["filename"] = df["tradingsymbol"].str.replace(" ", "_").str.replace("/", "_")
    return df


# ===========================
# Metric Computation
# ===========================


def annualized_return(values: pd.Series, dates: pd.Series) -> float:
    """Compute annualized return (CAGR)."""
    if len(values) < 2:
        return np.nan
    total_return = values.iloc[-1] / values.iloc[0] - 1
    days = (dates.iloc[-1] - dates.iloc[0]).days
    if days <= 0:
        return np.nan
    return (1 + total_return) ** (365.0 / days) - 1


def annualized_vol(returns: pd.Series) -> float:
    """Compute annualized volatility."""
    return returns.std() * np.sqrt(252)


def max_drawdown(values: pd.Series) -> float:
    """Compute maximum drawdown."""
    running_max = values.cummax()
    drawdown = values / running_max - 1
    return drawdown.min()


def sharpe_ratio(cagr: float, volatility: float, risk_free_rate: float = 0.05) -> float:
    """
    Compute Sharpe ratio.

    Args:
        cagr: Annualized return (CAGR)
        volatility: Annualized volatility
        risk_free_rate: Annual risk-free rate (default 5%)

    Returns:
        Sharpe ratio (excess return per unit of risk)
    """
    if volatility > 0:
        return (cagr - risk_free_rate) / volatility
    return np.nan


def compute_metrics(values: pd.Series, dates: pd.Series) -> dict:
    """Compute comprehensive performance metrics."""
    returns = values.pct_change().fillna(0)

    # Compute base metrics
    cagr = annualized_return(values, dates)
    volatility = annualized_vol(returns)

    metrics = {
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe_ratio(cagr, volatility),
        "max_drawdown": max_drawdown(values),
        "total_return": (values.iloc[-1] / values.iloc[0] - 1) if len(values) > 0 else np.nan,
        "final_value": values.iloc[-1] if len(values) > 0 else np.nan,
        "start_date": dates.iloc[0] if len(dates) > 0 else None,
        "end_date": dates.iloc[-1] if len(dates) > 0 else None,
    }

    return metrics


def align_series(portfolio_df: pd.DataFrame, index_df: pd.DataFrame) -> tuple:
    """
    Align portfolio and index dataframes by date.

    Returns:
        (aligned_portfolio_values, aligned_index_values, aligned_dates)
    """
    merged = pd.merge(
        portfolio_df[["date", "portfolio_value"]],
        index_df[["date", "close"]],
        on="date",
        how="inner",
    )
    if merged.empty:
        return None, None, None

    return merged["portfolio_value"], merged["close"], merged["date"]


def compute_correlation(portfolio_values: pd.Series, index_values: pd.Series) -> float:
    """Compute correlation between portfolio and index returns."""
    if portfolio_values is None or index_values is None or len(portfolio_values) < 2:
        return np.nan

    port_returns = portfolio_values.pct_change().dropna()
    idx_returns = index_values.pct_change().dropna()

    if len(port_returns) < 2 or len(idx_returns) < 2:
        return np.nan

    return port_returns.corr(idx_returns)


def compute_beta(portfolio_values: pd.Series, index_values: pd.Series) -> float:
    """Compute beta of portfolio vs index."""
    if portfolio_values is None or index_values is None or len(portfolio_values) < 2:
        return np.nan

    port_returns = portfolio_values.pct_change().dropna()
    idx_returns = index_values.pct_change().dropna()

    if len(port_returns) < 2 or len(idx_returns) < 2:
        return np.nan

    covariance = port_returns.cov(idx_returns)
    variance = idx_returns.var()

    return covariance / variance if variance > 0 else np.nan


# ===========================
# Chart Generation
# ===========================


def fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 encoded string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.close(fig)
    return img_base64


def plot_equity_curves(portfolio_df: pd.DataFrame, indices: dict, metadata: pd.DataFrame, category: str = None) -> str:
    """
    Plot equity curves for portfolio and selected indices.

    Args:
        portfolio_df: Portfolio equity DataFrame
        indices: Dict of index name -> DataFrame
        metadata: Index metadata DataFrame
        category: If specified, only plot indices from this category
    """
    if not HAS_MATPLOTLIB:
        return ""

    fig, ax = plt.subplots(figsize=(14, 8))

    # Normalize portfolio to 100
    port_normalized = portfolio_df["portfolio_value"] / portfolio_df["portfolio_value"].iloc[0] * 100
    ax.plot(portfolio_df["date"], port_normalized, label="Portfolio", linewidth=2.5, color="black", zorder=10)

    # Filter indices by category if specified
    if category and not metadata.empty:
        category_indices = metadata[metadata["category"] == category]["filename"].tolist()
        filtered_indices = {k: v for k, v in indices.items() if k in category_indices}
    else:
        filtered_indices = indices

    # Plot indices
    colors = plt.cm.tab20(np.linspace(0, 1, len(filtered_indices)))
    for (idx_name, idx_df), color in zip(filtered_indices.items(), colors):
        idx_normalized = idx_df["close"] / idx_df["close"].iloc[0] * 100
        ax.plot(idx_df["date"], idx_normalized, label=idx_name.replace("_", " "), alpha=0.7, linewidth=1.5, color=color)

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Normalized Value (Base 100)", fontsize=12)
    title = f"Portfolio vs {category.replace('_', ' ').title()} Indices" if category else "Portfolio vs All Indices"
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(loc="best", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=45)

    return fig_to_base64(fig)


def plot_correlation_heatmap(portfolio_df: pd.DataFrame, indices: dict) -> str:
    """Plot correlation heatmap between portfolio and indices."""
    if not HAS_MATPLOTLIB:
        return ""

    # Compute correlation matrix
    correlations = {}
    for idx_name, idx_df in indices.items():
        port_vals, idx_vals, _ = align_series(portfolio_df, idx_df)
        corr = compute_correlation(port_vals, idx_vals)
        if not np.isnan(corr):
            correlations[idx_name.replace("_", " ")] = corr

    if not correlations:
        return ""

    # Sort by correlation
    sorted_corr = dict(sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True))

    fig, ax = plt.subplots(figsize=(10, max(6, len(sorted_corr) * 0.3)))

    names = list(sorted_corr.keys())
    values = list(sorted_corr.values())

    colors = ["green" if v > 0 else "red" for v in values]
    y_pos = np.arange(len(names))

    ax.barh(y_pos, values, color=colors, alpha=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Correlation with Portfolio", fontsize=12)
    ax.set_title("Portfolio Correlation with Indices", fontsize=14, fontweight="bold")
    ax.axvline(x=0, color="black", linestyle="-", linewidth=0.8)
    ax.grid(True, axis="x", alpha=0.3)

    return fig_to_base64(fig)


def plot_performance_comparison(metrics_df: pd.DataFrame, metric: str, category: str = None) -> str:
    """Plot bar chart comparing specific metric across indices."""
    if not HAS_MATPLOTLIB:
        return ""

    df = metrics_df.copy()
    if category:
        df = df[df["category"] == category]

    if df.empty or metric not in df.columns:
        return ""

    df = df.sort_values(metric, ascending=False)

    fig, ax = plt.subplots(figsize=(12, max(6, len(df) * 0.3)))

    colors = ["green" if x > 0 else "red" for x in df[metric]]
    y_pos = np.arange(len(df))

    ax.barh(y_pos, df[metric], color=colors, alpha=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df["name"], fontsize=9)
    ax.set_xlabel(metric.replace("_", " ").title(), fontsize=12)
    title = f"{metric.replace('_', ' ').title()} Comparison"
    if category:
        title += f" ({category.replace('_', ' ').title()})"
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.3)

    return fig_to_base64(fig)


# ===========================
# HTML Report Generation
# ===========================


def generate_metrics_table(metrics_df: pd.DataFrame) -> str:
    """Generate HTML table for metrics comparison."""
    html = '<table class="metrics-table">\n'
    html += "<thead><tr>"
    html += "<th>Index</th><th>Category</th><th>CAGR</th><th>Volatility</th><th>Sharpe</th><th>Max DD</th><th>Correlation</th><th>Beta</th><th>Total Return</th>"
    html += "</tr></thead>\n<tbody>\n"

    for _, row in metrics_df.iterrows():
        html += "<tr>"
        html += f"<td><strong>{row['name']}</strong></td>"
        html += f"<td>{row['category'].replace('_', ' ').title()}</td>"
        html += f"<td>{row['cagr']:.2%}</td>"
        html += f"<td>{row['volatility']:.2%}</td>"
        html += f"<td>{row['sharpe']:.2f}</td>"
        html += f"<td>{row['max_drawdown']:.2%}</td>"
        html += f"<td>{row['correlation']:.3f}</td>"
        html += f"<td>{row['beta']:.3f}</td>"
        html += f"<td>{row['total_return']:.2%}</td>"
        html += "</tr>\n"

    html += "</tbody></table>\n"
    return html


def generate_html_report(
    portfolio_df: pd.DataFrame,
    indices: dict,
    metadata: pd.DataFrame,
    output_path: Path,
):
    """Generate comprehensive HTML report."""
    print("Generating report...")

    # Compute portfolio metrics
    portfolio_metrics = compute_metrics(portfolio_df["portfolio_value"], portfolio_df["date"])
    print(f"Portfolio CAGR: {portfolio_metrics['cagr']:.2%}")

    # Compute metrics for all indices
    all_metrics = []

    for idx_name, idx_df in indices.items():
        # Get metadata
        meta_row = metadata[metadata["filename"] == idx_name]
        if not meta_row.empty:
            display_name = meta_row.iloc[0]["name"]
            category = meta_row.iloc[0]["category"]
            description = meta_row.iloc[0].get("description", "")
        else:
            display_name = idx_name.replace("_", " ")
            category = "unknown"
            description = ""

        # Align with portfolio for correlation/beta
        port_vals, idx_vals, dates = align_series(portfolio_df, idx_df)

        if port_vals is None:
            print(f"Warning: No overlapping dates for {idx_name}, skipping")
            continue

        # Compute metrics
        idx_metrics = compute_metrics(idx_vals, dates)
        idx_metrics["name"] = display_name
        idx_metrics["filename"] = idx_name
        idx_metrics["category"] = category
        idx_metrics["description"] = description
        idx_metrics["correlation"] = compute_correlation(port_vals, idx_vals)
        idx_metrics["beta"] = compute_beta(port_vals, idx_vals)

        all_metrics.append(idx_metrics)

    metrics_df = pd.DataFrame(all_metrics)

    # Sort by CAGR descending
    metrics_df = metrics_df.sort_values("cagr", ascending=False)

    # Add portfolio row at top
    portfolio_row = portfolio_metrics.copy()
    portfolio_row["name"] = "Portfolio (Our Strategy)"
    portfolio_row["category"] = "portfolio"
    portfolio_row["correlation"] = 1.0
    portfolio_row["beta"] = 1.0
    portfolio_row["description"] = "Momentum-based strategy"
    metrics_df = pd.concat([pd.DataFrame([portfolio_row]), metrics_df], ignore_index=True)

    # Generate charts
    print("Generating charts...")

    # Chart 1: All indices equity curves
    chart_all = plot_equity_curves(portfolio_df, indices, metadata, category=None)

    # Chart 2: Correlation heatmap
    chart_corr = plot_correlation_heatmap(portfolio_df, indices)

    # Charts by category
    categories = metrics_df[metrics_df["category"] != "portfolio"]["category"].unique()
    category_charts = {}
    for cat in categories:
        category_charts[cat] = plot_equity_curves(portfolio_df, indices, metadata, category=cat)

    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Indices Performance Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #444;
            margin-top: 40px;
            border-bottom: 2px solid #ddd;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #555;
            margin-top: 30px;
        }}
        .summary-box {{
            background: #e7f3ff;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            border-left: 4px solid #007bff;
        }}
        .summary-box .metric {{
            display: inline-block;
            margin: 10px 20px;
        }}
        .summary-box .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .summary-box .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        .metrics-table th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #dee2e6;
            font-weight: 600;
            color: #495057;
        }}
        .metrics-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #dee2e6;
        }}
        .metrics-table tr:hover {{
            background: #f8f9fa;
        }}
        .chart {{
            margin: 30px 0;
            text-align: center;
        }}
        .chart img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .category-section {{
            margin: 40px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 6px;
        }}
        .info {{
            background: #fff3cd;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #ffc107;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Indices Performance Report</h1>

        <div class="info">
            <strong>Report Date:</strong> {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
            <strong>Portfolio Period:</strong> {portfolio_metrics['start_date'].strftime("%Y-%m-%d")} to {portfolio_metrics['end_date'].strftime("%Y-%m-%d")}<br>
            <strong>Indices Tracked:</strong> {len(metrics_df) - 1} indices across {len(categories)} categories
        </div>

        <div class="summary-box">
            <h3 style="margin-top: 0;">Portfolio Performance Summary</h3>
            <div class="metric">
                <div class="metric-label">CAGR</div>
                <div class="metric-value">{portfolio_metrics['cagr']:.2%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Volatility</div>
                <div class="metric-value">{portfolio_metrics['volatility']:.2%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">{portfolio_metrics['sharpe']:.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value">{portfolio_metrics['max_drawdown']:.2%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Return</div>
                <div class="metric-value">{portfolio_metrics['total_return']:.2%}</div>
            </div>
        </div>

        <h2>📈 Comprehensive Metrics Comparison</h2>
        {generate_metrics_table(metrics_df)}

        <h2>📉 Equity Curves - All Indices</h2>
        <div class="chart">
            <img src="data:image/png;base64,{chart_all}" alt="All Indices Equity Curves">
        </div>

        <h2>🔗 Correlation Analysis</h2>
        <div class="chart">
            <img src="data:image/png;base64,{chart_corr}" alt="Correlation Heatmap">
        </div>
"""

    # Add category sections
    for cat in sorted(categories):
        cat_display = cat.replace("_", " ").title()
        cat_df = metrics_df[metrics_df["category"] == cat]

        html += f"""
        <div class="category-section">
            <h2>{cat_display} ({len(cat_df)} indices)</h2>

            <h3>Metrics Table</h3>
            {generate_metrics_table(cat_df)}

            <h3>Equity Curves</h3>
            <div class="chart">
                <img src="data:image/png;base64,{category_charts[cat]}" alt="{cat_display} Equity Curves">
            </div>
        </div>
"""

    # Footer
    html += """
        <div class="footer">
            Generated by Kite-Lab Indices Reporting System<br>
            🤖 Powered by Claude Code
        </div>
    </div>
</body>
</html>
"""

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✓ Report saved to {output_path}")


# ===========================
# Main
# ===========================


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive HTML report comparing portfolio against tracked indices"
    )
    parser.add_argument(
        "--portfolio",
        required=True,
        help="Path to portfolio equity CSV (must have date, portfolio_value columns)",
    )
    parser.add_argument(
        "--indices-dir",
        default="indices_data",
        help="Directory containing indices CSV files (default: indices_data)",
    )
    parser.add_argument(
        "--metadata",
        default="data/static/tracked_indices.csv",
        help="Path to indices metadata CSV (default: data/static/tracked_indices.csv)",
    )
    parser.add_argument(
        "--output",
        default="indices_report.html",
        help="Output HTML file path (default: indices_report.html)",
    )

    args = parser.parse_args()

    # Load data
    print("Loading portfolio data...")
    portfolio_df = load_portfolio_equity(Path(args.portfolio))

    print("Loading indices data...")
    indices = load_index_data(Path(args.indices_dir))
    print(f"Loaded {len(indices)} indices")

    if not indices:
        print("Error: No indices found. Run scripts/fetch_indices_history.py first.")
        return 1

    print("Loading indices metadata...")
    metadata = load_index_metadata(Path(args.metadata))

    # Generate report
    generate_html_report(portfolio_df, indices, metadata, Path(args.output))

    print(f"\n✓ Report generation complete!")
    return 0


if __name__ == "__main__":
    exit(main())
