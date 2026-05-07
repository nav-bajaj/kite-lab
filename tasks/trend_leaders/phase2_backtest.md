# Phase 2: Backtest Engine

**File:** `scripts/backtest_trend_leaders.py`

**Status:** Done

**Depends on:** Phase 1 (needs signals CSV)

---

## Objective

Build a backtest engine with a dual-frequency rebalance loop: monthly entries + weekly exit checks. This is a new script (not a modification of the momentum engine) because the loop structure is fundamentally different.

---

## Tasks

- [ ] **2.1** Import reusable functions from `backtest_momentum.py` (`load_price_panels`, `load_benchmark`, `map_signal_to_trade`)
- [ ] **2.2** Implement signal loader for trend leader signals format
- [ ] **2.3** Pre-compute 200 DMA panel for weekly exit checks
- [ ] **2.4** Derive monthly entry dates (1st trading day of month) and weekly exit dates (last trading day of week)
- [ ] **2.5** Implement dual-frequency main loop (mark-to-market, weekly exits, monthly entries)
- [ ] **2.6** Implement position sizing with 7.5% cap and cash remainder
- [ ] **2.7** Implement trade execution (OHLC/4 + 20 bps slippage, whole shares)
- [ ] **2.8** Implement market filter variant (Nifty 500 < 200 DMA → 50% cap)
- [ ] **2.9** Implement monthly-only variant (no weekly exits)
- [ ] **2.10** Output equity CSV (date, portfolio_value, cash, invested, cash_pct, holdings_count, benchmark, drawdown, exposure)
- [ ] **2.11** Output trades CSV with exit reason (entry/monthly_exit/weekly_exit)
- [ ] **2.12** Output holdings snapshot per monthly rebalance
- [ ] **2.13** Output turnover CSV
- [ ] **2.14** Compute and output metrics CSV (CAGR, Sharpe, Sortino, Calmar, max DD, turnover, hit rate, avg holdings, avg cash%, % time invested)
- [ ] **2.15** Add CLI with argparse and `--variant` flag
- [ ] **2.16** Run base variant and validate

---

## Core Architecture: Dual-Frequency Loop

```python
# Pre-compute date sets
monthly_entry_dates = set(...)   # 1st trading day of each month
weekly_exit_dates = set(...)     # last trading day of each week (W-FRI)

for date in calendar:
    # 1. Mark-to-market
    portfolio_value = cash + sum(shares * close for each holding)

    # 2. WEEKLY EXIT CHECK (before monthly entry if same day)
    if date in weekly_exit_dates and variant != "monthly_only":
        for symbol in list(holdings):
            if close[symbol] < sma_200[symbol]:
                execute_sell(symbol, reason="weekly_exit")
                # Cash stays idle until next monthly

    # 3. MONTHLY ENTRY (1st trading day of month)
    if date in monthly_entry_dates:
        target_symbols = signals[date]

        # Market filter (if enabled)
        if market_filter and nifty500_close < nifty500_sma200:
            max_exposure = 0.50
        else:
            max_exposure = 1.0

        # Sell holdings NOT in new target
        for symbol in list(holdings):
            if symbol not in target_symbols:
                execute_sell(symbol, reason="monthly_exit")

        # Size and buy/rebalance all target positions
        n = len(target_symbols)
        raw_weight = 1/n if n > 0 else 0
        stock_weight = min(raw_weight, 0.075) * max_exposure

        for symbol in target_symbols:
            rebalance_to(symbol, portfolio_value * stock_weight)

    # 4. Record equity, drawdown, cash allocation
```

---

## Position Sizing Detail

```
N >= 20: weight = 1/N each, 0% cash
14 <= N < 20: weight = 1/N each (5.0-7.14%), 0% cash
N < 14: weight = 7.5% each (capped), rest in cash

Mid-month exits: remaining positions drift (no rebalance)
```

---

## Trade Execution

Consistent with momentum engine:
- **Entry price:** OHLC/4 on next trading day after signal
- **Exit price:** OHLC/4 on next trading day after exit signal
- **Slippage:** 20 bps on notional value
- **Whole shares:** Yes (floor allocation, distribute remainder)

---

## Output Files

All prefixed `tl20_` and saved to `--output-dir`:

### `tl20_equity.csv`
```
date,portfolio_value,cash,invested,cash_pct,holdings_count,benchmark,drawdown,exposure
```

### `tl20_trades.csv`
```
date,symbol,side,shares,price,notional,slippage,reason
```
`reason` is one of: `entry`, `monthly_exit`, `weekly_exit`

### `tl20_holdings.csv`
```
date,symbol,shares,cost_basis,weight,entry_date
```
Snapshot at each monthly rebalance.

### `tl20_turnover.csv`
```
date,buy_notional,sell_notional,turnover,turnover_pct
```

### `tl20_metrics.csv`
```
start,end,total_return,cagr,max_drawdown,max_drawdown_duration_days,
annualized_volatility,sharpe_ratio,sortino_ratio,calmar_ratio,
avg_turnover_pct,annualized_turnover,cost_drag_pct,
hit_rate_overall,avg_holding_days,median_holding_days,
trades_total,buys,sells,
avg_holdings_count,median_holdings_count,avg_cash_pct,pct_time_invested,
weekly_exits_count,monthly_exits_count
```

---

## CLI Interface

```bash
python scripts/backtest_trend_leaders.py \
  --signals data/trend_leaders/signals/trend_leaders_signals.csv \
  --prices-dir nse500_data \
  --benchmark data/benchmarks/nifty100.csv \
  --output-dir data/trend_leaders/backtests/base \
  --initial-capital 1000000 \
  --top-n 20 \
  --max-weight 0.075 \
  --slippage 0.002 \
  --variant base
```

**`--variant` options:**
- `base` — Monthly entry + weekly exit, no market filter
- `market_filter` — Same + Nifty 500 < 200 DMA caps exposure at 50%
- `monthly_only` — Monthly entry and exit only, no weekly checks

Market filter uses: `--market-filter-index indices_data/NIFTY_500.csv`

---

## Validation Criteria

- [ ] Cash invariant: `portfolio_value == cash + sum(shares * close)` at every timestep
- [ ] No stock exceeds 7.5% weight at entry
- [ ] Holdings never exceed `top_n` (20 in base)
- [ ] Weekly exits only fire on weekly check dates
- [ ] Every weekly-exited stock had `close < sma_200` on exit date
- [ ] Exited stocks stay out until next monthly rebalance
- [ ] No lookahead: signals use date t, execution on date t+1
- [ ] Cash never goes negative
- [ ] Total return matches equity curve endpoint

---

## Key Dependencies

| File | Usage |
|------|-------|
| `scripts/backtest_momentum.py` | Import `load_price_panels`, `load_benchmark`, `map_signal_to_trade` |
| `ta_indicators.py` | Import `sma()` for 200 DMA pre-computation |
| `indices_data/NIFTY_500.csv` | Market filter index (Variant 2) |
| `data/benchmarks/nifty100.csv` | Benchmark for comparison |
| Phase 1 signals CSV | Backtest input |
