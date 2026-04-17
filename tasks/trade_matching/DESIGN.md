# Trade Matching — Design Document

## 1. Matching Algorithm: FIFO Lots

Walk all trades for a universe in `(trade_date ASC, id ASC)` order. Maintain one
FIFO queue of "open lots" per symbol.

- On **BUY**: push a new lot `(buy_trade_id, remaining_shares, price, date)`
  onto the symbol's queue.
- On **SELL**: pop lots from the front until `sell_shares` is satisfied.
  - For each lot consumed (partially or fully), emit a `TradeMatch` row.
  - If a lot is only partially consumed, decrement `remaining_shares` on the
    lot and leave it at the front of the queue.
  - If `sell_shares` exceeds all open lots for the symbol, log a warning and
    emit a match with `shares_matched` capped at what was available. (Should
    not happen for the backtest; important guardrail for real-trading data.)

After the walk, any lot with `remaining_shares > 0` represents an **open
position** — no match is emitted.

**Why FIFO:** matches standard accounting practice, deterministic, handles both
the current 1-BUY→1-SELL pattern and future partial fills without code changes.

## 2. Database Schema

### New table: `trade_matches`

```sql
CREATE TABLE trade_matches (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(20) NOT NULL,
    buy_trade_id INTEGER NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    sell_trade_id INTEGER NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    shares_matched NUMERIC(18, 6) NOT NULL,
    entry_date DATE NOT NULL,
    exit_date DATE NOT NULL,
    entry_price NUMERIC(18, 6) NOT NULL,
    exit_price NUMERIC(18, 6) NOT NULL,
    holding_days INTEGER NOT NULL,
    realized_pnl NUMERIC(18, 4) NOT NULL,
    realized_pnl_pct NUMERIC(12, 6) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trade_matches_universe        ON trade_matches(universe);
CREATE INDEX idx_trade_matches_sell_trade_id   ON trade_matches(sell_trade_id);
CREATE INDEX idx_trade_matches_buy_trade_id    ON trade_matches(buy_trade_id);
CREATE INDEX idx_trade_matches_universe_symbol ON trade_matches(universe, symbol);
```

**Rationale for separate table (vs. columns on `trades`):**
- A single SELL can match multiple BUYs (partial fills) — 1:N needs a join table.
- Keeps the `trades` table clean: no mostly-null columns on BUY rows.
- Easy to wipe and rebuild idempotently (`DELETE WHERE universe = ?` then insert).

### SQLAlchemy model (sketch)

```python
class TradeMatch(Base):
    __tablename__ = "trade_matches"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, index=True)
    buy_trade_id = Column(Integer, ForeignKey("trades.id", ondelete="CASCADE"),
                          nullable=False)
    sell_trade_id = Column(Integer, ForeignKey("trades.id", ondelete="CASCADE"),
                           nullable=False)
    symbol = Column(String(50), nullable=False)
    shares_matched = Column(Numeric(18, 6), nullable=False)
    entry_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=False)
    entry_price = Column(Numeric(18, 6), nullable=False)
    exit_price = Column(Numeric(18, 6), nullable=False)
    holding_days = Column(Integer, nullable=False)
    realized_pnl = Column(Numeric(18, 4), nullable=False)
    realized_pnl_pct = Column(Numeric(12, 6), nullable=False)
    created_at = Column(DateTime, default=func.now())

    buy_trade = relationship("Trade", foreign_keys=[buy_trade_id])
    sell_trade = relationship("Trade", foreign_keys=[sell_trade_id])
```

## 3. Matching Service

File: `kite-api/app/services/trade_matching_service.py`

Public functions:

```python
def rebuild_matches(universe: str, session: Session) -> RebuildResult:
    """
    Wipe and rebuild all trade_matches for one universe.
    Returns stats: matches_created, unmatched_sells, open_lots_remaining.
    """

def rebuild_all_universes(session: Session) -> dict[str, RebuildResult]:
    """Rebuild matches for all universes (called from sync pipeline)."""
```

Private helpers:

```python
def _match_trades(trades: list[Trade]) -> list[TradeMatch]:
    """Pure FIFO matcher — takes ordered trades, returns matches."""
```

**Pricing for P&L — net of slippage (effective prices):**

The raw `trades.price` column is the OHLC/4 mid-price (gross). `trades.slippage`
holds the ₹ slippage cost for that row separately. Per-trade realized P&L must
use **effective** (net-of-slippage) prices since that reflects actual cash flow:

```
effective_buy_price  = (buy.notional  + buy.slippage)  / buy.shares
effective_sell_price = (sell.notional − sell.slippage) / sell.shares
```

For a match consuming `shares_matched` from a given buy lot, allocate the lot's
slippage pro-rata by shares:

```
buy_slip_alloc  = buy.slippage  * (shares_matched / buy.shares)
sell_slip_alloc = sell.slippage * (shares_matched / sell.shares)

entry_price = (buy.price  * shares_matched + buy_slip_alloc)  / shares_matched
            = buy.price  + buy_slip_alloc  / shares_matched
exit_price  = sell.price − sell_slip_alloc / shares_matched

realized_pnl     = (exit_price - entry_price) * shares_matched
                 = (sell.price − buy.price) * shares_matched
                   − buy_slip_alloc − sell_slip_alloc
realized_pnl_pct = (exit_price / entry_price − 1) * 100
```

This matches the cash-flow accounting in the backtest (`cash += shares * price *
(1 - slip)` on sells, `cash -= shares * price * (1 + slip)` on buys), and means
per-trade realized P&L summed across all matches equals total trading P&L
excluding only the drag from idle cash and fractional-share rounding.

## 4. API Changes

### Extend `TradeResponse` schema

```python
class MatchedBuy(BaseModel):
    buy_trade_id: int
    entry_date: date
    entry_price: Decimal
    shares_matched: Decimal
    holding_days: int
    realized_pnl: Decimal
    realized_pnl_pct: Decimal

class TradeResponse(BaseModel):
    # ... existing fields ...
    matches: list[MatchedBuy] | None = None   # populated for SELLs only
```

### `trade_service.get_trades()`

Add a left-join / separate query to fetch `trade_matches` for the SELL trades
in the page, group by `sell_trade_id`, attach as `matches`. Avoid N+1 by
batching: one query for matches filtered by `sell_trade_id IN (...)`.

### Extend `TradeSummary`

```python
class TradeSummary(BaseModel):
    # ... existing fields ...
    realized_pnl_total: Decimal
    win_rate: float             # matches with pnl > 0 / total matches
    avg_holding_days: float
    best_trade_pct: Decimal
    worst_trade_pct: Decimal
```

Computed via aggregate query on `trade_matches` filtered by universe.

### New endpoint (optional, v1.1)

`GET /api/trades/{sell_trade_id}/matches` — returns just the matched-buy
details for one SELL. Useful for lazy-loading in the UI if the list payload
grows too large. Skip for v1 since matches are small.

## 5. Sync Pipeline Hook

In `scripts/sync_to_database.py`, after `sync_trades_from_csv()` loads trades:

```python
from app.services.trade_matching_service import rebuild_matches

def sync_trade_matches(session, universe):
    result = rebuild_matches(universe, session)
    logger.info(
        f"[{universe}] trade_matches: {result.matches_created} created, "
        f"{result.unmatched_sells} unmatched sells, "
        f"{result.open_lots_remaining} open lots"
    )
```

Call after each universe's trade sync. Also add to `app/services/sync_service.py`
(used by the `/api/sync/all` admin button).

## 6. Frontend

### Row expansion in `trades-table.tsx`

- Add a chevron column at left edge, rendered only for SELL rows.
- `useState<Set<number>>` tracks expanded trade IDs.
- Expanded content spans full table width as an extra row:

```
┌─────────────────────────────────────────────────────────┐
│ 2026-04-12  SELL  INFY  10  ₹1,780  ₹17,800     ▼       │
├─────────────────────────────────────────────────────────┤
│   Matched BUY: 2026-03-20 @ ₹1,650  (23 days held)      │
│   Shares: 10                                            │
│   Realized P&L: +₹1,300  (+7.88%)                       │
└─────────────────────────────────────────────────────────┘
```

- Color: green if `realized_pnl >= 0`, red otherwise.
- If `matches.length > 1` (rare): render a list of matched BUYs, one per lot.

### Summary cards update (`trade-summary.tsx`)

Add three new cards: **Realized P&L**, **Win Rate**, **Avg Holding Days**.
Grid becomes 7 cells (or a second row of 3).

## 7. Edge Cases

| Case | Handling |
|------|----------|
| SELL with no prior BUY in universe | Log warning, emit no match (data bug — shouldn't happen). |
| BUY still open at end of history | No match emitted (it's an Open Position). |
| Multiple BUYs → one SELL | Multiple `trade_matches` rows; frontend stacks them. |
| One BUY → multiple SELLs | Multiple `trade_matches` rows for the same `buy_trade_id`. |
| Fractional shares | `Numeric(18, 6)` columns already support them. |
| Re-running sync | `rebuild_matches` wipes & rebuilds → idempotent. |

## 8. Testing

Unit tests (`kite-api/tests/test_trade_matching.py`):
- Single BUY → single SELL → one match, correct P&L.
- One BUY → two partial SELLs → two matches summing to the buy quantity.
- Two BUYs → one SELL covering both → two matches in FIFO order.
- Re-entry pattern (BUY → SELL → BUY → SELL same symbol) → two disjoint pairs.
- SELL with no prior BUY → no match + warning.
- Unmatched open BUY → no match + counted in `open_lots_remaining`.

Integration: run `rebuild_matches("nse500")` on current prod data, assert:
- `unmatched_sells == 0` (strict — backtest is clean).
- `sum(realized_pnl)` close to sum of `pnl_pct * notional / 100` recorded in
  backtest exit_records (within 0.5% tolerance for cash/slippage effects).

## 9. File Changes Summary

**New:**
- `kite-api/alembic/versions/YYYYMMDD_0004_add_trade_matches.py`
- `kite-api/app/services/trade_matching_service.py`
- `kite-api/tests/test_trade_matching.py`

**Modified:**
- `kite-api/app/models/models.py` — add `TradeMatch`
- `kite-api/app/schemas/trades.py` — add `MatchedBuy`, extend `TradeResponse`, `TradeSummary`
- `kite-api/app/services/trade_service.py` — join matches, extend summary
- `kite-api/app/services/sync_service.py` — call `rebuild_matches` after trade sync
- `scripts/sync_to_database.py` — same
- `kite-dashboard/src/lib/api.ts` (or equivalent) — add `MatchedBuy` type
- `kite-dashboard/src/components/trades/trades-table.tsx` — expandable rows
- `kite-dashboard/src/components/trades/trade-summary.tsx` — new cards

No changes to the backtest script itself — matching is a DB-side concern.
