# Final Portfolio Reporting Improvements

## Overview

This document outlines planned improvements to the final portfolio reporting system. The current reports (`report_backtests.py` and `report_final_portfolio.py`) provide basic metrics, but we can add significantly more insights for better portfolio analysis and risk management.

---

## Current State

### What We Currently Report

**report_backtests.py (used by final portfolio runner):**
- Summary metrics: Total Return, CAGR, Volatility, Sharpe, Max Drawdown
- Trading frequency: trades/week, month, year
- Average turnover %
- Equity curve chart vs benchmark
- Trailing returns (1M, 3M, 6M, 1Y)
- Current holdings with entry dates and ranks
- Top/bottom 5 contributors (realized PnL)
- Recent trades (last 30)
- Hit rates by entry rank quintile
- Cost drag, holding periods

**report_final_portfolio.py:**
- Similar metrics but focused on current portfolio state
- 30-day PnL chart
- Daily returns and largest swings
- Winners/losers analysis
- Rank history (last 8 rebalances)
- Recent portfolio changes

---

## Planned Improvements

### High Priority (Core Risk & Performance)

#### 1. Drawdown Analysis ✅ COMPLETED
**Status:** Implemented and tested

**Completed Components:**
- ✅ Drawdown chart (dual-panel: equity curve + DD% timeline)
- ✅ Top 5 worst drawdown periods table with recovery stats
- ✅ Current underwater status with alert styling
- ✅ Aggregate drawdown statistics (avg DD, duration, recovery factor)
- ✅ Color-coded status boxes (green if at peak, yellow if underwater)

**Implementation:** `report_backtests.py` - lines 69-236
- Functions: `compute_drawdown_series()`, `identify_drawdown_periods()`, `get_current_drawdown_stats()`, `compute_drawdown_stats()`, `generate_drawdown_chart()`
- Integrated into HTML report with full styling

---

#### 2. Score Filtering Metrics ✓
**Why:** Showcase the new score filtering feature we just added

**Components:**
- Number of stocks filtered out at each rebalance (failed entry threshold)
- Early exits due to score (vs rank-based exits)
- Average momentum score of portfolio over time
- Score distribution:
  - Current holdings vs full universe
  - Entry score distribution
  - Exit score distribution
- Score vs actual performance scatter plot
- Threshold breach analysis (how often stocks cross thresholds)
- Score filtering effectiveness:
  - % reduction in trades
  - Impact on CAGR
  - Impact on drawdown

**Output:** New dedicated section + charts

---

#### 3. Detailed Trade Analytics ✓
**Why:** Better understand trading patterns and profitability

**Components:**
- Win rate by holding period:
  - Buckets: <1 week, 1-2 weeks, 2-4 weeks, 1-2 months, >2 months
  - Win % and avg return per bucket
- Profit factor (gross profit / gross loss)
- Average win vs average loss (expectancy)
- Best single trade (symbol, return, holding period)
- Worst single trade
- Consecutive wins/losses streaks (longest)
- Trade distribution histogram (PnL buckets)
- Entry/exit efficiency metrics
- Round-trip analysis (full cycle stats)

**Output:** Enhanced trade analytics section + histogram

---

#### 4. Rolling Metrics Charts ✅ COMPLETED
**Status:** Implemented and tested

**Completed Components:**
- ✅ Rolling Sharpe Ratio chart (6-month window)
- ✅ Rolling Volatility chart (30/60/90 day overlays)
- ✅ Rolling Beta vs Benchmark chart (6-month)
- ✅ Rolling Correlation vs Benchmark chart (6-month)
- ✅ Rolling Max Drawdown chart (1-year window)
- ✅ Summary statistics table (avg, min, max for all metrics)

**Implementation:** `report_backtests.py` - lines 249-445
- Functions: `compute_rolling_sharpe()`, `compute_rolling_volatility()`, `compute_rolling_beta()`, `compute_rolling_correlation()`, `compute_rolling_max_drawdown()`, `generate_rolling_metrics_charts()`
- 5 charts generated showing performance consistency over time

**Why:** Show stability and consistency of performance over time

**Components:**
- Rolling 6-month Sharpe ratio
- Rolling volatility (30/60/90 day windows)
- Rolling beta vs benchmark
- Rolling correlation with benchmark
- Rolling max drawdown
- Charts showing these metrics over the full backtest period

**Output:** New "Rolling Metrics" section with 4-5 charts

---

#### 5. Position-Level Insights ✓
**Why:** Understand portfolio concentration and individual position risk

**Components:**
- Position sizing history chart (# of holdings over time)
- Concentration risk:
  - Herfindahl-Hirschman Index (HHI)
  - Top 5 position concentration %
  - Gini coefficient
- Average position size over time
- Stock-level risk contribution:
  - Each holding's contribution to portfolio volatility
  - Marginal VaR per position
- Position correlation matrix (current holdings)
- Sector/industry exposure breakdown (if metadata available)

**Output:** New "Portfolio Structure" section + charts

---

### Medium Priority (Enhanced Metrics)

#### 6. Comprehensive Risk Metrics ✓
**Why:** Professional risk assessment requires multiple angles

**Components:**
- Sortino Ratio (downside risk-adjusted returns)
- Calmar Ratio (CAGR / Max Drawdown)
- Beta vs benchmark
- Alpha vs benchmark
- Information Ratio (tracking error adjusted excess return)
- Treynor Ratio
- Ulcer Index (pain measurement)
- Value at Risk (VaR) - 95th/99th percentile
- Conditional VaR (CVaR/Expected Shortfall)
- Omega Ratio
- Tail ratio (95th percentile gain / 95th percentile loss)

**Output:** Enhanced summary metrics table

---

#### 7. Rebalancing Behavior Analysis ✓
**Why:** Understand trading costs and portfolio churn

**Components:**
- Turnover over time chart
- Trade frequency patterns:
  - By day of week
  - By month
  - By rebalance cycle
- Average rebalance size
- No-change rebalances (% of rebalances with zero trades)
- Churn rate (positions changed per rebalance)
- Average number of entries/exits per rebalance
- Trade clustering (are trades bunched or spread out?)

**Output:** New "Rebalancing Behavior" section + charts

---

#### 8. Monthly Returns Heatmap ✅ COMPLETED
**Status:** Implemented and tested

**Completed Components:**
- ✅ Monthly returns heatmap (calendar-style color-coded)
- ✅ Quarterly performance table
- ✅ Best/worst months (all-time)
- ✅ Average monthly return
- ✅ Monthly win rate
- ✅ Seasonality analysis (which months tend to outperform)
- ✅ Year-over-year comparison

**Implementation:** `report_backtests.py` - lines 448-593
- Functions: `compute_monthly_returns()`, `compute_quarterly_returns()`, `generate_monthly_heatmap()`, `analyze_monthly_performance()`
- Color-coded heatmap using RdYlGn colormap (-20% to +20% range)
- Quarterly summary table with annual comparison
- Integrated into HTML report with full styling

**Why:** Visual pattern recognition and seasonality

**Output:** New "Calendar Performance" section + heatmap

---

#### 9. Enhanced Benchmark Comparison ✓
**Why:** Better understand relative performance

**Components:**
- Relative strength chart (portfolio / benchmark ratio over time)
- Outperformance periods vs underperformance (highlight regions)
- Tracking error over time
- Up capture ratio (% of benchmark gains captured)
- Down capture ratio (% of benchmark losses captured)
- Multiple benchmarks side-by-side:
  - Nifty 50
  - Nifty 100
  - Nifty 500
  - Nifty Midcap 100
- Benchmark-relative drawdown
- Active share (portfolio deviation from benchmark)

**Output:** Enhanced benchmark section + relative performance chart

---

### Lower Priority (Enhanced Features)

#### 10. Enhanced Current Holdings Table ✅ COMPLETED
**Status:** Implemented and tested

**Completed Components:**
- ✅ Unrealized PnL (absolute and %)
- ✅ Position size (% of portfolio)
- ✅ 10-day trailing performance box (aggregate summary)
- ✅ 10-day portfolio return % and absolute PnL
- ✅ 10-day benchmark return % for comparison
- ✅ Day-by-day breakdown table (each of the 10 days)
- ✅ Color-coded cells (green/red) for daily performance
- ✅ Outperformance vs benchmark per day

**Implementation:** `report_backtests.py` - lines 659-740
- Functions: `enhance_holdings_table()`, `compute_trailing_performance()`
- Aggregate 10-day summary box with color coding
- Daily breakdown table showing each trading day individually
- Portfolio vs benchmark comparison for each day
- Integrated into HTML report with enhanced holdings table

**Why:** More actionable information about current positions

**Additions to current table:**
- Momentum score trend (last 4 weeks) - sparkline or mini chart (not yet implemented)
- Volatility rank vs portfolio average (not yet implemented)
- Recent price action (7d, 14d, 30d returns) (not yet implemented)
- Distance from entry/exit thresholds (not yet implemented)
- ATR (Average True Range) - for stop-loss planning (not yet implemented)
- Support/resistance levels (if available) (not yet implemented)
- Days to next earnings (if metadata available) (not yet implemented)

**Output:** Much richer holdings table with 10-day performance tracking

---

#### 11. Watch Lists ✓
**Why:** Forward-looking trade alerts

**Components:**
- **Entry Candidates:**
  - Stocks scoring just below entry threshold
  - Distance to threshold
  - Recent score momentum
- **Exit Watch:**
  - Current holdings close to exit threshold
  - Warning level (within 10% of threshold)
- **Threshold Crossings:**
  - Stocks that crossed thresholds in last rebalance
  - Near-misses (almost entered/exited)

**Output:** New "Watch List" section

---

#### 12. Forward-Looking Section ✓
**Why:** Help with planning and expectations

**Components:**
- Next rebalance date
- Expected turnover (based on current score trends)
- Likely entries (stocks trending toward threshold)
- Likely exits (holdings with declining scores)
- Projected portfolio changes (if predictable)
- Upcoming rebalance preview (estimated)

**Output:** New "Next Rebalance Preview" section

---

#### 13. System Health Indicators ✓
**Why:** Ensure data quality and system reliability

**Components:**
- Data freshness:
  - Last price update timestamp (per symbol)
  - Oldest stale data
- Missing data warnings:
  - Symbols with gaps
  - Recent data availability
- Signal generation metadata:
  - Signals file timestamp
  - Signal generation parameters used
  - Number of signals generated
- Backtest vs live drift indicators (if applicable)
- Data quality score
- System alerts/warnings

**Output:** New "System Health" section at bottom of report

---

## Implementation Plan

### Phase 1: High Priority (Week 1-2)
1. Drawdown analysis
2. Score filtering metrics
3. Trade analytics
4. Rolling metrics
5. Position insights

### Phase 2: Medium Priority (Week 3)
6. Risk metrics
7. Rebalancing analysis
8. Calendar heatmap
9. Enhanced benchmarks

### Phase 3: Lower Priority (Week 4)
10. Enhanced holdings table
11. Watch lists
12. Forward-looking
13. System health

---

## Technical Notes

- All new metrics should be added to `report_backtests.py` since that's what the final portfolio runner uses
- `report_final_portfolio.py` can be deprecated or aligned with the new format
- Consider creating helper modules for complex calculations (drawdown analysis, risk metrics, etc.)
- Charts should gracefully degrade if matplotlib is not installed
- All new sections should be optional/configurable via command-line flags if they add significant computation time

---

## Success Metrics

The improved reporting will be successful if it:
1. Reduces time to understand portfolio risk profile (< 2 minutes to identify key risks)
2. Provides actionable insights for portfolio management decisions
3. Clearly shows impact of score filtering feature
4. Helps identify when to adjust strategy parameters
5. Builds confidence in the portfolio through transparency

---

## Questions to Resolve

- Should we create a separate "rich report" or enhance the existing report?
- Do we want PDF export capability?
- Should reports be versioned/archived automatically?
- Do we need real-time/live reporting vs batch?
- Should we add email alerts for threshold crossings or significant events?

---

**Last Updated:** 2026-01-20
**Status:** Planning phase - ready to implement
