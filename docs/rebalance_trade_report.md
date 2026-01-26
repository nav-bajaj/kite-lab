# Enhanced Rebalance Trade Report

## Overview

This feature provides detailed trade execution reports for weekly rebalancing, showing exact prices, quantities, and dollar amounts for all trades.

## Rebalance Process

The portfolio follows a two-step rebalance process:

1. **Thursday EOD (Signal Generation)**
   - Momentum scores calculated using Thursday's closing prices
   - Top-N stocks ranked by z-scored momentum (return/volatility)
   - Signal file generated with stock rankings

2. **Friday (Trade Execution)**
   - Trades execute at Friday's OHLC/4 price (average of Open, High, Low, Close)
   - Portfolio rebalanced to equal-weight across all holdings
   - 0.2% slippage applied to simulate market impact

## Trade Pricing Model

**Pricing Formula:** `OHLC/4 = (Open + High + Low + Close) / 4`

This pricing model is implemented in `scripts/backtest_momentum.py` (line 16):
```python
df["trade_price"] = df[["open", "high", "low", "close"]].mean(axis=1)
```

**Why OHLC/4?**
- More realistic than using close price alone
- Accounts for intraday price movement
- Simulates realistic fill prices for market orders

## Report Contents

The detailed trade report (`trade_report_YYYY-MM-DD.md`) includes:

### Header Information
- **Signal Date (Thursday)**: Date signals were generated
- **Trade Date (Friday)**: Date trades will execute
- **Pricing Model**: OHLC/4 with slippage percentage
- **Portfolio Capital**: Total capital
- **Portfolio Size**: Number of stocks (default: 24)
- **Allocation per Stock**: Equal-weight allocation
- **Holdings Unchanged**: Number of stocks with no trades

### Exit Trades
Table showing stocks being sold:
- Symbol
- Old Rank
- Exit Price (Friday's OHLC/4)
- Shares to sell
- Proceeds (after 0.2% slippage)
- Trade Date

### Entry Trades
Table showing stocks being bought:
- Symbol
- New Rank
- Entry Price (Friday's OHLC/4)
- Shares to buy
- Cost (including 0.2% slippage)
- Trade Date

### Summary
- Total exits and proceeds
- Total entries and deployment
- Net cash flow
- Rank changes (no trades)
- Holdings unchanged (no trades)
- Portfolio turnover percentage

## Usage

### Standalone Script

Generate report for a specific rebalance:

```bash
python scripts/generate_rebalance_trade_report.py \
  --changes experiments/final_portfolio/.../rebalance/changes_2026-01-23.csv \
  --prices-dir nse500_data \
  --signal-date 2026-01-23 \
  --capital 1000000 \
  --portfolio-size 24 \
  --output trade_report.md
```

### Integrated Workflow

The report is automatically generated when running the final portfolio on Thursday (rebalance day):

```bash
python scripts/run_final_momentum_portfolio.py
```

On Thursday, this will create:
1. `changes_YYYY-MM-DD.csv` - Simple changes list
2. `changes_YYYY-MM-DD.md` - Markdown changes report
3. `trade_report_YYYY-MM-DD.md` - Detailed trade report with prices (**NEW**)

## Files Modified

1. **`scripts/generate_rebalance_trade_report.py`** (NEW)
   - Standalone script to generate detailed trade reports
   - Loads OHLC data for each symbol
   - Calculates shares and dollar amounts
   - Generates formatted markdown report

2. **`scripts/run_final_momentum_portfolio.py`**
   - Integrated trade report generation on rebalance day
   - Calls `generate_rebalance_trade_report.py` after changes CSV is created
   - Passes all necessary parameters (capital, portfolio size, slippage)

## Verification of Current Logic

The backtest already implements the correct Thursday→Friday logic:

**Signal Date Mapping** (`scripts/backtest_momentum.py` lines 59-67):
```python
def map_signal_to_trade(signal_date, calendar):
    """Map signal date (Thursday) to trade date (Friday)"""
    preferred = signal_date + pd.Timedelta(days=1)
    if preferred in calendar:
        return preferred
    # Fallback logic for holidays...
```

**Key Points:**
- Signals dated on Thursday (`W-THU` resampling)
- `map_signal_to_trade()` adds 1 day → Friday execution
- Trade prices use Friday's OHLC/4
- This matches real-world portfolio execution

## Example Report

```markdown
# Detailed Rebalance Trade Report

**Signal Date (Thursday):** 2020-07-16
**Trade Date (Friday):** 2020-07-17
**Pricing Model:** OHLC/4 (average of Open, High, Low, Close)
**Slippage:** 0.20%
**Portfolio Capital:** $1,000,000.00
**Portfolio Size:** 24 stocks (equal-weighted)
**Allocation per Stock:** $41,666.67
**Holdings Unchanged:** 14 stocks (no trades)

---

## Exit Trades (5 stocks)

Stocks being sold on Friday:

| Symbol | Old Rank | Exit Price | Shares | Proceeds | Trade Date |
|--------|----------|------------|--------|----------|------------|
| AJANTPHARM | 21 | $960.21 | 43.39 | $41,583.33 | 2020-07-17 |
| DEEPAKNTR | 23 | $527.08 | 79.05 | $41,583.33 | 2020-07-17 |
| ... | ... | ... | ... | ... | ... |

**Total Proceeds:** $207,916.67

## Entry Trades (5 stocks)

Stocks being bought on Friday:

| Symbol | New Rank | Entry Price | Shares | Cost | Trade Date |
|--------|----------|-------------|--------|------|------------|
| BSOFT | 10 | $110.24 | 377.22 | $41,666.67 | 2020-07-17 |
| MUTHOOTFIN | 11 | $1176.03 | 35.36 | $41,666.67 | 2020-07-17 |
| ... | ... | ... | ... | ... | ... |

**Total Deployment:** $208,333.33

## Summary

- **Exits:** 5 stocks, $207,916.67 proceeds
- **Entries:** 5 stocks, $208,333.33 deployment
- **Net Cash Flow:** $416.67
- **Rank Changes Only:** 0 stocks (no trades)
- **Holdings Unchanged:** 14 stocks (no trades)
- **Total Portfolio Size:** 24 stocks
- **Turnover:** 20.8%
```

## Benefits

1. **Transparency**: See exact prices and quantities for each trade
2. **Execution Planning**: Use report to place market orders on Friday
3. **Verification**: Confirm backtest assumptions match real-world execution
4. **Documentation**: Historical record of all rebalances with full details

## Notes

- Share quantities are estimates based on equal-weight allocation
- Actual shares held may differ based on portfolio history and rounding
- Report assumes all positions are fully deployed
- Net cash flow should be close to zero for balanced rebalances
