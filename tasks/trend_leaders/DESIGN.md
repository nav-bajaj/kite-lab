# Trend Leaders 20 — Design Decisions & Architecture

## Why a Separate Backtest Engine

The existing `backtest_momentum.py` assumes a **single uniform rebalance frequency** — entry and exit happen on the same weekly dates. Trend Leaders 20 needs **dual-frequency rebalancing**:

- **Monthly entry**: New positions selected once per month (1st trading day)
- **Weekly exit**: Existing positions checked every Friday for trend breaks

Grafting this onto the momentum engine would require pervasive changes to its calendar loop, exit logic, and position sizing — all of which would risk breaking the production momentum strategy. A separate engine is cleaner.

**What we DO reuse:** Utility functions (`load_price_panels`, `load_benchmark`, `map_signal_to_trade`, `sma`) are imported directly. The new engine follows the same patterns but has a fundamentally different main loop.

---

## Slippage: 20 bps (Not 10 bps)

The handoff spec suggested 10 bps slippage. We use **20 bps** instead because:

1. The existing momentum engine uses 20 bps with OHLC/4 pricing
2. Comparison between strategies must be apples-to-apples
3. 20 bps is more conservative/realistic for NSE 500 mid-caps
4. We can always re-run with 10 bps as a sensitivity test later

---

## Trade Execution Timing

Consistent with the momentum engine:

```
Signal date: close of date t (e.g., Friday close for weekly exit, 1st-of-month close for monthly entry)
Execution: OHLC/4 on date t+1 (next trading day)
Slippage: 20 bps on notional value
```

The `map_signal_to_trade()` function handles the date mapping, looking up to 5 calendar days forward to find the next trading day.

---

## Decision Change: Incremental Sizing (Not Full Rebalance)

**Original plan:** Full rebalance at monthly entry — size all positions to equal target weight.

**What happened:** Full rebalance generated massive unnecessary turnover. Even when 15 of 20 stocks persisted month-to-month, every position was trimmed/topped up to exact target weight. This generated 2696% annualized turnover — absurd for a "calmer" strategy.

**Final approach:** Incremental sizing. At monthly rebalance:
1. Sell only stocks that dropped below the exit threshold
2. Buy only NEW entrants with freed cash
3. Continuing positions drift — no trim/top-up

This reduced trades from ~1800 to ~1176 while improving CAGR from 16.5% to 20.8%.

---

## Decision Change: Raw Scores (Not Percentile Ranking)

**Original plan (from handoff spec):** Percentile-rank each TQS component cross-sectionally, then weighted sum.

**What happened:** Percentile ranking amplified tiny score differences. In bull markets, hundreds of stocks have near-identical raw scores (e.g., all with perfect MA stacking, perfect persistence). Percentile ranking converted these tiny differences into full 0-to-1 spreads, making rankings extremely volatile.

**Result:** Only 6.7 of 20 stocks persisted month-to-month (with either percentile or raw scoring). This is the fundamental driver of high turnover — it's a signal quality issue, not a backtest issue.

**Final approach:** Use raw component scores directly (all already 0-1 scaled) without percentile transformation. This didn't fix the persistence problem by itself (still 6.7/20) but produces more interpretable scores.

---

## Decision Added: Exit Hysteresis (Buffer = 20)

**Problem:** With strict top-20 entry/exit, a stock at rank 18 one month could slip to rank 22 the next (tiny score change), get sold, then re-enter at rank 19 the month after. This "churn at the boundary" caused excessive turnover.

**Solution:** Exit hysteresis. Signal file outputs top 40 stocks (not just top 20). Backtest enters from top 20, but only exits when rank drops below 40. Stocks ranked 21-40 stay in the portfolio.

**Impact with buffer=20 (exit when rank > 40):**
- CAGR: 17.2% → 20.8% (+3.6%)
- Sharpe: 1.03 → 1.25 (+0.22)
- Max DD: -20.1% → -18.9% (+1.2%)
- Monthly exits: 765 → 537 (-30%)

The buffer is the single most impactful improvement to the V1 strategy.

---

## Weekly Exit = Sell Only

When a stock exits mid-month (Close < 200 DMA on weekly check):

1. Position is sold entirely
2. Proceeds go to cash
3. Cash sits idle until next monthly rebalance
4. Remaining positions are NOT rebalanced (they drift)
5. No mid-month replacements

This is the key "calmer" behavior. The portfolio size naturally shrinks during corrections.

---

## Position Sizing Logic

```
If N >= 20 stocks qualify:
    weight = 1/N per stock (= 5% for N=20)
    cash = 0%

If 14 <= N < 20:
    weight = 1/N per stock (5.0% to 7.14%)
    cash = 0%

If N < 14:
    weight = 7.5% per stock (capped)
    cash = 1 - N * 7.5%

Examples:
    20 stocks → 5.0% each, 0% cash
    15 stocks → 6.67% each, 0% cash
    10 stocks → 7.5% each, 25% cash
    5 stocks  → 7.5% each, 62.5% cash
    0 stocks  → 100% cash
```

---

## 200 DMA Pre-computation

The 200 DMA panel is computed once before the backtest loop starts:

```python
sma_200_panel = close_panel.rolling(window=200, min_periods=200).mean()
```

During the weekly exit check, we look up `sma_200_panel.loc[date, symbol]`. This is both fast and ensures consistency between the signal generator and the backtest engine.

**Performance note:** Initial implementation used `close.apply(lambda s: sma(s, 200))` which took 9+ minutes due to per-column overhead. Switching to `close.rolling(200).mean()` (vectorized across all columns) reduced this to seconds.

---

## Trend Quality Score Component Design

### Component 1: MA Structure (30%)

Uses the **binary sub-scores** approach (cleaner and easier to test):

```
ma_score = 0.25 * I(Close > 50 DMA)
         + 0.25 * I(50 DMA > 100 DMA)
         + 0.25 * I(100 DMA > 200 DMA)
         + 0.25 * I(200 DMA slope > 0)
```

Since all eligible stocks already pass `Close > 200 DMA` and `50 > 200 DMA`, most will score 0.50+. The 100 DMA ordering and 200 DMA slope separate the best from the rest.

### Component 2: Trend Persistence (30%)

```
persistence = rolling_63d_count(Close > 100 DMA) / 63
```

Uses 100 DMA (not 200 DMA) because it's a faster signal — a stock can be above 200 DMA for months in a flat market, but being consistently above 100 DMA indicates active uptrend momentum.

### Component 3: Distance from 200 DMA (20%)

Penalized scoring with an "ideal zone" of 5-35% above 200 DMA:

```
distance = Close / 200 DMA - 1

if distance < 0.05:    score = distance / 0.05          (ramp up)
if 0.05 <= d <= 0.35:  score = 1.0                       (ideal zone)
if distance > 0.35:    score = max(0, 1 - (d-0.35)/0.35) (penalize overextension)
```

The 5-35% bands are opinionated. Raw distance is logged in the audit file so bands can be re-tuned.

### Component 4: Drawdown Control (20%)

```
rolling_high_126d = close.rolling(126).max()
score = clip(close / rolling_high_126d, 0, 1)
```

At 6-month high: score = 1.0. Down 10%: score = 0.90. Down 25%: score = 0.75.

### Observed Issue: Score Clustering in Bull Markets

In strong bull markets (eligible count 200-400), the top 20-40 stocks all have:
- MA structure: 1.0 (perfect stacking)
- Persistence: 1.0 (above 100 DMA every day)
- Distance from 200 DMA: 1.0 (in ideal zone)
- Only differentiated by drawdown control (0.90-0.99)

This means the composite TQS provides very little separation. Rankings near the boundary are driven by tiny drawdown differences that change weekly. This is the root cause of the high turnover.

---

## Market Filter Design (Variant 2)

```
If NIFTY_500 close < NIFTY_500 200 DMA:
    max_equity_exposure = 50%
    → All stock weights scaled down proportionally
Else:
    max_equity_exposure = 100%
```

Uses `indices_data/NIFTY_500.csv` for the Nifty 500 index close price.

**Result:** Reduced max DD by 1.1% (17.8% vs 18.9%) but cost 2.9% CAGR (17.9% vs 20.8%). The natural cash mechanism from the eligibility filter already provides some bear market protection.

---

## Benchmark Choice

We use **Nifty 100 TRI** (`data/benchmarks/nifty100.csv`) — same as the momentum strategy. Nifty 500 TRI is not available; flagged as a future TODO.

---

## Handling Edge Cases

### Date overlaps
A date can be both a monthly entry date AND a weekly exit date. Processing order:
1. Weekly exits first (sell broken trends)
2. Monthly entry (select new portfolio)

### Insufficient history
Stocks need at least 200 + 63 = 263 trading days before they become eligible (200 DMA warmup + persistence window). First rebalance date is Feb 2021 (price data starts Jan 2020).

### Corporate actions
The existing price data already includes corporate action adjustments. The trend strategy benefits from this automatically.

---

## Backtest Variants — Results

| # | Name | CAGR | Max DD | Sharpe | Finding |
|---|------|------|--------|--------|---------|
| 1 | Base | 20.8% | -18.9% | 1.25 | Best risk-adjusted (recommended) |
| 2 | Market Filter | 17.9% | -17.8% | 1.20 | Lowest DD, but costly in CAGR |
| 3 | Monthly Only | 20.0% | -20.8% | 1.18 | Weekly exits improve DD by 1.9% |
| 4 | Persistence Only | 23.4% | -29.6% | 1.16 | Highest CAGR but worst DD |

**Variant 3 answered:** Weekly exits DO reduce drawdown (20.8% → 18.9%) without excessive whipsaw (only 41 weekly exits in 5 years).

**Variant 4 answered:** Composite TQS DOES add value — 10.7% lower max DD than persistence-only at the cost of 2.6% CAGR.

---

## V1 Performance Assessment

**What works:**
- Max drawdown (-18.9%) is 11% better than momentum (-30%)
- Sharpe (1.25) and Calmar (1.10) are solid
- Weekly exit checks provide meaningful drawdown protection
- Composite TQS adds value over simpler signals
- Monthly win rate (62.9%) is strong
- Strategy always holds ~20 stocks (minimum eligible was 44)

**What doesn't work:**
- CAGR (20.8%) is too low for an active subscriber product alongside momentum (59.4%)
- Turnover (530%) is too high for a "calmer" strategy
- Rankings are volatile near the selection boundary in bull markets
- Most score differentiation comes from a single component (drawdown control)

**Root cause of low CAGR:** The strategy is defensive by design — it selects the "cleanest" trends, not the strongest. Stocks with the best MA stacking and persistence tend to be mature, well-established uptrends with modest further upside, not the explosive early-stage breakouts that drive high returns.

---

*Created: May 2026*
*Updated: May 2026 — V1 backtest results and implementation lessons*
