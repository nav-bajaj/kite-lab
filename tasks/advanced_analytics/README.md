# Advanced Analytics — Bloomberg-Style Intelligence Layer

## Overview

A suite of analytics features that provide insights unavailable in Zerodha or any Indian retail brokerage. Every feature passes a simple filter: **"Can the user already get this from their Kite account?"** If yes, we don't build it.

The unifying theme is **cross-sectional intelligence** — analytics that require computation across the full NSE 500 universe, across time, or across portfolio positions. Brokerages think in terms of individual stocks and your account. We think in terms of the universe, the signal, and portfolio-level risk.

**Depends on:** Existing dashboard infrastructure (Next.js + FastAPI + PostgreSQL), daily price data pipeline, momentum signal generation, backtest engine.

**Relationship to Sector Analytics:** The [sector_analytics](../sector_analytics/README.md) task covers sector rotation, heatmaps, and sector-vs-benchmark analysis. This document covers everything else. Some features (e.g., sector concentration in Portfolio Attribution) will consume sector data from that pipeline once available.

---

## Feature Clusters

### Cluster A: Cross-Sectional & Relative Analytics

These features answer: "Where does this stock (or sector) sit relative to everything else?"

#### A1. Momentum Rank Tracker

**What it is:** For any stock, show its momentum rank within the NSE 500 universe over time — not just today's rank, but the full trajectory (e.g., "rose from rank 350 to rank 18 over 8 weeks").

**Why Zerodha can't do this:** Zerodha shows absolute price charts. It has zero concept of cross-sectional ranking. Momentum rank is a derived metric computed across 500 stocks simultaneously — no brokerage computes this.

**Data requirements:**
- Historical momentum signals (`date, rank, symbol, score`) — already generated daily by `build_momentum_signals_flexible.py`
- Need to persist rank history in the database (currently only latest signals are stored)

**Key views:**
- **Rank trajectory chart:** X = date, Y = rank (inverted axis, rank 1 at top). Color band for top-24 zone.
- **Rank velocity:** Rate of rank change over trailing 4 weeks. Stocks accelerating into top-24 are "emerging" picks.
- **Rank distribution histogram:** Where has this stock spent most of its time? Always top-50, or a one-time fluke?
- **Universe-wide rank movement table:** Biggest rank gainers/losers this week across all 500 stocks.

**Computation:**
- Store: Extend daily signal pipeline to persist `(date, symbol, rank, score, mom_6m, vol_6m)` rows to a `signal_history` table.
- Query: Rank trajectory is a simple `SELECT date, rank FROM signal_history WHERE symbol = ? ORDER BY date`.
- Rank velocity: `rank_change = rank(t) - rank(t - 20 trading days)`.

**Database changes:**
- New table: `signal_history` (date, symbol, rank, score, raw_momentum, volatility, z_score). Partitioned by month or quarter if volume is a concern (~500 rows/day = ~125K rows/year).

**API endpoints:**
- `GET /api/analytics/rank-tracker/{symbol}?window=6m` — rank trajectory + velocity
- `GET /api/analytics/rank-movers?direction=up&limit=20` — biggest rank changes this week

**Frontend:**
- Rank trajectory chart (line chart, inverted Y-axis, top-24 band shaded)
- Rank movers table on a dedicated "Screener" or "Universe" page
- Integrate into single-stock detail view (if we build one)

---

#### A2. Momentum Breadth Indicators

**What it is:** Market-wide breadth analytics derived from momentum signals, not prices. Answers: "Is the momentum factor healthy right now, or is it narrowing dangerously?"

**Why Zerodha can't do this:** Breadth indicators based on price (advance/decline) are generic and widely available. Breadth indicators based on momentum signals are proprietary to our system.

**Data requirements:**
- Daily signal history (same `signal_history` table from A1)
- Index price data (already in `indices_data/`)

**Key metrics:**
- **Momentum breadth:** % of NSE 500 with positive momentum score (above zero z-score). Healthy market > 50%.
- **Momentum breadth divergence:** Index making new highs while momentum breadth is declining — classic warning signal. Compute as: `Nifty 500 at 52-week high AND momentum_breadth < 40%`.
- **Top-24 concentration:** How much of the top-24's total score is concentrated in the top 5? Rising concentration = fragile portfolio.
- **Rank churn rate:** How many stocks entered/exited top-50 this week? High churn = regime instability.
- **Momentum factor spread:** Average score of top decile minus bottom decile. Widening spread = momentum is working. Narrowing = momentum is struggling.

**Computation:**
- All metrics are aggregations over the `signal_history` table for a given date.
- Breadth divergence requires joining with index price data to detect index highs.
- Factor spread is `AVG(score WHERE rank <= 50) - AVG(score WHERE rank >= 450)`.

**API endpoints:**
- `GET /api/analytics/breadth?window=1y` — all breadth metrics as time series
- `GET /api/analytics/breadth/current` — latest snapshot with traffic-light status

**Frontend:**
- Dedicated "Market Regime" or "Breadth" dashboard panel
- Traffic-light summary: green (breadth > 50%, spread widening), yellow (mixed), red (divergence detected)
- Breadth + factor spread time series chart with Nifty 500 overlay

---

#### A3. Signal Decomposition (Per-Stock)

**What it is:** For any stock, break down its momentum score into components: raw 6-month return, realized volatility, vol-adjusted score, cross-sectional z-score, final rank. Shows exactly *why* a stock is ranked where it is.

**Why Zerodha can't do this:** This is proprietary signal logic. No brokerage shows you why a quantitative model selected a stock.

**Data requirements:**
- Signal history with component columns (already output by `build_momentum_signals_flexible.py`: `score, score_6m, mom_6m, vol_6m`)
- Need to persist all component columns, not just rank

**Key views:**
- **Waterfall chart:** Raw momentum → vol adjustment → z-score → final rank. Visual decomposition.
- **Component time series:** How each component evolved over time for this stock.
- **Peer comparison:** "VEDL has 42% raw momentum (rank 8 on momentum alone) but 1.8% daily vol (rank 3 on vol). Vol adjustment barely changes its rank."

**Computation:**
- Components already computed in the signal pipeline — just need to persist and expose them.
- Waterfall is a presentation-layer transformation of the stored components.

**API endpoints:**
- `GET /api/analytics/signal/{symbol}` — latest signal decomposition
- `GET /api/analytics/signal/{symbol}/history?window=6m` — component time series

**Frontend:**
- Waterfall chart (horizontal bar: raw momentum → vol penalty → z-score → rank)
- Component history (multi-line chart: momentum, vol, score over time)
- Accessible from any stock mention in the UI (rank tracker, holdings table, etc.)

---

### Cluster B: Portfolio-Level Intelligence

These features answer: "What's happening in my portfolio as a whole?"

#### B1. P&L Attribution & Decomposition

**What it is:** Break down portfolio P&L into per-holding contributions. Not just "stock X went up 3%" (Zerodha shows this) but "stock X contributed 45 bps to portfolio return this week because it was a 4.2% position."

**Why Zerodha can't do this:** Zerodha shows per-stock absolute P&L. It doesn't compute contribution-weighted returns, sector attribution, or factor attribution.

**Data requirements:**
- Daily portfolio holdings with weights (from `momentum_holdings.csv` or the `holdings` table snapshots)
- Daily stock returns (from `nse500_data/`)
- Sector mappings (from sector_analytics pipeline once available, or from universe file `Industry` column as fallback)

**Key views:**
- **Daily/weekly attribution table:** Each holding's weight, return, and contribution to portfolio return. Sorted by contribution.
- **Sector attribution:** Group holdings by sector, show sector-level contribution. "Metals contributed +180 bps, IT dragged -40 bps."
- **Attribution over time:** Stacked area chart showing which sectors/holdings drove returns each week.
- **Concentration risk:** "Top 5 holdings = 21% of portfolio, contributed 65% of this week's P&L."

**Computation:**
- Contribution = weight_i * return_i (for equal-weight, weight = 1/N for each holding)
- Sector attribution = SUM(contribution_i) for all holdings in sector
- Need daily snapshots of holdings — currently we store holdings at rebalance dates. Between rebalances, weights drift with returns. Reconstruct daily weights from rebalance-date weights + daily returns.

**Database changes:**
- New table: `daily_attribution` (date, symbol, weight, stock_return, contribution, sector). Materialized daily from holdings + price data.
- Or compute on-the-fly from holdings snapshots + price data (slower but no new table).

**API endpoints:**
- `GET /api/analytics/attribution?period=1w` — attribution breakdown for period
- `GET /api/analytics/attribution/sectors?period=1m` — sector-level attribution
- `GET /api/analytics/attribution/time-series?window=3m` — stacked attribution over time

**Frontend:**
- Attribution table with contribution bars (green/red horizontal bars per holding)
- Sector donut showing contribution (not just weight — contribution-weighted)
- Stacked area chart for time series attribution

---

#### B2. Risk Analytics

**What it is:** Portfolio-level risk metrics that no Indian retail platform provides: rolling beta, rolling correlation, marginal contribution to risk, drawdown decomposition.

**Why Zerodha can't do this:** Zerodha shows portfolio value and per-stock P&L. It has no concept of portfolio-level risk metrics, factor exposures, or risk decomposition.

**Data requirements:**
- Daily portfolio returns (from `momentum_equity.csv` or `equity_curve` table)
- Daily benchmark returns (from `indices_data/`)
- Daily per-holding returns and weights (same as B1)

**Key metrics:**
- **Rolling beta:** Portfolio beta to Nifty 100 over trailing 60 days. Shows how market-sensitive the portfolio is right now.
- **Rolling correlation:** Portfolio return correlation to benchmark. High correlation = you're paying for an expensive index fund.
- **Rolling Sharpe:** Trailing 60-day Sharpe ratio. Shows whether recent risk-adjusted performance is above or below the backtest average.
- **Marginal contribution to risk (MCTR):** For each holding, how much does it contribute to total portfolio volatility? "VEDL contributes 8.2% of portfolio vol despite being only 4.2% of weight."
- **Drawdown decomposition:** During drawdown periods, which holdings caused the damage? "Jan 2025 drawdown: -12% total, of which NATIONALUM = -3.2%, HINDZINC = -2.8%."
- **Value at Risk (VaR):** Historical 95% VaR — "On 95% of days, portfolio loss is less than X%."

**Computation:**
- Rolling beta: `cov(portfolio_returns, benchmark_returns) / var(benchmark_returns)` over 60-day window.
- MCTR: Requires covariance matrix of holdings. For 24 stocks, this is a 24x24 matrix — feasible to compute daily from trailing 60-day returns.
- Drawdown decomposition: During drawdown windows, sum per-holding contributions (same math as B1, filtered to drawdown periods).
- VaR: Sort trailing 252 daily returns, take 5th percentile.

**Database changes:**
- New table: `portfolio_risk` (date, beta, correlation, rolling_sharpe, var_95, portfolio_vol). One row per day.
- MCTR can be computed on-the-fly (only 24 holdings).

**API endpoints:**
- `GET /api/analytics/risk?window=1y` — rolling risk metrics time series
- `GET /api/analytics/risk/current` — latest risk snapshot
- `GET /api/analytics/risk/mctr` — marginal contribution to risk per holding
- `GET /api/analytics/risk/drawdown-decomposition?start=2025-01-10&end=2025-02-05` — drawdown attribution

**Frontend:**
- Risk dashboard panel with rolling beta, correlation, Sharpe charts
- MCTR bar chart (per holding, sorted by contribution)
- Drawdown waterfall chart during active or historical drawdowns

---

#### B3. Rebalance Impact Preview

**What it is:** Before executing a rebalance, show the projected impact on portfolio risk and sector concentration. "Dropping HINDCOPPER and adding TECHM would reduce metals exposure from 28% to 22% and lower portfolio vol by 1.2%."

**Why Zerodha can't do this:** Zerodha has no concept of forward-looking portfolio analytics. It shows your current holdings, period.

**Data requirements:**
- Current holdings + weights
- Proposed adds/drops from the rebalance signal (already generated Thursday)
- Covariance matrix of holdings (same as B2)
- Sector mappings

**Key views:**
- **Before/after comparison table:** Sector weights, portfolio vol, beta, concentration — current vs. proposed.
- **Risk delta:** "Portfolio vol changes from 22.1% to 21.3% (-0.8%)" and "Beta changes from 1.12 to 1.08."
- **New position profiles:** For each stock being added, show its momentum rank trajectory, volatility, sector, and how correlated it is with existing holdings.

**Computation:**
- Reconstruct post-rebalance weights (equal-weight with new set of 24).
- Compute portfolio vol using covariance matrix with new weight vector.
- Sector concentration is a simple groupby on the new holdings list.

**API endpoints:**
- `GET /api/analytics/rebalance-preview` — impact analysis for pending rebalance (available Thursday onward)

**Frontend:**
- Integrate into existing rebalance workflow page as a "Impact Analysis" tab
- Before/after side-by-side cards
- Risk delta highlighted in green (risk-reducing) or red (risk-increasing)

---

### Cluster C: Regime & Timing Intelligence

These features answer: "What environment are we in, and how should we expect the strategy to perform?"

#### C1. Volatility Regime Indicator

**What it is:** Classify the current market into a volatility regime (low / normal / high / crisis) based on cross-sectional volatility of the NSE 500 universe, and show how the momentum strategy historically performs in each regime.

**Why Zerodha can't do this:** India VIX exists but is a single number based on Nifty options. Cross-sectional realized vol across 500 stocks is a fundamentally different (and arguably better) measure of market stress.

**Data requirements:**
- Daily realized volatility for all NSE 500 stocks (already computed in signal pipeline as `vol_6m`)
- Historical portfolio returns (from `equity_curve` table)

**Key metrics:**
- **Cross-sectional vol:** Median 20-day realized vol across all 500 stocks. Not the same as VIX.
- **Regime classification:** Percentile-based: <25th = low, 25-75th = normal, 75-90th = high, >90th = crisis. Thresholds calibrated from 2020-2026 history.
- **Regime-conditional performance:** "In low-vol regimes, your strategy averages +1.2% weekly with 58% hit rate. In high-vol regimes, +0.4% weekly with 41% hit rate."
- **Regime duration:** "Current high-vol regime has lasted 12 trading days. Historical median duration for high-vol = 18 days."
- **Regime transition probability:** Based on historical frequencies: "After high-vol, probability of returning to normal within 2 weeks = 65%."

**Computation:**
- Cross-sectional vol: `MEDIAN(20d_rolling_std(daily_returns))` across all 500 stocks for each date.
- Regime classification: Rank current value against historical distribution.
- Conditional performance: Group portfolio daily returns by regime label, compute stats per group.

**Database changes:**
- New table: `market_regime` (date, cross_sectional_vol, regime_label, percentile). One row per day.

**API endpoints:**
- `GET /api/analytics/regime?window=1y` — regime time series
- `GET /api/analytics/regime/current` — current regime + conditional performance stats
- `GET /api/analytics/regime/performance` — strategy performance breakdown by regime

**Frontend:**
- Regime indicator badge on the main dashboard (colored: green/yellow/orange/red)
- Regime history chart (shaded background bands on equity curve)
- Conditional performance stats table

---

#### C2. Momentum Factor Health Monitor

**What it is:** Is the momentum factor itself working right now? Measures the spread between winners and losers, factor crowding, and crash risk.

**Why Zerodha can't do this:** Factor analytics don't exist in any Indian retail platform. This is institutional-grade quant intelligence.

**Data requirements:**
- Daily returns for top-quintile and bottom-quintile stocks by momentum rank
- Signal history (from A1's `signal_history` table)
- Correlation matrix of top-ranked stocks

**Key metrics:**
- **Long-short spread:** Return of top-50 stocks minus bottom-50 stocks (equal-weight). Positive = momentum is working. Rolling 20-day average.
- **Factor Sharpe:** Sharpe ratio of the long-short spread over trailing 60 days. Historically > 1.0 = strong momentum environment.
- **Crowding indicator:** Average pairwise correlation among top-24 holdings. Rising correlation = crowded trade = mean-reversion risk. Threshold: warn when avg correlation > 0.4.
- **Momentum crash detector:** Flag when long-short spread has 3+ consecutive negative weeks. Historically rare but devastating (2020 March, 2022 June).

**Computation:**
- Long-short spread: Compute daily equal-weight return of top-50 and bottom-50 from signal ranks + price data.
- Crowding: 24x24 correlation matrix from trailing 60-day returns. Average off-diagonal elements.
- Crash detector: Count consecutive negative weeks in long-short spread.

**Database changes:**
- New table: `factor_health` (date, long_short_spread, factor_sharpe_60d, avg_top24_correlation, consecutive_negative_weeks). One row per day.

**API endpoints:**
- `GET /api/analytics/factor-health?window=1y` — factor health time series
- `GET /api/analytics/factor-health/current` — latest snapshot with alerts

**Frontend:**
- Factor health dashboard panel
- Long-short spread chart with zero line
- Crowding gauge (correlation dial)
- Alert banner when crash detector triggers

---

#### C3. Turnover Forecast

**What it is:** Predict likely portfolio changes before rebalance day by projecting current rank trajectories forward.

**Why Zerodha can't do this:** Zerodha doesn't know your rebalance rules or momentum rankings.

**Data requirements:**
- Current ranks + rank velocity from trailing weeks (from `signal_history`)
- Current holdings list
- Min-hold-days status for each holding

**Key views:**
- **At-risk holdings:** Current holdings whose rank is declining and approaching the exit threshold. "NATIONALUM: rank 22 → 25 over 3 weeks, projected rank 28 next week — likely exit."
- **Emerging candidates:** Non-held stocks whose rank is rapidly improving. "TECHM: rank 45 → 30 → 18, projected rank 12 — likely entry."
- **Stability score:** % of portfolio expected to remain unchanged at next rebalance. "Portfolio stability: 83% (20 of 24 holdings likely to stay)."
- **Min-hold shield:** Holdings protected by min-hold-days that would otherwise be dropped. "IDEA: rank 32 but held only 4 days — shielded until day 8."

**Computation:**
- Rank velocity: Linear regression of rank over trailing 4 data points (weekly ranks).
- Projected rank: Extrapolate velocity by 1 week.
- At-risk: Current holding with projected rank > top-N threshold.
- Emerging: Non-held stock with projected rank < top-N threshold.
- Stability: Count of current holdings with projected rank still in top-N.

**API endpoints:**
- `GET /api/analytics/turnover-forecast` — full forecast with at-risk, emerging, stability

**Frontend:**
- Integrate into rebalance page as a "Forecast" tab (available Monday-Wednesday, before Thursday's actual signal)
- At-risk holdings highlighted in the current holdings table
- Emerging candidates table

---

### Cluster D: Signal Transparency & Strategy Diagnostics

These features answer: "Is the strategy working as expected? Where is it deviating from the backtest?"

#### D1. Backtest-vs-Live Drift Monitor

**What it is:** Continuously compare live portfolio performance against backtested expectations. Flag when live results diverge significantly.

**Why Zerodha can't do this:** Zerodha doesn't know your backtest. This is strategy-specific monitoring.

**Data requirements:**
- Live equity curve (from `equity_curve` table, updated daily)
- Backtested equity curve (from `momentum_equity.csv` for the same date range)
- Trade-level data: live fills vs. backtest assumed fills

**Key metrics:**
- **Cumulative drift:** Live cumulative return minus backtest cumulative return. "Live is -7.2% behind backtest since inception."
- **Rolling drift:** Trailing 60-day return difference. Shows whether drift is widening or narrowing.
- **Slippage gap:** Difference between backtest assumed execution price (OHLC/4 + 20bps) and actual fill prices. "Average realized slippage: 28 bps vs. assumed 20 bps."
- **Timing gap:** Return difference attributable to execution timing (backtest assumes Monday open, live may vary).
- **Hit rate comparison:** Live win rate vs. backtested win rate. "Live: 46.2% vs. Backtest: 49.3% — within normal variance."

**Computation:**
- Drift = live_equity_curve - backtest_equity_curve (aligned by date).
- Slippage gap requires matching live trades with backtest trades by symbol + date, comparing execution prices.
- Hit rate comparison is a simple aggregation from the trades table.

**Database changes:**
- Extend `trades` table (or add columns) to store actual fill prices alongside backtest prices.
- New table: `drift_metrics` (date, cumulative_drift, rolling_drift_60d, avg_slippage_realized, live_hit_rate). Computed weekly.

**API endpoints:**
- `GET /api/analytics/drift?window=1y` — drift time series
- `GET /api/analytics/drift/current` — latest drift summary with alerts

**Frontend:**
- Overlay chart: live vs. backtest equity curves (normalized)
- Drift time series below (green when live outperforms, red when underperforms)
- Alert banner when cumulative drift exceeds a threshold (e.g., -10%)

---

#### D2. Entry/Exit Quality Scoring

**What it is:** Score each completed trade on entry/exit quality. Was the entry at an optimal rank? Did we exit too early or too late?

**Why Zerodha can't do this:** Zerodha shows trade P&L. It doesn't evaluate trade quality relative to the signal that generated it.

**Data requirements:**
- Completed trades with entry/exit dates and prices (from `trades` table)
- Rank at entry and rank at exit (from `signal_history`)
- Post-exit price trajectory (did the stock keep going up after we sold?)

**Key metrics:**
- **Entry rank distribution:** "Average entry rank: 12. 80% of entries are in top-20." — validates signal quality.
- **Exit rank distribution:** "Average exit rank: 28." — shows we're exiting as momentum fades, not prematurely.
- **Missed continuation:** After exit, did the stock continue to rise? "32% of exits saw the stock gain >5% in the next 4 weeks." — quantifies cost of rank-based exits.
- **Holding period vs. optimal:** Compare actual holding period against the period that would have maximized return (hindsight metric, useful for calibrating min-hold-days).
- **Trade quality score:** Composite metric combining entry rank, P&L relative to max possible P&L during holding period, and exit timing. Scale 0-100.

**Computation:**
- Join trades with `signal_history` to get rank at entry and exit dates.
- Missed continuation: For each exit, compute 20-day forward return from exit date using price data.
- Trade quality score: `quality = (actual_return / max_possible_return_during_hold) * (1 - entry_rank/500) * 100`. Weighted formula, tunable.

**API endpoints:**
- `GET /api/analytics/trade-quality?period=6m` — aggregate trade quality metrics
- `GET /api/analytics/trade-quality/{symbol}` — per-stock trade quality history

**Frontend:**
- Trade quality summary cards (avg entry rank, avg exit rank, missed continuation %)
- Scatter plot: entry rank (X) vs. trade P&L (Y) — should show negative correlation (lower rank = higher P&L)
- Integrate quality score into existing trades table as an additional column

---

## Data Architecture

### New Database Tables

| Table | Rows/Day | Total (5yr) | Purpose |
|-------|----------|-------------|---------|
| `signal_history` | ~500 | ~625K | Rank + score components per stock per day |
| `daily_attribution` | ~24 | ~30K | Per-holding weight, return, contribution |
| `portfolio_risk` | 1 | ~1.25K | Rolling beta, correlation, Sharpe, VaR |
| `market_regime` | 1 | ~1.25K | Cross-sectional vol, regime label |
| `factor_health` | 1 | ~1.25K | Long-short spread, crowding, crash flags |
| `drift_metrics` | 1 (weekly) | ~260 | Live vs. backtest drift tracking |

**Total new storage:** ~660K rows, mostly in `signal_history`. At ~100 bytes/row, this is ~66 MB over 5 years. Negligible for PostgreSQL.

### Computation Pipeline

Most analytics are derived from two data sources:
1. **Signal history** — extended from the existing daily signal generation
2. **Price data + holdings** — already available

**Daily pipeline additions:**
```
Existing: fetch prices → build signals → store latest
                                ↓
New:      persist signal_history → compute regime/factor_health
          compute daily_attribution → compute portfolio_risk
```

**Estimated daily compute time:** <30 seconds for all new tables (500-stock universe, simple aggregations).

### Caching Strategy

- **Signal history queries:** Cache rank trajectories for 1 hour (data changes once daily).
- **Risk metrics:** Cache for 1 hour. Invalidate after daily pipeline completes.
- **Attribution:** Cache for 1 hour. Same invalidation.
- **Regime/factor health:** Cache for 1 hour. Rarely queried more than once per session.
- **Breadth indicators:** Cache for 1 hour.

Use the same LRU cache pattern as the existing sector service (invalidated after daily fetch).

---

## Implementation Phasing

### Phase 1: Data Foundation
**Goal:** Build the `signal_history` table and daily persistence pipeline. This table underpins A1, A2, A3, C2, C3, and D2 — so it unlocks the most features.

**Tasks:**
1. Design and create `signal_history` table + Alembic migration
2. Extend `build_momentum_signals_flexible.py` to persist all component columns to DB
3. Backfill `signal_history` from existing signal CSV files (2020-2026)
4. Add `signal_history` persistence to `run_daily_pipeline.py`

**Depends on:** Nothing — can start immediately.

---

### Phase 2: Cross-Sectional Analytics (Cluster A)
**Goal:** Ship Rank Tracker (A1), Breadth (A2), and Signal Decomposition (A3).

**Tasks:**
5. Rank tracker service + API endpoints (A1)
6. Rank movers computation (biggest weekly rank changes)
7. Breadth indicators service + API endpoints (A2)
8. Signal decomposition service + API endpoints (A3)
9. Frontend: Rank tracker chart + rank movers table
10. Frontend: Breadth dashboard panel with traffic-light summary
11. Frontend: Signal decomposition waterfall chart
12. QA: Verify rank trajectories match historical signals, breadth metrics make sense

**Depends on:** Phase 1.

---

### Phase 3: Portfolio Intelligence (Cluster B)
**Goal:** Ship Attribution (B1), Risk Analytics (B2), and Rebalance Preview (B3).

**Tasks:**
13. Attribution service: daily weight reconstruction + contribution calculation (B1)
14. `daily_attribution` table + migration + backfill
15. Risk analytics service: rolling beta, correlation, Sharpe, MCTR, VaR (B2)
16. `portfolio_risk` table + migration + backfill
17. Rebalance impact preview service (B3)
18. API endpoints for attribution, risk, rebalance preview
19. Frontend: Attribution table + sector attribution donut
20. Frontend: Risk dashboard (rolling metrics charts, MCTR bar chart)
21. Frontend: Rebalance impact panel (before/after comparison)
22. QA: Cross-check beta/correlation against manual calculations, verify attribution sums to portfolio return

**Depends on:** Phase 1. Can run in parallel with Phase 2.

---

### Phase 4: Regime & Timing (Cluster C)
**Goal:** Ship Volatility Regime (C1), Factor Health (C2), and Turnover Forecast (C3).

**Tasks:**
23. Volatility regime computation + `market_regime` table + migration (C1)
24. Regime-conditional performance analysis
25. Factor health computation + `factor_health` table + migration (C2)
26. Crowding indicator (pairwise correlation of top-24)
27. Turnover forecast service (C3)
28. API endpoints for regime, factor health, turnover forecast
29. Frontend: Regime indicator badge + regime history chart
30. Frontend: Factor health dashboard (long-short spread, crowding gauge)
31. Frontend: Turnover forecast tab on rebalance page
32. QA: Validate regime classifications against known market events (March 2020 = crisis, 2021 = low vol)

**Depends on:** Phase 1. Can run in parallel with Phases 2 and 3.

---

### Phase 5: Strategy Diagnostics (Cluster D)
**Goal:** Ship Drift Monitor (D1) and Trade Quality (D2).

**Tasks:**
33. Drift monitor service + `drift_metrics` table + migration (D1)
34. Slippage analysis: backtest vs. actual fill prices
35. Trade quality scoring service (D2)
36. API endpoints for drift and trade quality
37. Frontend: Drift overlay chart (live vs. backtest)
38. Frontend: Trade quality summary cards + scatter plot
39. QA: Verify drift calculations, validate quality scores against manual review of sample trades

**Depends on:** Phase 1 + live trading data. Can start once live trade fills are being recorded with actual prices.

---

### Phase 6: Polish & Integration
**Goal:** Unified experience, cross-linking, and alerts.

**Tasks:**
40. Universal stock search bar — type any symbol to see rank tracker + signal decomposition + trade history
41. Cross-linking: click a stock anywhere (holdings, attribution, movers table) → stock detail view
42. Alert system: configurable thresholds for regime change, drift, crowding, rank movements
43. Dashboard home page: summary cards for regime, factor health, portfolio risk, drift status
44. Performance optimization: ensure all analytics pages load in <2 seconds
45. Documentation: API docs for all new endpoints

**Depends on:** Phases 2-5.

---

## Dependency Graph

```
Phase 1: Data Foundation (signal_history table + pipeline)
   │
   ├──► Phase 2: Cross-Sectional Analytics (A1, A2, A3)
   │
   ├──► Phase 3: Portfolio Intelligence (B1, B2, B3)
   │
   ├──► Phase 4: Regime & Timing (C1, C2, C3)
   │
   └──► Phase 5: Strategy Diagnostics (D1, D2)
          │
          └──► Phase 6: Polish & Integration (all clusters)
```

Phases 2, 3, and 4 are independent of each other and can be built in parallel or in any order based on priority.

---

## Priority Recommendation

If building sequentially, the highest-impact order is:

1. **Phase 1** (Data Foundation) — prerequisite, do first
2. **Phase 2** (Cross-Sectional) — Rank Tracker alone is a killer feature, and Signal Decomposition builds trust
3. **Phase 4** (Regime & Timing) — Regime indicator and factor health are daily-use tools for strategy monitoring
4. **Phase 3** (Portfolio Intelligence) — Attribution and risk are valuable but less frequently consulted
5. **Phase 5** (Diagnostics) — Drift and trade quality are important but require live trading history to be meaningful
6. **Phase 6** (Polish) — Integration and alerts tie everything together

---

## Open Questions

- **Alert delivery:** In-dashboard only, or also email/push notifications? Email would require integrating a mail service.
- **Historical backfill depth:** Backfill `signal_history` from 2020 (full backtest range) or only from live trading start date? Full backfill is more useful for regime/breadth analysis but requires reprocessing old signals.
- **Refresh frequency:** Daily is sufficient for most metrics. Should any metrics update intraday (e.g., live portfolio risk during market hours)?
- **Access control:** Are all analytics available to all authenticated users, or are some admin-only?
- **Mobile responsiveness:** Some of these visualizations (waterfall charts, correlation matrices) are complex. Target desktop-first, or invest in mobile layouts?
