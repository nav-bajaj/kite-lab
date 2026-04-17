"""
Trade-related schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import date


class MatchedBuy(BaseModel):
    """Opening BUY leg that a SELL closes (FIFO-matched), with realized P&L."""
    buy_trade_id: int
    entry_date: date
    entry_price: float        # effective (net of slippage) per-share buy price
    shares_matched: float
    holding_days: int
    realized_pnl: float       # net of slippage on both legs
    realized_pnl_pct: float


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
    matches: Optional[List[MatchedBuy]] = None  # populated for SELL rows only

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
    # Realized P&L stats (from trade_matches)
    realized_pnl_total: Optional[float] = None
    win_rate: Optional[float] = None
    avg_holding_days: Optional[float] = None
    best_trade_pct: Optional[float] = None
    worst_trade_pct: Optional[float] = None
