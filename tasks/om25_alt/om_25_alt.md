# Omega Alternatives

## Context

OM25 using raw Omega Ratio appears to overlap heavily with the existing momentum portfolio.

This is expected because high Omega often comes from stocks with strong positive returns and limited downside, which can make it behave like smoother momentum.

The goal is to either modify Omega so it becomes more differentiated, or test different ratio-based strategy families.

---

## Path 1: Modify Omega

### 1. Relative Omega 25 / ROM25

Compute Omega on excess returns instead of absolute returns.

```text
excess_return = stock_daily_return - Nifty500_daily_return
```

This asks:

> Which stocks beat the market more cleanly than they lag the market?

This is the first Omega variant worth testing.

---

### 2. Sector-Neutral ROM25

Same as ROM25, but add sector constraints.

Example:

```text
Max 3 or 4 stocks per sector
```

This may reduce concentration in hot momentum sectors.

---

### 3. Residual Omega

Regress stock returns against benchmark returns:

```text
stock_return = alpha + beta * market_return + residual
```

Then compute Omega on residual returns.

This asks:

> Which stocks have favorable idiosyncratic upside/downside behavior after removing market beta?

---

### 4. Momentum-Excluded Omega

Exclude the top momentum stocks before ranking by Omega.

Example:

```text
Exclude top 20% by 6-month momentum
Rank remaining stocks by Omega
Select top 25
```

This intentionally avoids the most crowded momentum names.

---

## Path 2: Try Different Ratio-Based Strategies

### 1. Ulcer Index 25 / UI25

Rank stocks by low Ulcer Index.

Ulcer Index measures depth and duration of drawdowns.

Possible score:

```text
Score =
  40% low Ulcer Index
+ 30% positive 12M return
+ 30% low downside deviation
```

This could become a “smooth compounders” portfolio.

---

### 2. Low Volatility 25 / LV25

Rank by low realized volatility and/or low beta.

Possible signals:

```text
- 252-day realized volatility
- 252-day beta to Nifty 500
- downside deviation
- max drawdown
```

This is likely more differentiated from momentum and easier to explain to conservative subscribers.

---

### 3. Relative Sortino 25

Compute Sortino on excess returns:

```text
excess_return = stock_return - benchmark_return
Sortino = mean(excess_return) / downside_deviation(excess_return)
```

This may be similar to Relative Omega but simpler.

---

### 4. Consistency Score 25 / CS25

Select stocks with consistent positive participation rather than explosive momentum.

Possible signals:

```text
- % positive months in last 12 months
- % positive weeks in last 52 weeks
- low monthly return volatility
- positive 12M return filter
```

This could identify steady performers rather than high-momentum spikes.

---

### 5. Pullback 25 / PB25

A short-term mean reversion strategy.

Basic idea:

```text
Buy stocks in long-term uptrends that are temporarily oversold.
```

Possible signals:

```text
- RSI(2) or RSI(5)
- short-term return z-score
- price below 20 DMA but above 200 DMA
```

This may be more differentiated, but turnover and subscriber execution may be harder.

---

## Recommended Test Order

1. ROM25: Relative Omega using stock returns minus Nifty 500 returns.
2. Sector-Capped ROM25.
3. UI25: Low Ulcer Index / smooth compounder portfolio.
4. LV25: Low volatility / low beta defensive equity portfolio.
5. CS25: Return consistency portfolio.

---

## Key Comparison Metrics

Compare every candidate against Momentum, TL25, OM25, and the benchmark.

```text
- CAGR
- Sharpe
- Sortino
- Max drawdown
- Calmar
- Portfolio Omega
- Correlation with Momentum
- Correlation with TL25
- Average holdings overlap
- Latest holdings overlap
- Turnover
- Sector concentration
- Average cash allocation
```

---

## Main Decision Question

The next strategy should become a separate subscriber portfolio only if it is meaningfully differentiated.

Ask:

> Does this strategy provide a distinct return/risk profile, lower overlap, and a clear subscriber use case compared with Momentum and TL25?
