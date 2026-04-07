# Live Portfolio (Open Positions) Feature

## Overview

Add a new "Open Positions" tab to the dashboard that shows the current portfolio with live prices during market hours. Updates in real-time using Zerodha API.

## Features

- Display current holdings with entry prices
- Live price updates during market hours (9:15 AM - 3:30 PM IST)
- Real-time P&L calculations (total and day)
- Market status indicator
- Support for all universes (NSE 500, Nifty 100, Nifty 250)

## Columns

| Column | Description |
|--------|-------------|
| Symbol | Stock symbol |
| Qty | Number of shares held |
| Entry Price | Average purchase price |
| LTP | Last Traded Price (live) |
| Invested | Qty × Entry Price |
| Current Value | Qty × LTP |
| Total P&L (₹) | Current Value - Invested |
| Total P&L (%) | (Total P&L / Invested) × 100 |
| Day P&L (₹) | Qty × Day Change |
| Day P&L (%) | Day Change % |

---

## Tasks

### Phase 1: Design

#### Task #6: Design Open Positions data model and API contracts
**Status:** ✅ Complete

Define the data structures and API contracts:
- Holdings data structure (symbol, qty, avg_price, entry_date)
- Live quote data structure (ltp, day_open, day_high, day_low, day_change, day_change_pct)
- Combined position response (holdings + live data + computed P&L)
- Market status endpoint structure
- Determine real-time approach: SSE vs WebSocket vs polling

---

### Phase 2: Backend

#### Task #7: Create holdings database table and service
**Status:** ✅ Complete
**Blocked by:** #6

Create database table and service to store actual holdings:
- Create Alembic migration for holdings table (symbol, qty, avg_price, entry_date, universe)
- Create HoldingsService to CRUD holdings
- Create endpoint to sync holdings from CSV or manual entry
- Ensure holdings can be tracked per universe (nse500, nifty100, nifty250)

#### Task #8: Create live quotes endpoint using Zerodha API
**Status:** ✅ Complete
**Blocked by:** #6

Create endpoint to fetch live quotes from Zerodha:
- GET /api/positions/quotes - fetch LTP for all holdings
- Use kite.quote() or kite.ltp() for batch price fetch
- Include market hours detection (9:15 AM - 3:30 PM IST)
- Handle token expiry gracefully
- Cache quotes briefly (1-2 seconds) to avoid rate limiting

#### Task #9: Create positions endpoint with P&L calculations
**Status:** ✅ Complete
**Blocked by:** #7, #8

Create main positions endpoint:
- GET /api/positions - returns holdings with live prices and P&L
- Compute: invested_value = qty * avg_price
- Compute: current_value = qty * ltp
- Compute: total_pnl = current_value - invested_value
- Compute: total_pnl_pct = (total_pnl / invested_value) * 100
- Compute: day_pnl = qty * day_change
- Compute: day_pnl_pct = day_change_pct
- Include market_status (open/closed) in response
- Include last_updated timestamp

#### Task #10: Implement SSE endpoint for real-time price streaming
**Status:** ✅ Complete
**Blocked by:** #9

Create Server-Sent Events endpoint for live updates:
- GET /api/positions/stream - SSE endpoint for real-time prices
- Poll Zerodha API every 2-3 seconds during market hours
- Send price updates to connected clients
- Include heartbeat to keep connection alive
- Stop streaming outside market hours (send market_closed event)

---

### Phase 3: Frontend

#### Task #11: Create Open Positions page and routing
**Status:** ✅ Complete
**Blocked by:** #6

Create new page for Open Positions:
- Create app/(dashboard)/positions/page.tsx
- Add "Open Positions" to navigation sidebar
- Set up basic page layout with header and market status indicator
- Add universe selector (nse500, nifty100, nifty250)

#### Task #12: Build positions table component
**Status:** ✅ Complete
**Blocked by:** #9, #11

Create table component to display positions:
- Columns: Symbol, Qty, Entry Price, LTP, Invested, Current Value, Total P&L (₹), Total P&L (%), Day P&L (₹), Day P&L (%)
- Color coding: green for profit, red for loss
- Sort by any column
- Show totals row at bottom (total invested, total current, total P&L)
- Responsive design for mobile

#### Task #13: Implement real-time price updates on frontend
**Status:** ✅ Complete
**Blocked by:** #10, #12

Connect to SSE stream for live updates:
- Create usePositionsStream hook using EventSource
- Update prices in real-time without page refresh
- Show "live" indicator when streaming
- Fallback to polling if SSE fails
- Handle reconnection on disconnect
- Show last updated timestamp

#### Task #14: Add market status indicator and summary cards
**Status:** ✅ Complete
**Blocked by:** #12

Add status indicators and summary:
- Market status badge (Open/Closed with color)
- Summary cards showing:
  - Total Invested Value
  - Current Portfolio Value
  - Total P&L (₹ and %)
  - Day P&L (₹ and %)
- Last updated timestamp with auto-refresh indicator

---

### Phase 4: QA

#### Task #15: Test and polish Open Positions feature
**Status:** ✅ Complete
**Blocked by:** #13, #14

Final testing and polish:
- Test during market hours with live data
- Test outside market hours (should show last close prices)
- Test token expiry handling
- Test with different universes
- Add loading states and error handling
- Ensure mobile responsiveness
- Performance optimization (memo, virtualization if needed)

---

## Dependency Graph

```
#6  Design data model & API contracts
     │
     ├──► #7  Create holdings DB table & service
     │         │
     ├──► #8  Create live quotes endpoint (Zerodha)
     │         │
     │         └──► #9  Create positions endpoint with P&L
     │                   │
     │                   ├──► #10 Implement SSE streaming
     │                   │         │
     ├──► #11 Create Open Positions page        │
     │         │                                │
     │         └──► #12 Build positions table ◄─┘
     │                   │
     │                   ├──► #13 Real-time updates (frontend)
     │                   │
     │                   └──► #14 Market status & summary cards
     │                             │
     └─────────────────────────────┴──► #15 Test & polish
```

---

## API Endpoints (Planned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/positions | Get positions with live prices and P&L |
| GET | /api/positions/quotes | Get live quotes only |
| GET | /api/positions/stream | SSE stream for real-time updates |
| GET | /api/positions/market-status | Get market open/closed status |
| POST | /api/positions/sync | Sync holdings from CSV |

---

## Tech Stack

**Backend:**
- FastAPI (existing)
- PostgreSQL (existing)
- Zerodha KiteConnect API
- Server-Sent Events (SSE)

**Frontend:**
- Next.js 14 (existing)
- React with TypeScript
- Tailwind CSS + shadcn/ui (existing)
- EventSource API for SSE

---

## Setup Instructions

### 1. Run Database Migration

```bash
cd kite-api
alembic upgrade head
```

### 2. Install New Dependencies

```bash
pip install sse-starlette cachetools
```

### 3. Restart API Server

```bash
uvicorn app.main:app --reload
```

### 4. Sync Positions

Navigate to `/positions` in the dashboard and click "Sync from CSV" to load your portfolio holdings.

---

## Behavior

**During Market Hours (9:15 AM - 3:30 PM IST):**
- Live prices fetched from Zerodha API every 3 seconds via SSE
- Real-time P&L calculations
- "Market Open" badge with live indicator

**Outside Market Hours:**
- Shows last closing prices from local CSV files
- Day change calculated relative to previous trading day's close
- "Market Closed" badge
- Prices still visible, not empty

**Pre-Market:**
- Shows previous day's closing prices
- "Pre-Market" badge
