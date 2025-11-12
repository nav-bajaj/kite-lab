import argparse
import base64
import io
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


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


def annualized_return(values: pd.Series, dates: pd.Series) -> float:
    total_return = values.iloc[-1] / values.iloc[0] - 1
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
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(df["date"], norm_port, label="Portfolio")
    ax.plot(df["date"], norm_bench, label="Benchmark", linestyle="--")
    ax.set_title("Equity vs Benchmark")
    ax.legend()
    ax.grid(alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def compute_symbol_pnl(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["symbol", "pnl"])
    trades = trades.sort_values("date")
    positions = defaultdict(float)
    cost_basis = defaultdict(float)
    pnl = defaultdict(float)

    for row in trades.itertuples():
        sym = row.symbol
        shares = row.shares
        price = row.price
        slip = row.slippage
        if row.side.upper() == "BUY":
            total_cost = shares * price + slip
            positions[sym] += shares
            cost_basis[sym] += total_cost
        else:
            if positions[sym] <= 0:
                continue
            if shares > positions[sym]:
                shares = positions[sym]
            avg_cost = cost_basis[sym] / positions[sym]
            proceeds = shares * price - slip
            realized = proceeds - avg_cost * shares
            pnl[sym] += realized
            positions[sym] -= shares
            cost_basis[sym] -= avg_cost * shares

    data = sorted(pnl.items(), key=lambda x: x[1], reverse=True)
    return pd.DataFrame(data, columns=["symbol", "pnl"])


def format_percent(value):
    if pd.isna(value):
        return "-"
    return f"{value:.2%}"


def analyze_run(run_path: Path, label: str):
    equity = load_equity(run_path / "momentum_equity.csv")
    trades = load_trades(run_path / "momentum_trades.csv")

    metrics = {
        "label": label,
        "total_return": equity["portfolio_value"].iloc[-1] / equity["portfolio_value"].iloc[0] - 1,
        "benchmark_return": equity["benchmark"].iloc[-1] / equity["benchmark"].iloc[0] - 1,
        "cagr": annualized_return(equity["portfolio_value"], equity["date"]),
        "bench_cagr": annualized_return(equity["benchmark"], equity["date"]),
        "vol": annualized_vol(equity["portfolio_return"]),
        "bench_vol": annualized_vol(equity["benchmark_return"]),
        "max_dd": max_drawdown(equity["portfolio_value"]),
    }
    metrics["sharpe"] = (
        (metrics["cagr"] or 0) / metrics["vol"] if metrics["vol"] not in (0, None) else np.nan
    )

    periods = {}
    for label_per, days in [("1M", 30), ("3M", 90), ("6M", 180), ("1Y", 365)]:
        periods[label_per] = {
            "portfolio": trailing_return(equity["portfolio_value"], equity["date"], days),
            "benchmark": trailing_return(equity["benchmark"], equity["date"], days),
        }

    chart = generate_equity_chart(equity)
    symbol_pnl = compute_symbol_pnl(trades)
    best = symbol_pnl.head(5)
    worst = symbol_pnl.tail(5).iloc[::-1] if not symbol_pnl.empty else symbol_pnl

    return {
        "metrics": metrics,
        "periods": periods,
        "chart": chart,
        "best": best,
        "worst": worst,
        "recent_trades": trades.tail(30),
        "date_range": (equity["date"].iloc[0], equity["date"].iloc[-1]),
    }


def build_report(run_paths, output_path: Path):
    analyses = []
    for path in run_paths:
        run_path = Path(path)
        label = run_path.name
        analyses.append(analyze_run(run_path, label))

    summary_rows = []
    for entry in analyses:
        m = entry["metrics"]
        summary_rows.append(
            {
                "Scenario": m["label"],
                "Total Return": format_percent(m["total_return"]),
                "Benchmark Return": format_percent(m["benchmark_return"]),
                "CAGR": format_percent(m["cagr"]),
                "Volatility": format_percent(m["vol"]),
                "Sharpe": f"{m['sharpe']:.2f}" if not pd.isna(m["sharpe"]) else "-",
                "Max Drawdown": format_percent(m["max_dd"]),
            }
        )
    summary_html = pd.DataFrame(summary_rows).to_html(index=False, escape=False)

    sections = []
    for entry in analyses:
        m = entry["metrics"]
        label = m["label"]
        date_range = f"{entry['date_range'][0].date()} → {entry['date_range'][1].date()}"

        periods_df = pd.DataFrame(
            [
                {
                    "Period": k,
                    "Portfolio": format_percent(v["portfolio"]),
                    "Benchmark": format_percent(v["benchmark"]),
                }
                for k, v in entry["periods"].items()
            ]
        )
        period_html = periods_df.to_html(index=False, escape=False)

        best_html = (
            entry["best"].to_html(index=False) if not entry["best"].empty else "<p>No realized gains.</p>"
        )
        worst_html = (
            entry["worst"].to_html(index=False) if not entry["worst"].empty else "<p>No realized losses.</p>"
        )
        trades_html = (
            entry["recent_trades"].to_html(index=False) if not entry["recent_trades"].empty else "<p>No trades.</p>"
        )
        chart_html = (
            f'<img src="data:image/png;base64,{entry["chart"]}" alt="{label} chart" />'
            if entry["chart"]
            else "<p>Chart unavailable (matplotlib missing).</p>"
        )

        sections.append(
            f"""
            <section>
                <h2>{label} ({date_range})</h2>
                <div>{chart_html}</div>
                <h3>Trailing Returns</h3>
                {period_html}
                <h3>Top 5 Contributors</h3>
                {best_html}
                <h3>Bottom 5 Contributors</h3>
                {worst_html}
                <h3>Recent Trades</h3>
                {trades_html}
            </section>
            """
        )

    html = f"""
    <html>
    <head>
        <meta charset='utf-8'>
        <title>Momentum Backtest Comparison</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            section {{ margin-bottom: 40px; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            table, th, td {{ border: 1px solid #ddd; }}
            th, td {{ padding: 8px; text-align: center; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <h1>Momentum Backtest Comparison</h1>
        <p>Runs compared: {', '.join(Path(p).name for p in run_paths)}</p>
        <h2>Summary Metrics</h2>
        {summary_html}
        {''.join(sections)}
    </body>
    </html>
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Saved report to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate HTML comparison report for multiple backtests")
    parser.add_argument("--runs", nargs="+", required=True, help="List of backtest result directories")
    parser.add_argument("--output", type=Path, default=Path("data/backtests/report.html"))
    args = parser.parse_args()

    build_report(args.runs, args.output)


if __name__ == "__main__":
    main()
