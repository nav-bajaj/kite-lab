#!/usr/bin/env python3
"""Generate a concise daily HTML report for the momentum portfolio.

Reads the latest experiment data and per-symbol price files to produce a
single-page dashboard with: summary card, position breakdown, trailing
10-day performance, 30-day chart, and sector/industry exposure.

Usage:
    python scripts/generate_daily_report.py
    python scripts/generate_daily_report.py --output custom_report.html
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
except ImportError:
    plt = None


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def find_latest_experiment_dir(root: Path) -> Path:
    """Return the most-recently-created experiment directory under *root*."""
    dirs = sorted(
        [d for d in root.iterdir() if d.is_dir() and d.name.startswith("final_portfolio_2")],
        key=lambda d: d.name,
    )
    if not dirs:
        raise FileNotFoundError(f"No experiment directories found under {root}")
    return dirs[-1]


def load_equity(path: Path) -> pd.DataFrame:
    """Load momentum_equity.csv and add return columns."""
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["portfolio_return"] = df["portfolio_value"].pct_change().fillna(0)
    df["benchmark_return"] = df["benchmark"].pct_change().fillna(0)
    return df


def load_holdings(path: Path) -> pd.DataFrame:
    """Load momentum_holdings.csv (current positions)."""
    df = pd.read_csv(path)
    if "entry_date" in df.columns:
        df["entry_date"] = pd.to_datetime(df["entry_date"])
    return df


def load_symbol_prices(symbol: str, prices_dir: Path) -> pd.DataFrame:
    """Load daily OHLCV for a single symbol and return the last rows."""
    p = prices_dir / f"{symbol}_day.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def load_industry_map(universe_path: Path) -> dict:
    """Return {symbol: industry} from the universe CSV."""
    df = pd.read_csv(universe_path)
    col_sym = "Symbol" if "Symbol" in df.columns else "symbol"
    col_ind = "Industry" if "Industry" in df.columns else "industry"
    return dict(zip(df[col_sym].str.strip(), df[col_ind].str.strip()))


# ---------------------------------------------------------------------------
# Computation helpers
# ---------------------------------------------------------------------------

def compute_today_summary(equity: pd.DataFrame) -> dict:
    """Derive headline numbers from the equity curve."""
    if len(equity) < 2:
        raise ValueError("Need at least 2 rows in equity data")
    today = equity.iloc[-1]
    prev = equity.iloc[-2]

    port_val = today["portfolio_value"]
    port_prev = prev["portfolio_value"]
    port_chg = port_val - port_prev
    port_ret = port_chg / port_prev if port_prev else 0

    bench_ret = (today["benchmark"] - prev["benchmark"]) / prev["benchmark"] if prev["benchmark"] else 0

    peak = equity["portfolio_value"].cummax().iloc[-1]
    drawdown = port_val / peak - 1 if peak else 0

    return {
        "date": today["date"],
        "portfolio_value": port_val,
        "daily_change_rs": port_chg,
        "daily_return": port_ret,
        "benchmark_return": bench_ret,
        "outperformance": port_ret - bench_ret,
        "drawdown": drawdown,
    }


def compute_position_breakdown(holdings: pd.DataFrame, prices_dir: Path) -> pd.DataFrame:
    """Build per-position table with today's and previous close + PnL."""
    rows = []
    for _, h in holdings.iterrows():
        symbol = h["symbol"]
        shares = h["shares"]
        prices = load_symbol_prices(symbol, prices_dir)
        if prices.empty or len(prices) < 2:
            continue
        today_close = prices["close"].iloc[-1]
        prev_close = prices["close"].iloc[-2]
        chg_pct = (today_close - prev_close) / prev_close if prev_close else 0
        position_value = shares * today_close
        daily_pnl = shares * (today_close - prev_close)
        rows.append(
            {
                "Symbol": symbol,
                "Prev Close": prev_close,
                "Today Close": today_close,
                "Change %": chg_pct,
                "Position Value": position_value,
                "Daily PnL": daily_pnl,
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Daily PnL", ascending=False).reset_index(drop=True)
    return df


def compute_trailing_10d(equity: pd.DataFrame) -> pd.DataFrame:
    """Return the last 10 trading days of returns."""
    tail = equity.tail(11).copy()  # 11 rows to get 10 return periods
    tail["Portfolio PnL"] = tail["portfolio_value"].diff()
    tail = tail.iloc[1:]  # drop first row (NaN diff)
    return tail[["date", "portfolio_return", "Portfolio PnL", "benchmark_return"]].copy()


def generate_30d_chart(equity: pd.DataFrame) -> str:
    """Create a 30-day portfolio-vs-benchmark chart, return base64 PNG."""
    if plt is None:
        return ""
    last30 = equity.tail(30).copy()
    if last30.empty:
        return ""

    base_port = last30["portfolio_value"].iloc[0]
    base_bench = last30["benchmark"].iloc[0]
    last30["port_norm"] = last30["portfolio_value"] / base_port
    last30["bench_norm"] = last30["benchmark"] / base_bench

    fig, ax = plt.subplots(figsize=(8, 3), dpi=100)
    ax.plot(last30["date"], last30["port_norm"], label="Portfolio", linewidth=1.5, color="#007bff")
    ax.plot(last30["date"], last30["bench_norm"], label="Benchmark", linewidth=1.5, color="#6c757d")
    ax.axhline(1.0, color="#dee2e6", linewidth=0.8, linestyle="--")
    ax.set_ylabel("Normalized (1.0 = start)")
    ax.legend(loc="upper left", fontsize=8)
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title("Last 30 Trading Days", fontsize=10)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def compute_sector_exposure(positions: pd.DataFrame, industry_map: dict) -> pd.DataFrame:
    """Group positions by industry and aggregate."""
    if positions.empty:
        return pd.DataFrame()
    positions = positions.copy()
    positions["Industry"] = positions["Symbol"].map(industry_map).fillna("Unknown")
    grouped = (
        positions.groupby("Industry")
        .agg(Stocks=("Symbol", "count"), Value=("Position Value", "sum"), PnL=("Daily PnL", "sum"))
        .reset_index()
    )
    total_value = grouped["Value"].sum()
    grouped["Weight %"] = grouped["Value"] / total_value * 100 if total_value else 0
    grouped = grouped.sort_values("Value", ascending=False).reset_index(drop=True)
    return grouped


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def _color(val: float) -> str:
    """Return green/red color string based on sign."""
    if val > 0:
        return "#28a745"
    elif val < 0:
        return "#dc3545"
    return "#333"


def _fmt_pct(val: float) -> str:
    return f"{val * 100:+.2f}%"


def _fmt_rs(val: float) -> str:
    if abs(val) >= 1e5:
        return f"\u20b9{val:+,.0f}"
    return f"\u20b9{val:+,.2f}"


def _fmt_val(val: float) -> str:
    return f"\u20b9{val:,.0f}"


def render_html(
    summary: dict,
    positions: pd.DataFrame,
    trailing: pd.DataFrame,
    chart_b64: str,
    sector: pd.DataFrame,
) -> str:
    """Assemble the full HTML report."""

    # --- Section 1: Summary card ---
    s = summary
    summary_html = f"""
    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px;
                padding: 20px; margin-bottom: 20px;">
        <h2 style="margin-top: 0;">Portfolio Summary &mdash; {s['date'].strftime('%A, %d %B %Y')}</h2>
        <table style="border: none; width: auto;">
            <tr>
                <td style="border: none; padding: 4px 20px 4px 0; font-weight: bold;">Portfolio Value</td>
                <td style="border: none; padding: 4px 0;">{_fmt_val(s['portfolio_value'])}</td>
            </tr>
            <tr>
                <td style="border: none; padding: 4px 20px 4px 0; font-weight: bold;">Daily Change</td>
                <td style="border: none; padding: 4px 0; color: {_color(s['daily_return'])};">
                    {_fmt_pct(s['daily_return'])} ({_fmt_rs(s['daily_change_rs'])})
                </td>
            </tr>
            <tr>
                <td style="border: none; padding: 4px 20px 4px 0; font-weight: bold;">Benchmark Change</td>
                <td style="border: none; padding: 4px 0; color: {_color(s['benchmark_return'])};">
                    {_fmt_pct(s['benchmark_return'])}
                </td>
            </tr>
            <tr>
                <td style="border: none; padding: 4px 20px 4px 0; font-weight: bold;">Outperformance</td>
                <td style="border: none; padding: 4px 0; color: {_color(s['outperformance'])};">
                    {_fmt_pct(s['outperformance'])}
                </td>
            </tr>
            <tr>
                <td style="border: none; padding: 4px 20px 4px 0; font-weight: bold;">Current Drawdown</td>
                <td style="border: none; padding: 4px 0; color: {_color(s['drawdown'])};">
                    {_fmt_pct(s['drawdown'])}
                </td>
            </tr>
        </table>
    </div>
    """

    # --- Section 2: Position breakdown ---
    pos_rows = ""
    total_value = 0.0
    total_pnl = 0.0
    if not positions.empty:
        for _, r in positions.iterrows():
            chg_color = _color(r["Change %"])
            pnl_color = _color(r["Daily PnL"])
            pos_rows += f"""
            <tr>
                <td style="text-align: left; font-weight: bold;">{r['Symbol']}</td>
                <td>{r['Prev Close']:,.2f}</td>
                <td>{r['Today Close']:,.2f}</td>
                <td style="color: {chg_color};">{_fmt_pct(r['Change %'])}</td>
                <td>{_fmt_val(r['Position Value'])}</td>
                <td style="color: {pnl_color};">{_fmt_rs(r['Daily PnL'])}</td>
            </tr>"""
            total_value += r["Position Value"]
            total_pnl += r["Daily PnL"]

    pos_rows += f"""
    <tr style="background-color: #e9ecef; font-weight: bold;">
        <td style="text-align: left;">TOTAL</td>
        <td></td><td></td><td></td>
        <td>{_fmt_val(total_value)}</td>
        <td style="color: {_color(total_pnl)};">{_fmt_rs(total_pnl)}</td>
    </tr>"""

    positions_html = f"""
    <h2>Position Breakdown</h2>
    <table>
        <tr style="background-color: #e9ecef;">
            <th style="text-align: left;">Symbol</th>
            <th>Prev Close</th>
            <th>Today Close</th>
            <th>Change %</th>
            <th>Position Value</th>
            <th>Daily PnL</th>
        </tr>
        {pos_rows}
    </table>
    """

    # --- Section 3: Trailing 10-day ---
    trail_rows = ""
    cum_port_pnl = 0.0
    cum_port_ret = 1.0
    cum_bench_ret = 1.0
    if not trailing.empty:
        for _, r in trailing.iterrows():
            p_ret = r["portfolio_return"]
            b_ret = r["benchmark_return"]
            outperf = p_ret - b_ret
            cum_port_pnl += r["Portfolio PnL"]
            cum_port_ret *= 1 + p_ret
            cum_bench_ret *= 1 + b_ret
            trail_rows += f"""
            <tr>
                <td>{r['date'].strftime('%Y-%m-%d')}</td>
                <td style="color: {_color(p_ret)};">{_fmt_pct(p_ret)}</td>
                <td style="color: {_color(r['Portfolio PnL'])};">{_fmt_rs(r['Portfolio PnL'])}</td>
                <td style="color: {_color(b_ret)};">{_fmt_pct(b_ret)}</td>
                <td style="color: {_color(outperf)};">{_fmt_pct(outperf)}</td>
            </tr>"""

    total_port_ret = cum_port_ret - 1
    total_bench_ret = cum_bench_ret - 1
    total_outperf = total_port_ret - total_bench_ret
    trail_rows += f"""
    <tr style="background-color: #e9ecef; font-weight: bold;">
        <td>TOTAL (10d)</td>
        <td style="color: {_color(total_port_ret)};">{_fmt_pct(total_port_ret)}</td>
        <td style="color: {_color(cum_port_pnl)};">{_fmt_rs(cum_port_pnl)}</td>
        <td style="color: {_color(total_bench_ret)};">{_fmt_pct(total_bench_ret)}</td>
        <td style="color: {_color(total_outperf)};">{_fmt_pct(total_outperf)}</td>
    </tr>"""

    trailing_html = f"""
    <h2>Trailing 10-Day Summary</h2>
    <table>
        <tr style="background-color: #e9ecef;">
            <th>Date</th>
            <th>Portfolio Return</th>
            <th>Portfolio PnL</th>
            <th>Benchmark Return</th>
            <th>Outperformance</th>
        </tr>
        {trail_rows}
    </table>
    """

    # --- Section 4: 30-day chart ---
    chart_html = ""
    if chart_b64:
        chart_html = f"""
        <h2>Last 30 Trading Days</h2>
        <img src="data:image/png;base64,{chart_b64}" alt="30-day chart" style="max-width: 100%; height: auto;">
        """

    # --- Section 5: Sector exposure ---
    sec_rows = ""
    if not sector.empty:
        for _, r in sector.iterrows():
            pnl_color = _color(r["PnL"])
            sec_rows += f"""
            <tr>
                <td style="text-align: left;">{r['Industry']}</td>
                <td>{r['Stocks']}</td>
                <td>{_fmt_val(r['Value'])}</td>
                <td>{r['Weight %']:.1f}%</td>
                <td style="color: {pnl_color};">{_fmt_rs(r['PnL'])}</td>
            </tr>"""

    sector_html = f"""
    <h2>Sector / Industry Exposure</h2>
    <table>
        <tr style="background-color: #e9ecef;">
            <th style="text-align: left;">Industry</th>
            <th># Stocks</th>
            <th>Value</th>
            <th>Weight %</th>
            <th>Daily PnL</th>
        </tr>
        {sec_rows}
    </table>
    """

    # --- Assemble full HTML ---
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Daily Portfolio Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #fff; color: #333; }}
        h1 {{ color: #333; margin-bottom: 5px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        table, th, td {{ border: 1px solid #ddd; }}
        th, td {{ padding: 8px; text-align: center; }}
        th {{ background-color: #e9ecef; }}
        img {{ max-width: 100%; height: auto; }}
        .subtitle {{ color: #6c757d; margin-top: 0; }}
    </style>
</head>
<body>
    <h1>Daily Portfolio Report</h1>
    <p class="subtitle">NSE 500 Momentum &middot; L6 &middot; Weekly Rebalance &middot; Top 24</p>
    {summary_html}
    {positions_html}
    {trailing_html}
    {chart_html}
    {sector_html}
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #dee2e6;">
    <p style="color: #6c757d; font-size: 12px;">
        Generated from latest experiment data. Prices from nse500_data daily files.
    </p>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate daily HTML portfolio report")
    parser.add_argument(
        "--experiment-root",
        type=Path,
        default=Path("experiments/final_portfolio"),
        help="Root directory containing experiment folders",
    )
    parser.add_argument(
        "--prices-dir",
        type=Path,
        default=Path("nse500_data"),
        help="Directory with per-symbol daily price CSVs",
    )
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=Path("data/static/nse500_universe.csv"),
        help="Universe CSV with symbol-to-industry mapping",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/final_portfolio/daily_report.html"),
        help="Output HTML file path",
    )
    args = parser.parse_args()

    # Find latest experiment
    exp_dir = find_latest_experiment_dir(args.experiment_root)
    print(f"Using experiment: {exp_dir.name}")

    backtest_dir = exp_dir / "backtests" / "baseline"
    equity_path = backtest_dir / "momentum_equity.csv"
    holdings_path = backtest_dir / "momentum_holdings.csv"

    if not equity_path.exists():
        raise FileNotFoundError(f"Equity file not found: {equity_path}")
    if not holdings_path.exists():
        raise FileNotFoundError(f"Holdings file not found: {holdings_path}")

    # Load data
    equity = load_equity(equity_path)
    holdings = load_holdings(holdings_path)
    industry_map = load_industry_map(args.universe_file) if args.universe_file.exists() else {}

    # Compute sections
    summary = compute_today_summary(equity)
    positions = compute_position_breakdown(holdings, args.prices_dir)
    trailing = compute_trailing_10d(equity)
    chart_b64 = generate_30d_chart(equity)
    sector = compute_sector_exposure(positions, industry_map)

    # Render and write
    html = render_html(summary, positions, trailing, chart_b64, sector)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html)
    print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
