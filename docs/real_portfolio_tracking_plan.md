# Real Portfolio Tracking Implementation Plan

## Overview

Implement tracking of your real Zerodha portfolio against the model momentum portfolio, with slippage measurement and divergence reporting.

## Key Questions Answered

### 1. Initial Deployment: Equal-Weight or Match Current Model?

**Recommendation: Equal-weight across all 24 current model stocks**

The model portfolio is already equal-weight (1/24 = 4.17% each stock). When you deploy capital on Monday:
- Buy all 24 stocks from `final_portfolio_24.csv` with equal allocation
- Each position: `capital / 24` (e.g., ₹4L → ~₹16,667 per stock)
- This immediately aligns with the model

The model doesn't use score-based weights - scores only determine *which* 24 stocks, not *how much* of each.

### 2. Tracking Entries/Exits

- Daily snapshot of real holdings via `kite.holdings()` API
- Compare against model holdings from `final_portfolio_24.csv`
- Track: missing positions, extra positions, weight deviations
- Store history in new `real_holdings` table

### 3. Slippage Measurement

- Capture actual execution prices from `kite.trades()` API
- Compare to model price (OHLC/4 average from `nse500_data/` CSVs)
- Slippage = `(actual_price - model_price) / model_price`
- Track per-trade and aggregate slippage metrics

---

## Implementation Phases

### Phase 1: KiteConnect API Extensions
**Files to modify:**
- `data_pipeline/price_client.py`

Add methods to PriceClient:
```python
def fetch_holdings(self) -> pd.DataFrame
def fetch_positions(self) -> pd.DataFrame
def fetch_orders(self, from_date=None, to_date=None) -> pd.DataFrame
def fetch_trades(self, from_date=None, to_date=None) -> pd.DataFrame
```

These wrap KiteConnect API calls:
- `kite.holdings()` - Current portfolio holdings
- `kite.positions()` - Intraday positions
- `kite.orders()` - Order history
- `kite.trades()` - Trade executions

### Phase 2: Database Schema
**File to modify:**
- `kite-api/app/models/models.py`

New tables:

**RealHolding** - Daily snapshots of actual Zerodha holdings
| Column | Type | Description |
|--------|------|-------------|
| universe | str | "nse500" / "nifty100" |
| snapshot_date | date | Date of snapshot |
| symbol | str | Trading symbol |
| quantity | int | Shares held |
| average_price | decimal | Avg buy price |
| last_price | decimal | Current price |
| pnl | decimal | Unrealized P&L |
| notional | decimal | Position value |
| weight_pct | decimal | % of portfolio |

**RealTrade** - Actual executed trades
| Column | Type | Description |
|--------|------|-------------|
| order_id | str | Zerodha order ID |
| trade_date | date | Execution date |
| symbol | str | Trading symbol |
| side | str | BUY/SELL |
| quantity | int | Shares traded |
| price | decimal | Actual fill price |
| model_price | decimal | OHLC/4 model price |
| slippage_pct | decimal | Slippage percentage |

**PortfolioDivergence** - Daily comparison metrics
| Column | Type | Description |
|--------|------|-------------|
| report_date | date | Comparison date |
| real_value | decimal | Actual portfolio value |
| model_value | decimal | Model portfolio value |
| missing_positions | json | Stocks in model, not real |
| extra_positions | json | Stocks in real, not model |
| tracking_error | decimal | Weight deviation metric |

### Phase 3: Holdings Fetcher Script
**New file:**
- `scripts/fetch_real_holdings.py`

Functions:
- Fetch real holdings from Zerodha API
- Save daily snapshot to `data/real_portfolio/holdings_YYYY-MM-DD.csv`
- Insert into `real_holdings` database table
- Run daily (integrate with `run_daily_pipeline.py`)

### Phase 4: Comparison Service
**New file:**
- `kite-api/app/services/real_portfolio_service.py`

Core functions:
```python
def compare_portfolios(real_holdings, model_holdings) -> dict:
    """
    Returns:
    - matching_positions: stocks in both
    - missing_positions: in model, not in real
    - extra_positions: in real, not in model
    - weight_deviations: per-position weight diff
    """

def calculate_slippage(real_trade, model_price) -> dict:
    """
    Returns:
    - slippage_pct: (actual - model) / model
    - slippage_amount: per share
    - favorable: True if better than model
    """

def generate_alignment_orders(divergence, capital) -> list:
    """Generate orders to align real with model"""
```

### Phase 5: API Endpoints
**File to modify:**
- `kite-api/app/api/portfolio.py`

New endpoints:
- `GET /api/real/holdings` - Current Zerodha holdings
- `GET /api/real/comparison` - Real vs model comparison
- `GET /api/real/slippage` - Slippage analysis
- `GET /api/real/divergence` - Historical tracking error

### Phase 6: Initial Deployment Tool
**New file:**
- `scripts/generate_initial_orders.py`

Generate buy orders for initial deployment:
```bash
python scripts/generate_initial_orders.py \
  --capital 400000 \
  --output orders/initial_deployment.csv
```

Output format:
```csv
symbol,target_shares,target_notional,current_price,weight_pct
HINDCOPPER,50,16667,333.34,4.17
NATIONALUM,100,16667,166.67,4.17
...
```

---

## Data Flow

```
┌─────────────────────┐     ┌──────────────────────┐
│   Zerodha API       │     │   Model Portfolio    │
│   kite.holdings()   │     │   final_portfolio_24 │
└─────────┬───────────┘     └──────────┬───────────┘
          │                            │
          ▼                            ▼
┌─────────────────────────────────────────────────┐
│         Comparison Engine                        │
│    (real_portfolio_service.py)                  │
│  - Weight deviations                            │
│  - Missing/extra positions                      │
│  - Slippage calculation                         │
└─────────────────────┬───────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Database │ │   CSV    │ │   API    │
   │ real_*   │ │ Reports  │ │ Endpoints│
   └──────────┘ └──────────┘ └──────────┘
```

---

## Weekly Workflow (Post-Implementation)

**Thursday:**
1. Run `scripts/run_final_momentum_portfolio.py` (generates model changes)
2. Run `scripts/fetch_real_holdings.py` (captures current state)
3. Review comparison: which trades needed to align

**Friday:**
1. Generate model orders (existing flow)
2. Compare to real portfolio for execution planning

**Monday:**
1. Execute trades in Zerodha console
2. After market close: run `scripts/track_slippage.py`
3. Compare actual fills to model prices

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `data_pipeline/price_client.py` | Modify | Add holdings/orders/trades methods |
| `kite-api/app/models/models.py` | Modify | Add RealHolding, RealTrade, PortfolioDivergence |
| `scripts/fetch_real_holdings.py` | Create | Daily holdings snapshot |
| `scripts/track_slippage.py` | Create | Slippage calculation |
| `scripts/generate_initial_orders.py` | Create | Initial deployment orders |
| `kite-api/app/services/real_portfolio_service.py` | Create | Comparison logic |
| `kite-api/app/api/portfolio.py` | Modify | Add real portfolio endpoints |
| `data/real_portfolio/` | Create | Directory for real holdings CSVs |

---

## Verification Plan

1. **API Integration Test:**
   - Run `fetch_real_holdings.py` after login
   - Verify holdings returned match Zerodha console

2. **Comparison Test:**
   - Manually compare output vs model portfolio
   - Check missing/extra position detection

3. **Slippage Calculation Test:**
   - After executing a trade, compare fill price
   - Verify slippage calc against OHLC/4 price

4. **End-to-End Test:**
   - Deploy small test capital (e.g., ₹50K)
   - Track through one rebalance cycle
   - Verify all metrics computed correctly

---

## Configuration (User Choices)

- **Initial capital:** ₹10L (full model allocation)
- **Non-model positions:** Track separately (mark as "non-model" in reports, don't auto-sell)
- **Storage:** Both CSV files (`data/real_portfolio/`) and PostgreSQL database

## Notes

- Model uses OHLC/4 average with 0.2% assumed slippage
- Real slippage may be better or worse depending on execution
- Equal-weight target: ₹41,667 per position (₹10L / 24 stocks = 4.17%)
- Min-hold-days (8 days) applies to model; real portfolio is discretionary
- Non-model positions will appear in reports with `is_model=False` flag
