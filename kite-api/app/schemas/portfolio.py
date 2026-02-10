"""
Portfolio-related schemas.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class PortfolioSummary(BaseModel):
    """Portfolio overview response."""
    total_value: float
    cash: float
    invested: float
    daily_pnl: float
    daily_pnl_pct: float
    total_return: float
    total_return_pct: float
    holdings_count: int
    as_of_date: date

    class Config:
        from_attributes = True


class HoldingResponse(BaseModel):
    """Individual holding in portfolio."""
    symbol: str
    shares: float
    avg_cost: float
    current_price: float
    notional: float
    pnl: float
    pnl_pct: float
    weight: float
    entry_date: Optional[date] = None
    holding_days: Optional[int] = None
    rank: Optional[int] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    class Config:
        from_attributes = True


class HoldingsSummary(BaseModel):
    """Summary statistics for holdings."""
    total_pnl: float
    winners: int
    losers: int


class HoldingsResponse(BaseModel):
    """Holdings list response."""
    holdings: List[HoldingResponse]
    summary: HoldingsSummary


class AllocationItem(BaseModel):
    """Single allocation item for charts."""
    name: str
    value: float
    percentage: float
