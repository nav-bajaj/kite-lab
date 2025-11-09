import argparse
import base64
import io
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

import numpy as np
import pandas as pd


def load_equity(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    if df.empty:
        raise RuntimeError(f"Equity file {path} is empty")
    df = df.sort_values("date").reset_index(drop=True)
    df["portfolio_return"] = df["portfolio_value"].pct_change().fillna(0)
    df["benchmark_return"] = df["benchmark"].pct_change().fillna(0)
    return df


def load_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date")


def annualized_return(df: pd.Series, dates: pd.Series) -> float:
    total_return = df.iloc[-1] / df.iloc[0] - 1
    days = (dates.iloc[-1] - dates.iloc[0]).days
    if days <= 0:
        return np.nan
    return (1 + total_return) ** (365.0 / days) - 1


def annualized_vol(returns: pd.Series) -> float:
    return returns.std() * np.sqrt(252)


def max_drawdown(values: pd.Series) -> float:
    running_max = values.cummax()
    drawdown = values / running_max - 1
    return drawdown.min()


def trailing_return(values: pd.Series, dates: pd.Series, days: int) -> float:
    end_date = dates.iloc[-1]
    start_date = end_date - pd.Timedelta(days=days)
    mask = dates >= start_date
    subset = values[mask]
    if len(subset) < 2:
        return np.nan
    return subset.iloc[-1] / subset.iloc[0] - 1


def generate_equity_chart(df: pd.DataFrame) -> str:
    if plt is None:
        return ""
    norm_port = df["portfolio_value"] / df["portfolio_value"].iloc[0]
    norm_bench = df["benchmark"] / df["benchmark"].iloc[0]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["date"], norm_port, label="Portfolio")
    ax.plot(df["date"], norm_bench, label="Benchmark", linestyle="--")
    ax.set_title("Portfolio vs Benchmark (normalized)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth (x)")
    ax.legend()
    ax.grid(alpha=0.3)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def trades_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    gross = df.groupby("side")["notional"].sum()
    summary = pd.DataFrame({
        "Metric": ["Buys", "Sells", "Total trades"],
        "Value": [gross.get("BUY", 0), gross.get("SELL", 0), len(df)],
    })
    return summary


def format_percent(value):
    if pd.isna(value):
        return "-"
    return f"{value:.2%}"


def build_report(equity_path: Path, trades_path: Path, output_path: Path):
    equity = load_equity(equity_path)
    trades = load_trades(trades_path)

    port_cagr = annualized_return(equity["portfolio_value"], equity["date"])
    bench_cagr = annualized_return(equity["benchmark"], equity["date"])
    port_vol = annualized_vol(equity["portfolio_return"])
    bench_vol = annualized_vol(equity["benchmark_return"])
    sharpe = np.nan
    if port_vol and not np.isnan(port_vol) and port_vol != 0:
        sharpe = (port_cagr - 0.0) / port_vol
    max_dd = max_drawdown(equity["portfolio_value"])

    summary_rows = [
        {"Metric": "Total Return", "Portfolio": format_percent(equity["portfolio_value"].iloc[-1] / equity["portfolio_value"].iloc[0] - 1),
         "Benchmark": format_percent(equity["benchmark"].iloc[-1] / equity["benchmark"].iloc[0] - 1)},
        {"Metric": "CAGR", "Portfolio": format_percent(port_cagr), "Benchmark": format_percent(bench_cagr)},
        {"Metric": "Volatility", "Portfolio": format_percent(port_vol), "Benchmark": format_percent(bench_vol)},
        {"Metric": "Sharpe (rf=0)", "Portfolio": f"{sharpe:.2f}" if sharpe is not None and not np.isnan(sharpe) else "-", "Benchmark": "-"},
        {"Metric": "Max Drawdown", "Portfolio": format_percent(max_dd), "Benchmark": "-"},
    ]
    summary_html = pd.DataFrame(summary_rows).to_html(index=False, escape=False)

    period_rows = []
    for label, days in [("1M", 30), ("3M", 90), ("6M", 180), ("1Y", 365), ("3Y", 1095)]:
        port = format_percent(trailing_return(equity["portfolio_value"], equity["date"], days))
        bench = format_percent(trailing_return(equity["benchmark"], equity["date"], days))
        period_rows.append({"Period": label, "Portfolio": port, "Benchmark": bench})
    periods_html = pd.DataFrame(period_rows).to_html(index=False, escape=False)

    trades_table_html = trades.tail(50).to_html(index=False) if not trades.empty else "<p>No trades recorded.</p>"
    trade_summary_html = trades_summary(trades).to_html(index=False) if not trades.empty else ""

    chart_b64 = generate_equity_chart(equity)

    html = f"""
    <html>
    <head>
        <meta charset='utf-8'>
        <title>Momentum Backtest Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            table, th, td {{ border: 1px solid #ddd; }}
            th, td {{ padding: 8px; text-align: center; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <h1>Momentum Backtest Report</h1>
        <p>Date range: {equity['date'].iloc[0].date()} → {equity['date'].iloc[-1].date()}</p>

        <h2>Performance Summary</h2>
        {summary_html}

        <h2>Trailing Returns</h2>
        {periods_html}

        <h2>Equity Curve</h2>
        {('<img src="data:image/png;base64,' + chart_b64 + '" alt="Equity Curve" />') if chart_b64 else '<p>Matplotlib not available; chart omitted.</p>'}

        <h2>Trades Summary</h2>
        {trade_summary_html if trade_summary_html else '<p>No trades.</p>'}

        <h2>Recent Trades</h2>
        {trades_table_html}
    </body>
    </html>
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Saved report to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report for momentum backtest")
    parser.add_argument("--equity", type=Path, default=Path("data/backtests/momentum_equity.csv"))
    parser.add_argument("--trades", type=Path, default=Path("data/backtests/momentum_trades.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/backtests/report.html"))
    args = parser.parse_args()

    build_report(args.equity, args.trades, args.output)


if __name__ == "__main__":
    main()
