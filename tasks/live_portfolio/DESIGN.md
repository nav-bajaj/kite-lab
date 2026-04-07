# Open Positions Feature - Design Document

## Task #6: Data Model and API Contracts

### 1. Database Schema

#### Holdings Table

Stores actual portfolio holdings that can be synced from CSV or entered manually.

```sql
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(20) NOT NULL,       -- 'nse500', 'nifty100', 'nifty250'
    symbol VARCHAR(50) NOT NULL,          -- Trading symbol (e.g., 'INFY')
    instrument_token BIGINT,              -- Zerodha instrument token for API calls
    qty INTEGER NOT NULL,                 -- Number of shares held
    avg_price NUMERIC(18, 4) NOT NULL,    -- Average purchase price
    entry_date DATE,                      -- Date of entry (for reference)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(universe, symbol)              -- One entry per symbol per universe
);

CREATE INDEX ix_holdings_universe ON holdings(universe);
CREATE INDEX ix_holdings_symbol ON holdings(symbol);
```

### 2. Pydantic Schemas

#### Request Schemas

```python
class HoldingSyncRequest(BaseModel):
    """Request to sync holdings from CSV data."""
    universe: Literal["nse500", "nifty100", "nifty250"]
    holdings: List[HoldingInput]

class HoldingInput(BaseModel):
    """Single holding input."""
    symbol: str
    qty: int
    avg_price: float
    entry_date: Optional[date] = None
```

#### Response Schemas

```python
class LiveQuote(BaseModel):
    """Live price data from Zerodha API."""
    symbol: str
    instrument_token: int
    ltp: float                    # Last Traded Price
    open: float                   # Day's open price
    high: float                   # Day's high
    low: float                    # Day's low
    close: float                  # Previous close
    change: float                 # Day change in price (ltp - close)
    change_pct: float             # Day change percentage
    volume: int                   # Day's volume
    last_trade_time: Optional[datetime] = None

class Position(BaseModel):
    """Single position with live data and P&L."""
    symbol: str
    qty: int
    avg_price: float              # Entry/average price
    entry_date: Optional[date] = None

    # Live data
    ltp: float                    # Last Traded Price
    day_change: float             # Price change today
    day_change_pct: float         # Price change % today

    # Computed values
    invested: float               # qty * avg_price
    current_value: float          # qty * ltp
    total_pnl: float              # current_value - invested
    total_pnl_pct: float          # (total_pnl / invested) * 100
    day_pnl: float                # qty * day_change
    day_pnl_pct: float            # day_change_pct (same as price change %)

class MarketStatus(BaseModel):
    """Market open/closed status."""
    is_open: bool
    status: Literal["pre_open", "open", "closed"]
    message: str                  # e.g., "Market is open", "Market closed at 3:30 PM"
    next_open: Optional[datetime] = None
    last_updated: datetime

class PositionsSummary(BaseModel):
    """Portfolio-level summary."""
    total_invested: float
    total_current_value: float
    total_pnl: float
    total_pnl_pct: float
    day_pnl: float
    day_pnl_pct: float
    position_count: int
    winners: int                  # Positions with positive P&L
    losers: int                   # Positions with negative P&L

class PositionsResponse(BaseModel):
    """Full positions response with live data."""
    universe: str
    positions: List[Position]
    summary: PositionsSummary
    market_status: MarketStatus
    last_updated: datetime

class QuotesResponse(BaseModel):
    """Batch quotes response."""
    quotes: Dict[str, LiveQuote]  # symbol -> quote
    market_status: MarketStatus
    last_updated: datetime

class SSEMessage(BaseModel):
    """Server-Sent Event message format."""
    event: Literal["price_update", "market_status", "heartbeat", "error"]
    data: Union[PositionsResponse, MarketStatus, str]
    timestamp: datetime
```

### 3. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/positions` | Get positions with live prices and P&L |
| GET | `/api/positions/quotes` | Get live quotes only (no P&L calculation) |
| GET | `/api/positions/stream` | SSE stream for real-time updates |
| GET | `/api/positions/market-status` | Get current market status |
| POST | `/api/positions/sync` | Sync holdings from CSV data |
| GET | `/api/positions/holdings` | Get raw holdings (no live prices) |

#### Endpoint Details

**GET /api/positions**
```
Query Params:
  - universe: string (default: "nse500")

Response: PositionsResponse
```

**GET /api/positions/stream**
```
Query Params:
  - universe: string (default: "nse500")
  - interval: int (default: 3, min: 2, max: 10) - seconds between updates

Response: text/event-stream (SSE)
  - Sends PositionsResponse every {interval} seconds during market hours
  - Sends heartbeat every 30 seconds
  - Sends market_status event on market open/close transitions
```

**POST /api/positions/sync**
```
Body: HoldingSyncRequest

Response: {
  "success": true,
  "synced_count": 24,
  "universe": "nse500"
}
```

### 4. Real-Time Approach: Server-Sent Events (SSE)

**Why SSE over WebSocket:**
1. **Simpler implementation** - One-way server-to-client, no bidirectional complexity
2. **Auto-reconnect** - Built into EventSource API
3. **HTTP-compatible** - Works through proxies, load balancers
4. **Sufficient for use case** - We only need server → client price updates

**SSE Implementation Strategy:**

```python
@router.get("/stream")
async def positions_stream(
    universe: UniverseId = Query(default="nse500"),
    interval: int = Query(default=3, ge=2, le=10),
):
    """SSE endpoint for real-time position updates."""

    async def event_generator():
        while True:
            market_status = get_market_status()

            if market_status.is_open:
                # Fetch live prices and compute positions
                positions = await get_positions_with_live_prices(universe)
                yield {
                    "event": "price_update",
                    "data": positions.model_dump_json()
                }
                await asyncio.sleep(interval)
            else:
                # Send market closed status
                yield {
                    "event": "market_status",
                    "data": market_status.model_dump_json()
                }
                # Wait longer when market is closed
                await asyncio.sleep(60)

            # Heartbeat every 30 seconds
            if should_send_heartbeat():
                yield {"event": "heartbeat", "data": "ping"}

    return EventSourceResponse(event_generator())
```

### 5. Market Hours Detection

```python
import pytz
from datetime import datetime, time

IST = pytz.timezone("Asia/Kolkata")

MARKET_OPEN = time(9, 15)   # 9:15 AM IST
MARKET_CLOSE = time(15, 30)  # 3:30 PM IST

def get_market_status() -> MarketStatus:
    now = datetime.now(IST)
    current_time = now.time()
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    # Weekends
    if weekday >= 5:
        return MarketStatus(
            is_open=False,
            status="closed",
            message="Market closed (weekend)",
            next_open=get_next_trading_day_open(),
            last_updated=now
        )

    # Pre-market
    if current_time < MARKET_OPEN:
        return MarketStatus(
            is_open=False,
            status="pre_open",
            message=f"Market opens at 9:15 AM IST",
            next_open=now.replace(hour=9, minute=15, second=0),
            last_updated=now
        )

    # Market hours
    if MARKET_OPEN <= current_time <= MARKET_CLOSE:
        return MarketStatus(
            is_open=True,
            status="open",
            message="Market is open",
            last_updated=now
        )

    # After hours
    return MarketStatus(
        is_open=False,
        status="closed",
        message="Market closed at 3:30 PM IST",
        next_open=get_next_trading_day_open(),
        last_updated=now
    )
```

### 6. Zerodha API Integration

**Quote Fetching:**
```python
from kiteconnect import KiteConnect

def get_live_quotes(symbols: List[str]) -> Dict[str, LiveQuote]:
    """Fetch live quotes from Zerodha API."""
    kite = get_kite_client()

    # Build instrument list (NSE: prefix required)
    instruments = [f"NSE:{symbol}" for symbol in symbols]

    # Batch fetch (max 500 per call)
    quotes_data = kite.quote(instruments)

    result = {}
    for instrument, data in quotes_data.items():
        symbol = instrument.replace("NSE:", "")
        ohlc = data.get("ohlc", {})
        result[symbol] = LiveQuote(
            symbol=symbol,
            instrument_token=data.get("instrument_token"),
            ltp=data.get("last_price", 0),
            open=ohlc.get("open", 0),
            high=ohlc.get("high", 0),
            low=ohlc.get("low", 0),
            close=ohlc.get("close", 0),
            change=data.get("net_change", 0),
            change_pct=data.get("change", 0),  # Note: Zerodha returns % as "change"
            volume=data.get("volume", 0),
            last_trade_time=data.get("last_trade_time")
        )

    return result
```

**Rate Limiting:**
- Zerodha allows ~3 requests/second
- Cache quotes for 1-2 seconds to avoid rate limiting
- Use `cachetools.TTLCache` for simple in-memory caching

### 7. Caching Strategy

```python
from cachetools import TTLCache
import threading

# Thread-safe cache with 2-second TTL
_quotes_cache = TTLCache(maxsize=100, ttl=2)
_cache_lock = threading.Lock()

def get_cached_quotes(symbols: List[str], universe: str) -> Dict[str, LiveQuote]:
    """Get quotes with caching."""
    cache_key = f"{universe}:{','.join(sorted(symbols))}"

    with _cache_lock:
        if cache_key in _quotes_cache:
            return _quotes_cache[cache_key]

    # Cache miss - fetch from API
    quotes = get_live_quotes(symbols)

    with _cache_lock:
        _quotes_cache[cache_key] = quotes

    return quotes
```

### 8. Error Handling

```python
class PositionError(Exception):
    """Base exception for position errors."""
    pass

class TokenExpiredError(PositionError):
    """Zerodha access token expired."""
    pass

class MarketDataError(PositionError):
    """Failed to fetch market data."""
    pass

# In endpoints:
@router.get("")
async def get_positions(universe: UniverseId = Query(default="nse500")):
    try:
        return await positions_service.get_positions(universe)
    except TokenExpiredError:
        raise HTTPException(
            status_code=401,
            detail="Zerodha token expired. Please re-login."
        )
    except MarketDataError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch market data: {str(e)}"
        )
```

### 9. File Structure

```
kite-api/app/
├── models/
│   └── models.py          # Add Holding model
├── schemas/
│   └── positions.py       # New: Position schemas
├── services/
│   ├── positions_service.py   # New: Position business logic
│   ├── quotes_service.py      # New: Zerodha quote fetching
│   └── market_service.py      # New: Market status
└── api/
    └── positions.py       # New: Position endpoints
```

### 10. Dependencies

Add to `requirements.txt`:
```
sse-starlette>=1.6.5      # SSE support for FastAPI
cachetools>=5.3.0          # TTL cache for quotes
pytz>=2023.3               # Timezone handling
```

---

## Implementation Order

1. **Create Holdings model** (Task #7)
   - Add SQLAlchemy model
   - Create Alembic migration
   - Add sync endpoint

2. **Create quotes service** (Task #8)
   - Zerodha API integration
   - Caching layer
   - Market status detection

3. **Create positions endpoint** (Task #9)
   - Combine holdings + quotes
   - P&L calculations
   - Response formatting

4. **Add SSE streaming** (Task #10)
   - EventSource endpoint
   - Heartbeat mechanism
   - Market hours logic

---

*Design approved for implementation.*
