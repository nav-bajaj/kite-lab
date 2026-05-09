"""
Simulate SIP (Systematic Investment Plan) into the momentum portfolio strategy.

Invests a fixed amount on the 15th of each month (or next trading day if holiday).
Shows both pre-tax and post-tax returns (25% tax on FY gains, Indian FY April-March).
Compares momentum SIP returns against an equivalent SIP into the Nifty 100 benchmark.

Usage:
    # Run on all three universes + benchmark (default)
    python scripts/sip_momentum_returns.py

    # Custom monthly investment
    python scripts/sip_momentum_returns.py --monthly-investment 50000

    # Single universe
    python scripts/sip_momentum_returns.py --universe nse500

    # Custom tax rate
    python scripts/sip_momentum_returns.py --tax-rate 0.20
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

COLORS = {
    "NSE 500": "#1f77b4",
    "Nifty 100": "#2ca02c",
    "Nifty 250": "#ff7f0e",
    "Benchmark": "#d62728",
    "Invested": "#888888",
}

SIP_DAY = 15  # Fixed SIP date each month


def find_latest_equity(universe: str) -> Path | None:
    """Find the latest momentum_equity.csv for a universe."""
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


def load_daily_returns(path: Path, value_col: str = "portfolio_value") -> pd.DataFrame:
    """Load CSV and compute daily returns from a value column."""
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    if value_col not in df.columns:
        raise ValueError(f"Missing '{value_col}' column in {path}")
    df["daily_return"] = df[value_col].pct_change().fillna(0)
    return df[["date", "daily_return"]]


def _build_sip_dates(trading_dates: pd.Series) -> set[pd.Timestamp]:
    """
    For each month in the trading calendar, find the SIP investment date:
    the 15th if it's a trading day, otherwise the next available trading day.
    """
    trading_set = set(trading_dates)
    sip_dates = set()

    # Get unique year-month combinations
    months = trading_dates.dt.to_period("M").unique()

    for period in months:
        # Target the 15th of this month
        target = pd.Timestamp(period.start_time.year, period.start_time.month, SIP_DAY)

        # Find the next trading day on or after the 15th
        candidates = trading_dates[trading_dates >= target]
        if len(candidates) > 0:
            sip_dates.add(candidates.iloc[0])

    return sip_dates


def get_financial_year_end(dt: pd.Timestamp) -> tuple[int, int]:
    """Return (year, month) of FY end. Indian FY: April 1 - March 31."""
    if dt.month >= 4:
        return (dt.year + 1, 3)
    else:
        return (dt.year, 3)


def simulate_sip(
    returns_df: pd.DataFrame,
    monthly_investment: float,
    tax_rate: float = 0.25,
) -> pd.DataFrame:
    """
    Simulate SIP with fixed date (15th or next trading day) and FY tax deduction.

    Returns DataFrame with columns:
        date, portfolio_value, post_tax_value, total_invested, gain_pct, post_tax_gain_pct
    """
    dates = returns_df["date"]
    daily_returns = returns_df["daily_return"].values

    sip_dates = _build_sip_dates(dates)

    portfolio_value = 0.0
    post_tax_value = 0.0
    total_invested = 0.0

    # Track FY start capital for tax calculation (on post-tax track)
    current_fy_end = None
    fy_start_capital = 0.0  # total_invested at start of FY (cost basis for tax)
    fy_start_value = 0.0    # post_tax_value at start of FY

    out_dates = []
    out_values = []
    out_post_tax = []
    out_invested = []

    for i in range(len(dates)):
        dt = pd.Timestamp(dates.iloc[i])

        # Check if we've crossed into a new FY — apply tax on previous FY gains
        fy_end = get_financial_year_end(dt)
        if current_fy_end is not None and fy_end != current_fy_end:
            # Tax the gains from previous FY on the post-tax track
            # Gains = current post_tax_value - value at FY start
            # We only tax investment gains, not new deposits
            fy_gain = post_tax_value - fy_start_value
            if fy_gain > 0:
                tax = fy_gain * tax_rate
                post_tax_value -= tax

            fy_start_value = post_tax_value

        current_fy_end = fy_end

        # Invest on SIP date
        if dt in sip_dates:
            portfolio_value += monthly_investment
            post_tax_value += monthly_investment
            total_invested += monthly_investment
            # New investment adds to FY start tracking
            fy_start_value += monthly_investment

        # Apply day's return
        portfolio_value *= (1 + daily_returns[i])
        post_tax_value *= (1 + daily_returns[i])

        out_dates.append(dt)
        out_values.append(portfolio_value)
        out_post_tax.append(post_tax_value)
        out_invested.append(total_invested)

    result = pd.DataFrame({
        "date": out_dates,
        "portfolio_value": out_values,
        "post_tax_value": out_post_tax,
        "total_invested": out_invested,
    })
    result["gain_pct"] = result["portfolio_value"] / result["total_invested"] - 1
    result["post_tax_gain_pct"] = result["post_tax_value"] / result["total_invested"] - 1
    return result


def _solve_xirr(cashflows: np.ndarray, year_fracs: np.ndarray) -> float | None:
    """Solve XIRR via Newton's method given cashflow amounts and year fractions."""
    def npv(rate: float) -> float:
        return np.sum(cashflows / (1 + rate) ** year_fracs)

    def npv_deriv(rate: float) -> float:
        return np.sum(-year_fracs * cashflows / (1 + rate) ** (year_fracs + 1))

    for guess in [0.1, 0.3, 0.5, 1.0]:
        rate = guess
        try:
            for _ in range(200):
                f_val = npv(rate)
                f_deriv = npv_deriv(rate)
                if abs(f_deriv) < 1e-14:
                    break
                new_rate = rate - f_val / f_deriv
                if new_rate <= -1:
                    new_rate = (rate + (-1)) / 2
                if abs(new_rate - rate) < 1e-9:
                    return new_rate
                rate = new_rate
        except (OverflowError, FloatingPointError):
            continue

    return None


def _get_sip_cashflows(sip_df: pd.DataFrame, monthly_investment: float) -> tuple[list, list]:
    """Extract (dates, amounts) of SIP investment cashflows from a SIP result DataFrame."""
    invested = sip_df["total_invested"]
    diffs = invested.diff().fillna(invested.iloc[0])
    inv_mask = diffs > 0

    dates = []
    amounts = []
    for _, row in sip_df[inv_mask].iterrows():
        dates.append(row["date"])
        amounts.append(-monthly_investment)

    return dates, amounts


def compute_xirr(
    sip_df: pd.DataFrame,
    monthly_investment: float,
    value_col: str = "portfolio_value",
) -> float | None:
    """Compute XIRR (annualized IRR) for SIP cashflows."""
    inv_dates, inv_amounts = _get_sip_cashflows(sip_df, monthly_investment)

    dates = inv_dates + [sip_df["date"].iloc[-1]]
    cfs = inv_amounts + [sip_df[value_col].iloc[-1]]

    base = dates[0]
    year_fracs = np.array([(d - base).days / 365.25 for d in dates])
    return _solve_xirr(np.array(cfs), year_fracs)


def compute_monthly_xirr(
    sip_df: pd.DataFrame,
    monthly_investment: float,
    value_col: str = "portfolio_value",
) -> pd.DataFrame:
    """Compute XIRR at each month-end, returning a DataFrame with date and xirr columns."""
    inv_dates, inv_amounts = _get_sip_cashflows(sip_df, monthly_investment)

    # Resample to month-end
    monthly = sip_df.set_index("date").resample("ME").last().reset_index()

    results = []
    for _, row in monthly.iterrows():
        end_date = row["date"]
        end_value = row[value_col]

        if pd.isna(end_value) or end_value <= 0:
            results.append({"date": end_date, "xirr": np.nan})
            continue

        # Collect cashflows up to this month-end
        cf_dates = []
        cf_amounts = []
        for d, a in zip(inv_dates, inv_amounts):
            if d <= end_date:
                cf_dates.append(d)
                cf_amounts.append(a)

        if len(cf_dates) < 2:
            results.append({"date": end_date, "xirr": np.nan})
            continue

        # Add terminal value
        cf_dates.append(end_date)
        cf_amounts.append(end_value)

        base = cf_dates[0]
        year_fracs = np.array([(d - base).days / 365.25 for d in cf_dates])

        # Need at least some time elapsed
        if year_fracs[-1] < 0.25:
            results.append({"date": end_date, "xirr": np.nan})
            continue

        xirr = _solve_xirr(np.array(cf_amounts), year_fracs)
        results.append({"date": end_date, "xirr": xirr if xirr is not None else np.nan})

    return pd.DataFrame(results)


def generate_chart(
    sip_results: dict[str, pd.DataFrame],
    output_path: Path,
    monthly_investment: float,
) -> bool:
    """Generate SIP equity curve chart with pre-tax and post-tax lines."""
    if not HAS_MATPLOTLIB:
        print("Warning: matplotlib not available, skipping chart generation")
        return False

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

    # Top: Pre-tax
    first_df = next(iter(sip_results.values()))
    ax1.plot(
        first_df["date"], first_df["total_invested"] / 100000,
        label="Total Invested", linewidth=2, color=COLORS["Invested"],
        linestyle="--", alpha=0.7,
    )
    for label, df in sip_results.items():
        color = COLORS.get(label, None)
        ax1.plot(df["date"], df["portfolio_value"] / 100000, label=label, linewidth=1.8, color=color)

    ax1.set_ylabel("Value (₹ Lakhs)", fontsize=12)
    ax1.set_title(f"SIP Pre-Tax Growth (₹{monthly_investment / 1000:.0f}K/month on 15th)", fontsize=14, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # Bottom: Post-tax
    ax2.plot(
        first_df["date"], first_df["total_invested"] / 100000,
        label="Total Invested", linewidth=2, color=COLORS["Invested"],
        linestyle="--", alpha=0.7,
    )
    for label, df in sip_results.items():
        color = COLORS.get(label, None)
        ax2.plot(df["date"], df["post_tax_value"] / 100000, label=label, linewidth=1.8, color=color)

    ax2.set_ylabel("Value (₹ Lakhs)", fontsize=12)
    ax2.set_xlabel("Date", fontsize=12)
    ax2.set_title("SIP Post-Tax Growth (25% tax on FY gains)", fontsize=14, fontweight="bold")
    ax2.legend(loc="upper left", fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return True


def _heatmap_color(value: float) -> str:
    """Return background CSS color. Red < 0 < Green."""
    if np.isnan(value):
        return "#f5f5f5"
    clamped = max(-0.50, min(2.0, value))
    if clamped < 0:
        intensity = min(abs(clamped) / 0.50, 1.0)
        r, g, b = 255, int(255 * (1 - intensity * 0.6)), int(255 * (1 - intensity * 0.6))
    else:
        intensity = min(clamped / 2.0, 1.0)
        r, g, b = int(255 * (1 - intensity * 0.55)), 255, int(255 * (1 - intensity * 0.55))
    return f"rgb({r},{g},{b})"


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def generate_heatmap_html(
    sip_results: dict[str, pd.DataFrame],
    output_path: Path,
    monthly_investment: float,
    tax_rate: float,
) -> None:
    """Generate HTML heatmap showing monthly SIP gain % — pre-tax and post-tax tables."""

    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        f"<title>SIP Returns Heatmap (₹{monthly_investment / 1000:.0f}K/month)</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 35px; margin-bottom: 4px; color: #333; }",
        "  h3 { margin-top: 5px; margin-bottom: 8px; color: #888; font-weight: normal; font-size: 14px; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 60px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        f"<h1>SIP Returns Heatmap</h1>",
        f"<div class='subtitle'>₹{monthly_investment / 1000:.0f}K invested on 15th of each month "
        f"(or next trading day). Cell = cumulative gain % (value / invested − 1). "
        f"Tax: {tax_rate:.0%} on FY gains (April–March).</div>",
    ]

    for label, df in sip_results.items():
        monthly = df.set_index("date").resample("ME").last().reset_index()
        monthly["year"] = monthly["date"].dt.year
        monthly["month"] = monthly["date"].dt.month
        years = sorted(monthly["year"].unique())

        for mode, gain_col, subtitle in [
            ("Pre-Tax", "gain_pct", "Before tax deduction"),
            ("Post-Tax", "post_tax_gain_pct", f"After {tax_rate:.0%} annual tax on FY gains"),
        ]:
            html_parts.append(f"<h2>{label} — {mode}</h2>")
            html_parts.append(f"<h3>{subtitle}</h3>")
            html_parts.append("<table>")
            html_parts.append("<tr><th>Year</th>")
            for m in MONTH_NAMES:
                html_parts.append(f"<th>{m}</th>")
            html_parts.append("</tr>")

            for year in years:
                html_parts.append("<tr>")
                html_parts.append(f"<td class='year-col'>{year}</td>")
                for month in range(1, 13):
                    row = monthly[(monthly["year"] == year) & (monthly["month"] == month)]
                    if row.empty or pd.isna(row[gain_col].iloc[0]):
                        html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                    else:
                        val = row[gain_col].iloc[0]
                        bg = _heatmap_color(val)
                        html_parts.append(f"<td style='background:{bg};'>{val:+.1%}</td>")
                html_parts.append("</tr>")

            html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def _xirr_heatmap_color(value: float) -> str:
    """Return background CSS color for XIRR. Red < 0 < Green, scaled for 0-60% range."""
    if np.isnan(value):
        return "#f5f5f5"
    clamped = max(-0.30, min(0.60, value))
    if clamped < 0:
        intensity = min(abs(clamped) / 0.30, 1.0)
        r, g, b = 255, int(255 * (1 - intensity * 0.6)), int(255 * (1 - intensity * 0.6))
    else:
        intensity = min(clamped / 0.60, 1.0)
        r, g, b = int(255 * (1 - intensity * 0.55)), 255, int(255 * (1 - intensity * 0.55))
    return f"rgb({r},{g},{b})"


def generate_xirr_heatmap_html(
    sip_results: dict[str, pd.DataFrame],
    output_path: Path,
    monthly_investment: float,
    tax_rate: float,
) -> None:
    """Generate a separate HTML heatmap of monthly XIRR values (pre-tax and post-tax)."""

    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        f"<title>SIP XIRR Heatmap (₹{monthly_investment / 1000:.0f}K/month)</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 35px; margin-bottom: 4px; color: #333; }",
        "  h3 { margin-top: 5px; margin-bottom: 8px; color: #888; font-weight: normal; font-size: 14px; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 60px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        f"<h1>SIP XIRR Heatmap</h1>",
        f"<div class='subtitle'>₹{monthly_investment / 1000:.0f}K invested on 15th of each month. "
        f"Cell = annualized XIRR as of month end (all cashflows up to that point). "
        f"Tax: {tax_rate:.0%} on FY gains (April–March). "
        f"First 3 months omitted (insufficient data).</div>",
    ]

    for label, df in sip_results.items():
        for value_col, mode, subtitle in [
            ("portfolio_value", "Pre-Tax", "Before tax deduction"),
            ("post_tax_value", "Post-Tax", f"After {tax_rate:.0%} annual tax on FY gains"),
        ]:
            print(f"  Computing monthly XIRR for {label} ({mode})...")
            monthly_xirr = compute_monthly_xirr(df, monthly_investment, value_col)
            monthly_xirr["year"] = monthly_xirr["date"].dt.year
            monthly_xirr["month"] = monthly_xirr["date"].dt.month
            years = sorted(monthly_xirr["year"].unique())

            html_parts.append(f"<h2>{label} — {mode}</h2>")
            html_parts.append(f"<h3>{subtitle}</h3>")
            html_parts.append("<table>")
            html_parts.append("<tr><th>Year</th>")
            for m in MONTH_NAMES:
                html_parts.append(f"<th>{m}</th>")
            html_parts.append("</tr>")

            for year in years:
                html_parts.append("<tr>")
                html_parts.append(f"<td class='year-col'>{year}</td>")
                for month in range(1, 13):
                    row = monthly_xirr[(monthly_xirr["year"] == year) & (monthly_xirr["month"] == month)]
                    if row.empty or pd.isna(row["xirr"].iloc[0]):
                        html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                    else:
                        val = row["xirr"].iloc[0]
                        bg = _xirr_heatmap_color(val)
                        html_parts.append(f"<td style='background:{bg};'>{val:+.1%}</td>")
                html_parts.append("</tr>")

            html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def generate_rolling_sip_html(
    return_series: list[tuple[str, pd.DataFrame]],
    output_path: Path,
    monthly_investment: float,
    tax_rate: float,
) -> None:
    """Generate rolling SIP returns heatmap: XIRR for every possible N-year SIP start date."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        f"<title>Rolling SIP Returns (₹{monthly_investment / 1000:.0f}K/month)</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 35px; margin-bottom: 4px; color: #333; }",
        "  h3 { margin-top: 5px; margin-bottom: 8px; color: #888; font-weight: normal; font-size: 14px; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 60px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .summary-row td { font-weight: 600; background: #f8f8f8; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        f"<h1>Rolling SIP Returns</h1>",
        f"<div class='subtitle'>₹{monthly_investment / 1000:.0f}K/month SIP — "
        f"cell shows the XIRR you'd earn if you started a SIP in that month and held for N years. "
        f"Pre-tax only.</div>",
    ]

    for label, returns_df in return_series:
        for window_years in [3, 5]:
            window_months = window_years * 12
            print(f"  Computing {window_years}Y rolling SIP for {label}...")

            dates = returns_df["date"]
            months = sorted(dates.dt.to_period("M").unique())
            all_xirrs = []  # for summary stats

            # Build month -> rows mapping for fast slicing
            results = {}  # (year, month) -> xirr
            for start_period in months:
                end_period = start_period + window_months
                # Slice returns for this window
                start_date = start_period.start_time
                end_date = end_period.start_time
                window_returns = returns_df[
                    (returns_df["date"] >= start_date) & (returns_df["date"] < end_date)
                ]
                # Need roughly the right number of months
                if len(window_returns) < window_months * 15:  # ~15 trading days minimum per month
                    continue

                sip_df = simulate_sip(window_returns.reset_index(drop=True), monthly_investment, tax_rate)
                xirr = compute_xirr(sip_df, monthly_investment, "portfolio_value")
                if xirr is not None:
                    results[(start_period.year, start_period.month)] = xirr
                    all_xirrs.append(xirr)

            if not results:
                continue

            years = sorted(set(y for y, m in results))

            html_parts.append(f"<h2>{label} — {window_years}-Year SIP</h2>")
            html_parts.append(f"<h3>XIRR if you started SIP in that month and held for {window_years} years</h3>")
            html_parts.append("<table>")
            html_parts.append("<tr><th>Start Year</th>")
            for m in MONTH_NAMES:
                html_parts.append(f"<th>{m}</th>")
            html_parts.append("</tr>")

            for year in years:
                html_parts.append("<tr>")
                html_parts.append(f"<td class='year-col'>{year}</td>")
                for month in range(1, 13):
                    val = results.get((year, month))
                    if val is None:
                        html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                    else:
                        bg = _xirr_heatmap_color(val)
                        html_parts.append(f"<td style='background:{bg};'>{val:+.1%}</td>")
                html_parts.append("</tr>")

            # Summary row
            if all_xirrs:
                arr = np.array(all_xirrs)
                html_parts.append("<tr class='summary-row'>")
                html_parts.append("<td class='year-col'>Summary</td>")
                html_parts.append(f"<td colspan='4'>Min: {arr.min():+.1%}</td>")
                html_parts.append(f"<td colspan='4'>Median: {np.median(arr):+.1%}</td>")
                html_parts.append(f"<td colspan='4'>Max: {arr.max():+.1%}</td>")
                html_parts.append("</tr>")

            html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def generate_installment_returns_html(
    return_series: list[tuple[str, pd.DataFrame]],
    output_path: Path,
    monthly_investment: float,
) -> None:
    """Generate heatmap showing the total return earned by each monthly SIP installment."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        f"<title>Per-Installment Returns (₹{monthly_investment / 1000:.0f}K/month)</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 35px; margin-bottom: 4px; color: #333; }",
        "  h3 { margin-top: 5px; margin-bottom: 8px; color: #888; font-weight: normal; font-size: 14px; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 60px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        f"<h1>Per-Installment SIP Returns</h1>",
        f"<div class='subtitle'>Total return earned by each ₹{monthly_investment / 1000:.0f}K installment "
        f"from its investment date to the latest date. Earlier installments earn more (invested longer).</div>",
    ]

    for label, returns_df in return_series:
        dates = returns_df["date"]
        daily_returns = returns_df["daily_return"].values
        sip_dates = _build_sip_dates(dates)

        # Compute cumulative return from each date to the end
        cum_from_end = np.ones(len(daily_returns))
        for i in range(len(daily_returns) - 2, -1, -1):
            cum_from_end[i] = cum_from_end[i + 1] * (1 + daily_returns[i + 1])

        # Map SIP dates to their return
        date_to_idx = {pd.Timestamp(dates.iloc[i]): i for i in range(len(dates))}
        installment_returns = {}
        for sip_date in sorted(sip_dates):
            idx = date_to_idx.get(sip_date)
            if idx is not None:
                ret = cum_from_end[idx] - 1
                installment_returns[(sip_date.year, sip_date.month)] = ret

        if not installment_returns:
            continue

        years = sorted(set(y for y, m in installment_returns))

        html_parts.append(f"<h2>{label}</h2>")
        html_parts.append(f"<h3>Total return of each monthly installment to present</h3>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Year</th>")
        for m in MONTH_NAMES:
            html_parts.append(f"<th>{m}</th>")
        html_parts.append("</tr>")

        for year in years:
            html_parts.append("<tr>")
            html_parts.append(f"<td class='year-col'>{year}</td>")
            for month in range(1, 13):
                val = installment_returns.get((year, month))
                if val is None:
                    html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                else:
                    bg = _heatmap_color(val)
                    html_parts.append(f"<td style='background:{bg};'>{val:+.1%}</td>")
            html_parts.append("</tr>")

        html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def generate_sip_vs_lumpsum_html(
    return_series: list[tuple[str, pd.DataFrame]],
    sip_results: dict[str, pd.DataFrame],
    output_path: Path,
    monthly_investment: float,
) -> None:
    """Generate SIP vs Lump Sum comparison report."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        "<title>SIP vs Lump Sum Comparison</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 35px; margin-bottom: 8px; color: #333; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 80px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .label-col { font-weight: 600; text-align: left; }",
        "  .better { color: #16a34a; font-weight: 600; }",
        "  .worse { color: #dc2626; }",
        "  .section { margin-top: 20px; }",
        "  h3 { margin-top: 25px; margin-bottom: 4px; color: #333; }",
        "  h4 { margin-top: 5px; margin-bottom: 8px; color: #888; font-weight: normal; font-size: 14px; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        "<h1>SIP vs Lump Sum Comparison</h1>",
        f"<div class='subtitle'>Compares ₹{monthly_investment / 1000:.0f}K/month SIP "
        f"against investing the same total amount on day one as a lump sum.</div>",
    ]

    for label, returns_df in return_series:
        if label not in sip_results:
            continue
        sip_df = sip_results[label]
        total_invested = sip_df["total_invested"].iloc[-1]

        # Simulate lump sum: invest total_invested on day 1
        daily_returns = returns_df["daily_return"].values
        dates = returns_df["date"].values
        lump_values = np.zeros(len(daily_returns))
        lump_values[0] = total_invested
        for i in range(1, len(daily_returns)):
            lump_values[i] = lump_values[i - 1] * (1 + daily_returns[i])

        sip_final = sip_df["portfolio_value"].iloc[-1]
        lump_final = lump_values[-1]

        # CAGR for lump sum
        days = (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[0])).days
        lump_cagr = (lump_final / total_invested) ** (365.25 / days) - 1 if days > 0 else 0

        sip_xirr = compute_xirr(sip_df, monthly_investment, "portfolio_value")

        # Max drawdown for both
        sip_peak = sip_df["portfolio_value"].cummax()
        sip_dd = ((sip_df["portfolio_value"] - sip_peak) / sip_peak).min()

        lump_peak = np.maximum.accumulate(lump_values)
        lump_dd = ((lump_values - lump_peak) / lump_peak).min()

        sip_wins = "better" if sip_final >= lump_final else "worse"
        lump_wins = "better" if lump_final >= sip_final else "worse"

        html_parts.append(f"<h2>{label}</h2>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Metric</th><th>SIP</th><th>Lump Sum</th></tr>")
        html_parts.append(f"<tr><td class='label-col'>Total Invested</td>"
                         f"<td>₹{total_invested:,.0f}</td><td>₹{total_invested:,.0f}</td></tr>")
        html_parts.append(f"<tr><td class='label-col'>Final Value</td>"
                         f"<td class='{sip_wins}'>₹{sip_final:,.0f}</td>"
                         f"<td class='{lump_wins}'>₹{lump_final:,.0f}</td></tr>")
        html_parts.append(f"<tr><td class='label-col'>Total Return</td>"
                         f"<td>{sip_final / total_invested - 1:+.1%}</td>"
                         f"<td>{lump_final / total_invested - 1:+.1%}</td></tr>")
        html_parts.append(f"<tr><td class='label-col'>Annualized (XIRR / CAGR)</td>"
                         f"<td>{sip_xirr:.1%}</td><td>{lump_cagr:.1%}</td></tr>" if sip_xirr else "")
        html_parts.append(f"<tr><td class='label-col'>Max Drawdown</td>"
                         f"<td>{sip_dd:.1%}</td><td>{lump_dd:.1%}</td></tr>")
        html_parts.append("</table>")

        # Monthly heatmap: SIP advantage (SIP value - lump sum value) as % of invested
        lump_df = pd.DataFrame({"date": pd.to_datetime(dates), "lump_value": lump_values})
        merged = pd.merge(sip_df[["date", "portfolio_value", "total_invested"]], lump_df, on="date")
        monthly = merged.set_index("date").resample("ME").last().reset_index()
        monthly["sip_advantage"] = (monthly["portfolio_value"] - monthly["lump_value"]) / monthly["total_invested"]
        monthly["year"] = monthly["date"].dt.year
        monthly["month"] = monthly["date"].dt.month

        years = sorted(monthly["year"].unique())
        html_parts.append(f"<h3>Monthly SIP Advantage</h3>")
        html_parts.append("<h4>SIP value minus lump sum value, as % of total invested. Green = SIP ahead.</h4>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Year</th>")
        for m in MONTH_NAMES:
            html_parts.append(f"<th>{m}</th>")
        html_parts.append("</tr>")

        for year in years:
            html_parts.append("<tr>")
            html_parts.append(f"<td class='year-col'>{year}</td>")
            for month in range(1, 13):
                row = monthly[(monthly["year"] == year) & (monthly["month"] == month)]
                if row.empty or pd.isna(row["sip_advantage"].iloc[0]):
                    html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                else:
                    val = row["sip_advantage"].iloc[0]
                    bg = _heatmap_color(val)
                    html_parts.append(f"<td style='background:{bg};'>{val:+.1%}</td>")
            html_parts.append("</tr>")

        html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def generate_underwater_html(
    sip_results: dict[str, pd.DataFrame],
    output_path: Path,
    monthly_investment: float,
) -> None:
    """Generate underwater analysis: when and how much the portfolio was below total invested."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        "<title>SIP Underwater Analysis</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 35px; margin-bottom: 8px; color: #333; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 80px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .label-col { font-weight: 600; text-align: left; background: #f0f0f0; }",
        "  .negative { color: #dc2626; }",
        "  .positive { color: #16a34a; }",
        "  h3 { margin-top: 25px; margin-bottom: 4px; color: #333; }",
        "  h4 { margin-top: 5px; margin-bottom: 8px; color: #888; font-weight: normal; font-size: 14px; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        "<h1>SIP Underwater Analysis</h1>",
        f"<div class='subtitle'>Shows periods when the SIP portfolio was worth less than the total amount invested. "
        f"'Underwater' = portfolio value &lt; total invested.</div>",
    ]

    # Summary table across all universes
    html_parts.append("<h2>Summary</h2>")
    html_parts.append("<table>")
    html_parts.append("<tr><th>Universe</th><th>Max Underwater %</th><th>Max Underwater ₹</th>"
                     "<th>Worst Date</th><th>Days Underwater</th><th>Longest Streak</th>"
                     "<th>Permanently Above Water</th></tr>")

    for label, df in sip_results.items():
        underwater_pct = df["portfolio_value"] / df["total_invested"] - 1
        underwater_mask = underwater_pct < 0

        total_days = underwater_mask.sum()
        worst_idx = underwater_pct.idxmin()
        worst_pct = underwater_pct.iloc[worst_idx]
        worst_amount = df["portfolio_value"].iloc[worst_idx] - df["total_invested"].iloc[worst_idx]
        worst_date = df["date"].iloc[worst_idx]

        # Longest consecutive streak
        streaks = []
        current_streak = 0
        for uw in underwater_mask:
            if uw:
                current_streak += 1
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 0
        if current_streak > 0:
            streaks.append(current_streak)
        longest_streak = max(streaks) if streaks else 0

        # Date permanently above water
        last_underwater_idx = underwater_mask[underwater_mask].index[-1] if total_days > 0 else None
        if last_underwater_idx is not None and last_underwater_idx < len(df) - 1:
            perm_above = df["date"].iloc[last_underwater_idx + 1].strftime("%Y-%m-%d")
        else:
            perm_above = "Still underwater" if total_days > 0 and underwater_mask.iloc[-1] else "Never underwater"

        html_parts.append(
            f"<tr><td class='label-col'>{label}</td>"
            f"<td class='negative'>{worst_pct:+.1%}</td>"
            f"<td class='negative'>₹{worst_amount:,.0f}</td>"
            f"<td>{worst_date.strftime('%Y-%m-%d')}</td>"
            f"<td>{total_days}</td>"
            f"<td>{longest_streak}</td>"
            f"<td>{perm_above}</td></tr>"
        )

    html_parts.append("</table>")

    # Monthly heatmap per universe
    for label, df in sip_results.items():
        monthly = df.set_index("date").resample("ME").last().reset_index()
        monthly["underwater_pct"] = monthly["portfolio_value"] / monthly["total_invested"] - 1
        monthly["year"] = monthly["date"].dt.year
        monthly["month"] = monthly["date"].dt.month
        years = sorted(monthly["year"].unique())

        html_parts.append(f"<h3>{label}</h3>")
        html_parts.append(f"<h4>Monthly gain/loss vs invested. Red = underwater, Green = above water.</h4>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Year</th>")
        for m in MONTH_NAMES:
            html_parts.append(f"<th>{m}</th>")
        html_parts.append("</tr>")

        for year in years:
            html_parts.append("<tr>")
            html_parts.append(f"<td class='year-col'>{year}</td>")
            for month in range(1, 13):
                row = monthly[(monthly["year"] == year) & (monthly["month"] == month)]
                if row.empty or pd.isna(row["underwater_pct"].iloc[0]):
                    html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                else:
                    val = row["underwater_pct"].iloc[0]
                    bg = _heatmap_color(val)
                    html_parts.append(f"<td style='background:{bg};'>{val:+.1%}</td>")
            html_parts.append("</tr>")

        html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def generate_cost_averaging_html(
    return_series: list[tuple[str, pd.DataFrame]],
    output_path: Path,
    monthly_investment: float,
) -> None:
    """Generate rupee cost averaging report: avg cost per unit vs current NAV."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        "<title>Rupee Cost Averaging Analysis</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 35px; margin-bottom: 8px; color: #333; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 80px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .label-col { font-weight: 600; text-align: left; background: #f0f0f0; }",
        "  .positive { color: #16a34a; font-weight: 600; }",
        "  h3 { margin-top: 25px; margin-bottom: 4px; color: #333; }",
        "  h4 { margin-top: 5px; margin-bottom: 8px; color: #888; font-weight: normal; font-size: 14px; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        "<h1>Rupee Cost Averaging Analysis</h1>",
        f"<div class='subtitle'>Portfolio equity curve normalized to NAV=100 at start. "
        f"Each ₹{monthly_investment / 1000:.0f}K buys units at that day's NAV. "
        f"Avg cost vs current NAV shows the cost averaging benefit.</div>",
    ]

    # Summary table
    html_parts.append("<h2>Summary</h2>")
    html_parts.append("<table>")
    html_parts.append("<tr><th>Universe</th><th>Current NAV</th><th>Avg Cost/Unit</th>"
                     "<th>Total Units</th><th>Cost Avg Benefit</th></tr>")

    for label, returns_df in return_series:
        dates = returns_df["date"]
        daily_returns = returns_df["daily_return"].values

        # Build NAV series (start at 100)
        nav = np.zeros(len(daily_returns))
        nav[0] = 100
        for i in range(1, len(daily_returns)):
            nav[i] = nav[i - 1] * (1 + daily_returns[i])

        sip_dates = _build_sip_dates(dates)
        date_to_idx = {pd.Timestamp(dates.iloc[i]): i for i in range(len(dates))}

        total_units = 0.0
        total_cost = 0.0
        for sip_date in sorted(sip_dates):
            idx = date_to_idx.get(sip_date)
            if idx is not None:
                units_bought = monthly_investment / nav[idx]
                total_units += units_bought
                total_cost += monthly_investment

        avg_cost = total_cost / total_units if total_units > 0 else 0
        current_nav = nav[-1]
        benefit = current_nav / avg_cost - 1 if avg_cost > 0 else 0

        html_parts.append(
            f"<tr><td class='label-col'>{label}</td>"
            f"<td>{current_nav:.2f}</td>"
            f"<td>{avg_cost:.2f}</td>"
            f"<td>{total_units:,.1f}</td>"
            f"<td class='positive'>{benefit:+.1%}</td></tr>"
        )

    html_parts.append("</table>")

    # NAV at SIP date heatmap
    for label, returns_df in return_series:
        dates = returns_df["date"]
        daily_returns = returns_df["daily_return"].values

        nav = np.zeros(len(daily_returns))
        nav[0] = 100
        for i in range(1, len(daily_returns)):
            nav[i] = nav[i - 1] * (1 + daily_returns[i])

        sip_dates = _build_sip_dates(dates)
        date_to_idx = {pd.Timestamp(dates.iloc[i]): i for i in range(len(dates))}

        nav_at_sip = {}
        for sip_date in sorted(sip_dates):
            idx = date_to_idx.get(sip_date)
            if idx is not None:
                nav_at_sip[(sip_date.year, sip_date.month)] = nav[idx]

        if not nav_at_sip:
            continue

        all_navs = list(nav_at_sip.values())
        nav_min, nav_max = min(all_navs), max(all_navs)
        nav_mid = (nav_min + nav_max) / 2

        years = sorted(set(y for y, m in nav_at_sip))

        html_parts.append(f"<h3>{label} — NAV at SIP Date</h3>")
        html_parts.append(f"<h4>Lower NAV = more units bought = better entry. "
                         f"Range: {nav_min:.0f} to {nav_max:.0f}</h4>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Year</th>")
        for m in MONTH_NAMES:
            html_parts.append(f"<th>{m}</th>")
        html_parts.append("</tr>")

        for year in years:
            html_parts.append("<tr>")
            html_parts.append(f"<td class='year-col'>{year}</td>")
            for month in range(1, 13):
                val = nav_at_sip.get((year, month))
                if val is None:
                    html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                else:
                    # Color: green for low NAV (good buy), red for high NAV
                    if nav_max > nav_min:
                        norm = (val - nav_min) / (nav_max - nav_min)  # 0=low, 1=high
                    else:
                        norm = 0.5
                    # Invert: low NAV = green, high NAV = red
                    intensity = norm
                    if intensity > 0.5:
                        i = (intensity - 0.5) * 2
                        r, g, b = 255, int(255 * (1 - i * 0.5)), int(255 * (1 - i * 0.5))
                    else:
                        i = (0.5 - intensity) * 2
                        r, g, b = int(255 * (1 - i * 0.4)), 255, int(255 * (1 - i * 0.4))
                    bg = f"rgb({r},{g},{b})"
                    html_parts.append(f"<td style='background:{bg};'>{val:.0f}</td>")
            html_parts.append("</tr>")

        html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def generate_capture_ratio_html(
    return_series: list[tuple[str, pd.DataFrame]],
    benchmark_returns: pd.DataFrame | None,
    output_path: Path,
) -> None:
    """Generate up/down capture ratio report vs benchmark."""
    if benchmark_returns is None:
        return

    html_parts = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        "<title>Up/Down Capture Ratio</title>",
        "<style>",
        "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
        "         margin: 30px; background: #fafafa; color: #333; }",
        "  h1 { margin-bottom: 5px; }",
        "  h2 { margin-top: 35px; margin-bottom: 8px; color: #333; }",
        "  .subtitle { color: #888; font-size: 14px; margin-bottom: 25px; }",
        "  table { border-collapse: collapse; margin-bottom: 20px; }",
        "  th, td { padding: 8px 14px; text-align: center; border: 1px solid #ddd;"
        "           font-size: 13px; min-width: 80px; }",
        "  th { background: #f0f0f0; font-weight: 600; }",
        "  .label-col { font-weight: 600; text-align: left; background: #f0f0f0; }",
        "  .good { color: #16a34a; font-weight: 600; }",
        "  h3 { margin-top: 25px; margin-bottom: 4px; color: #333; }",
        "  h4 { margin-top: 5px; margin-bottom: 8px; color: #888; font-weight: normal; font-size: 14px; }",
        "  .year-col { font-weight: 600; background: #f0f0f0; text-align: left; }",
        "  .na { color: #ccc; }",
        "</style>",
        "</head><body>",
        "<h1>Up/Down Capture Ratio</h1>",
        "<div class='subtitle'>Measures how much of the benchmark's monthly gains (up capture) "
        "and losses (down capture) the strategy captures. "
        "Ideal: high up capture, low down capture. Uses raw portfolio returns, not SIP values.</div>",
    ]

    # Compute benchmark monthly returns
    bench_monthly = benchmark_returns.set_index("date").resample("ME")["daily_return"].apply(
        lambda x: (1 + x).prod() - 1
    ).reset_index()
    bench_monthly.columns = ["date", "bench_return"]

    # Summary table
    html_parts.append("<h2>Summary</h2>")
    html_parts.append("<table>")
    html_parts.append("<tr><th>Universe</th><th>Up Capture</th><th>Down Capture</th>"
                     "<th>Capture Spread</th><th>Up Months</th><th>Down Months</th></tr>")

    universe_data = {}

    for label, returns_df in return_series:
        # Compute strategy monthly returns
        strat_monthly = returns_df.set_index("date").resample("ME")["daily_return"].apply(
            lambda x: (1 + x).prod() - 1
        ).reset_index()
        strat_monthly.columns = ["date", "strat_return"]

        merged = pd.merge(strat_monthly, bench_monthly, on="date", how="inner")
        up_months = merged[merged["bench_return"] > 0]
        down_months = merged[merged["bench_return"] < 0]

        up_capture = (up_months["strat_return"].mean() / up_months["bench_return"].mean()) if len(up_months) > 0 else np.nan
        down_capture = (down_months["strat_return"].mean() / down_months["bench_return"].mean()) if len(down_months) > 0 else np.nan
        spread = up_capture - down_capture if not (np.isnan(up_capture) or np.isnan(down_capture)) else np.nan

        universe_data[label] = merged

        html_parts.append(
            f"<tr><td class='label-col'>{label}</td>"
            f"<td>{up_capture:.0%}</td>"
            f"<td>{down_capture:.0%}</td>"
            f"<td class='good'>{spread:+.0%}</td>"
            f"<td>{len(up_months)}</td>"
            f"<td>{len(down_months)}</td></tr>"
        )

    html_parts.append("</table>")

    # Monthly excess return heatmap per universe
    for label, merged in universe_data.items():
        merged = merged.copy()
        merged["excess"] = merged["strat_return"] - merged["bench_return"]
        merged["year"] = merged["date"].dt.year
        merged["month"] = merged["date"].dt.month
        years = sorted(merged["year"].unique())

        html_parts.append(f"<h3>{label} — Monthly Excess Return vs Benchmark</h3>")
        html_parts.append(f"<h4>Strategy return minus benchmark return. Green = outperform.</h4>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>Year</th>")
        for m in MONTH_NAMES:
            html_parts.append(f"<th>{m}</th>")
        html_parts.append("</tr>")

        for year in years:
            html_parts.append("<tr>")
            html_parts.append(f"<td class='year-col'>{year}</td>")
            for month in range(1, 13):
                row = merged[(merged["year"] == year) & (merged["month"] == month)]
                if row.empty:
                    html_parts.append("<td class='na' style='background:#f5f5f5;'>—</td>")
                else:
                    val = row["excess"].iloc[0]
                    # Scale for ±20% range
                    clamped = max(-0.20, min(0.20, val))
                    if clamped < 0:
                        i = min(abs(clamped) / 0.20, 1.0)
                        r, g, b = 255, int(255 * (1 - i * 0.6)), int(255 * (1 - i * 0.6))
                    else:
                        i = min(clamped / 0.20, 1.0)
                        r, g, b = int(255 * (1 - i * 0.55)), 255, int(255 * (1 - i * 0.55))
                    bg = f"rgb({r},{g},{b})"
                    html_parts.append(f"<td style='background:{bg};'>{val:+.1%}</td>")
            html_parts.append("</tr>")

        html_parts.append("</table>")

    html_parts.append("</body></html>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(html_parts))


def print_summary(
    sip_results: dict[str, pd.DataFrame],
    monthly_investment: float,
) -> None:
    """Print summary table with pre-tax and post-tax values, gains, and XIRR."""
    print(f"\n{'=' * 115}")
    print(f"  SIP SUMMARY (₹{monthly_investment / 1000:.0f}K/month on 15th)")
    print(f"{'=' * 115}\n")

    header = (
        f"{'Universe':<15} {'Invested':>14} "
        f"{'Pre-Tax Value':>14} {'Gain %':>8} {'XIRR':>7}  "
        f"{'Post-Tax Value':>15} {'Gain %':>8} {'XIRR':>7}"
    )
    print(header)
    print("-" * 115)

    for label, df in sip_results.items():
        invested = df["total_invested"].iloc[-1]
        pre_val = df["portfolio_value"].iloc[-1]
        post_val = df["post_tax_value"].iloc[-1]
        pre_gain = pre_val / invested - 1
        post_gain = post_val / invested - 1
        pre_xirr = compute_xirr(df, monthly_investment, "portfolio_value")
        post_xirr = compute_xirr(df, monthly_investment, "post_tax_value")
        pre_xirr_s = f"{pre_xirr:.1%}" if pre_xirr is not None else "N/A"
        post_xirr_s = f"{post_xirr:.1%}" if post_xirr is not None else "N/A"

        print(
            f"{label:<15} "
            f"₹{invested:>12,.0f} "
            f"₹{pre_val:>12,.0f} "
            f"{pre_gain:>7.1%} "
            f"{pre_xirr_s:>7}  "
            f"₹{post_val:>13,.0f} "
            f"{post_gain:>7.1%} "
            f"{post_xirr_s:>7}"
        )

    print(f"\n{'=' * 115}")


def main():
    parser = argparse.ArgumentParser(
        description="Simulate SIP into momentum portfolio strategy"
    )
    parser.add_argument(
        "--universe",
        choices=["nse500", "nifty100", "nifty250", "all"],
        default="all",
        help="Stock universe to analyze (default: all)",
    )
    parser.add_argument(
        "--monthly-investment",
        type=float,
        default=100000,
        help="Monthly SIP amount in rupees (default: 100000)",
    )
    parser.add_argument(
        "--tax-rate",
        type=float,
        default=0.25,
        help="Annual tax rate on FY gains (default: 0.25 = 25%%)",
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("data/benchmarks/nifty100.csv"),
        help="Benchmark CSV path (default: data/benchmarks/nifty100.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/sip_returns"),
        help="Directory to save outputs (default: reports/sip_returns/)",
    )

    args = parser.parse_args()

    # Collect daily return series: list of (label, returns_df)
    # portfolio_series = universes only (no benchmark) — used for analytics
    # return_series = universes + benchmark — used for SIP simulation
    portfolio_series = []

    universes = list(UNIVERSE_CONFIGS.keys()) if args.universe == "all" else [args.universe]
    for universe in universes:
        equity_path = find_latest_equity(universe)
        if equity_path is None:
            print(f"⚠ Skipping {UNIVERSE_CONFIGS[universe]['label']}: no equity file found")
            continue
        label = UNIVERSE_CONFIGS[universe]["label"]
        print(f"Loading {label} from {equity_path}")
        portfolio_series.append((label, load_daily_returns(equity_path, "portfolio_value")))

    if not portfolio_series:
        print("No equity data found. Nothing to do.")
        return 1

    return_series = list(portfolio_series)

    # Load benchmark
    bench_returns = None
    if args.benchmark.exists():
        print(f"Loading benchmark from {args.benchmark}")
        bench_returns = load_daily_returns(args.benchmark, "close")
        earliest = min(df["date"].iloc[0] for _, df in return_series)
        latest = max(df["date"].iloc[-1] for _, df in return_series)
        bench_returns = bench_returns[
            (bench_returns["date"] >= earliest) & (bench_returns["date"] <= latest)
        ].reset_index(drop=True)
        bench_returns.loc[bench_returns.index[0], "daily_return"] = 0
        return_series.append(("Benchmark", bench_returns))
    else:
        print(f"⚠ Benchmark file not found: {args.benchmark}")

    # Simulate SIP for each series
    sip_results: dict[str, pd.DataFrame] = {}
    for label, returns_df in return_series:
        sip_results[label] = simulate_sip(returns_df, args.monthly_investment, args.tax_rate)

    # Print summary
    print_summary(sip_results, args.monthly_investment)

    # Save outputs
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_dfs = []
    for label, df in sip_results.items():
        slug = label.lower().replace(" ", "_")
        renamed = df[["date", "portfolio_value", "post_tax_value", "total_invested", "gain_pct", "post_tax_gain_pct"]].rename(columns={
            "portfolio_value": f"{slug}_pretax",
            "post_tax_value": f"{slug}_posttax",
            "total_invested": f"{slug}_invested",
            "gain_pct": f"{slug}_pretax_gain",
            "post_tax_gain_pct": f"{slug}_posttax_gain",
        })
        csv_dfs.append(renamed)

    merged = csv_dfs[0]
    for extra in csv_dfs[1:]:
        merged = pd.merge(merged, extra, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)

    csv_path = args.output_dir / "sip_returns.csv"
    merged.to_csv(csv_path, index=False)
    print(f"\n✓ CSV saved to {csv_path}")

    # Chart
    chart_path = args.output_dir / "sip_returns.png"
    if generate_chart(sip_results, chart_path, args.monthly_investment):
        print(f"✓ Chart saved to {chart_path}")

    # Heatmap
    heatmap_path = args.output_dir / "sip_heatmap.html"
    generate_heatmap_html(sip_results, heatmap_path, args.monthly_investment, args.tax_rate)
    print(f"✓ Heatmap saved to {heatmap_path}")

    # XIRR heatmap (separate file)
    xirr_path = args.output_dir / "sip_xirr_heatmap.html"
    generate_xirr_heatmap_html(sip_results, xirr_path, args.monthly_investment, args.tax_rate)
    print(f"✓ XIRR heatmap saved to {xirr_path}")

    # Rolling SIP returns
    rolling_path = args.output_dir / "sip_rolling_returns.html"
    generate_rolling_sip_html(portfolio_series, rolling_path, args.monthly_investment, args.tax_rate)
    print(f"✓ Rolling SIP returns saved to {rolling_path}")

    # Per-installment returns
    installment_path = args.output_dir / "sip_installment_returns.html"
    generate_installment_returns_html(return_series, installment_path, args.monthly_investment)
    print(f"✓ Installment returns saved to {installment_path}")

    # SIP vs Lump Sum
    lumpsum_path = args.output_dir / "sip_vs_lumpsum.html"
    generate_sip_vs_lumpsum_html(return_series, sip_results, lumpsum_path, args.monthly_investment)
    print(f"✓ SIP vs Lump Sum saved to {lumpsum_path}")

    # Underwater analysis
    underwater_path = args.output_dir / "sip_underwater.html"
    generate_underwater_html(sip_results, underwater_path, args.monthly_investment)
    print(f"✓ Underwater analysis saved to {underwater_path}")

    # Rupee cost averaging
    cost_avg_path = args.output_dir / "sip_cost_averaging.html"
    generate_cost_averaging_html(return_series, cost_avg_path, args.monthly_investment)
    print(f"✓ Cost averaging saved to {cost_avg_path}")

    # Capture ratio
    capture_path = args.output_dir / "sip_capture_ratio.html"
    generate_capture_ratio_html(portfolio_series, bench_returns, capture_path)
    print(f"✓ Capture ratio saved to {capture_path}")

    return 0


if __name__ == "__main__":
    exit(main())
