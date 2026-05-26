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


# ============================================================================
# Comprehensive Risk Metrics
# ============================================================================


def sortino_ratio(returns: pd.Series, cagr: float, risk_free_rate: float = 0.05) -> float:
    """
    Calculate Sortino Ratio (excess return / downside deviation).

    Unlike Sharpe, only penalizes downside volatility.
    """
    downside_returns = returns[returns < 0]
    if len(downside_returns) == 0:
        return np.nan
    downside_vol = downside_returns.std() * np.sqrt(252)
    if downside_vol == 0:
        return np.nan
    return (cagr - risk_free_rate) / downside_vol


def calmar_ratio(cagr: float, max_dd: float) -> float:
    """
    Calculate Calmar Ratio (CAGR / Max Drawdown).

    Measures return per unit of drawdown risk.
    """
    if max_dd == 0 or max_dd >= 0:
        return np.nan
    return cagr / abs(max_dd)


def ulcer_index(values: pd.Series) -> float:
    """
    Calculate Ulcer Index (measure of downside risk).

    Measures depth and duration of drawdowns.
    Formula: sqrt(mean(drawdown^2))
    """
    running_max = values.cummax()
    drawdown = values / running_max - 1
    ulcer = np.sqrt(np.mean(drawdown ** 2))
    return ulcer


def information_ratio(portfolio_returns: pd.Series, benchmark_returns: pd.Series,
                      portfolio_cagr: float, benchmark_cagr: float) -> float:
    """
    Calculate Information Ratio (excess return / tracking error).

    Measures consistency of outperformance vs benchmark.
    """
    tracking_error = (portfolio_returns - benchmark_returns).std() * np.sqrt(252)
    if tracking_error == 0:
        return np.nan
    return (portfolio_cagr - benchmark_cagr) / tracking_error


def value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Value at Risk (VaR) at given confidence level.

    Returns the percentile loss (positive value indicates loss).
    """
    return -np.percentile(returns, (1 - confidence) * 100)


def conditional_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Conditional VaR (CVaR / Expected Shortfall).

    Average loss beyond VaR threshold.
    """
    var_threshold = value_at_risk(returns, confidence)
    tail_losses = returns[returns <= -var_threshold]
    if len(tail_losses) == 0:
        return 0
    return -tail_losses.mean()


def omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    """
    Calculate Omega Ratio (probability-weighted gains / losses).

    Ratio of area above threshold to area below threshold.
    """
    gains = returns[returns > threshold]
    losses = returns[returns <= threshold]

    if len(losses) == 0:
        return np.inf

    total_gains = gains.sum() - threshold * len(gains)
    total_losses = threshold * len(losses) - losses.sum()

    if total_losses == 0:
        return np.inf

    return total_gains / total_losses


def tail_ratio(returns: pd.Series) -> float:
    """
    Calculate Tail Ratio (95th percentile gain / 95th percentile loss).

    Measures asymmetry of extreme outcomes.
    """
    p95_gain = np.percentile(returns, 95)
    p5_loss = np.percentile(returns, 5)

    if p5_loss >= 0:
        return np.nan

    return abs(p95_gain / p5_loss)


def compute_comprehensive_risk_metrics(equity_df: pd.DataFrame,
                                      portfolio_returns: pd.Series,
                                      benchmark_returns: pd.Series,
                                      cagr: float,
                                      benchmark_cagr: float,
                                      max_dd: float,
                                      risk_free_rate: float = 0.05) -> dict:
    """
    Compute all comprehensive risk metrics.

    Returns dict with all advanced risk metrics.
    """
    metrics = {}

    # Sortino Ratio
    metrics['sortino_ratio'] = sortino_ratio(portfolio_returns, cagr, risk_free_rate)

    # Calmar Ratio
    metrics['calmar_ratio'] = calmar_ratio(cagr, max_dd)

    # Ulcer Index
    metrics['ulcer_index'] = ulcer_index(equity_df['portfolio_value'])

    # Information Ratio
    metrics['information_ratio'] = information_ratio(
        portfolio_returns, benchmark_returns, cagr, benchmark_cagr
    )

    # Value at Risk (95% and 99%)
    metrics['var_95'] = value_at_risk(portfolio_returns, 0.95)
    metrics['var_99'] = value_at_risk(portfolio_returns, 0.99)

    # Conditional VaR
    metrics['cvar_95'] = conditional_var(portfolio_returns, 0.95)
    metrics['cvar_99'] = conditional_var(portfolio_returns, 0.99)

    # Omega Ratio
    metrics['omega_ratio'] = omega_ratio(portfolio_returns, threshold=0.0)

    # Tail Ratio
    metrics['tail_ratio'] = tail_ratio(portfolio_returns)

    return metrics


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


def compute_monthly_returns(values: pd.Series, dates: pd.Series) -> pd.DataFrame:
    """Compute monthly returns from daily portfolio values"""
    df = pd.DataFrame({'date': dates, 'value': values})
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Resample to month-end and compute returns
    monthly = df['value'].resample('ME').last()
    monthly_returns = monthly.pct_change()

    # Create a dataframe with year, month, return
    result = pd.DataFrame({
        'year': monthly_returns.index.year,
        'month': monthly_returns.index.month,
        'return': monthly_returns.values
    })

    return result.dropna()


def compute_quarterly_returns(values: pd.Series, dates: pd.Series) -> pd.DataFrame:
    """Compute quarterly returns from daily portfolio values"""
    df = pd.DataFrame({'date': dates, 'value': values})
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Resample to quarter-end and compute returns
    quarterly = df['value'].resample('QE').last()
    quarterly_returns = quarterly.pct_change()

    # Create a dataframe with year, quarter, return
    result = pd.DataFrame({
        'year': quarterly_returns.index.year,
        'quarter': quarterly_returns.index.quarter,
        'return': quarterly_returns.values
    })

    return result.dropna()


def generate_monthly_heatmap(monthly_returns: pd.DataFrame) -> str:
    """Generate monthly returns heatmap"""
    if plt is None:
        return ""

    # Pivot to get years as rows, months as columns
    heatmap_data = monthly_returns.pivot(index='year', columns='month', values='return')

    # Ensure all months are present (1-12)
    for month in range(1, 13):
        if month not in heatmap_data.columns:
            heatmap_data[month] = np.nan
    heatmap_data = heatmap_data[sorted(heatmap_data.columns)]

    # Create heatmap
    fig, ax = plt.subplots(figsize=(12, max(4, len(heatmap_data) * 0.5)))

    # Plot heatmap
    im = ax.imshow(heatmap_data.values * 100, aspect='auto', cmap='RdYlGn',
                   vmin=-20, vmax=20, interpolation='nearest')

    # Set ticks
    ax.set_xticks(np.arange(12))
    ax.set_yticks(np.arange(len(heatmap_data)))

    # Label with month names and years
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ax.set_xticklabels(month_names)
    ax.set_yticklabels(heatmap_data.index)

    # Rotate the tick labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Add text annotations
    for i in range(len(heatmap_data)):
        for j in range(12):
            value = heatmap_data.iloc[i, j]
            if not np.isnan(value):
                text = ax.text(j, i, f'{value*100:.1f}%',
                             ha="center", va="center", color="black", fontsize=8)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Monthly Return (%)', rotation=270, labelpad=15)

    ax.set_title('Monthly Returns Heatmap')
    ax.set_xlabel('Month')
    ax.set_ylabel('Year')

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def analyze_monthly_performance(monthly_returns: pd.DataFrame) -> dict:
    """Analyze monthly performance patterns"""
    if monthly_returns.empty:
        return {
            'avg_monthly_return': 0,
            'monthly_win_rate': 0,
            'best_month': {},
            'worst_month': {},
            'best_months_avg': {},
            'worst_months_avg': {},
            'seasonality': {}
        }

    # Overall statistics
    avg_monthly = monthly_returns['return'].mean()
    monthly_win_rate = (monthly_returns['return'] > 0).sum() / len(monthly_returns)

    # Best and worst single months
    best_idx = monthly_returns['return'].idxmax()
    worst_idx = monthly_returns['return'].idxmin()

    best_month = {
        'year': int(monthly_returns.loc[best_idx, 'year']),
        'month': int(monthly_returns.loc[best_idx, 'month']),
        'return': monthly_returns.loc[best_idx, 'return']
    }

    worst_month = {
        'year': int(monthly_returns.loc[worst_idx, 'year']),
        'month': int(monthly_returns.loc[worst_idx, 'month']),
        'return': monthly_returns.loc[worst_idx, 'return']
    }

    # Top 5 best and worst months
    best_months = monthly_returns.nlargest(5, 'return')
    worst_months = monthly_returns.nsmallest(5, 'return')

    # Seasonality: average return by calendar month
    seasonality = monthly_returns.groupby('month')['return'].agg(['mean', 'count']).to_dict('index')

    return {
        'avg_monthly_return': avg_monthly,
        'monthly_win_rate': monthly_win_rate,
        'best_month': best_month,
        'worst_month': worst_month,
        'best_months': best_months,
        'worst_months': worst_months,
        'seasonality': seasonality
    }


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


def enhance_holdings_table(holdings: pd.DataFrame, equity: pd.DataFrame) -> pd.DataFrame:
    """Enhance holdings table with additional computed metrics"""
    if holdings.empty or equity.empty:
        return holdings

    enhanced = holdings.copy()

    # Get latest portfolio value
    latest_portfolio_value = equity["portfolio_value"].iloc[-1]

    # Compute % of portfolio for each holding
    if "notional" in enhanced.columns:
        enhanced["portfolio_pct"] = (enhanced["notional"] / latest_portfolio_value) * 100

    # Compute unrealized PnL (absolute)
    if "pnl_pct" in enhanced.columns and "notional" in enhanced.columns and "shares" in enhanced.columns and "avg_cost" in enhanced.columns:
        # Unrealized PnL = Current Value - Cost Basis
        cost_basis = enhanced["shares"] * enhanced["avg_cost"]
        enhanced["unrealized_pnl"] = enhanced["notional"] - cost_basis

    # Sort by portfolio percentage (largest positions first)
    if "portfolio_pct" in enhanced.columns:
        enhanced = enhanced.sort_values("portfolio_pct", ascending=False)

    return enhanced


def compute_trailing_performance(equity: pd.DataFrame, days: int = 10) -> dict:
    """Compute trailing N-day performance for portfolio and benchmark"""
    if len(equity) < days:
        return {
            "portfolio_return_pct": 0,
            "portfolio_pnl": 0,
            "benchmark_return_pct": 0,
            "days": 0,
            "daily_data": pd.DataFrame()
        }

    # Get last N+1 days (need extra day for computing returns)
    trailing_equity = equity.tail(days + 1).copy()

    # Compute aggregate performance
    portfolio_start = trailing_equity["portfolio_value"].iloc[0]
    portfolio_end = trailing_equity["portfolio_value"].iloc[-1]
    benchmark_start = trailing_equity["benchmark"].iloc[0]
    benchmark_end = trailing_equity["benchmark"].iloc[-1]

    portfolio_return_pct = (portfolio_end / portfolio_start - 1) if portfolio_start > 0 else 0
    portfolio_pnl = portfolio_end - portfolio_start
    benchmark_return_pct = (benchmark_end / benchmark_start - 1) if benchmark_start > 0 else 0

    # Compute daily returns for each day
    daily_data = []
    for i in range(1, len(trailing_equity)):
        date = trailing_equity["date"].iloc[i]
        port_prev = trailing_equity["portfolio_value"].iloc[i - 1]
        port_curr = trailing_equity["portfolio_value"].iloc[i]
        bench_prev = trailing_equity["benchmark"].iloc[i - 1]
        bench_curr = trailing_equity["benchmark"].iloc[i]

        port_daily_return = (port_curr / port_prev - 1) if port_prev > 0 else 0
        port_daily_pnl = port_curr - port_prev
        bench_daily_return = (bench_curr / bench_prev - 1) if bench_prev > 0 else 0
        outperformance = port_daily_return - bench_daily_return

        daily_data.append({
            "date": date,
            "portfolio_return": port_daily_return,
            "portfolio_pnl": port_daily_pnl,
            "benchmark_return": bench_daily_return,
            "outperformance": outperformance
        })

    daily_df = pd.DataFrame(daily_data)

    return {
        "portfolio_return_pct": portfolio_return_pct,
        "portfolio_pnl": portfolio_pnl,
        "benchmark_return_pct": benchmark_return_pct,
        "days": days,
        "daily_data": daily_df
    }


def compute_round_trip_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Compute round-trip trades (match BUY and SELL for each symbol).

    Returns DataFrame with columns:
    - symbol: stock symbol
    - entry_date: buy date
    - exit_date: sell date
    - holding_days: days held
    - entry_price: average buy price
    - exit_price: average sell price
    - shares: number of shares
    - entry_value: total buy value
    - exit_value: total sell value
    - pnl: profit/loss
    - return_pct: percentage return
    """
    if trades.empty:
        return pd.DataFrame()

    round_trips = []

    for symbol in trades["symbol"].unique():
        symbol_trades = trades[trades["symbol"] == symbol].sort_values("date")

        position = 0  # Current position size
        entry_value = 0  # Total value of current position
        entry_date = None
        entry_shares = 0

        for _, trade in symbol_trades.iterrows():
            if trade["side"] == "BUY":
                # Add to position
                position += trade["shares"]
                entry_value += trade["notional"]
                if entry_date is None:
                    entry_date = trade["date"]
                entry_shares = position

            elif trade["side"] == "SELL" and position > 0:
                # Close position (full or partial)
                sell_shares = trade["shares"]
                sell_value = trade["notional"]

                # Proportion of position being closed
                close_proportion = min(sell_shares / position, 1.0)

                # Calculate PnL for this portion
                portion_entry_value = entry_value * close_proportion
                portion_shares = position * close_proportion

                pnl = sell_value - portion_entry_value
                return_pct = (sell_value / portion_entry_value - 1) if portion_entry_value > 0 else 0
                holding_days = (trade["date"] - entry_date).days

                round_trips.append({
                    "symbol": symbol,
                    "entry_date": entry_date,
                    "exit_date": trade["date"],
                    "holding_days": holding_days,
                    "entry_price": portion_entry_value / portion_shares if portion_shares > 0 else 0,
                    "exit_price": sell_value / sell_shares if sell_shares > 0 else 0,
                    "shares": portion_shares,
                    "entry_value": portion_entry_value,
                    "exit_value": sell_value,
                    "pnl": pnl,
                    "return_pct": return_pct,
                })

                # Update position
                position -= sell_shares
                entry_value -= portion_entry_value

                # If fully closed, reset
                if position <= 0.01:  # Small threshold for floating point
                    position = 0
                    entry_value = 0
                    entry_date = None
                    entry_shares = 0

    return pd.DataFrame(round_trips)


def analyze_trade_performance(round_trips: pd.DataFrame) -> dict:
    """Analyze trade performance metrics."""
    if round_trips.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "expectancy": 0,
            "best_trade": None,
            "worst_trade": None,
            "avg_holding_days": 0,
            "longest_win_streak": 0,
            "longest_loss_streak": 0,
        }

    winners = round_trips[round_trips["pnl"] > 0]
    losers = round_trips[round_trips["pnl"] <= 0]

    total_wins = winners["pnl"].sum()
    total_losses = abs(losers["pnl"].sum())

    # Best and worst trades
    best_idx = round_trips["return_pct"].idxmax() if not round_trips.empty else None
    worst_idx = round_trips["return_pct"].idxmin() if not round_trips.empty else None

    best_trade = None
    worst_trade = None

    if best_idx is not None:
        best = round_trips.loc[best_idx]
        best_trade = {
            "symbol": best["symbol"],
            "return_pct": best["return_pct"],
            "pnl": best["pnl"],
            "holding_days": best["holding_days"],
            "entry_date": best["entry_date"],
            "exit_date": best["exit_date"],
        }

    if worst_idx is not None:
        worst = round_trips.loc[worst_idx]
        worst_trade = {
            "symbol": worst["symbol"],
            "return_pct": worst["return_pct"],
            "pnl": worst["pnl"],
            "holding_days": worst["holding_days"],
            "entry_date": worst["entry_date"],
            "exit_date": worst["exit_date"],
        }

    # Win/loss streaks
    round_trips = round_trips.sort_values("exit_date")
    is_winner = (round_trips["pnl"] > 0).astype(int)
    streaks = (is_winner != is_winner.shift()).cumsum()
    win_streaks = round_trips[is_winner == 1].groupby(streaks).size()
    loss_streaks = round_trips[is_winner == 0].groupby(streaks).size()

    return {
        "total_trades": len(round_trips),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": len(winners) / len(round_trips) if len(round_trips) > 0 else 0,
        "avg_win": winners["pnl"].mean() if len(winners) > 0 else 0,
        "avg_loss": losers["pnl"].mean() if len(losers) > 0 else 0,
        "profit_factor": total_wins / total_losses if total_losses > 0 else float('inf'),
        "expectancy": round_trips["pnl"].mean(),
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "avg_holding_days": round_trips["holding_days"].mean(),
        "longest_win_streak": win_streaks.max() if not win_streaks.empty else 0,
        "longest_loss_streak": loss_streaks.max() if not loss_streaks.empty else 0,
    }


def analyze_win_rate_by_holding_period(round_trips: pd.DataFrame) -> pd.DataFrame:
    """Analyze win rate and average return by holding period buckets."""
    if round_trips.empty:
        return pd.DataFrame()

    # Define holding period buckets (in days)
    buckets = [
        ("< 1 week", 0, 7),
        ("1-2 weeks", 7, 14),
        ("2-4 weeks", 14, 28),
        ("1-2 months", 28, 60),
        ("> 2 months", 60, float('inf')),
    ]

    results = []
    for label, min_days, max_days in buckets:
        mask = (round_trips["holding_days"] >= min_days) & (round_trips["holding_days"] < max_days)
        bucket_trades = round_trips[mask]

        if len(bucket_trades) == 0:
            continue

        winners = bucket_trades[bucket_trades["pnl"] > 0]

        results.append({
            "bucket": label,
            "count": len(bucket_trades),
            "win_rate": len(winners) / len(bucket_trades),
            "avg_return": bucket_trades["return_pct"].mean(),
            "avg_pnl": bucket_trades["pnl"].mean(),
            "total_pnl": bucket_trades["pnl"].sum(),
        })

    return pd.DataFrame(results)


def generate_trade_distribution_chart(round_trips: pd.DataFrame) -> str:
    """Generate histogram of trade PnL distribution."""
    if round_trips.empty or not plt:
        return ""

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot histogram of returns
    returns_pct = round_trips["return_pct"] * 100  # Convert to percentage
    ax.hist(returns_pct, bins=30, alpha=0.7, color="steelblue", edgecolor="black")

    # Add vertical line at zero
    ax.axvline(x=0, color="red", linestyle="--", linewidth=2, alpha=0.7)

    # Labels
    ax.set_xlabel("Return (%)", fontsize=12)
    ax.set_ylabel("Number of Trades", fontsize=12)
    ax.set_title("Trade Return Distribution", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # Add statistics annotation
    mean_return = returns_pct.mean()
    median_return = returns_pct.median()
    ax.text(
        0.02, 0.98,
        f"Mean: {mean_return:.2f}%\nMedian: {median_return:.2f}%",
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    # Convert to base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ============================================================================
# Position-Level Insights
# ============================================================================


def reconstruct_holdings_over_time(trades: pd.DataFrame, equity: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct the portfolio holdings on each date from trade history.

    Returns DataFrame with columns: date, num_holdings, position_weights (dict)
    """
    if trades.empty or equity.empty:
        return pd.DataFrame()

    # Build position tracking
    positions = {}  # symbol -> shares
    holdings_history = []

    for date in equity["date"]:
        # Process all trades up to this date
        day_trades = trades[trades["date"] <= date]

        # Rebuild positions from scratch for each date
        temp_positions = {}
        for _, trade in day_trades.iterrows():
            symbol = trade["symbol"]
            if trade["side"] == "BUY":
                temp_positions[symbol] = temp_positions.get(symbol, 0) + trade["shares"]
            else:  # SELL
                temp_positions[symbol] = temp_positions.get(symbol, 0) - trade["shares"]

        # Clean up zero/negative positions
        positions = {s: shares for s, shares in temp_positions.items() if shares > 0.001}

        # Get portfolio value for this date
        port_value = equity[equity["date"] == date]["portfolio_value"].iloc[0] if len(equity[equity["date"] == date]) > 0 else None

        if port_value and port_value > 0:
            # Calculate position weights (simplified - equal weight assumption)
            num_positions = len(positions)
            if num_positions > 0:
                # We don't have individual position values, so approximate with equal weights
                weights = {symbol: 1.0 / num_positions for symbol in positions}
            else:
                weights = {}
        else:
            weights = {}

        holdings_history.append({
            "date": date,
            "num_holdings": len(positions),
            "position_weights": weights
        })

    return pd.DataFrame(holdings_history)


def compute_concentration_metrics(weights: dict) -> dict:
    """
    Compute concentration risk metrics from position weights.

    Args:
        weights: dict of {symbol: weight}

    Returns:
        dict with HHI, top_5_concentration, gini_coefficient
    """
    if not weights:
        return {
            "hhi": 0,
            "top_5_concentration": 0,
            "gini_coefficient": 0
        }

    values = np.array(list(weights.values()))

    # Herfindahl-Hirschman Index (sum of squared weights)
    hhi = np.sum(values ** 2)

    # Top 5 concentration
    sorted_values = np.sort(values)[::-1]
    top_5_concentration = np.sum(sorted_values[:5])

    # Gini coefficient (measure of inequality)
    # Formula: (2 * sum(i * x_i)) / (n * sum(x_i)) - (n+1)/n
    n = len(values)
    sorted_values = np.sort(values)
    cumsum = np.cumsum(sorted_values)
    gini = (2 * np.sum((np.arange(1, n + 1)) * sorted_values)) / (n * cumsum[-1]) - (n + 1) / n

    return {
        "hhi": hhi,
        "top_5_concentration": top_5_concentration,
        "gini_coefficient": gini
    }


def analyze_position_sizing(trades: pd.DataFrame, equity: pd.DataFrame) -> dict:
    """
    Analyze position sizing and concentration over time.

    Returns dict with:
        - holdings_history: DataFrame with date, num_holdings, concentration metrics
        - avg_num_holdings: float
        - avg_position_size: float (as percentage)
        - avg_hhi: float
        - avg_gini: float
    """
    if trades.empty or equity.empty:
        return {
            "holdings_history": pd.DataFrame(),
            "avg_num_holdings": 0,
            "avg_position_size": 0,
            "avg_hhi": 0,
            "avg_gini": 0,
            "avg_top5_concentration": 0
        }

    holdings_over_time = reconstruct_holdings_over_time(trades, equity)

    if holdings_over_time.empty:
        return {
            "holdings_history": holdings_over_time,
            "avg_num_holdings": 0,
            "avg_position_size": 0,
            "avg_hhi": 0,
            "avg_gini": 0,
            "avg_top5_concentration": 0
        }

    # Compute concentration metrics for each date
    concentration_data = []
    for _, row in holdings_over_time.iterrows():
        metrics = compute_concentration_metrics(row["position_weights"])
        concentration_data.append({
            "date": row["date"],
            "num_holdings": row["num_holdings"],
            "hhi": metrics["hhi"],
            "top_5_concentration": metrics["top_5_concentration"],
            "gini_coefficient": metrics["gini_coefficient"]
        })

    holdings_history = pd.DataFrame(concentration_data)

    # Compute averages
    avg_num_holdings = holdings_history["num_holdings"].mean()
    avg_position_size = (1.0 / avg_num_holdings * 100) if avg_num_holdings > 0 else 0
    avg_hhi = holdings_history["hhi"].mean()
    avg_gini = holdings_history["gini_coefficient"].mean()
    avg_top5 = holdings_history["top_5_concentration"].mean()

    return {
        "holdings_history": holdings_history,
        "avg_num_holdings": avg_num_holdings,
        "avg_position_size": avg_position_size,
        "avg_hhi": avg_hhi,
        "avg_gini": avg_gini,
        "avg_top5_concentration": avg_top5
    }


def generate_position_sizing_charts(position_analysis: dict) -> dict:
    """
    Generate charts for position sizing analysis.

    Returns dict with base64-encoded chart images:
        - holdings_count_chart: Number of holdings over time
        - concentration_chart: HHI and Gini over time
    """
    if plt is None:
        return {"holdings_count_chart": None, "concentration_chart": None}

    holdings_history = position_analysis.get("holdings_history", pd.DataFrame())

    if holdings_history.empty:
        return {"holdings_count_chart": None, "concentration_chart": None}

    charts = {}

    # Chart 1: Number of holdings over time
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(holdings_history["date"], holdings_history["num_holdings"], color="#2196F3", linewidth=2)
    ax.axhline(
        y=position_analysis["avg_num_holdings"],
        color="red",
        linestyle="--",
        label=f"Average: {position_analysis['avg_num_holdings']:.1f}"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Number of Holdings")
    ax.set_title("Portfolio Size Over Time")
    ax.grid(True, alpha=0.3)
    ax.legend()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    charts["holdings_count_chart"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Chart 2: Concentration metrics over time
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # HHI
    ax1.plot(holdings_history["date"], holdings_history["hhi"], color="#FF9800", linewidth=2)
    ax1.axhline(
        y=position_analysis["avg_hhi"],
        color="red",
        linestyle="--",
        label=f"Average: {position_analysis['avg_hhi']:.4f}"
    )
    ax1.set_ylabel("HHI")
    ax1.set_title("Herfindahl-Hirschman Index (Lower = Less Concentrated)")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Gini Coefficient
    ax2.plot(holdings_history["date"], holdings_history["gini_coefficient"], color="#9C27B0", linewidth=2)
    ax2.axhline(
        y=position_analysis["avg_gini"],
        color="red",
        linestyle="--",
        label=f"Average: {position_analysis['avg_gini']:.4f}"
    )
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Gini Coefficient")
    ax2.set_title("Gini Coefficient (Lower = More Equal Distribution)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    charts["concentration_chart"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    return charts


# ============================================================================
# Rebalancing Behavior Analysis
# ============================================================================


def load_turnover(path: Path) -> pd.DataFrame:
    """Load turnover data from CSV."""
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date")


def analyze_rebalancing_behavior(trades: pd.DataFrame, turnover_df: pd.DataFrame,
                                 equity: pd.DataFrame) -> dict:
    """
    Analyze rebalancing patterns, turnover, and trading frequency.

    Returns dict with:
        - turnover_stats: Dict with avg, median, max turnover
        - rebalance_dates: List of rebalance dates
        - avg_rebalance_size: Average number of trades per rebalance
        - trade_frequency_patterns: Dict with patterns by day/month
        - churn_rate: Average positions changed per rebalance
        - no_change_rebalances: Number and percentage of rebalances with no trades
    """
    if trades.empty or equity.empty:
        return {
            "turnover_stats": {},
            "rebalance_dates": [],
            "avg_rebalance_size": 0,
            "trade_frequency_patterns": {},
            "churn_rate": 0,
            "no_change_rebalances_count": 0,
            "no_change_rebalances_pct": 0
        }

    # Turnover statistics
    turnover_stats = {}
    if not turnover_df.empty:
        turnover_stats = {
            "avg_turnover": turnover_df["turnover_pct"].mean(),
            "median_turnover": turnover_df["turnover_pct"].median(),
            "max_turnover": turnover_df["turnover_pct"].max(),
            "min_turnover": turnover_df["turnover_pct"].min(),
            "std_turnover": turnover_df["turnover_pct"].std()
        }

    # Group trades by date to identify rebalance events
    trades_by_date = trades.groupby("date").agg({
        "symbol": "count",  # Number of trades
        "notional": "sum"   # Total notional value
    }).reset_index()
    trades_by_date.columns = ["date", "num_trades", "total_notional"]

    rebalance_dates = trades_by_date["date"].tolist()
    avg_rebalance_size = trades_by_date["num_trades"].mean()

    # Trade frequency patterns
    trades_with_day = trades.copy()
    trades_with_day["day_of_week"] = pd.to_datetime(trades_with_day["date"]).dt.day_name()
    trades_with_day["month"] = pd.to_datetime(trades_with_day["date"]).dt.month_name()

    day_of_week_counts = trades_with_day["day_of_week"].value_counts().to_dict()
    month_counts = trades_with_day["month"].value_counts().to_dict()

    trade_frequency_patterns = {
        "by_day_of_week": day_of_week_counts,
        "by_month": month_counts
    }

    # Churn rate: average number of BUY + SELL per rebalance
    churn_rate = avg_rebalance_size / 2  # Each position change involves 1 buy + 1 sell on average

    # No-change rebalances: dates in equity with no trades
    # This is harder to determine without explicit rebalance schedule
    # For weekly rebalance, we can estimate expected rebalances vs actual
    days_elapsed = (equity["date"].iloc[-1] - equity["date"].iloc[0]).days
    expected_rebalances = days_elapsed / 7  # Weekly rebalancing
    actual_rebalances = len(rebalance_dates)
    no_change_rebalances = max(0, expected_rebalances - actual_rebalances)
    no_change_rebalances_pct = no_change_rebalances / expected_rebalances if expected_rebalances > 0 else 0

    return {
        "turnover_stats": turnover_stats,
        "turnover_df": turnover_df,
        "rebalance_dates": rebalance_dates,
        "avg_rebalance_size": avg_rebalance_size,
        "trade_frequency_patterns": trade_frequency_patterns,
        "churn_rate": churn_rate,
        "no_change_rebalances_count": int(no_change_rebalances),
        "no_change_rebalances_pct": no_change_rebalances_pct,
        "trades_by_date": trades_by_date
    }


def generate_rebalancing_charts(rebalancing_analysis: dict) -> dict:
    """
    Generate charts for rebalancing behavior analysis.

    Returns dict with base64-encoded images:
        - turnover_chart: Turnover over time
        - rebalance_frequency_chart: Trades per rebalance distribution
    """
    if plt is None:
        return {"turnover_chart": None, "rebalance_frequency_chart": None}

    charts = {}

    # Chart 1: Turnover over time
    turnover_df = rebalancing_analysis.get("turnover_df", pd.DataFrame())
    if not turnover_df.empty:
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(turnover_df["date"], turnover_df["turnover_pct"] * 100,
                color="#FF9800", linewidth=1.5, alpha=0.7)

        # Add rolling average
        if len(turnover_df) > 10:
            rolling_avg = turnover_df["turnover_pct"].rolling(window=10, min_periods=1).mean() * 100
            ax.plot(turnover_df["date"], rolling_avg,
                   color="#F44336", linewidth=2, label="10-Week Moving Avg")

        # Add average line
        avg_turnover = rebalancing_analysis["turnover_stats"].get("avg_turnover", 0) * 100
        ax.axhline(y=avg_turnover, color="green", linestyle="--",
                  label=f"Average: {avg_turnover:.1f}%")

        ax.set_xlabel("Date")
        ax.set_ylabel("Turnover %")
        ax.set_title("Portfolio Turnover Over Time")
        ax.grid(True, alpha=0.3)
        ax.legend()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        charts["turnover_chart"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Chart 2: Rebalance size distribution
    trades_by_date = rebalancing_analysis.get("trades_by_date", pd.DataFrame())
    if not trades_by_date.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(trades_by_date["num_trades"], bins=20, color="#2196F3", alpha=0.7, edgecolor="black")

        avg_size = rebalancing_analysis.get("avg_rebalance_size", 0)
        ax.axvline(x=avg_size, color="red", linestyle="--", linewidth=2,
                  label=f"Average: {avg_size:.1f} trades")

        ax.set_xlabel("Number of Trades per Rebalance")
        ax.set_ylabel("Frequency")
        ax.set_title("Distribution of Rebalance Sizes")
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        charts["rebalance_frequency_chart"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    return charts


# ============================================================================
# Enhanced Benchmark Comparison
# ============================================================================


def compute_relative_strength(portfolio_values: pd.Series, benchmark_values: pd.Series) -> pd.Series:
    """
    Compute relative strength ratio (portfolio / benchmark).

    Values > 1 indicate outperformance, < 1 indicate underperformance.
    """
    # Normalize both to start at 1.0
    portfolio_norm = portfolio_values / portfolio_values.iloc[0]
    benchmark_norm = benchmark_values / benchmark_values.iloc[0]
    return portfolio_norm / benchmark_norm


def compute_tracking_error_series(portfolio_returns: pd.Series,
                                  benchmark_returns: pd.Series,
                                  window: int = 60) -> pd.Series:
    """
    Compute rolling tracking error (standard deviation of excess returns).

    Args:
        window: Rolling window in trading days (default 60 = ~3 months)
    """
    excess_returns = portfolio_returns - benchmark_returns
    tracking_error = excess_returns.rolling(window=window, min_periods=20).std() * np.sqrt(252)
    return tracking_error


def compute_capture_ratios(portfolio_returns: pd.Series,
                           benchmark_returns: pd.Series) -> dict:
    """
    Compute up-capture and down-capture ratios.

    Up-capture: % of benchmark gains captured by portfolio
    Down-capture: % of benchmark losses captured by portfolio
    """
    # Separate up and down periods
    up_periods = benchmark_returns > 0
    down_periods = benchmark_returns < 0

    # Calculate average returns in each period
    portfolio_up = portfolio_returns[up_periods].mean()
    benchmark_up = benchmark_returns[up_periods].mean()

    portfolio_down = portfolio_returns[down_periods].mean()
    benchmark_down = benchmark_returns[down_periods].mean()

    # Calculate ratios
    up_capture = (portfolio_up / benchmark_up) if benchmark_up != 0 else np.nan
    down_capture = (portfolio_down / benchmark_down) if benchmark_down != 0 else np.nan

    return {
        "up_capture": up_capture,
        "down_capture": down_capture,
        "up_periods_count": up_periods.sum(),
        "down_periods_count": down_periods.sum()
    }


def compute_benchmark_relative_drawdown(portfolio_values: pd.Series,
                                        benchmark_values: pd.Series) -> pd.Series:
    """
    Compute drawdown relative to benchmark (excess return drawdown).

    Shows how portfolio performs vs benchmark from its relative peak.
    """
    relative_strength = compute_relative_strength(portfolio_values, benchmark_values)
    running_max = relative_strength.cummax()
    relative_dd = relative_strength / running_max - 1
    return relative_dd


def analyze_benchmark_comparison(equity_df: pd.DataFrame) -> dict:
    """
    Comprehensive benchmark comparison analysis.

    Returns dict with all benchmark-relative metrics and data.
    """
    portfolio_values = equity_df["portfolio_value"]
    benchmark_values = equity_df["benchmark"]
    portfolio_returns = equity_df["portfolio_return"]
    benchmark_returns = equity_df["benchmark_return"]

    # Relative strength
    relative_strength = compute_relative_strength(portfolio_values, benchmark_values)

    # Tracking error over time
    tracking_error = compute_tracking_error_series(portfolio_returns, benchmark_returns)

    # Capture ratios
    capture_ratios = compute_capture_ratios(portfolio_returns, benchmark_returns)

    # Benchmark-relative drawdown
    relative_dd = compute_benchmark_relative_drawdown(portfolio_values, benchmark_values)

    # Outperformance/underperformance periods
    outperformance_days = (portfolio_returns > benchmark_returns).sum()
    underperformance_days = (portfolio_returns < benchmark_returns).sum()
    total_days = len(portfolio_returns)

    return {
        "relative_strength": relative_strength,
        "tracking_error": tracking_error,
        "capture_ratios": capture_ratios,
        "relative_drawdown": relative_dd,
        "outperformance_days": outperformance_days,
        "underperformance_days": underperformance_days,
        "outperformance_pct": outperformance_days / total_days if total_days > 0 else 0,
        "dates": equity_df["date"]
    }


def generate_benchmark_comparison_charts(benchmark_analysis: dict) -> dict:
    """
    Generate charts for benchmark comparison analysis.

    Returns dict with base64-encoded images:
        - relative_strength_chart: Portfolio/Benchmark ratio over time
        - tracking_error_chart: Rolling tracking error
        - relative_drawdown_chart: Excess return drawdown
    """
    if plt is None:
        return {"relative_strength_chart": None, "tracking_error_chart": None,
                "relative_drawdown_chart": None}

    charts = {}
    dates = benchmark_analysis.get("dates")

    # Chart 1: Relative Strength (Portfolio / Benchmark)
    relative_strength = benchmark_analysis.get("relative_strength")
    if relative_strength is not None and not relative_strength.empty:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(dates, relative_strength, color="#2196F3", linewidth=2)
        ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.5, label="Parity")

        # Shade outperformance/underperformance regions
        ax.fill_between(dates, 1, relative_strength,
                        where=(relative_strength >= 1), alpha=0.2, color="green",
                        label="Outperformance")
        ax.fill_between(dates, 1, relative_strength,
                        where=(relative_strength < 1), alpha=0.2, color="red",
                        label="Underperformance")

        ax.set_xlabel("Date")
        ax.set_ylabel("Relative Strength (Portfolio / Benchmark)")
        ax.set_title("Portfolio Performance Relative to Benchmark")
        ax.grid(True, alpha=0.3)
        ax.legend()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        charts["relative_strength_chart"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Chart 2: Tracking Error Over Time
    tracking_error = benchmark_analysis.get("tracking_error")
    if tracking_error is not None and not tracking_error.empty:
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(dates, tracking_error * 100, color="#FF9800", linewidth=2)
        avg_te = tracking_error.mean() * 100
        ax.axhline(y=avg_te, color="red", linestyle="--",
                  label=f"Average: {avg_te:.2f}%")

        ax.set_xlabel("Date")
        ax.set_ylabel("Tracking Error (%)")
        ax.set_title("Rolling 60-Day Tracking Error vs Benchmark")
        ax.grid(True, alpha=0.3)
        ax.legend()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        charts["tracking_error_chart"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Chart 3: Benchmark-Relative Drawdown
    relative_dd = benchmark_analysis.get("relative_drawdown")
    if relative_dd is not None and not relative_dd.empty:
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.fill_between(dates, 0, relative_dd * 100,
                       where=(relative_dd <= 0), alpha=0.5, color="red")
        ax.plot(dates, relative_dd * 100, color="#F44336", linewidth=2)
        ax.axhline(y=0, color="gray", linestyle="-", alpha=0.5)

        ax.set_xlabel("Date")
        ax.set_ylabel("Relative Drawdown (%)")
        ax.set_title("Benchmark-Relative Drawdown (Excess Return Drawdown)")
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        charts["relative_drawdown_chart"] = base64.b64encode(buf.getvalue()).decode("utf-8")

    return charts


def analyze_run(run_path: Path, label: str):
    equity = load_equity(run_path / "momentum_equity.csv")
    trades = load_trades(run_path / "momentum_trades.csv")
    metrics_file = load_metrics(run_path / "momentum_metrics.csv")
    holdings = load_holdings(run_path / "momentum_holdings.csv")

    # Enhance holdings with additional metrics
    holdings = enhance_holdings_table(holdings, equity)

    # Compute 10-day trailing performance
    trailing_10d = compute_trailing_performance(equity, days=10)

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

    # Comprehensive risk metrics
    comprehensive_risk = compute_comprehensive_risk_metrics(
        equity,
        equity["portfolio_return"],
        equity["benchmark_return"],
        metrics["cagr"],
        metrics["bench_cagr"],
        metrics["max_dd"]
    )
    metrics.update(comprehensive_risk)

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

    # Monthly and quarterly analysis
    monthly_returns = compute_monthly_returns(equity["portfolio_value"], equity["date"])
    quarterly_returns = compute_quarterly_returns(equity["portfolio_value"], equity["date"])
    monthly_heatmap = generate_monthly_heatmap(monthly_returns)
    monthly_analysis = analyze_monthly_performance(monthly_returns)

    # Trade analytics
    round_trips = compute_round_trip_trades(trades)
    trade_performance = analyze_trade_performance(round_trips)
    win_rate_by_period = analyze_win_rate_by_holding_period(round_trips)
    trade_dist_chart = generate_trade_distribution_chart(round_trips)

    # Position-level insights
    position_analysis = analyze_position_sizing(trades, equity)
    position_charts = generate_position_sizing_charts(position_analysis)

    # Rebalancing behavior analysis
    turnover = load_turnover(run_path / "momentum_turnover.csv")
    rebalancing_analysis = analyze_rebalancing_behavior(trades, turnover, equity)
    rebalancing_charts = generate_rebalancing_charts(rebalancing_analysis)

    # Enhanced benchmark comparison
    benchmark_comparison = analyze_benchmark_comparison(equity)
    benchmark_charts = generate_benchmark_comparison_charts(benchmark_comparison)

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
        "monthly_returns": monthly_returns,
        "quarterly_returns": quarterly_returns,
        "monthly_heatmap": monthly_heatmap,
        "monthly_analysis": monthly_analysis,
        "trailing_10d": trailing_10d,
        "round_trips": round_trips,
        "trade_performance": trade_performance,
        "win_rate_by_period": win_rate_by_period,
        "trade_dist_chart": trade_dist_chart,
        "position_analysis": position_analysis,
        "position_charts": position_charts,
        "rebalancing_analysis": rebalancing_analysis,
        "rebalancing_charts": rebalancing_charts,
        "benchmark_comparison": benchmark_comparison,
        "benchmark_charts": benchmark_charts,
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

            # Add comprehensive risk metrics section
            risk_metrics_html = ""
            if m.get("sortino_ratio") is not None:
                risk_metrics_data = [
                    {"Metric": "Sortino Ratio", "Value": format_number(m.get("sortino_ratio"), 2), "Description": "Return / Downside Deviation"},
                    {"Metric": "Calmar Ratio", "Value": format_number(m.get("calmar_ratio"), 2), "Description": "CAGR / Max Drawdown"},
                    {"Metric": "Information Ratio", "Value": format_number(m.get("information_ratio"), 2), "Description": "Excess Return / Tracking Error"},
                    {"Metric": "Omega Ratio", "Value": format_number(m.get("omega_ratio"), 2), "Description": "Gains / Losses Ratio"},
                    {"Metric": "Ulcer Index", "Value": format_number(m.get("ulcer_index"), 4), "Description": "Drawdown Pain Measure"},
                    {"Metric": "VaR (95%)", "Value": format_percent(m.get("var_95")), "Description": "95% Confidence Loss"},
                    {"Metric": "VaR (99%)", "Value": format_percent(m.get("var_99")), "Description": "99% Confidence Loss"},
                    {"Metric": "CVaR (95%)", "Value": format_percent(m.get("cvar_95")), "Description": "Expected Shortfall (95%)"},
                    {"Metric": "CVaR (99%)", "Value": format_percent(m.get("cvar_99")), "Description": "Expected Shortfall (99%)"},
                    {"Metric": "Tail Ratio", "Value": format_number(m.get("tail_ratio"), 2), "Description": "95th Pct Gain / 5th Pct Loss"},
                ]
                risk_metrics_html = pd.DataFrame(risk_metrics_data).to_html(index=False, escape=False)

            # Combine both tables
            metrics_table = f"""
                <h4>Trading Metrics</h4>
                {metrics_table}
                <h4 style="margin-top: 20px;">Comprehensive Risk Metrics</h4>
                <p style="font-size: 0.9em; color: #666;">Advanced risk-adjusted performance measures beyond basic Sharpe ratio.</p>
                {risk_metrics_html}
            """
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
        trailing_10d_html = ""

        # Build 10-day performance summary
        trailing_10d = entry.get("trailing_10d", {})
        if trailing_10d:
            portfolio_ret = trailing_10d.get("portfolio_return_pct", 0)
            portfolio_pnl = trailing_10d.get("portfolio_pnl", 0)
            benchmark_ret = trailing_10d.get("benchmark_return_pct", 0)
            days = trailing_10d.get("days", 10)

            # Color code based on performance
            port_color = "green" if portfolio_ret >= 0 else "red"
            bench_color = "green" if benchmark_ret >= 0 else "red"

            # Build day-by-day table
            daily_data = trailing_10d.get("daily_data", pd.DataFrame())
            daily_table_html = ""
            if not daily_data.empty:
                daily_rows = []
                for idx, row in daily_data.iterrows():
                    date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                    port_ret_color = "green" if row['portfolio_return'] >= 0 else "red"
                    bench_ret_color = "green" if row['benchmark_return'] >= 0 else "red"
                    outperf_color = "green" if row['outperformance'] >= 0 else "red"

                    daily_rows.append(f"""
                        <tr>
                            <td style="padding: 5px; text-align: center;">{date_str}</td>
                            <td style="padding: 5px; text-align: right; color: {port_ret_color};">{format_percent(row['portfolio_return'])}</td>
                            <td style="padding: 5px; text-align: right; color: {port_ret_color};">{format_number(row['portfolio_pnl'], 0)}</td>
                            <td style="padding: 5px; text-align: right; color: {bench_ret_color};">{format_percent(row['benchmark_return'])}</td>
                            <td style="padding: 5px; text-align: right; color: {outperf_color};">{format_percent(row['outperformance'])}</td>
                        </tr>
                    """)

                daily_table_html = f"""
                <h5 style="margin-top: 15px; margin-bottom: 10px;">Daily Breakdown</h5>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <thead>
                        <tr style="background-color: #e9ecef;">
                            <th style="padding: 8px; text-align: center; border: 1px solid #dee2e6;">Date</th>
                            <th style="padding: 8px; text-align: right; border: 1px solid #dee2e6;">Portfolio Return</th>
                            <th style="padding: 8px; text-align: right; border: 1px solid #dee2e6;">Portfolio PnL</th>
                            <th style="padding: 8px; text-align: right; border: 1px solid #dee2e6;">Benchmark Return</th>
                            <th style="padding: 8px; text-align: right; border: 1px solid #dee2e6;">Outperformance</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(daily_rows)}
                    </tbody>
                </table>
                """

            trailing_10d_html = f"""
            <div style="background-color: #f8f9fa; padding: 15px; border: 1px solid #dee2e6; margin: 10px 0; border-radius: 5px;">
                <h4 style="margin-top: 0;">Trailing {days}-Day Performance</h4>
                <table style="width: 100%; border: none;">
                    <tr>
                        <td style="border: none; padding: 5px;"><strong>Portfolio Return:</strong></td>
                        <td style="border: none; padding: 5px; color: {port_color}; font-weight: bold;">{format_percent(portfolio_ret)}</td>
                        <td style="border: none; padding: 5px;"><strong>Absolute PnL:</strong></td>
                        <td style="border: none; padding: 5px; color: {port_color}; font-weight: bold;">{format_number(portfolio_pnl, 0)}</td>
                    </tr>
                    <tr>
                        <td style="border: none; padding: 5px;"><strong>Benchmark Return:</strong></td>
                        <td style="border: none; padding: 5px; color: {bench_color}; font-weight: bold;">{format_percent(benchmark_ret)}</td>
                        <td style="border: none; padding: 5px;"><strong>Outperformance:</strong></td>
                        <td style="border: none; padding: 5px; font-weight: bold;">{format_percent(portfolio_ret - benchmark_ret)}</td>
                    </tr>
                </table>
                {daily_table_html}
            </div>
            """

        if not holdings_df.empty:
            dfh = holdings_df.copy()
            for col in dfh.columns:
                if "date" in col and pd.api.types.is_datetime64_any_dtype(dfh[col]):
                    dfh[col] = dfh[col].dt.date.astype(str)
            percent_cols = {"pnl_pct", "contribution_pct", "portfolio_pct"}
            money_cols = {"avg_cost", "last_price", "notional", "unrealized_pnl"}
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

        # Rolling metrics section removed for performance

        # Build calendar performance section
        monthly_heatmap = entry.get("monthly_heatmap", "")
        monthly_analysis = entry.get("monthly_analysis", {})
        quarterly_returns = entry.get("quarterly_returns", pd.DataFrame())

        if monthly_heatmap:
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

            # Monthly heatmap chart
            monthly_heatmap_html = f'<img src="data:image/png;base64,{monthly_heatmap}" alt="Monthly Returns Heatmap" />'

            # Monthly statistics
            avg_monthly = monthly_analysis.get('avg_monthly_return', 0)
            monthly_win_rate = monthly_analysis.get('monthly_win_rate', 0)
            best_month = monthly_analysis.get('best_month', {})
            worst_month = monthly_analysis.get('worst_month', {})

            monthly_stats_df = pd.DataFrame([
                {"Metric": "Average Monthly Return", "Value": format_percent(avg_monthly)},
                {"Metric": "Monthly Win Rate", "Value": format_percent(monthly_win_rate)},
                {"Metric": "Best Month", "Value": f"{month_names[best_month.get('month', 1) - 1]} {best_month.get('year', '')} ({format_percent(best_month.get('return', 0))})"},
                {"Metric": "Worst Month", "Value": f"{month_names[worst_month.get('month', 1) - 1]} {worst_month.get('year', '')} ({format_percent(worst_month.get('return', 0))})"},
            ])
            monthly_stats_html = monthly_stats_df.to_html(index=False, escape=False)

            # Seasonality table (average return by calendar month)
            seasonality = monthly_analysis.get('seasonality', {})
            if seasonality:
                seasonality_data = []
                for month_num in range(1, 13):
                    if month_num in seasonality:
                        seasonality_data.append({
                            "Month": month_names[month_num - 1],
                            "Avg Return": format_percent(seasonality[month_num]['mean']),
                            "Count": int(seasonality[month_num]['count'])
                        })
                seasonality_df = pd.DataFrame(seasonality_data)
                seasonality_html = seasonality_df.to_html(index=False, escape=False)
            else:
                seasonality_html = "<p>Insufficient data for seasonality analysis.</p>"

            # Quarterly returns table
            if not quarterly_returns.empty:
                quarterly_pivot = quarterly_returns.pivot(index='year', columns='quarter', values='return')
                quarterly_data = []
                for year in quarterly_pivot.index:
                    row = {"Year": int(year)}
                    for q in range(1, 5):
                        if q in quarterly_pivot.columns:
                            val = quarterly_pivot.loc[year, q]
                            row[f"Q{q}"] = format_percent(val) if not pd.isna(val) else "-"
                        else:
                            row[f"Q{q}"] = "-"
                    quarterly_data.append(row)
                quarterly_df = pd.DataFrame(quarterly_data)
                quarterly_html = quarterly_df.to_html(index=False, escape=False)
            else:
                quarterly_html = "<p>Insufficient data for quarterly analysis.</p>"

            calendar_section = f"""
                <h3>Calendar Performance</h3>
                <p>Visual representation of monthly and quarterly returns.</p>
                <h4>Monthly Returns Heatmap</h4>
                {monthly_heatmap_html}
                <h4>Monthly Performance Summary</h4>
                {monthly_stats_html}
                <h4>Quarterly Returns</h4>
                {quarterly_html}
            """
        else:
            calendar_section = "<h3>Calendar Performance</h3><p>Calendar performance unavailable (matplotlib missing).</p>"

        # Trade Analytics Section
        trade_perf = entry.get("trade_performance", {})
        win_rate_by_period = entry.get("win_rate_by_period", pd.DataFrame())
        trade_dist_chart = entry.get("trade_dist_chart", "")

        if trade_perf and trade_perf.get("total_trades", 0) > 0:
            # Performance metrics table
            perf_metrics = [
                {"Metric": "Total Trades", "Value": format_number(trade_perf["total_trades"], 0)},
                {"Metric": "Winning Trades", "Value": format_number(trade_perf["winning_trades"], 0)},
                {"Metric": "Losing Trades", "Value": format_number(trade_perf["losing_trades"], 0)},
                {"Metric": "Win Rate", "Value": format_percent(trade_perf["win_rate"])},
                {"Metric": "Average Win", "Value": f"₹{format_number(trade_perf['avg_win'], 0)}"},
                {"Metric": "Average Loss", "Value": f"₹{format_number(trade_perf['avg_loss'], 0)}"},
                {"Metric": "Profit Factor", "Value": format_number(trade_perf["profit_factor"], 2)},
                {"Metric": "Expectancy (Avg PnL)", "Value": f"₹{format_number(trade_perf['expectancy'], 0)}"},
                {"Metric": "Avg Holding Days", "Value": format_number(trade_perf["avg_holding_days"], 1)},
                {"Metric": "Longest Win Streak", "Value": format_number(trade_perf["longest_win_streak"], 0)},
                {"Metric": "Longest Loss Streak", "Value": format_number(trade_perf["longest_loss_streak"], 0)},
            ]
            perf_metrics_html = pd.DataFrame(perf_metrics).to_html(index=False, escape=False)

            # Best and worst trades
            best_trade = trade_perf.get("best_trade")
            worst_trade = trade_perf.get("worst_trade")

            best_trade_html = ""
            if best_trade:
                best_trade_html = f"""
                <div style="background: #e8f5e9; padding: 10px; border-radius: 4px; margin: 10px 0;">
                    <strong>{best_trade['symbol']}</strong><br>
                    Return: <span style="color: green; font-weight: bold;">{format_percent(best_trade['return_pct'])}</span>
                    (₹{format_number(best_trade['pnl'], 0)})<br>
                    Held: {int(best_trade['holding_days'])} days
                    ({best_trade['entry_date'].strftime('%Y-%m-%d')} → {best_trade['exit_date'].strftime('%Y-%m-%d')})
                </div>
                """

            worst_trade_html = ""
            if worst_trade:
                worst_trade_html = f"""
                <div style="background: #ffebee; padding: 10px; border-radius: 4px; margin: 10px 0;">
                    <strong>{worst_trade['symbol']}</strong><br>
                    Return: <span style="color: red; font-weight: bold;">{format_percent(worst_trade['return_pct'])}</span>
                    (₹{format_number(worst_trade['pnl'], 0)})<br>
                    Held: {int(worst_trade['holding_days'])} days
                    ({worst_trade['entry_date'].strftime('%Y-%m-%d')} → {worst_trade['exit_date'].strftime('%Y-%m-%d')})
                </div>
                """

            # Win rate by holding period
            win_rate_html = ""
            if not win_rate_by_period.empty:
                win_rate_display = win_rate_by_period.copy()
                win_rate_display["win_rate"] = win_rate_display["win_rate"].apply(lambda x: format_percent(x))
                win_rate_display["avg_return"] = win_rate_display["avg_return"].apply(lambda x: format_percent(x))
                win_rate_display["avg_pnl"] = win_rate_display["avg_pnl"].apply(lambda x: f"₹{format_number(x, 0)}")
                win_rate_display["total_pnl"] = win_rate_display["total_pnl"].apply(lambda x: f"₹{format_number(x, 0)}")
                win_rate_display.columns = ["Holding Period", "Trades", "Win Rate", "Avg Return", "Avg PnL", "Total PnL"]
                win_rate_html = win_rate_display.to_html(index=False, escape=False)

            # Trade distribution chart
            trade_dist_html = ""
            if trade_dist_chart:
                trade_dist_html = f'<img src="data:image/png;base64,{trade_dist_chart}" alt="Trade Distribution" style="max-width: 100%;" />'

            trade_analytics_section = f"""
                <h3>Trade Analytics</h3>

                <h4>Performance Metrics</h4>
                {perf_metrics_html}

                <h4>Best Trade</h4>
                {best_trade_html}

                <h4>Worst Trade</h4>
                {worst_trade_html}

                <h4>Win Rate by Holding Period</h4>
                {win_rate_html}

                <h4>Trade Return Distribution</h4>
                {trade_dist_html}
            """
        else:
            trade_analytics_section = "<h3>Trade Analytics</h3><p>No trade data available.</p>"

        # Position-Level Insights Section removed for performance

        # Rebalancing Behavior Section
        rebalancing_analysis = entry.get("rebalancing_analysis", {})
        rebalancing_charts = entry.get("rebalancing_charts", {})

        if rebalancing_analysis and rebalancing_analysis.get("turnover_stats"):
            turnover_stats = rebalancing_analysis["turnover_stats"]
            trade_freq = rebalancing_analysis.get("trade_frequency_patterns", {})

            # Summary metrics table
            rebalance_metrics = [
                {"Metric": "Avg Turnover", "Value": format_percent(turnover_stats.get("avg_turnover", 0))},
                {"Metric": "Median Turnover", "Value": format_percent(turnover_stats.get("median_turnover", 0))},
                {"Metric": "Max Turnover", "Value": format_percent(turnover_stats.get("max_turnover", 0))},
                {"Metric": "Min Turnover", "Value": format_percent(turnover_stats.get("min_turnover", 0))},
                {"Metric": "Turnover Std Dev", "Value": format_percent(turnover_stats.get("std_turnover", 0))},
                {"Metric": "Total Rebalances", "Value": format_number(len(rebalancing_analysis.get("rebalance_dates", [])), 0)},
                {"Metric": "Avg Trades per Rebalance", "Value": format_number(rebalancing_analysis.get("avg_rebalance_size", 0), 1)},
                {"Metric": "Churn Rate (Positions Changed)", "Value": format_number(rebalancing_analysis.get("churn_rate", 0), 1)},
                {"Metric": "No-Change Rebalances", "Value": f"{rebalancing_analysis.get('no_change_rebalances_count', 0)} ({format_percent(rebalancing_analysis.get('no_change_rebalances_pct', 0))})"},
            ]
            rebalance_metrics_html = pd.DataFrame(rebalance_metrics).to_html(index=False, escape=False)

            # Charts
            turnover_chart_html = ""
            if rebalancing_charts.get("turnover_chart"):
                turnover_chart_html = f'<img src="data:image/png;base64,{rebalancing_charts["turnover_chart"]}" alt="Turnover Over Time" style="max-width: 100%;" />'

            rebalance_freq_chart_html = ""
            if rebalancing_charts.get("rebalance_frequency_chart"):
                rebalance_freq_chart_html = f'<img src="data:image/png;base64,{rebalancing_charts["rebalance_frequency_chart"]}" alt="Rebalance Size Distribution" style="max-width: 100%;" />'

            rebalancing_section = f"""
                <h3>Rebalancing Behavior Analysis</h3>
                <p>Analysis of portfolio turnover, trading patterns, and rebalancing frequency.</p>

                <h4>Rebalancing Metrics</h4>
                {rebalance_metrics_html}

                <h4>Turnover Over Time</h4>
                {turnover_chart_html}

                <h4>Rebalance Size Distribution</h4>
                {rebalance_freq_chart_html}
            """
        else:
            rebalancing_section = "<h3>Rebalancing Behavior Analysis</h3><p>Rebalancing analysis unavailable (no turnover data).</p>"

        # Enhanced Benchmark Comparison Section
        benchmark_comparison = entry.get("benchmark_comparison", {})
        benchmark_charts = entry.get("benchmark_charts", {})

        if benchmark_comparison and benchmark_comparison.get("capture_ratios"):
            capture = benchmark_comparison["capture_ratios"]

            # Summary metrics table
            bench_metrics = [
                {"Metric": "Up Capture Ratio", "Value": format_percent(capture.get("up_capture", 0)),
                 "Description": "% of benchmark gains captured"},
                {"Metric": "Down Capture Ratio", "Value": format_percent(capture.get("down_capture", 0)),
                 "Description": "% of benchmark losses captured"},
                {"Metric": "Up Periods", "Value": format_number(capture.get("up_periods_count", 0), 0),
                 "Description": "Days when benchmark was positive"},
                {"Metric": "Down Periods", "Value": format_number(capture.get("down_periods_count", 0), 0),
                 "Description": "Days when benchmark was negative"},
                {"Metric": "Outperformance Days", "Value": f"{benchmark_comparison.get('outperformance_days', 0)} ({format_percent(benchmark_comparison.get('outperformance_pct', 0))})",
                 "Description": "Days beating benchmark"},
                {"Metric": "Underperformance Days", "Value": f"{benchmark_comparison.get('underperformance_days', 0)} ({format_percent(1 - benchmark_comparison.get('outperformance_pct', 0))})",
                 "Description": "Days trailing benchmark"},
            ]
            bench_metrics_html = pd.DataFrame(bench_metrics).to_html(index=False, escape=False)

            # Interpretation box
            up_capture = capture.get("up_capture", 0)
            down_capture = capture.get("down_capture", 0)

            # Up capture interpretation
            if up_capture >= 1.0:
                up_color = "#4CAF50"
                up_text = "Capturing all benchmark gains and more"
            elif up_capture >= 0.8:
                up_color = "#8BC34A"
                up_text = "Good upside participation"
            else:
                up_color = "#FF9800"
                up_text = "Missing significant upside"

            # Down capture interpretation
            if down_capture <= 0.5:
                down_color = "#4CAF50"
                down_text = "Excellent downside protection"
            elif down_capture <= 0.8:
                down_color = "#8BC34A"
                down_text = "Good downside protection"
            elif down_capture <= 1.0:
                down_color = "#FF9800"
                down_text = "Moderate downside protection"
            else:
                down_color = "#F44336"
                down_text = "Amplifying benchmark losses"

            interpretation_html = f"""
            <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 10px 0;">
                <h4 style="margin-top: 0;">Capture Ratio Interpretation</h4>
                <div style="margin: 10px 0;">
                    <strong>Up Capture ({format_percent(up_capture)}):</strong>
                    <span style="color: {up_color}; font-weight: bold;">→ {up_text}</span>
                    <br>
                    <small>Values > 100% indicate outperformance in up markets</small>
                </div>
                <div style="margin: 10px 0;">
                    <strong>Down Capture ({format_percent(down_capture)}):</strong>
                    <span style="color: {down_color}; font-weight: bold;">→ {down_text}</span>
                    <br>
                    <small>Values < 100% indicate better downside protection than benchmark</small>
                </div>
                <p style="margin: 10px 0; font-size: 0.9em; color: #666;">
                    <strong>Ideal Profile:</strong> Up Capture > 100%, Down Capture < 100%
                    (capture gains, protect downside)
                </p>
            </div>
            """

            # Charts
            relative_strength_html = ""
            if benchmark_charts.get("relative_strength_chart"):
                relative_strength_html = f'<img src="data:image/png;base64,{benchmark_charts["relative_strength_chart"]}" alt="Relative Strength" style="max-width: 100%;" />'

            tracking_error_html = ""
            if benchmark_charts.get("tracking_error_chart"):
                tracking_error_html = f'<img src="data:image/png;base64,{benchmark_charts["tracking_error_chart"]}" alt="Tracking Error" style="max-width: 100%;" />'

            relative_dd_html = ""
            if benchmark_charts.get("relative_drawdown_chart"):
                relative_dd_html = f'<img src="data:image/png;base64,{benchmark_charts["relative_drawdown_chart"]}" alt="Relative Drawdown" style="max-width: 100%;" />'

            benchmark_section = f"""
                <h3>Enhanced Benchmark Comparison</h3>
                <p>Comprehensive analysis of performance relative to benchmark.</p>

                <h4>Benchmark Comparison Metrics</h4>
                {bench_metrics_html}

                {interpretation_html}

                <h4>Relative Strength (Portfolio / Benchmark)</h4>
                {relative_strength_html}

                <h4>Rolling Tracking Error</h4>
                {tracking_error_html}

                <h4>Benchmark-Relative Drawdown</h4>
                {relative_dd_html}
            """
        else:
            benchmark_section = "<h3>Enhanced Benchmark Comparison</h3><p>Benchmark comparison unavailable.</p>"

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

                {calendar_section}

                {trade_analytics_section}

                {rebalancing_section}

                {benchmark_section}

                <h3>Trailing Returns</h3>
                {period_html}
                <h3>Portfolio Stats</h3>
                {metrics_table}
                <h3>Current Holdings</h3>
                {trailing_10d_html}
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
