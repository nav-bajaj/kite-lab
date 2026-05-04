# Phase 4: Report Generation & Momentum Comparison

**Status:** Done

**Depends on:** Phase 3 (all backtest variants completed)

---

## Objective

Generate HTML reports for Trend Leaders 20 and produce a detailed comparison against the existing momentum strategy to determine if TL20 is differentiated enough to be a separate subscriber product.

---

## Tasks

- [ ] **4.1** Generate HTML report for all 4 TL20 variants (equity curves, drawdown, heatmaps)
- [ ] **4.2** Load existing momentum equity curve (`data/backtests/momentum_equity.csv`)
- [ ] **4.3** Compute return correlation (daily + monthly) between TL20 and momentum
- [ ] **4.4** Compute drawdown overlap analysis
- [ ] **4.5** Identify months where momentum was down but TL20 was flat/up (and vice versa)
- [ ] **4.6** Compute combined portfolio metrics (50/50 blend)
- [ ] **4.7** Generate comparison report HTML
- [ ] **4.8** Create summary metrics table across all strategies

---

## Report 1: Trend Leaders 20 Strategy Report

**Output:** `data/trend_leaders/reports/trend_leaders_20_report.html`

**Approach:** Reuse `scripts/report_backtests.py` which generates HTML from backtest output directories. The existing `analyze_run()` function works on any directory with `*_equity.csv`, `*_trades.csv`, etc.

**Contents:**
- Equity curve vs benchmark (all 4 variants overlaid)
- Drawdown curve
- Monthly returns heatmap
- Rolling 6-month and 12-month returns
- Rolling volatility
- Number of holdings over time
- Cash allocation over time
- Turnover over time
- Trade distribution (P&L histogram)
- Summary metrics table comparing all 4 variants
- Top drawdown periods analysis
- Current holdings breakdown (latest rebalance)

---

## Report 2: Momentum Comparison Report

**Output:** `data/trend_leaders/reports/comparison_vs_momentum.html`

**Contents:**

### Performance Comparison Table
```
| Metric              | Momentum (NSE500 L6) | TL20 Base | TL20 + Market Filter | Benchmark |
|---------------------|----------------------|-----------|----------------------|-----------|
| CAGR                | 59.4%                |           |                      | ~15%      |
| Max Drawdown        | -30.0%               |           |                      | ~-20%     |
| Sharpe Ratio        | 1.92                 |           |                      | ~0.7      |
| Sortino Ratio       |                      |           |                      |           |
| Calmar Ratio        |                      |           |                      |           |
| Annualized Turnover | 123%                 |           |                      | 0%        |
| Avg Holding Days    | 43.3                 |           |                      |           |
```

### Correlation Analysis
- Daily return correlation (target: < 0.7)
- Monthly return correlation
- Rolling 6-month correlation over time (chart)

### Drawdown Overlap
- Scatter plot: momentum drawdown vs TL20 drawdown by month
- Months where momentum DD > 5% but TL20 DD < 2% (diversification value)
- Months where both strategies are in drawdown (systemic risk)

### Differential Analysis
- Monthly returns where momentum was negative but TL20 was positive
- Monthly returns where TL20 held significant cash (>20%)
- Overlap in stock holdings (% of TL20 stocks also in momentum portfolio)

### Combined Portfolio (50/50 Blend)
- CAGR, Sharpe, max DD of a 50% momentum + 50% TL20 blend
- Does the blend have better risk-adjusted returns than either alone?
- Equity curve of the blend vs each strategy

---

## Metrics Required

From the handoff spec, ensure all these are reported:

```
Total Return
CAGR
Annualized Volatility
Sharpe Ratio
Sortino Ratio
Max Drawdown
Calmar Ratio
Win Rate by Month
Best Month
Worst Month
Average Monthly Return
% Time Invested (non-cash)
Average Number of Holdings
Median Number of Holdings
Average Cash Allocation
Average Turnover per Rebalance
Annualized Turnover
Number of Trades
Average Holding Period
Correlation with momentum returns
Correlation with benchmark returns
```

---

## Charts Required

```
Equity curve vs benchmark
Drawdown curve
Monthly returns heatmap
Rolling 6-month returns
Rolling 12-month returns
Rolling volatility
Number of holdings over time
Cash allocation over time
Turnover over time
```

---

## Key Differentiation Thresholds

The strategy is worth offering as a separate product if:
- [ ] Return correlation with momentum < 0.7
- [ ] Max drawdown is lower than momentum (-30%)
- [ ] Turnover is significantly lower than momentum (123%)
- [ ] Cash allocation is meaningful during corrections (>20% at some point)
- [ ] 50/50 blend has better Sharpe than either strategy alone
