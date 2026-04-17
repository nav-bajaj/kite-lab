# Trade Matching & Per-Trade P&L

## Overview

Match each SELL trade to its opening BUY trade(s) using FIFO (first-in-first-out)
so the dashboard can show realized P&L per closed trade. On the Trades tab, a SELL
row becomes expandable — clicking it reveals the matched BUY, holding days, entry
price, exit price, and realized P&L (₹ and %).

Applies to every universe (`nse500`, `nifty100`, `nifty250`) independently.

## Goals

- Persist trade-pair matches in the database (idempotent, rebuildable).
- Expose per-trade P&L via the existing `/api/trades` API.
- Expandable SELL rows on the Trades page with matched-buy details.
- Run matching automatically as part of `sync_to_database.py`.

## Non-Goals (for v1)

- Open (unmatched) BUY trades don't show unrealized P&L here — that's Open Positions.
- No position averaging across multiple partial buys *inside the backtest* —
  backtest is always 1 BUY → 1 SELL per cycle, but we use a FIFO lot model so
  real-trading edge cases (scaling in/out) work if we ever need them.
- No cost-basis methods other than FIFO (no LIFO/avg-cost toggle).

## Columns on Expanded SELL Row

| Field | Description |
|-------|-------------|
| Entry Date | `trade_date` of matched BUY |
| Entry Price | `price` of matched BUY |
| Exit Date | `trade_date` of SELL (already visible) |
| Exit Price | `price` of SELL (already visible) |
| Shares Matched | Shares in this match (= SELL shares for 1:1 case) |
| Holding Days | `exit_date - entry_date` |
| Realized P&L (₹) | `(effective_sell - effective_buy) * shares` (net of slippage) |
| Realized P&L (%) | `(effective_sell / effective_buy - 1) * 100` |

Effective prices reconstruct actual cash flow from the existing `trades` columns:
`effective_buy  = (notional + slippage) / shares`;
`effective_sell = (notional − slippage) / shares`.

---

## Tasks

### Phase 1: Design

#### Task #1: Data model and matching algorithm design
**Status:** ✅ Complete — see [DESIGN.md](DESIGN.md)

Decide FIFO lot model, schema (`trade_matches` table), and API shape.

---

### Phase 2: Backend

#### Task #2: Create `trade_matches` table + Alembic migration
**Status:** ✅ Complete
**Blocked by:** #1

- Added `TradeMatch` model in [app/models/models.py](../../kite-api/app/models/models.py).
- Migration [20260417_0004_add_trade_matches.py](../../kite-api/alembic/versions/20260417_0004_add_trade_matches.py) applied.
- Indexes on `(universe)`, `(sell_trade_id)`, `(buy_trade_id)`, `(universe, symbol)`.

#### Task #3: FIFO matching service
**Status:** ✅ Complete
**Blocked by:** #2

- [app/services/trade_matching_service.py](../../kite-api/app/services/trade_matching_service.py) — per-symbol FIFO lot queue.
- `rebuild_matches(universe, session)` wipes and rebuilds; idempotent.
- 7 unit tests in [tests/test_trade_matching.py](../../kite-api/tests/test_trade_matching.py) covering 1:1, partial fills, multi-buy coverage, re-entry, unmatched sell, open lot, cash-flow reconciliation.

#### Task #4: Hook matching into sync pipeline
**Status:** ✅ Complete
**Blocked by:** #3

- `sync_all()` in [app/services/sync_service.py](../../kite-api/app/services/sync_service.py) calls `rebuild_matches` after trades sync.
- [scripts/sync_to_database.py](../../scripts/sync_to_database.py) prints match counts, unmatched sell shares, open-lot count per universe.
- Verified against prod data: nse500 1066 matches / nifty100 763 / nifty250 933, 0 unmatched sells across all three.

#### Task #5: Extend `/api/trades` response with match info
**Status:** ✅ Complete
**Blocked by:** #2

- Added `MatchedBuy` schema; `TradeResponse.matches` populated on SELL rows only.
- `trade_service.get_trades()` batch-fetches matches for all SELL IDs on the page (no N+1).
- Effective prices (net of slippage) used throughout.

#### Task #6: Trade summary: realized P&L, win rate, avg holding days
**Status:** ✅ Complete
**Blocked by:** #5

- `get_trade_summary()` returns `realized_pnl_total`, `win_rate`, `avg_holding_days`, `best_trade_pct`, `worst_trade_pct`, `avg_winner_pct`, `avg_loser_pct`.

---

### Phase 3: Frontend

#### Task #7: Expandable row UI for Trades table
**Status:** ✅ Complete
**Blocked by:** #5

- SELL rows expandable via chevron in [trades-table.tsx](../../kite-dashboard/src/components/trades/trades-table.tsx).
- Added "Realized P&L" column to main row.
- Expanded panel shows entry date, net entry price, holding days, net exit price, realized ₹ & %.
- Multi-lot matches (1 SELL → N BUYs) render stacked under the SELL.

#### Task #8: Trade Summary cards redesign
**Status:** ✅ Complete
**Blocked by:** #6

- Two-row layout in [trade-summary.tsx](../../kite-dashboard/src/components/trades/trade-summary.tsx):
  - Row 1 (headline): Realized P&L · Win Rate · Avg Hold Days.
  - Row 2 (distribution): Best Trade · Worst Trade · Avg Winner · Avg Loser.
- Removed count-based cards (Total Trades / Buys / Sells / Total Notional) per user feedback — replaced with trade-quality metrics.

---

### Phase 4: QA

#### Task #9: Test & verify matching correctness
**Status:** ✅ Complete
**Blocked by:** #4, #7

- All 7 unit tests pass.
- Prod-data reconciliation: realized P&L covers ~91% of total equity gain across all three universes, with the remaining ~9% as unrealized P&L on current 24 open positions — matches expectation.
- Manually verified expandable UI across nse500, nifty100, nifty250.

---

## Dependency Graph

```
#1 Design
  │
  └──► #2 trade_matches table + migration
         │
         ├──► #3 FIFO matching service
         │      │
         │      └──► #4 Hook into sync pipeline
         │
         └──► #5 Extend /api/trades with match info
                │
                ├──► #6 Summary with realized P&L
                │      │
                │      └──► #8 Summary cards update
                │
                └──► #7 Expandable row UI
                       │
         ┌─────────────┘
         ▼
        #9 QA
```

---

## Implementation Order

1. #2 Model + migration (run `alembic upgrade head`)
2. #3 Matching service + unit tests
3. #4 Wire into sync pipeline, run a fresh sync locally
4. #5 API response extension
5. #7 Frontend expandable row
6. #6 + #8 Summary enhancements
7. #9 QA pass, then deploy to Railway

---

## Open Questions

- **Unmatched BUYs:** leftover BUYs with no SELL are "open" — already visible in
  Open Positions. No handling needed on the Trades tab.
- **Multi-lot edge case:** in the backtest this never happens, but the FIFO
  model handles 1 SELL matching multiple earlier BUYs (produces multiple
  `trade_matches` rows, UI shows them stacked under the SELL).

## Resolved

- **Pricing basis for P&L:** **net of slippage** (effective prices). Uses
  `(notional ± slippage) / shares` on each side so realized P&L matches actual
  cash flow. Per-trade totals will reconcile with the equity curve up to idle
  cash and fractional-share rounding.
