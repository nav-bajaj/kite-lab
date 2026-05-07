# Phase 3: Run All 4 Backtest Variants

**Status:** Done

**Depends on:** Phase 1 (signals) + Phase 2 (backtest engine)

---

## Objective

Run all 4 strategy variants, validate results, and compare performance across variants.

---

## Tasks

- [ ] **3.1** Generate composite signals (Phase 1 output)
- [ ] **3.2** Generate persistence-only signals (`--scoring-mode persistence_only`)
- [ ] **3.3** Run Variant 1: Base (monthly entry + weekly exit, no market filter)
- [ ] **3.4** Run Variant 2: Market Filter (+ Nifty 500 < 200 DMA caps at 50%)
- [ ] **3.5** Run Variant 3: Monthly Only (no weekly exit checks)
- [ ] **3.6** Run Variant 4: Persistence Only (simpler signal, weekly exits)
- [ ] **3.7** Validate all 4 variants pass verification checks
- [ ] **3.8** Create comparison summary table across variants

---

## Variant Definitions

| # | Name | Signals | Entry | Exit | Market Filter | Output Dir |
|---|------|---------|-------|------|---------------|------------|
| 1 | Base | Composite TQS | Monthly | Weekly (`Close < 200 DMA`) | No | `backtests/base/` |
| 2 | Market Filter | Composite TQS | Monthly | Weekly | Yes (50% cap) | `backtests/market_filter/` |
| 3 | Monthly Only | Composite TQS | Monthly | Monthly only | No | `backtests/monthly_only/` |
| 4 | Persistence Only | Persistence rank | Monthly | Weekly | No | `backtests/persistence_only/` |

---

## Commands

```bash
# Variant 1: Base
python scripts/backtest_trend_leaders.py \
  --signals data/trend_leaders/signals/trend_leaders_signals.csv \
  --prices-dir nse500_data \
  --benchmark data/benchmarks/nifty100.csv \
  --output-dir data/trend_leaders/backtests/base \
  --variant base

# Variant 2: Market Filter
python scripts/backtest_trend_leaders.py \
  --signals data/trend_leaders/signals/trend_leaders_signals.csv \
  --prices-dir nse500_data \
  --benchmark data/benchmarks/nifty100.csv \
  --output-dir data/trend_leaders/backtests/market_filter \
  --variant market_filter \
  --market-filter-index indices_data/NIFTY_500.csv

# Variant 3: Monthly Only
python scripts/backtest_trend_leaders.py \
  --signals data/trend_leaders/signals/trend_leaders_signals.csv \
  --prices-dir nse500_data \
  --benchmark data/benchmarks/nifty100.csv \
  --output-dir data/trend_leaders/backtests/monthly_only \
  --variant monthly_only

# Variant 4: Persistence Only
python scripts/build_trend_leaders_signals.py \
  --prices-dir nse500_data \
  --output data/trend_leaders/signals/persistence_only_signals.csv \
  --scoring-mode persistence_only \
  --top-n 20

python scripts/backtest_trend_leaders.py \
  --signals data/trend_leaders/signals/persistence_only_signals.csv \
  --prices-dir nse500_data \
  --benchmark data/benchmarks/nifty100.csv \
  --output-dir data/trend_leaders/backtests/persistence_only \
  --variant base
```

---

## Key Questions Each Variant Answers

| Variant | Question |
|---------|----------|
| Base | Does the core strategy produce a reasonable 15-25 stock portfolio? |
| Market Filter | Does the macro overlay improve risk-adjusted returns or just reduce CAGR? |
| Monthly Only | Do weekly exit checks reduce drawdown, or just cause whipsaw? |
| Persistence Only | Does the composite TQS add value over a simpler single-factor signal? |

---

## Expected Comparison Table

```
| Metric              | Base    | Market Filter | Monthly Only | Persistence Only |
|---------------------|---------|---------------|--------------|------------------|
| CAGR                |         |               |              |                  |
| Max Drawdown        |         |               |              |                  |
| Sharpe Ratio        |         |               |              |                  |
| Sortino Ratio       |         |               |              |                  |
| Calmar Ratio        |         |               |              |                  |
| Annualized Turnover |         |               |              |                  |
| Avg Cash %          |         |               |              |                  |
| Avg Holdings        |         |               |              |                  |
| Hit Rate            |         |               |              |                  |
| Total Trades        |         |               |              |                  |
```

---

## Validation Per Variant

For each variant, verify:
- [ ] Equity curve is monotonically non-decreasing in good periods (no data errors)
- [ ] Cash % matches expected behavior (higher in corrections)
- [ ] Holdings count stays within bounds
- [ ] Market filter variant shows reduced exposure when Nifty 500 < 200 DMA
- [ ] Monthly-only variant has fewer trades than base
- [ ] Persistence-only variant has different stock selection than composite
