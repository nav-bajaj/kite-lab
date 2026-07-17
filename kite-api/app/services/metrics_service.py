"""
Metrics Service - Calculate and retrieve performance metrics from database.
"""
from datetime import date, datetime
from functools import lru_cache
from typing import Optional, List
from collections import defaultdict

import numpy as np
import pandas as pd
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import get_session_local
from app.models.models import Metric, EquityCurve
from app.insights._paths import indices_dir
from app.insights._freshness import file_signature

# Benchmark index per portfolio: NSE-500-based strategies compare vs Nifty 500,
# the Nifty-250 strategy vs Nifty 250 (LargeMidcap 250). (universe -> (csv, label))
_BENCHMARK: dict[str, tuple[str, str]] = {
    "l6_v2": ("NIFTY_500.csv", "Nifty 500"),
    "combo_defensive": ("NIFTY_500.csv", "Nifty 500"),
    "tl25_v3": ("NIFTY_500.csv", "Nifty 500"),
    "nse500": ("NIFTY_500.csv", "Nifty 500"),
    "om25_v3": ("NIFTY_LARGEMID250.csv", "Nifty 250"),
    "nifty250": ("NIFTY_LARGEMID250.csv", "Nifty 250"),
    "nifty100": ("NIFTY_100.csv", "Nifty 100"),
}
_DEFAULT_BENCHMARK = ("NIFTY_500.csv", "Nifty 500")


@lru_cache(maxsize=8)
def _index_close_map_cached(filename: str, signature: float) -> dict[str, float]:
    df = pd.read_csv(indices_dir() / filename, parse_dates=["date"])
    s = df.set_index("date")["close"].dropna()
    return {d.strftime("%Y-%m-%d"): float(v) for d, v in s.items()}


def _index_close_map(filename: str) -> dict[str, float]:
    return _index_close_map_cached(filename, file_signature(indices_dir() / filename))


def get_metrics(universe: str = "nse500") -> dict:
    """
    Get comprehensive performance metrics for a universe.

    Returns metrics from database plus calculated ratios.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Get latest metrics record
        metric = db.query(Metric).filter(
            Metric.universe == universe
        ).order_by(desc(Metric.computed_date)).first()

        if not metric:
            return {"error": f"No metrics found for {universe}"}

        # Get equity curve for additional calculations
        equity_data = db.query(EquityCurve).filter(
            EquityCurve.universe == universe
        ).order_by(EquityCurve.date).all()

        # Calculate volatility and ratios
        volatility = calculate_volatility(equity_data)
        cagr_pct = float(metric.cagr) * 100 if metric.cagr else 0
        max_dd_pct = float(metric.max_drawdown) * 100 if metric.max_drawdown else 0

        # Use stored ratios if available, otherwise calculate
        sharpe = float(metric.sharpe_ratio) if metric.sharpe_ratio else calculate_sharpe(cagr_pct, volatility)
        sortino = float(metric.sortino_ratio) if metric.sortino_ratio else calculate_sortino(equity_data, cagr_pct)
        calmar = float(metric.calmar_ratio) if metric.calmar_ratio else (
            round(cagr_pct / abs(max_dd_pct), 2) if max_dd_pct != 0 else None
        )

        # Calculate MTD and YTD from equity curve
        mtd = calculate_mtd(equity_data)
        ytd = calculate_ytd(equity_data)

        return {
            "universe": universe,
            "period": {
                "start": str(metric.start_date) if metric.start_date else None,
                "end": str(metric.end_date) if metric.end_date else None,
                "days": (metric.end_date - metric.start_date).days if metric.start_date and metric.end_date else 0
            },
            "returns": {
                "total_return": round(float(metric.total_return) * 100, 2) if metric.total_return else 0,
                "cagr": round(cagr_pct, 2),
                "mtd": mtd,
                "ytd": ytd
            },
            "risk": {
                "max_drawdown": round(max_dd_pct, 2),
                "max_dd_duration": metric.max_drawdown_duration,
                "volatility": volatility,
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "calmar_ratio": calmar
            },
            "activity": {
                "total_trades": metric.trades_total or 0,
                "avg_turnover": round(float(metric.avg_turnover_pct) * 100, 2) if metric.avg_turnover_pct else 0,
                "annualized_turnover": round(float(metric.annualized_turnover) * 100, 2) if metric.annualized_turnover else 0,
                "avg_holding_days": round(float(metric.avg_holding_days), 1) if metric.avg_holding_days else 0,
                "hit_rate": round(float(metric.hit_rate) * 100, 2) if metric.hit_rate else 0
            }
        }
    finally:
        db.close()


def get_equity_curve(
    universe: str = "nse500",
    start: Optional[date] = None,
    end: Optional[date] = None
) -> dict:
    """
    Get equity curve data for charting.

    Returns daily portfolio value, benchmark, and drawdown.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        query = db.query(EquityCurve).filter(
            EquityCurve.universe == universe
        )

        if start:
            query = query.filter(EquityCurve.date >= start)
        if end:
            query = query.filter(EquityCurve.date <= end)

        query = query.order_by(EquityCurve.date)
        records = query.all()

        if not records:
            return {"data": [], "count": 0, "error": f"No equity curve data for {universe}"}

        # Benchmark: the portfolio's matched index (Nifty 500 / 250 / 100),
        # overriding the stored value so it reflects the right size tier. The
        # frontend rebases it to the portfolio's ₹10L starting base.
        bench_file, bench_label = _BENCHMARK.get(universe, _DEFAULT_BENCHMARK)
        try:
            closes = _index_close_map(bench_file)
        except (FileNotFoundError, KeyError, OSError):
            closes = {}

        data = []
        for r in records:
            date_str = str(r.date)
            data.append({
                "date": date_str,
                "portfolio_value": float(r.portfolio_value),
                "benchmark_value": closes.get(date_str),
                "drawdown": round(float(r.drawdown) * 100, 2) if r.drawdown else 0
            })

        return {
            "universe": universe,
            "benchmark_label": bench_label,
            "data": data,
            "count": len(data)
        }
    finally:
        db.close()


def get_monthly_returns(universe: str = "nse500") -> dict:
    """
    Calculate monthly returns matrix for heatmap display.

    Returns years and monthly return percentages.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        records = db.query(EquityCurve).filter(
            EquityCurve.universe == universe
        ).order_by(EquityCurve.date).all()

        if not records:
            return {"years": [], "data": [], "error": f"No data for {universe}"}

        # Group by year-month and get first/last values
        monthly = defaultdict(lambda: defaultdict(dict))

        for record in records:
            year = record.date.year
            month = record.date.month
            value = float(record.portfolio_value)

            if "first" not in monthly[year][month]:
                monthly[year][month]["first"] = value
            monthly[year][month]["last"] = value

        # Calculate returns for each month
        years = sorted(monthly.keys())
        data = []

        for year in years:
            months = [None] * 12  # Jan=0, Dec=11

            for month in range(1, 13):
                if month in monthly[year]:
                    first_val = monthly[year][month]["first"]
                    last_val = monthly[year][month]["last"]
                    if first_val > 0:
                        ret = ((last_val - first_val) / first_val) * 100
                        months[month - 1] = round(ret, 2)

            # Calculate YTD
            ytd = calculate_ytd_for_year(records, year)

            data.append({
                "year": year,
                "months": months,
                "ytd": ytd
            })

        return {
            "universe": universe,
            "years": years,
            "data": data
        }
    finally:
        db.close()


# Helper functions

def calculate_volatility(equity_data: List[EquityCurve], annualize: bool = True) -> float:
    """Calculate annualized volatility from equity curve."""
    if len(equity_data) < 2:
        return 0

    values = [float(e.portfolio_value) for e in equity_data]
    returns = np.diff(values) / values[:-1]
    vol = np.std(returns)

    if annualize:
        vol *= np.sqrt(252)  # Trading days per year

    return round(vol * 100, 2)


def calculate_sharpe(cagr_pct: float, volatility: float, risk_free: float = 5.0) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        cagr_pct: CAGR as percentage (e.g., 56.3 for 56.3%)
        volatility: Annualized volatility as percentage (e.g., 25.0 for 25%)
        risk_free: Risk-free rate as percentage (default 5%)
    """
    if volatility == 0:
        return 0
    return round((cagr_pct - risk_free) / volatility, 2)


def calculate_sortino(equity_data: List[EquityCurve], cagr_pct: float, risk_free: float = 5.0) -> float:
    """Calculate Sortino ratio using downside deviation."""
    if len(equity_data) < 2:
        return 0

    values = [float(e.portfolio_value) for e in equity_data]
    returns = np.diff(values) / values[:-1]

    # Only negative returns for downside deviation
    negative_returns = returns[returns < 0]
    if len(negative_returns) == 0:
        return 0

    downside_dev = np.std(negative_returns) * np.sqrt(252) * 100  # As percentage
    if downside_dev == 0:
        return 0

    return round((cagr_pct - risk_free) / downside_dev, 2)


def calculate_mtd(equity_data: List[EquityCurve]) -> float:
    """Calculate month-to-date return."""
    if not equity_data:
        return 0

    today = date.today()
    current_month_start = date(today.year, today.month, 1)

    # Find first value of current month
    month_start_value = None
    latest_value = None

    for record in equity_data:
        if record.date >= current_month_start:
            if month_start_value is None:
                month_start_value = float(record.portfolio_value)
            latest_value = float(record.portfolio_value)

    if month_start_value is None or latest_value is None or month_start_value == 0:
        return 0

    return round(((latest_value - month_start_value) / month_start_value) * 100, 2)


def calculate_ytd(equity_data: List[EquityCurve]) -> float:
    """Calculate year-to-date return."""
    if not equity_data:
        return 0

    today = date.today()
    year_start = date(today.year, 1, 1)

    # Find first value of current year
    year_start_value = None
    latest_value = None

    for record in equity_data:
        if record.date >= year_start:
            if year_start_value is None:
                year_start_value = float(record.portfolio_value)
            latest_value = float(record.portfolio_value)

    if year_start_value is None or latest_value is None or year_start_value == 0:
        return 0

    return round(((latest_value - year_start_value) / year_start_value) * 100, 2)


def calculate_ytd_for_year(equity_data: List[EquityCurve], year: int) -> float:
    """Calculate YTD return for a specific year."""
    year_records = [r for r in equity_data if r.date.year == year]

    if not year_records:
        return 0

    first_value = float(year_records[0].portfolio_value)
    last_value = float(year_records[-1].portfolio_value)

    if first_value == 0:
        return 0

    return round(((last_value - first_value) / first_value) * 100, 2)
