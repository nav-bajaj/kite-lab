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


def load_metrics(path: Path) -> dict:
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def load_holdings(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["entry_date"])
    if "contribution_pct" in df.columns:
        df = df.sort_values("contribution_pct", ascending=False)
    return df


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


def compute_drawdown_series(values: pd.Series, dates: pd.Series) -> pd.DataFrame:
    """Compute drawdown series with peaks and troughs"""
    running_max = values.cummax()
    drawdown = values / running_max - 1
    df = pd.DataFrame({
        'date': dates,
        'value': values,
        'peak': running_max,
        'drawdown': drawdown
    })
    return df


def identify_drawdown_periods(values: pd.Series, dates: pd.Series) -> list:
    """Identify distinct drawdown periods with start, trough, end, and recovery"""
    dd_series = compute_drawdown_series(values, dates)

    periods = []
    in_drawdown = False
    period_start = None
    period_start_value = None
    period_trough_idx = None
    period_trough_value = None

    for idx, row in dd_series.iterrows():
        if not in_drawdown and row['drawdown'] < 0:
            # Start of new drawdown
            in_drawdown = True
            period_start = idx
            period_start_value = row['peak']
            period_trough_idx = idx
            period_trough_value = row['drawdown']
        elif in_drawdown:
            # Track deepest point
            if row['drawdown'] < period_trough_value:
                period_trough_idx = idx
                period_trough_value = row['drawdown']

            # Check if recovered
            if row['drawdown'] >= 0:
                # End of drawdown - recovered
                periods.append({
                    'start_date': dd_series.loc[period_start, 'date'],
                    'trough_date': dd_series.loc[period_trough_idx, 'date'],
                    'end_date': row['date'],
                    'start_value': period_start_value,
                    'trough_value': dd_series.loc[period_trough_idx, 'value'],
                    'end_value': row['value'],
                    'drawdown_pct': period_trough_value,
                    'duration_days': (dd_series.loc[period_trough_idx, 'date'] - dd_series.loc[period_start, 'date']).days,
                    'recovery_days': (row['date'] - dd_series.loc[period_trough_idx, 'date']).days,
                    'total_days': (row['date'] - dd_series.loc[period_start, 'date']).days,
                    'recovered': True
                })
                in_drawdown = False

    # Handle ongoing drawdown
    if in_drawdown:
        periods.append({
            'start_date': dd_series.loc[period_start, 'date'],
            'trough_date': dd_series.loc[period_trough_idx, 'date'],
            'end_date': dd_series.iloc[-1]['date'],
            'start_value': period_start_value,
            'trough_value': dd_series.loc[period_trough_idx, 'value'],
            'end_value': dd_series.iloc[-1]['value'],
            'drawdown_pct': period_trough_value,
            'duration_days': (dd_series.loc[period_trough_idx, 'date'] - dd_series.loc[period_start, 'date']).days,
            'recovery_days': None,
            'total_days': (dd_series.iloc[-1]['date'] - dd_series.loc[period_start, 'date']).days,
            'recovered': False
        })

    return periods


def get_current_drawdown_stats(values: pd.Series, dates: pd.Series) -> dict:
    """Get current drawdown and time underwater stats"""
    if values.empty:
        return {
            'current_drawdown': 0,
            'days_underwater': 0,
            'is_underwater': False,
            'days_since_peak': 0
        }

    current_value = values.iloc[-1]
    peak_value = values.max()
    current_dd = current_value / peak_value - 1 if peak_value > 0 else 0

    # Find last peak
    peak_indices = values[values == values.cummax()].index
    if len(peak_indices) > 0:
        last_peak_idx = peak_indices[-1]
        last_peak_date = dates.iloc[last_peak_idx]
        current_date = dates.iloc[-1]
        days_since_peak = (current_date - last_peak_date).days
    else:
        days_since_peak = 0

    is_underwater = current_dd < -0.001  # More than 0.1% below peak

    return {
        'current_drawdown': current_dd,
        'days_underwater': days_since_peak if is_underwater else 0,
        'is_underwater': is_underwater,
        'days_since_peak': days_since_peak
    }


def compute_drawdown_stats(periods: list) -> dict:
    """Compute aggregate drawdown statistics"""
    if not periods:
        return {
            'avg_drawdown': 0,
            'avg_duration': 0,
            'avg_recovery': 0,
            'recovery_factor': 0,
            'num_drawdowns': 0
        }

    recovered_periods = [p for p in periods if p['recovered']]

    avg_dd = np.mean([p['drawdown_pct'] for p in periods])
    avg_duration = np.mean([p['duration_days'] for p in periods])
    avg_recovery = np.mean([p['recovery_days'] for p in recovered_periods]) if recovered_periods else None

    # Recovery factor: average recovery time / average drawdown duration
    recovery_factor = avg_recovery / avg_duration if (avg_recovery and avg_duration > 0) else None

    return {
        'avg_drawdown': avg_dd,
        'avg_duration': avg_duration,
        'avg_recovery': avg_recovery,
        'recovery_factor': recovery_factor,
        'num_drawdowns': len(periods)
    }


def generate_drawdown_chart(values: pd.Series, dates: pd.Series) -> str:
    """Generate drawdown chart showing drawdown % over time"""
    if plt is None:
        return ""

    dd_series = compute_drawdown_series(values, dates)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    # Top chart: equity curve with peaks
    ax1.plot(dd_series['date'], dd_series['value'], label='Portfolio Value', linewidth=1.5)
    ax1.plot(dd_series['date'], dd_series['peak'], label='Peak', linestyle='--', alpha=0.5, color='green')
    ax1.set_ylabel('Portfolio Value')
    ax1.set_title('Portfolio Value & Drawdowns')
    ax1.legend(loc='upper left')
    ax1.grid(alpha=0.3)

    # Bottom chart: drawdown %
    ax2.fill_between(dd_series['date'], dd_series['drawdown'] * 100, 0, alpha=0.3, color='red', label='Drawdown')
    ax2.plot(dd_series['date'], dd_series['drawdown'] * 100, color='darkred', linewidth=1)
    ax2.set_ylabel('Drawdown %')
    ax2.set_xlabel('Date')
    ax2.legend(loc='lower left')
    ax2.grid(alpha=0.3)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def trailing_return(values: pd.Series, dates: pd.Series, days: int) -> float:
    end_date = dates.iloc[-1]
    start_date = end_date - pd.Timedelta(days=days)
    mask = dates >= start_date
    subset = values[mask]
    if len(subset) < 2:
        return np.nan
    return subset.iloc[-1] / subset.iloc[0] - 1


def compute_rolling_sharpe(returns: pd.Series, window: int, risk_free_rate: float = 0.0) -> pd.Series:
    """Compute rolling Sharpe ratio over a window of days"""
    if len(returns) < window:
        return pd.Series(index=returns.index, dtype=float)

    excess_returns = returns - risk_free_rate / 252
    rolling_mean = excess_returns.rolling(window=window, min_periods=window).mean()
    rolling_std = excess_returns.rolling(window=window, min_periods=window).std()

    sharpe = (rolling_mean / rolling_std) * np.sqrt(252)
    return sharpe


def compute_rolling_volatility(returns: pd.Series, window: int) -> pd.Series:
    """Compute rolling annualized volatility over a window of days"""
    if len(returns) < window:
        return pd.Series(index=returns.index, dtype=float)

    rolling_std = returns.rolling(window=window, min_periods=window).std()
    rolling_vol = rolling_std * np.sqrt(252)
    return rolling_vol


def compute_rolling_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series, window: int) -> pd.Series:
    """Compute rolling beta vs benchmark over a window of days"""
    if len(portfolio_returns) < window or len(benchmark_returns) < window:
        return pd.Series(index=portfolio_returns.index, dtype=float)

    # Align the series
    aligned = pd.DataFrame({
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if len(aligned) < window:
        return pd.Series(index=portfolio_returns.index, dtype=float)

    # Calculate rolling covariance and variance
    rolling_cov = aligned['portfolio'].rolling(window=window, min_periods=window).cov(aligned['benchmark'])
    rolling_var = aligned['benchmark'].rolling(window=window, min_periods=window).var()

    beta = rolling_cov / rolling_var
    return beta


def compute_rolling_correlation(portfolio_returns: pd.Series, benchmark_returns: pd.Series, window: int) -> pd.Series:
    """Compute rolling correlation vs benchmark over a window of days"""
    if len(portfolio_returns) < window or len(benchmark_returns) < window:
        return pd.Series(index=portfolio_returns.index, dtype=float)

    # Align the series
    aligned = pd.DataFrame({
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if len(aligned) < window:
        return pd.Series(index=portfolio_returns.index, dtype=float)

    rolling_corr = aligned['portfolio'].rolling(window=window, min_periods=window).corr(aligned['benchmark'])
    return rolling_corr


def compute_rolling_max_drawdown(values: pd.Series, window: int) -> pd.Series:
    """Compute rolling maximum drawdown over a window of days"""
    if len(values) < window:
        return pd.Series(index=values.index, dtype=float)

    def max_dd_window(window_values):
        if len(window_values) == 0:
            return np.nan
        running_max = window_values.cummax()
        drawdown = window_values / running_max - 1
        return drawdown.min()

    rolling_dd = values.rolling(window=window, min_periods=window).apply(max_dd_window, raw=False)
    return rolling_dd


def generate_rolling_metrics_charts(equity: pd.DataFrame) -> dict:
    """Generate charts for various rolling metrics"""
    if plt is None:
        return {}

    portfolio_returns = equity["portfolio_return"].dropna()
    benchmark_returns = equity["benchmark_return"].dropna()
    portfolio_values = equity["portfolio_value"]
    dates = equity["date"]

    # Compute rolling metrics
    rolling_sharpe_126 = compute_rolling_sharpe(portfolio_returns, window=126)  # ~6 months
    rolling_vol_30 = compute_rolling_volatility(portfolio_returns, window=30)
    rolling_vol_60 = compute_rolling_volatility(portfolio_returns, window=60)
    rolling_vol_90 = compute_rolling_volatility(portfolio_returns, window=90)
    rolling_beta_126 = compute_rolling_beta(portfolio_returns, benchmark_returns, window=126)
    rolling_corr_126 = compute_rolling_correlation(portfolio_returns, benchmark_returns, window=126)
    rolling_dd_252 = compute_rolling_max_drawdown(portfolio_values, window=252)  # 1 year

    charts = {}

    # Chart 1: Rolling Sharpe Ratio
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, rolling_sharpe_126, label='6-Month Rolling Sharpe', linewidth=1.5)
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.axhline(y=1, color='green', linestyle='--', alpha=0.3, label='Sharpe = 1.0')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_xlabel('Date')
    ax.set_title('Rolling Sharpe Ratio (6-Month Window)')
    ax.legend()
    ax.grid(alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    charts['sharpe'] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Chart 2: Rolling Volatility (multiple windows)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, rolling_vol_30 * 100, label='30-Day', alpha=0.7, linewidth=1)
    ax.plot(dates, rolling_vol_60 * 100, label='60-Day', alpha=0.7, linewidth=1)
    ax.plot(dates, rolling_vol_90 * 100, label='90-Day', alpha=0.7, linewidth=1.5)
    ax.set_ylabel('Annualized Volatility (%)')
    ax.set_xlabel('Date')
    ax.set_title('Rolling Volatility (Multiple Windows)')
    ax.legend()
    ax.grid(alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    charts['volatility'] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Chart 3: Rolling Beta
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, rolling_beta_126, label='6-Month Rolling Beta', linewidth=1.5, color='purple')
    ax.axhline(y=1, color='gray', linestyle='--', alpha=0.5, label='Beta = 1.0')
    ax.set_ylabel('Beta')
    ax.set_xlabel('Date')
    ax.set_title('Rolling Beta vs Benchmark (6-Month Window)')
    ax.legend()
    ax.grid(alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    charts['beta'] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Chart 4: Rolling Correlation
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, rolling_corr_126, label='6-Month Rolling Correlation', linewidth=1.5, color='orange')
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('Correlation')
    ax.set_xlabel('Date')
    ax.set_title('Rolling Correlation vs Benchmark (6-Month Window)')
    ax.set_ylim(-1, 1)
    ax.legend()
    ax.grid(alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    charts['correlation'] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Chart 5: Rolling Max Drawdown
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, rolling_dd_252 * 100, label='1-Year Rolling Max DD', linewidth=1.5, color='red')
    ax.set_ylabel('Max Drawdown (%)')
    ax.set_xlabel('Date')
    ax.set_title('Rolling Maximum Drawdown (1-Year Window)')
    ax.legend()
    ax.grid(alpha=0.3)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    charts['rolling_dd'] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Compute summary statistics for rolling metrics
    stats = {
        'avg_sharpe_6m': rolling_sharpe_126.mean(),
        'std_sharpe_6m': rolling_sharpe_126.std(),
        'min_sharpe_6m': rolling_sharpe_126.min(),
        'max_sharpe_6m': rolling_sharpe_126.max(),
        'avg_vol_90d': rolling_vol_90.mean(),
        'min_vol_90d': rolling_vol_90.min(),
        'max_vol_90d': rolling_vol_90.max(),
        'avg_beta_6m': rolling_beta_126.mean(),
        'min_beta_6m': rolling_beta_126.min(),
        'max_beta_6m': rolling_beta_126.max(),
        'avg_corr_6m': rolling_corr_126.mean(),
        'min_corr_6m': rolling_corr_126.min(),
        'max_corr_6m': rolling_corr_126.max(),
        'avg_rolling_dd_1y': rolling_dd_252.mean(),
        'worst_rolling_dd_1y': rolling_dd_252.min(),
    }

    return {'charts': charts, 'stats': stats}


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


def format_number(value, decimals=1):
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.{decimals}f}"


def analyze_run(run_path: Path, label: str):
    equity = load_equity(run_path / "momentum_equity.csv")
    trades = load_trades(run_path / "momentum_trades.csv")
    metrics_file = load_metrics(run_path / "momentum_metrics.csv")
    holdings = load_holdings(run_path / "momentum_holdings.csv")

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

    # merge extended metrics if available
    metrics.update({k: v for k, v in metrics_file.items() if k not in metrics})

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

    # Drawdown analysis
    dd_periods = identify_drawdown_periods(equity["portfolio_value"], equity["date"])
    dd_periods_sorted = sorted(dd_periods, key=lambda x: x['drawdown_pct'])[:5]  # Top 5 worst
    current_dd = get_current_drawdown_stats(equity["portfolio_value"], equity["date"])
    dd_stats = compute_drawdown_stats(dd_periods)
    dd_chart = generate_drawdown_chart(equity["portfolio_value"], equity["date"])

    # Rolling metrics analysis
    rolling_metrics = generate_rolling_metrics_charts(equity)

    return {
        "metrics": metrics,
        "periods": periods,
        "chart": chart,
        "best": best,
        "worst": worst,
        "recent_trades": trades.tail(30),
        "date_range": (equity["date"].iloc[0], equity["date"].iloc[-1]),
        "metrics_file": metrics_file,
        "holdings": holdings,
        "drawdown_periods": dd_periods_sorted,
        "current_drawdown": current_dd,
        "drawdown_stats": dd_stats,
        "drawdown_chart": dd_chart,
        "rolling_metrics": rolling_metrics,
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
                "Trades/Week": format_number(m.get("trades_per_week")),
                "Trades/Month": format_number(m.get("trades_per_month")),
                "Trades/Year": format_number(m.get("trades_per_year")),
                "Avg Turnover %": format_percent(m.get("avg_turnover_pct")),
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    # Rank by CAGR
    def extract_cagr(val):
        try:
            return float(val.strip("%")) / 100
        except Exception:
            return -1e9
    summary_df["CAGR_numeric"] = summary_df["CAGR"].apply(extract_cagr)
    summary_df.sort_values("CAGR_numeric", ascending=False, inplace=True)
    summary_df.insert(0, "Rank", range(1, len(summary_df) + 1))
    summary_df.drop(columns=["CAGR_numeric"], inplace=True)
    summary_html = summary_df.to_html(index=False, escape=False)

    ranking_html = ""  # Ranking already reflected in summary by CAGR

    sections = []
    for entry in analyses:
        m = entry["metrics"]
        label = m["label"]
        date_range = f"{entry['date_range'][0].date()} → {entry['date_range'][1].date()}"
        config_html = f"<p><strong>Settings:</strong> lookbacks={m.get('lookbacks','n/a')}, top_n={m.get('top_n','n/a')}, scenario={m.get('scenario','n/a')}</p>"
        metrics_detail = entry.get("metrics_file", {})
        if metrics_detail:
            metrics_table = pd.DataFrame(
                [
                    {"Metric": "Trades (total)", "Value": format_number(metrics_detail.get("trades_total"), 0)},
                    {"Metric": "Trades per week", "Value": format_number(metrics_detail.get("trades_per_week"))},
                    {"Metric": "Trades per month", "Value": format_number(metrics_detail.get("trades_per_month"))},
                    {"Metric": "Trades per year", "Value": format_number(metrics_detail.get("trades_per_year"))},
                    {"Metric": "Avg turnover %", "Value": format_percent(metrics_detail.get("avg_turnover_pct"))},
                    {"Metric": "Max turnover %", "Value": format_percent(metrics_detail.get("max_turnover_pct"))},
                    {"Metric": "Cost drag %", "Value": format_percent(metrics_detail.get("cost_drag_pct"))},
                    {"Metric": "Max DD duration (days)", "Value": format_number(metrics_detail.get("max_drawdown_duration_days"), 0)},
                    {"Metric": "Avg holding days", "Value": format_number(metrics_detail.get("avg_holding_days"), 1)},
                    {"Metric": "Median holding days", "Value": format_number(metrics_detail.get("median_holding_days"), 1)},
                    {"Metric": "Hit-rate overall", "Value": format_percent(metrics_detail.get("hit_rate_overall"))},
                    {"Metric": "Hit-rate q1", "Value": format_percent(metrics_detail.get("hit_rate_q1"))},
                    {"Metric": "Hit-rate q2", "Value": format_percent(metrics_detail.get("hit_rate_q2"))},
                    {"Metric": "Hit-rate q3", "Value": format_percent(metrics_detail.get("hit_rate_q3"))},
                    {"Metric": "Hit-rate q4", "Value": format_percent(metrics_detail.get("hit_rate_q4"))},
                    {"Metric": "Hit-rate q5", "Value": format_percent(metrics_detail.get("hit_rate_q5"))},
                ]
            ).to_html(index=False, escape=False)
        else:
            metrics_table = "<p>No metrics file found.</p>"

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
        holdings_df = entry.get("holdings", pd.DataFrame())
        holdings_html = "<p>No current holdings.</p>"
        if not holdings_df.empty:
            dfh = holdings_df.copy()
            for col in dfh.columns:
                if "date" in col and pd.api.types.is_datetime64_any_dtype(dfh[col]):
                    dfh[col] = dfh[col].dt.date.astype(str)
            percent_cols = {"pnl_pct", "contribution_pct"}
            money_cols = {"avg_cost", "last_price", "notional"}
            int_cols = {"shares", "entry_rank", "holding_days"}

            def _fmt_val(col, val):
                if pd.isna(val):
                    return ""
                if col in percent_cols:
                    return f"{val:.2%}"
                if col in money_cols:
                    return f"{val:.2f}"
                if col in int_cols:
                    return f"{int(round(val))}"
                return val

            fmt = {col: (lambda v, c=col: _fmt_val(c, v)) for col in dfh.columns}
            holdings_html = dfh.to_html(index=False, justify="center", border=1, classes="holdings", formatters=fmt)

        # Build drawdown section
        dd_chart_html = (
            f'<img src="data:image/png;base64,{entry["drawdown_chart"]}" alt="Drawdown chart" />'
            if entry.get("drawdown_chart")
            else "<p>Drawdown chart unavailable (matplotlib missing).</p>"
        )

        # Current drawdown status
        current_dd = entry.get("current_drawdown", {})
        if current_dd.get("is_underwater", False):
            current_dd_html = f"""
            <div style="background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0;">
                <strong>⚠ Portfolio Currently Underwater</strong><br/>
                Current Drawdown: <strong>{format_percent(current_dd.get('current_drawdown', 0))}</strong><br/>
                Days Underwater: <strong>{current_dd.get('days_underwater', 0)}</strong> days
            </div>
            """
        else:
            current_dd_html = f"""
            <div style="background-color: #d4edda; padding: 10px; border-left: 4px solid #28a745; margin: 10px 0;">
                <strong>✓ Portfolio at or near Peak</strong><br/>
                Days Since Peak: <strong>{current_dd.get('days_since_peak', 0)}</strong> days
            </div>
            """

        # Drawdown statistics summary
        dd_stats = entry.get("drawdown_stats", {})
        dd_summary_df = pd.DataFrame([
            {"Metric": "Number of Drawdowns", "Value": format_number(dd_stats.get("num_drawdowns", 0), 0)},
            {"Metric": "Average Drawdown", "Value": format_percent(dd_stats.get("avg_drawdown", 0))},
            {"Metric": "Average Duration (days)", "Value": format_number(dd_stats.get("avg_duration", 0), 0)},
            {"Metric": "Average Recovery (days)", "Value": format_number(dd_stats.get("avg_recovery", 0), 0) if dd_stats.get("avg_recovery") else "-"},
            {"Metric": "Recovery Factor", "Value": format_number(dd_stats.get("recovery_factor", 0), 2) if dd_stats.get("recovery_factor") else "-"},
        ])
        dd_summary_html = dd_summary_df.to_html(index=False, escape=False)

        # Top 5 worst drawdown periods
        dd_periods = entry.get("drawdown_periods", [])
        if dd_periods:
            dd_periods_data = []
            for i, period in enumerate(dd_periods, 1):
                dd_periods_data.append({
                    "Rank": i,
                    "Drawdown": format_percent(period['drawdown_pct']),
                    "Start": period['start_date'].date() if hasattr(period['start_date'], 'date') else period['start_date'],
                    "Trough": period['trough_date'].date() if hasattr(period['trough_date'], 'date') else period['trough_date'],
                    "End": period['end_date'].date() if hasattr(period['end_date'], 'date') else period['end_date'],
                    "Duration (days)": period['duration_days'],
                    "Recovery (days)": period['recovery_days'] if period['recovered'] else "Ongoing",
                    "Total (days)": period['total_days'],
                    "Status": "✓ Recovered" if period['recovered'] else "⚠ Ongoing"
                })
            dd_periods_df = pd.DataFrame(dd_periods_data)
            dd_periods_html = dd_periods_df.to_html(index=False, escape=False)
        else:
            dd_periods_html = "<p>No significant drawdown periods identified.</p>"

        # Build rolling metrics section
        rolling_metrics = entry.get("rolling_metrics", {})
        rolling_charts = rolling_metrics.get("charts", {})
        rolling_stats = rolling_metrics.get("stats", {})

        if rolling_charts:
            rolling_sharpe_chart = f'<img src="data:image/png;base64,{rolling_charts["sharpe"]}" alt="Rolling Sharpe" />' if rolling_charts.get("sharpe") else ""
            rolling_vol_chart = f'<img src="data:image/png;base64,{rolling_charts["volatility"]}" alt="Rolling Volatility" />' if rolling_charts.get("volatility") else ""
            rolling_beta_chart = f'<img src="data:image/png;base64,{rolling_charts["beta"]}" alt="Rolling Beta" />' if rolling_charts.get("beta") else ""
            rolling_corr_chart = f'<img src="data:image/png;base64,{rolling_charts["correlation"]}" alt="Rolling Correlation" />' if rolling_charts.get("correlation") else ""
            rolling_dd_chart = f'<img src="data:image/png;base64,{rolling_charts["rolling_dd"]}" alt="Rolling Max DD" />' if rolling_charts.get("rolling_dd") else ""

            # Rolling metrics summary table
            rolling_stats_df = pd.DataFrame([
                {"Metric": "Avg Rolling Sharpe (6M)", "Value": format_number(rolling_stats.get("avg_sharpe_6m", 0), 2)},
                {"Metric": "Min Rolling Sharpe (6M)", "Value": format_number(rolling_stats.get("min_sharpe_6m", 0), 2)},
                {"Metric": "Max Rolling Sharpe (6M)", "Value": format_number(rolling_stats.get("max_sharpe_6m", 0), 2)},
                {"Metric": "Avg Rolling Vol (90D)", "Value": format_percent(rolling_stats.get("avg_vol_90d", 0))},
                {"Metric": "Min Rolling Vol (90D)", "Value": format_percent(rolling_stats.get("min_vol_90d", 0))},
                {"Metric": "Max Rolling Vol (90D)", "Value": format_percent(rolling_stats.get("max_vol_90d", 0))},
                {"Metric": "Avg Rolling Beta (6M)", "Value": format_number(rolling_stats.get("avg_beta_6m", 0), 2)},
                {"Metric": "Min Rolling Beta (6M)", "Value": format_number(rolling_stats.get("min_beta_6m", 0), 2)},
                {"Metric": "Max Rolling Beta (6M)", "Value": format_number(rolling_stats.get("max_beta_6m", 0), 2)},
                {"Metric": "Avg Rolling Correlation (6M)", "Value": format_number(rolling_stats.get("avg_corr_6m", 0), 2)},
                {"Metric": "Avg Rolling Max DD (1Y)", "Value": format_percent(rolling_stats.get("avg_rolling_dd_1y", 0))},
                {"Metric": "Worst Rolling Max DD (1Y)", "Value": format_percent(rolling_stats.get("worst_rolling_dd_1y", 0))},
            ])
            rolling_stats_html = rolling_stats_df.to_html(index=False, escape=False)

            rolling_metrics_section = f"""
                <h3>Rolling Metrics Analysis</h3>
                <p>Analysis of performance stability and consistency over time using rolling windows.</p>
                <h4>Rolling Sharpe Ratio</h4>
                {rolling_sharpe_chart}
                <h4>Rolling Volatility</h4>
                {rolling_vol_chart}
                <h4>Rolling Beta vs Benchmark</h4>
                {rolling_beta_chart}
                <h4>Rolling Correlation vs Benchmark</h4>
                {rolling_corr_chart}
                <h4>Rolling Maximum Drawdown</h4>
                {rolling_dd_chart}
                <h4>Rolling Metrics Summary</h4>
                {rolling_stats_html}
            """
        else:
            rolling_metrics_section = "<h3>Rolling Metrics Analysis</h3><p>Rolling metrics unavailable (matplotlib missing).</p>"

        sections.append(
            f"""
            <section>
                <h2>{label} ({date_range})</h2>
                {config_html}
                <div>{chart_html}</div>

                <h3>Drawdown Analysis</h3>
                {current_dd_html}
                {dd_chart_html}
                <h4>Drawdown Summary Statistics</h4>
                {dd_summary_html}
                <h4>Top 5 Worst Drawdown Periods</h4>
                {dd_periods_html}

                {rolling_metrics_section}

                <h3>Trailing Returns</h3>
                {period_html}
                <h3>Portfolio Stats</h3>
                {metrics_table}
                <h3>Current Holdings</h3>
                {holdings_html}
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
