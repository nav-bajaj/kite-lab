"""
Trade-related schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import date


class TradeResponse(BaseModel):
    """Individual trade record."""
    id: int
    date: date
    symbol: str
    side: Literal["BUY", "SELL"]
    shares: float
    price: float
    notional: float
    slippage: Optional[float] = None

    class Config:
        from_attributes = True


class TradesListResponse(BaseModel):
    """Paginated trades list."""
    trades: List[TradeResponse]
    total_count: int
    limit: int
    offset: int


class TradeSummary(BaseModel):
    """Trade statistics summary."""
    total_trades: int
    buys: int
    sells: int
    total_notional: float
    avg_trade_size: float
    hit_rate: Optional[float] = None
