"""
Performance metrics schemas.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class PeriodInfo(BaseModel):
    """Time period information."""
    start: date
    end: date
    days: int


class ReturnsMetrics(BaseModel):
    """Return-related metrics."""
    total_return: float
    cagr: float
    mtd: Optional[float] = None
    ytd: Optional[float] = None


class RiskMetrics(BaseModel):
    """Risk-related metrics."""
    max_drawdown: float
    max_dd_duration: Optional[int] = None
    volatility: float
    sharpe_ratio: float
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None


class ActivityMetrics(BaseModel):
    """Trading activity metrics."""
    total_trades: int
    avg_turnover: float
    annualized_turnover: float
    avg_holding_days: float
    hit_rate: float


class MetricsResponse(BaseModel):
    """Full metrics response."""
    period: PeriodInfo
    returns: ReturnsMetrics
    risk: RiskMetrics
    activity: ActivityMetrics


class EquityCurvePoint(BaseModel):
    """Single point on equity curve."""
    date: date
    portfolio_value: float
    benchmark_value: Optional[float] = None
    drawdown: Optional[float] = None


class MonthlyReturn(BaseModel):
    """Monthly return for a single year."""
    year: int
    months: List[Optional[float]]  # 12 elements, None if no data
    ytd: float


class MonthlyReturns(BaseModel):
    """Monthly returns matrix."""
    years: List[int]
    data: List[MonthlyReturn]
