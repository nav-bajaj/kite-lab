import argparse
import base64
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


@dataclass
class BenchmarkSeries:
    name: str
    df: pd.DataFrame


def load_signals(signals_path: Path, top_n: int) -> pd.DataFrame:
    df = pd.read_csv(signals_path, parse_dates=["date"])
    if df.empty:
        raise SystemExit(f"Signals file is empty: {signals_path}")
    df = df[df["rank"] <= top_n].copy()
    df.sort_values(["date", "rank"], inplace=True)
    return df


def load_price_panel(prices_dir: Path, symbols) -> pd.DataFrame:
    series = []
    for symbol in sorted(set(symbols)):
        path = prices_dir / f"{symbol}_day.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=["date", "close"], parse_dates=["date"])
        if df.empty:
            continue
        df = df.dropna(subset=["close"])
        df["symbol"] = symbol
        series.append(df)
    if not series:
        raise SystemExit(f"No price data found under {prices_dir}")
    combined = pd.concat(series, ignore_index=True)
    panel = combined.pivot(index="date", columns="symbol", values="close").sort_index()
    return panel


def load_benchmarks(benchmarks_dir: Path) -> list:
    benches = []
    if not benchmarks_dir.exists():
        return benches
    for path in sorted(benchmarks_dir.glob("*.csv")):
        df = pd.read_csv(path, parse_dates=["date"])
        if "close" not in df.columns or df.empty:
            continue
        df = df.sort_values("date").set_index("date")
        name = path.stem
        benches.append(BenchmarkSeries(name=name, df=df[["close"]].copy()))
    return benches


def compute_portfolio_equity(signals: pd.DataFrame, prices: pd.DataFrame, top_n: int) -> pd.DataFrame:
    rebalance_dates = sorted(set(signals["date"]))
    rebalance_dates = [d for d in rebalance_dates if d in prices.index]
    if not rebalance_dates:
        raise SystemExit("No rebalance dates overlap with price data")

    signals_by_date = {d: g for d, g in signals.groupby("date")}
    price_slice = prices.loc[rebalance_dates[0] :].copy()

    portfolio_value = 1.0
    values = []
    weights = None
    prev_row = None

    for date, row in price_slice.iterrows():
        if weights is None or date in signals_by_date:
            holdings = signals_by_date.get(date)
            if holdings is None or holdings.empty:
                weights = None
            else:
                symbols = holdings["symbol"].tolist()
                available = [sym for sym in symbols if sym in price_slice.columns]
                if not available:
                    weights = None
                else:
                    weights = pd.Series(1 / len(available), index=available)

        if prev_row is None:
            values.append((date, portfolio_value))
            prev_row = row
            continue

        if weights is None:
            values.append((date, portfolio_value))
            prev_row = row
            continue

        valid = weights.index[(row[weights.index].notna()) & (prev_row[weights.index].notna())]
        if len(valid) == 0:
            values.append((date, portfolio_value))
            prev_row = row
            continue

        weights_today = weights.loc[valid]
        weights_today = weights_today / weights_today.sum()
        daily_returns = row[valid] / prev_row[valid] - 1
        port_ret = float((daily_returns * weights_today).sum())
        portfolio_value *= (1 + port_ret)
        values.append((date, portfolio_value))
        prev_row = row

    equity = pd.DataFrame(values, columns=["date", "portfolio_value"]).set_index("date")
    equity["portfolio_return"] = equity["portfolio_value"].pct_change().fillna(0)
    return equity


def trailing_return(values: pd.Series, days: int) -> float:
    if values.empty:
        return np.nan
    end_idx = len(values) - 1
    start_idx = max(0, end_idx - days)
    if end_idx == start_idx:
        return np.nan
    return values.iloc[end_idx] / values.iloc[start_idx] - 1


def annualized_return(values: pd.Series, dates: pd.Series) -> float:
    if len(values) < 2:
        return np.nan
    total_return = values.iloc[-1] / values.iloc[0] - 1
    days = (dates.iloc[-1] - dates.iloc[0]).days
    if days <= 0:
        return np.nan
    return (1 + total_return) ** (365.0 / days) - 1


def annualized_vol(returns: pd.Series, scale: float = 252.0) -> float:
    return returns.std() * np.sqrt(scale)


def max_drawdown(values: pd.Series) -> float:
    if values.empty:
        return np.nan
    running_max = values.cummax()
    drawdown = values / running_max - 1
    return drawdown.min()


def build_holdings_history(signals: pd.DataFrame, top_n: int) -> list:
    history = []
    for date, group in signals.groupby("date"):
        top = group[group["rank"] <= top_n].copy()
        top.sort_values("rank", inplace=True)
        history.append((date, top))
    history.sort(key=lambda x: x[0])
    return history


def compute_entry_exit(history: list) -> dict:
    entry_dates = {}
    exit_dates = {}
    current = set()

    for date, holdings in history:
        symbols = set(holdings["symbol"].tolist())
        entering = symbols - current
        exiting = current - symbols
        for sym in entering:
            entry_dates[sym] = date
        for sym in exiting:
            exit_dates[sym] = date
        current = symbols

    return {
        "entry_dates": entry_dates,
        "exit_dates": exit_dates,
        "current": current,
        "last_date": history[-1][0] if history else None,
    }


def compute_rank_history(history: list, current_symbols, lookback: int = 8) -> pd.DataFrame:
    recent = history[-lookback:]
    data = {"symbol": sorted(current_symbols)}
    for date, holdings in recent:
        rank_map = dict(zip(holdings["symbol"], holdings["rank"]))
        label = date.date().isoformat()
        data[label] = [rank_map.get(sym, "") for sym in data["symbol"]]
    return pd.DataFrame(data)


def compute_symbol_returns(prices: pd.DataFrame, symbols, days: int) -> pd.Series:
    subset = prices[list(symbols)].dropna(how="all")
    if subset.empty:
        return pd.Series(dtype=float)
    if len(subset) <= days:
        return pd.Series(dtype=float)
    end = subset.iloc[-1]
    start = subset.iloc[-(days + 1)]
    returns = end / start - 1
    return returns.dropna()


def compute_returns_since_entry(prices: pd.DataFrame, entry_dates: dict) -> dict:
    returns = {}
    for symbol, entry_date in entry_dates.items():
        if symbol not in prices.columns:
            continue
        series = prices[symbol].dropna()
        if series.empty:
            continue
        entry_slice = series.loc[entry_date:]
        if entry_slice.empty:
            continue
        entry_price = entry_slice.iloc[0]
        latest_price = series.iloc[-1]
        returns[symbol] = latest_price / entry_price - 1
    return returns


def generate_chart(series_map: dict, title: str, ylabel: str) -> str:
    if plt is None:
        return ""
    fig, ax = plt.subplots(figsize=(8, 3))
    for label, series in series_map.items():
        ax.plot(series.index, series.values, label=label)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def format_percent(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.2%}"


def build_report(signals_path: Path, prices_dir: Path, benchmarks_dir: Path, output_path: Path, top_n: int):
    signals = load_signals(signals_path, top_n)
    symbols = signals["symbol"].unique().tolist()
    prices = load_price_panel(prices_dir, symbols)
    history = build_holdings_history(signals, top_n)
    status = compute_entry_exit(history)

    latest_date = status["last_date"]
    if latest_date is None:
        raise SystemExit("No holdings history available")
    latest_holdings = history[-1][1].copy()
    current_symbols = set(latest_holdings["symbol"].tolist())

    equity = compute_portfolio_equity(signals, prices, top_n)
    equity.index = pd.to_datetime(equity.index)

    benchmarks = load_benchmarks(benchmarks_dir)
    bench_series = {}
    bench_summary = []

    for bench in benchmarks:
        aligned = bench.df.reindex(equity.index).dropna()
        if aligned.empty:
            continue
        norm = aligned["close"] / aligned["close"].iloc[0]
        bench_series[bench.name] = norm
        bench_summary.append(
            {
                "Benchmark": bench.name,
                "Total Return": format_percent(norm.iloc[-1] - 1),
                "CAGR": format_percent(annualized_return(norm, norm.index.to_series())),
                "Volatility": format_percent(annualized_vol(norm.pct_change().dropna())),
            }
        )

    portfolio_norm = equity["portfolio_value"] / equity["portfolio_value"].iloc[0]
    chart_equity = generate_chart({"Portfolio": portfolio_norm, **bench_series}, "Equity vs Benchmarks", "Indexed")

    daily_returns = equity["portfolio_return"].dropna()
    last_30 = daily_returns.tail(30)
    if not last_30.empty:
        pnl_series = (1 + last_30).cumprod() - 1
        chart_pnl = generate_chart({"Portfolio": pnl_series}, "30-Day Cumulative PnL", "Cumulative Return")
    else:
        chart_pnl = ""

    daily_vol = annualized_vol(last_30)
    weekly_returns = equity["portfolio_value"].resample("W-FRI").last().pct_change().dropna()
    weekly_vol = annualized_vol(weekly_returns.tail(12), scale=52.0)

    swings = pd.DataFrame(
        {
            "date": last_30.index.date.astype(str),
            "return": last_30.values,
        }
    )
    swings_sorted = swings.sort_values("return", ascending=False)
    top_swings = swings_sorted.head(5)
    bottom_swings = swings_sorted.tail(5).iloc[::-1]

    returns_30d = compute_symbol_returns(prices, current_symbols, 30)
    returns_90d = compute_symbol_returns(prices, current_symbols, 90)
    returns_since_entry = compute_returns_since_entry(prices, status["entry_dates"])

    winners_30 = returns_30d.sort_values(ascending=False).head(5).reset_index()
    winners_30.columns = ["symbol", "return_30d"]
    losers_30 = returns_30d.sort_values(ascending=True).head(5).reset_index()
    losers_30.columns = ["symbol", "return_30d"]

    best_quarter = returns_90d.sort_values(ascending=False).head(5).reset_index()
    best_quarter.columns = ["symbol", "return_90d"]

    entry_dates = status["entry_dates"]
    exit_dates = status["exit_dates"]

    latest_holdings = latest_holdings.merge(
        prices.iloc[-1].rename("last_price").reset_index().rename(columns={"index": "symbol"}),
        on="symbol",
        how="left",
    )
    latest_holdings["entry_date"] = latest_holdings["symbol"].map(entry_dates)
    latest_holdings["holding_days"] = (latest_date - latest_holdings["entry_date"]).dt.days
    latest_holdings["return_30d"] = latest_holdings["symbol"].map(returns_30d)
    latest_holdings["return_90d"] = latest_holdings["symbol"].map(returns_90d)
    latest_holdings["return_since_entry"] = latest_holdings["symbol"].map(returns_since_entry)

    rank_history = compute_rank_history(history, current_symbols)

    recent_changes = []
    if len(history) >= 2:
        prev_symbols = set(history[-2][1]["symbol"].tolist())
        added = sorted(current_symbols - prev_symbols)
        removed = sorted(prev_symbols - current_symbols)
        for sym in added:
            recent_changes.append(
                {
                    "symbol": sym,
                    "action": "added",
                    "entry_date": entry_dates.get(sym),
                    "exit_date": "",
                }
            )
        for sym in removed:
            recent_changes.append(
                {
                    "symbol": sym,
                    "action": "removed",
                    "entry_date": entry_dates.get(sym),
                    "exit_date": exit_dates.get(sym),
                }
            )

    recent_changes_df = pd.DataFrame(recent_changes)

    primary_benchmark = bench_summary[0]["Benchmark"] if bench_summary else None
    primary_series = bench_series.get(primary_benchmark) if primary_benchmark else None
    benchmark_norm = primary_series if primary_series is not None else None

    summary_metrics = pd.DataFrame(
        [
            {
                "Metric": "Total Return",
                "Portfolio": format_percent(portfolio_norm.iloc[-1] - 1),
                "Benchmark": format_percent(benchmark_norm.iloc[-1] - 1) if benchmark_norm is not None else "-",
            },
            {
                "Metric": "CAGR",
                "Portfolio": format_percent(annualized_return(portfolio_norm, portfolio_norm.index.to_series())),
                "Benchmark": format_percent(
                    annualized_return(benchmark_norm, benchmark_norm.index.to_series())
                )
                if benchmark_norm is not None
                else "-",
            },
            {
                "Metric": "Volatility (annualized)",
                "Portfolio": format_percent(annualized_vol(daily_returns)),
                "Benchmark": format_percent(annualized_vol(benchmark_norm.pct_change().dropna()))
                if benchmark_norm is not None
                else "-",
            },
            {
                "Metric": "Max Drawdown",
                "Portfolio": format_percent(max_drawdown(equity["portfolio_value"])),
                "Benchmark": format_percent(max_drawdown(benchmark_norm)) if benchmark_norm is not None else "-",
            },
            {
                "Metric": "30D Return",
                "Portfolio": format_percent(trailing_return(portfolio_norm, 30)),
                "Benchmark": format_percent(trailing_return(benchmark_norm, 30)) if benchmark_norm is not None else "-",
            },
            {
                "Metric": "90D Return",
                "Portfolio": format_percent(trailing_return(portfolio_norm, 90)),
                "Benchmark": format_percent(trailing_return(benchmark_norm, 90)) if benchmark_norm is not None else "-",
            },
        ]
    )

    if bench_summary:
        bench_summary_df = pd.DataFrame(bench_summary)
    else:
        bench_summary_df = pd.DataFrame(
            [{"Benchmark": "(none found)", "Total Return": "-", "CAGR": "-", "Volatility": "-"}]
        )

    def format_table(df, percent_cols=None):
        df = df.copy()
        percent_cols = percent_cols or []
        for col in percent_cols:
            if col in df.columns:
                df[col] = df[col].apply(format_percent)
        if "entry_date" in df.columns:
            df["entry_date"] = df["entry_date"].astype(str)
        if "exit_date" in df.columns:
            df["exit_date"] = df["exit_date"].astype(str)
        if "holding_days" in df.columns:
            df["holding_days"] = df["holding_days"].apply(lambda v: "" if pd.isna(v) else int(v))
        return df.to_html(index=False, escape=False)

    holdings_table = format_table(
        latest_holdings[
            [
                "rank",
                "symbol",
                "score",
                "entry_date",
                "holding_days",
                "return_30d",
                "return_90d",
                "return_since_entry",
            ]
        ],
        percent_cols=["return_30d", "return_90d", "return_since_entry"],
    )

    periods = []
    for label, days in [("1M", 30), ("3M", 90), ("6M", 180), ("1Y", 365)]:
        periods.append(
            {
                "Period": label,
                "Portfolio": format_percent(trailing_return(portfolio_norm, days)),
                "Benchmark": format_percent(trailing_return(benchmark_norm, days))
                if benchmark_norm is not None
                else "-",
            }
        )
    periods_df = pd.DataFrame(periods)

    stats_rows = [
        {"Metric": "Daily Vol (annualized, 30d)", "Value": format_percent(daily_vol)},
        {"Metric": "Weekly Vol (annualized, 12w)", "Value": format_percent(weekly_vol)},
        {"Metric": "Holdings (current)", "Value": len(current_symbols)},
    ]
    stats_df = pd.DataFrame(stats_rows)

    html = f"""
    <html>
    <head>
        <meta charset='utf-8'>
        <title>Final Momentum Portfolio Report</title>
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
        <h1>Final Momentum Portfolio Report</h1>
        <p>As of {latest_date.date().isoformat()}</p>
        <h2>Summary Metrics</h2>
        {summary_metrics.to_html(index=False, escape=False)}
        <h2>Benchmarks</h2>
        {bench_summary_df.to_html(index=False, escape=False)}

        <section>
            <h2>Final Portfolio ({equity.index.min().date()} → {equity.index.max().date()})</h2>
            <div>{f'<img src="data:image/png;base64,{chart_equity}" />' if chart_equity else '<p>Chart unavailable (matplotlib missing).</p>'}</div>
            <h3>Trailing Returns</h3>
            {periods_df.to_html(index=False, escape=False)}
            <h3>Portfolio Stats</h3>
            {stats_df.to_html(index=False, escape=False)}
            <h3>Current Holdings</h3>
            {holdings_table}
            <h3>Rank History (last 8 rebalances)</h3>
            {rank_history.to_html(index=False, escape=False)}
        </section>

        <section>
            <h2>Performance Details</h2>
            <h3>30-Day PnL</h3>
            {f'<img src="data:image/png;base64,{chart_pnl}" />' if chart_pnl else '<p>Chart unavailable (matplotlib missing).</p>'}
            <h3>Daily Returns (last 30 sessions)</h3>
            {swings.to_html(index=False, escape=False)}
            <h3>Largest PnL Swings (last 30 sessions)</h3>
            <h4>Top 5 Up Days</h4>
            {format_table(top_swings, percent_cols=["return"])}
            <h4>Top 5 Down Days</h4>
            {format_table(bottom_swings, percent_cols=["return"])}
        </section>

        <section>
            <h2>Winners & Losers</h2>
            <h3>Biggest Winners (30d)</h3>
            {format_table(winners_30, percent_cols=["return_30d"])}
            <h3>Biggest Losers (30d)</h3>
            {format_table(losers_30, percent_cols=["return_30d"])}
            <h3>Best Performers (Quarter)</h3>
            {format_table(best_quarter, percent_cols=["return_90d"])}
        </section>

        <section>
            <h2>Recent Changes</h2>
            {format_table(recent_changes_df) if not recent_changes_df.empty else '<p>No changes from last rebalance.</p>'}
        </section>

        <section>
            <h2>Entry / Exit Dates</h2>
            <p>Entry dates are derived from the signals history. Exit dates are set on the first rebalance date where a symbol drops out.</p>
        </section>
    </body>
    </html>
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Saved report to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate the final momentum portfolio report")
    parser.add_argument("--signals", type=Path, default=Path("data/final_portfolio/final_top24_signals.csv"))
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--benchmarks-dir", type=Path, default=Path("data/benchmarks"))
    parser.add_argument("--output", type=Path, default=Path("experiments/final_portfolio/report_rich.html"))
    parser.add_argument("--top-n", type=int, default=24)
    args = parser.parse_args()

    build_report(args.signals, args.prices_dir, args.benchmarks_dir, args.output, args.top_n)


if __name__ == "__main__":
    main()
