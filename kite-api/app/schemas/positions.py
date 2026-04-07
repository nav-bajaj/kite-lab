"""
Schemas for Open Positions feature.

Provides live portfolio tracking with real-time prices from Zerodha API.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Literal, Union
from datetime import date, datetime


# --- Request Schemas ---

class OpenPositionInput(BaseModel):
    """Single position input for sync."""
    symbol: str
    qty: int
    avg_price: float
    entry_date: Optional[date] = None


class PositionsSyncRequest(BaseModel):
    """Request to sync open positions from CSV or manual entry."""
    universe: Literal["nse500", "nifty100", "nifty250"]
    positions: List[OpenPositionInput]


# --- Live Quote Schema ---

class LiveQuote(BaseModel):
    """Live price data from Zerodha API."""
    symbol: str
    instrument_token: Optional[int] = None
    ltp: float                        # Last Traded Price
    open: float                       # Day's open price
    high: float                       # Day's high
    low: float                        # Day's low
    close: float                      # Previous close
    change: float                     # Day change in price (ltp - close)
    change_pct: float                 # Day change percentage
    volume: Optional[int] = None      # Day's volume
    last_trade_time: Optional[datetime] = None


# --- Position Schema ---

class Position(BaseModel):
    """Single position with live data and P&L calculations."""
    symbol: str
    qty: int
    avg_price: float                  # Entry/average price
    entry_date: Optional[date] = None

    # Live data
    ltp: float                        # Last Traded Price
    day_change: float                 # Price change today
    day_change_pct: float             # Price change % today

    # Computed values
    invested: float                   # qty * avg_price
    current_value: float              # qty * ltp
    total_pnl: float                  # current_value - invested
    total_pnl_pct: float              # (total_pnl / invested) * 100
    day_pnl: float                    # qty * day_change
    day_pnl_pct: float                # Same as day_change_pct

    class Config:
        from_attributes = True


# --- Market Status Schema ---

class MarketStatus(BaseModel):
    """Market open/closed status."""
    is_open: bool
    status: Literal["pre_open", "open", "closed"]
    message: str                      # e.g., "Market is open"
    next_open: Optional[datetime] = None
    last_updated: datetime


# --- Summary Schema ---

class PositionsSummary(BaseModel):
    """Portfolio-level summary statistics."""
    total_invested: float
    total_current_value: float
    total_pnl: float
    total_pnl_pct: float
    day_pnl: float
    day_pnl_pct: float
    position_count: int
    winners: int                      # Positions with positive total P&L
    losers: int                       # Positions with negative total P&L


# --- Response Schemas ---

class PositionsResponse(BaseModel):
    """Full positions response with live data."""
    universe: str
    positions: List[Position]
    summary: PositionsSummary
    market_status: MarketStatus
    last_updated: datetime


class QuotesResponse(BaseModel):
    """Batch quotes response."""
    quotes: Dict[str, LiveQuote]      # symbol -> quote
    market_status: MarketStatus
    last_updated: datetime


class HoldingsOnlyResponse(BaseModel):
    """Raw holdings without live prices."""
    universe: str
    holdings: List[OpenPositionInput]
    count: int


class SyncResponse(BaseModel):
    """Response from sync operation."""
    success: bool
    synced_count: int
    universe: str
    message: str


# --- SSE Event Schema ---

class SSEMessage(BaseModel):
    """Server-Sent Event message format."""
    event: Literal["price_update", "market_status", "heartbeat", "error"]
    data: Union[PositionsResponse, MarketStatus, str, dict]
    timestamp: datetime
