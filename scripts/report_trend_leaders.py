"""
Generate HTML report for Trend Leaders 20 strategy backtests.

Produces a comprehensive report with:
- Performance metrics table (all variants)
- Equity curve vs benchmark
- Drawdown chart
- Monthly returns heatmap
- Rolling Sharpe and volatility
- Holdings count and cash allocation over time
- Trade analysis (P&L distribution, exit reasons)
- Comparison with momentum strategy

Usage:
    python scripts/report_trend_leaders.py
    python scripts/report_trend_leaders.py --output data/trend_leaders/reports/trend_leaders_20_report.html
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
    from matplotlib.colors import TwoSlopeNorm
except ImportError:
    plt = None


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Chart generators
# ---------------------------------------------------------------------------

def chart_equity_curve(equity_df: pd.DataFrame, label: str = "TL20") -> str:
    fig, ax = plt.subplots(figsize=(12, 5))
    dates = equity_df["date"]
    pv = equity_df["portfolio_value"]
    bm = equity_df["benchmark"]

    # Normalize both to 100
    pv_norm = pv / pv.iloc[0] * 100
    bm_norm = bm / bm.iloc[0] * 100

    ax.plot(dates, pv_norm, label=f"{label} Portfolio", linewidth=1.5, color="#2563eb")
    ax.plot(dates, bm_norm, label="Nifty 100 TRI", linewidth=1.0, color="#9ca3af", alpha=0.8)
    ax.fill_between(dates, pv_norm, bm_norm, where=(pv_norm >= bm_norm),
                    alpha=0.1, color="#2563eb")
    ax.fill_between(dates, pv_norm, bm_norm, where=(pv_norm < bm_norm),
                    alpha=0.1, color="#ef4444")
    ax.set_ylabel("Growth of 100")
    ax.set_title(f"{label} — Equity Curve vs Benchmark")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    return fig_to_base64(fig)


def chart_drawdown(equity_df: pd.DataFrame, label: str = "TL20") -> str:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    dates = equity_df["date"]
    dd = equity_df["drawdown"] * 100

    ax.fill_between(dates, dd, 0, color="#ef4444", alpha=0.4)
    ax.plot(dates, dd, color="#dc2626", linewidth=0.8)
    ax.set_ylabel("Drawdown (%)")
    ax.set_title(f"{label} — Underwater Chart")
    ax.set_ylim(dd.min() * 1.2, 2)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    return fig_to_base64(fig)


def chart_monthly_heatmap(equity_df: pd.DataFrame) -> str:
    pv = equity_df.set_index("date")["portfolio_value"]
    monthly = pv.resample("ME").last().pct_change().dropna()
    monthly_df = pd.DataFrame({
        "year": monthly.index.year,
        "month": monthly.index.month,
        "return": monthly.values
    })
    pivot = monthly_df.pivot(index="year", columns="month", values="return")
    pivot.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    fig, ax = plt.subplots(figsize=(12, max(3, len(pivot) * 0.6)))
    vmax = max(abs(pivot.min().min()), abs(pivot.max().max()))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto", norm=norm)

    ax.set_xticks(range(12))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("Monthly Returns Heatmap")

    for i in range(len(pivot)):
        for j in range(12):
            val = pivot.iloc[i, j]
            if not np.isnan(val):
                color = "white" if abs(val) > vmax * 0.6 else "black"
                ax.text(j, i, f"{val:.1%}", ha="center", va="center",
                        fontsize=8, color=color)

    fig.colorbar(im, ax=ax, shrink=0.8, format="%.0f%%")
    plt.tight_layout()
    return fig_to_base64(fig)


def chart_rolling_metrics(equity_df: pd.DataFrame, window: int = 126) -> str:
    returns = equity_df.set_index("date")["portfolio_value"].pct_change().dropna()

    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    # Rolling Sharpe
    rolling_mean = returns.rolling(window).mean() * 252
    rolling_std = returns.rolling(window).std() * np.sqrt(252)
    rolling_sharpe = rolling_mean / rolling_std
    axes[0].plot(rolling_sharpe.index, rolling_sharpe.values, color="#2563eb", linewidth=1)
    axes[0].axhline(y=0, color="gray", linewidth=0.5)
    axes[0].axhline(y=1, color="green", linewidth=0.5, linestyle="--", alpha=0.5)
    axes[0].set_ylabel("Rolling Sharpe")
    axes[0].set_title(f"Rolling {window}-Day Metrics")
    axes[0].grid(True, alpha=0.3)

    # Rolling volatility
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)
    axes[1].plot(rolling_vol.index, rolling_vol.values * 100, color="#f59e0b", linewidth=1)
    axes[1].set_ylabel("Volatility (%)")
    axes[1].grid(True, alpha=0.3)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig_to_base64(fig)


def chart_holdings_and_cash(equity_df: pd.DataFrame) -> str:
    fig, axes = plt.subplots(2, 1, figsize=(12, 5), sharex=True)
    dates = equity_df["date"]

    # Holdings count
    axes[0].plot(dates, equity_df["holdings_count"], color="#2563eb", linewidth=1)
    axes[0].axhline(y=20, color="gray", linewidth=0.5, linestyle="--")
    axes[0].set_ylabel("Holdings")
    axes[0].set_title("Portfolio Composition Over Time")
    axes[0].set_ylim(0, 25)
    axes[0].grid(True, alpha=0.3)

    # Cash %
    axes[1].fill_between(dates, equity_df["cash_pct"] * 100, 0,
                         color="#f59e0b", alpha=0.4)
    axes[1].plot(dates, equity_df["cash_pct"] * 100, color="#d97706", linewidth=0.8)
    axes[1].set_ylabel("Cash (%)")
    axes[1].set_ylim(0, max(50, equity_df["cash_pct"].max() * 120))
    axes[1].grid(True, alpha=0.3)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig_to_base64(fig)


def chart_trade_pnl(trades_df: pd.DataFrame) -> str:
    if trades_df.empty or "reason" not in trades_df.columns:
        return ""

    sells = trades_df[trades_df["side"] == "SELL"].copy()
    if sells.empty:
        return ""

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Exit reason pie
    reason_counts = sells["reason"].value_counts()
    colors = {"monthly_exit": "#3b82f6", "weekly_exit": "#ef4444",
              "entry": "#10b981", "rebalance_trim": "#f59e0b"}
    pie_colors = [colors.get(r, "#9ca3af") for r in reason_counts.index]
    axes[0].pie(reason_counts.values, labels=reason_counts.index, colors=pie_colors,
                autopct="%1.0f%%", startangle=90)
    axes[0].set_title("Exit Reasons")

    # Monthly trade count
    sells["month"] = sells["date"].dt.to_period("M")
    monthly_trades = sells.groupby("month").size()
    axes[1].bar(range(len(monthly_trades)), monthly_trades.values,
                color="#3b82f6", alpha=0.6)
    axes[1].set_ylabel("Sells per Month")
    axes[1].set_title("Monthly Exit Frequency")
    axes[1].set_xlabel("Month")
    axes[1].grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    return fig_to_base64(fig)


def chart_variant_comparison(all_equity: dict) -> str:
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = {"base": "#2563eb", "market_filter": "#10b981",
              "monthly_only": "#f59e0b", "persistence_only": "#8b5cf6"}

    for name, eq in all_equity.items():
        pv = eq["portfolio_value"]
        pv_norm = pv / pv.iloc[0] * 100
        ax.plot(eq["date"], pv_norm, label=name, linewidth=1.2,
                color=colors.get(name, "#6b7280"))

    # Benchmark
    first_eq = next(iter(all_equity.values()))
    bm = first_eq["benchmark"]
    bm_norm = bm / bm.iloc[0] * 100
    ax.plot(first_eq["date"], bm_norm, label="Benchmark", linewidth=1,
            color="#9ca3af", linestyle="--")

    ax.set_ylabel("Growth of 100")
    ax.set_title("Variant Comparison — Equity Curves")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    return fig_to_base64(fig)


def chart_vs_momentum(tl20_equity: pd.DataFrame, mom_equity: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(12, 5))

    # Align dates
    common = tl20_equity["date"][tl20_equity["date"].isin(mom_equity["date"])]
    tl20 = tl20_equity[tl20_equity["date"].isin(common)].reset_index(drop=True)
    mom = mom_equity[mom_equity["date"].isin(common)].reset_index(drop=True)

    tl20_norm = tl20["portfolio_value"] / tl20["portfolio_value"].iloc[0] * 100
    mom_norm = mom["portfolio_value"] / mom["portfolio_value"].iloc[0] * 100
    bm_norm = tl20["benchmark"] / tl20["benchmark"].iloc[0] * 100

    ax.plot(tl20["date"], tl20_norm, label="Trend Leaders 20", linewidth=1.5, color="#2563eb")
    ax.plot(tl20["date"], mom_norm, label="Momentum L6", linewidth=1.5, color="#ef4444")
    ax.plot(tl20["date"], bm_norm, label="Nifty 100", linewidth=1, color="#9ca3af", linestyle="--")
    ax.set_ylabel("Growth of 100")
    ax.set_title("Trend Leaders 20 vs Momentum Strategy")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()
    return fig_to_base64(fig)


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def format_pct(val, decimals=1):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "-"
    return f"{val*100:.{decimals}f}%"


def format_num(val, decimals=2):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "-"
    return f"{val:.{decimals}f}"


def build_metrics_table(all_metrics: dict) -> str:
    rows_def = [
        ("Total Return", "total_return", format_pct),
        ("CAGR", "cagr", format_pct),
        ("Ann. Volatility", "annualized_volatility", format_pct),
        ("Sharpe Ratio", "sharpe_ratio", lambda v: format_num(v)),
        ("Sortino Ratio", "sortino_ratio", lambda v: format_num(v)),
        ("Calmar Ratio", "calmar_ratio", lambda v: format_num(v)),
        ("Max Drawdown", "max_drawdown", format_pct),
        ("Max DD Duration (days)", "max_drawdown_duration_days", lambda v: format_num(v, 0)),
        ("Ann. Turnover (1-sided)", "annualized_turnover", format_pct),
        ("Hit Rate", "hit_rate_overall", format_pct),
        ("Monthly Win Rate", "win_rate_monthly", format_pct),
        ("Avg Monthly Return", "avg_monthly_return", format_pct),
        ("Best Month", "best_month", format_pct),
        ("Worst Month", "worst_month", format_pct),
        ("Avg Holding Days", "avg_holding_days", lambda v: format_num(v, 0)),
        ("Median Holding Days", "median_holding_days", lambda v: format_num(v, 0)),
        ("Avg Holdings Count", "avg_holdings_count", lambda v: format_num(v, 1)),
        ("Avg Cash %", "avg_cash_pct", format_pct),
        ("% Time Invested", "pct_time_invested", format_pct),
        ("Total Trades", "trades_total", lambda v: format_num(v, 0)),
        ("Buys", "buys", lambda v: format_num(v, 0)),
        ("Sells", "sells", lambda v: format_num(v, 0)),
        ("Weekly Exits", "weekly_exits", lambda v: format_num(v, 0)),
        ("Monthly Exits", "monthly_exits", lambda v: format_num(v, 0)),
        ("Cost Drag", "cost_drag_pct", format_pct),
    ]

    names = list(all_metrics.keys())
    header = "<tr><th>Metric</th>" + "".join(f"<th>{n}</th>" for n in names) + "</tr>"
    body = ""
    for label, key, fmt in rows_def:
        cells = ""
        for name in names:
            val = all_metrics[name].get(key)
            cells += f"<td>{fmt(val)}</td>"
        body += f"<tr><td><strong>{label}</strong></td>{cells}</tr>"

    return f"<table class='metrics'>{header}{body}</table>"


def build_html_report(
    all_metrics: dict,
    all_equity: dict,
    charts: dict,
    output_path: Path,
):
    metrics_table = build_metrics_table(all_metrics)

    chart_sections = ""
    for title, img_b64 in charts.items():
        if img_b64:
            chart_sections += f"""
            <div class="chart-section">
                <h3>{title}</h3>
                <img src="data:image/png;base64,{img_b64}" />
            </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Trend Leaders 20 — Backtest Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 1200px; margin: 0 auto; padding: 20px; background: #f8fafc; color: #1e293b; }}
h1 {{ color: #1e40af; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; }}
h2 {{ color: #1e3a5f; margin-top: 40px; }}
h3 {{ color: #475569; }}
table.metrics {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 13px; }}
table.metrics th {{ background: #1e40af; color: white; padding: 8px 12px; text-align: right; }}
table.metrics th:first-child {{ text-align: left; }}
table.metrics td {{ padding: 6px 12px; border-bottom: 1px solid #e2e8f0; text-align: right; }}
table.metrics td:first-child {{ text-align: left; }}
table.metrics tr:hover {{ background: #f1f5f9; }}
.chart-section {{ margin: 30px 0; }}
.chart-section img {{ width: 100%; border: 1px solid #e2e8f0; border-radius: 8px; }}
.summary-box {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;
                padding: 16px; margin: 20px 0; }}
.summary-box h3 {{ margin-top: 0; color: #1e40af; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
@media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>Trend Leaders 20 — Backtest Report</h1>
<p>Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>

<div class="summary-box">
<h3>Strategy Summary</h3>
<p><strong>Universe:</strong> NSE 500 | <strong>Holdings:</strong> ~20 stocks |
<strong>Entry:</strong> Monthly | <strong>Exit:</strong> Weekly (Close &lt; 200 DMA) |
<strong>Exit Buffer:</strong> 20 (keep until rank &gt; 40) |
<strong>Sizing:</strong> Equal weight, 7.5% cap |
<strong>Slippage:</strong> 20 bps (OHLC/4)</p>
</div>

<h2>Performance Metrics</h2>
{metrics_table}

{chart_sections}

</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Report saved: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate Trend Leaders 20 HTML report")
    parser.add_argument("--data-dir", default="data/trend_leaders", type=Path)
    parser.add_argument("--output", default=None, type=Path)
    parser.add_argument("--momentum-equity", default="data/backtests/momentum_equity.csv", type=Path)
    args = parser.parse_args()

    if args.output is None:
        args.output = args.data_dir / "reports" / "trend_leaders_20_report.html"

    if plt is None:
        raise SystemExit("matplotlib is required for report generation")

    # Load all variant data
    variants = ["base", "market_filter", "monthly_only", "persistence_only"]
    all_metrics = {}
    all_equity = {}

    for variant in variants:
        variant_dir = args.data_dir / "backtests" / variant
        metrics_path = variant_dir / "tl20_metrics.csv"
        equity_path = variant_dir / "tl20_equity.csv"

        if not metrics_path.exists():
            print(f"  Skipping {variant} (no metrics file)")
            continue

        m = pd.read_csv(metrics_path)
        if not m.empty:
            all_metrics[variant] = m.iloc[0].to_dict()

        if equity_path.exists():
            eq = pd.read_csv(equity_path, parse_dates=["date"])
            all_equity[variant] = eq

    if not all_metrics:
        raise SystemExit("No variant data found")

    print(f"Loaded {len(all_metrics)} variants: {list(all_metrics.keys())}")

    # Load base variant trades for trade analysis
    base_trades_path = args.data_dir / "backtests" / "base" / "tl20_trades.csv"
    base_trades = pd.read_csv(base_trades_path, parse_dates=["date"]) if base_trades_path.exists() else pd.DataFrame()

    # Load momentum equity for comparison
    mom_equity = None
    if args.momentum_equity.exists():
        mom_equity = pd.read_csv(args.momentum_equity, parse_dates=["date"])
        print(f"Loaded momentum equity for comparison")

    # Generate charts
    print("Generating charts...")
    charts = {}

    base_eq = all_equity.get("base")
    if base_eq is not None:
        charts["Equity Curve (Base Variant)"] = chart_equity_curve(base_eq, "TL20 Base")
        charts["Drawdown (Base Variant)"] = chart_drawdown(base_eq, "TL20 Base")
        charts["Monthly Returns Heatmap"] = chart_monthly_heatmap(base_eq)
        charts["Rolling 6-Month Metrics"] = chart_rolling_metrics(base_eq, 126)
        charts["Holdings & Cash Allocation"] = chart_holdings_and_cash(base_eq)

    if not base_trades.empty:
        charts["Trade Analysis"] = chart_trade_pnl(base_trades)

    if len(all_equity) > 1:
        charts["All Variants — Equity Curves"] = chart_variant_comparison(all_equity)

    if mom_equity is not None and base_eq is not None:
        charts["Trend Leaders vs Momentum Strategy"] = chart_vs_momentum(base_eq, mom_equity)

    # Build report
    print("Building HTML report...")
    build_html_report(all_metrics, all_equity, charts, args.output)


if __name__ == "__main__":
    main()
