# OM25 — Design & Decisions Log

> ⚠️ **REBASELINED MAY 2026.** Earlier numbers in this doc reflected a same-day-close → same-day-OHLC/4 lookahead bug in the weekly trailing-stop logic. The fix is in `scripts/_clean_engine.py` (the engine used for all enhanced OM25 variants). Strategy parameters and design decisions are unchanged; performance figures are corrected to honest no-lookahead values throughout.

## Strategy Identity

**Core thesis:** Stocks that participate more in market rallies AND have asymmetric upside-vs-downside behavior compound faster with less pain. Different lens from momentum (highest returners) and trend-following (cleanest uptrends).

**What makes it different:**
- Momentum asks: "What went up the most?"
- TL25 asks: "What has the cleanest trend structure?"
- OM25 asks: "What goes up aggressively on good days AND has structural downside protection?"

A stock can have high momentum but terrible capture ratio (it went up 100% but crashed 30% on every market dip). A stock can have mediocre momentum but excellent capture ratio (it only went up 40% but participated in every rally and dodged every selloff). OM25 selects the latter.

---

## Final Production Configuration

### Two Tiers, One Signal

```
SIGNAL (identical for both tiers):
  upside_capture = avg(stock return on market-up days) / avg(market return on up days)
  capture_ratio  = upside_capture / downside_capture
  composite      = 0.5 * percentile_rank(upside_capture) + 0.5 * percentile_rank(capture_ratio)
  Select top 25 by composite, percentile-ranked among eligible stocks (cross-sectional).

ELIGIBILITY:
  - 220+ valid daily return observations in the 252-day lookback
  - Positive 252-day total return

EXIT (identical for both tiers):
  - Weekly check
  - Sell if Close < 200 DMA OR Close < (peak × (1 - 4 × ATR(20)))
  - Exit buffer: drop from holdings if rank falls below 40 at next rebalance

SIZING:
  - Equal weight (1/N), max 7.5% per position
  - Incremental: only buy new entrants, let continuing positions drift

SLIPPAGE:
  - 20 bps (OHLC/4 pricing on next trading day after signal)

DIFFERENT BETWEEN TIERS:
  Monthly tier:   Entry on 1st trading day of each month
  Bi-weekly tier: Entry every other Friday
```

### Tier 1 — Monthly (Conservative)
| Metric | Value |
|--------|-------|
| CAGR | 54.4% |
| Max DD | -24.0% |
| Sharpe | 2.76 |
| Sortino | 3.44 |
| Calmar | 2.27 |
| Vol | 19.7% |
| Beta | 0.82 |
| Avg Cash | 21.4% |

### Tier 2 — Bi-weekly (Aggressive)
| Metric | Value |
|--------|-------|
| CAGR | 60.6% |
| Max DD | -25.1% |
| Sharpe | 2.61 |
| Sortino | 3.06 |
| Calmar | 2.42 |
| Vol | 23.2% |
| Beta | 1.04 |
| Avg Cash | 10.0% |

---

## Why Both Tiers?

The two tiers serve different subscriber profiles. They are NOT independent strategies — they share the exact same signal. The differentiation is purely in **deployment cadence**.

### Monthly = Defensive via Cash Drag

Cross-correlation analysis between the two tiers:

| Measurement | Monthly | Bi-weekly | Gap |
|-------------|---------|-----------|-----|
| Headline beta | 0.82 | 1.04 | +0.22 |
| Stock-portion beta (cash removed) | 1.20 | 1.21 | +0.005 |

**98% of the beta gap is explained by cash drag, not stock selection.** Both tiers pick stocks with the same ~1.20 deployed beta. Monthly's "lower beta" comes from holding 21% cash on average vs bi-weekly's 10%.

This means:
- They use **identical stock selection** (same signal, same composite score)
- They differ only in **how often cash gets redeployed**
- Cash itself functions as the implicit risk modulator on the monthly tier

### Drawdown Personalities

| | Monthly | Bi-weekly |
|---|---------|-----------|
| # Significant DDs (>5%) | 11 | 17 |
| # Deep DDs (>10%) | 4 | 6 |
| Avg DD duration | 80 days | 32 days |
| Longest DD | 353 days | 328 days |

- **Monthly:** Fewer drawdowns, but each one lasts ~2.5 months. Slow to recover because it "freezes" in cash for weeks.
- **Bi-weekly:** More frequent drawdowns but each ~1 month. Recovers ~2.5x faster because it can redeploy capital every 2 weeks.

### When Each Wins

| Year | Monthly | Bi-weekly | Winner |
|------|---------|-----------|--------|
| 2022 (rate-hike chop) | +0.2% | +11.7% | Bi-weekly (faster post-correction redeploy) |
| 2023 (clean bull) | +83.0% | +106.1% | Bi-weekly (captures bull better) |
| 2024 | +57.2% | +60.1% | Tied |
| 2025 (chop + correction) | -4.4% | -8.7% | Monthly (cash buffer) |
| 2026 YTD | +18.1% | +12.0% | Monthly |

**Bi-weekly wins clean trends. Monthly wins choppy/down markets.** Subscribers can choose based on their risk tolerance.

---

## Evolution of the Signal

### V1: Pure Omega Ratio (Rejected)
- Signal: sum(positive returns) / abs(sum(negative returns))
- Result: 35.4% CAGR, 1.59 Sharpe
- Rejected: 0.92 correlation with momentum — Omega Ratio is essentially momentum restated in distributional terms

### V2: Upside/Downside Capture Ratio (Foundation)
- Signal: upside_capture / downside_capture
- Result: 32.9% CAGR, 2.20 Sharpe, 0.79 correlation
- Why it works: measures market-sensitivity asymmetry, not absolute return. Two stocks with identical omega can have very different capture ratios.

### V3: Upside Capture Only (Bridge)
- Signal: upside_capture only (drop denominator)
- Result: 45.2% CAGR, 2.04 Sharpe, -27.3% DD
- Higher CAGR but worse drawdown — picks aggressive stocks that also fall hard

### V4: Composite Score (FINAL)
- Signal: 50/50 percentile rank of upside_capture + capture_ratio
- Picks stocks that score well on BOTH dimensions
- Result: 54.4% CAGR, 2.76 Sharpe, -24.0% DD (Monthly)
- The composite balances aggressive upside with structural downside protection

### Why composite score works:
- Pure capture_ratio: too defensive, picks low-vol "stable" stocks
- Pure upside_capture: too aggressive, picks high-beta names that crash hard
- 50/50 blend: requires high upside AND good asymmetry — finds stocks that are aggressive but smart

---

## Trading Mechanics Decisions

### Why this exit logic
- **4x ATR (no floor)**: Tested 3x (too tight, 25.9% CAGR clipped winners), 5x (too loose), N-day low (never triggers before 200 DMA). 4x adapts to each stock's volatility.
- **Weekly exit checks**: 4x ATR is wide enough to handle weekly noise; bi-weekly checks reduce stops marginally but the 4x already absorbs noise.
- **200 DMA secondary trigger**: Catches stocks that break trend regardless of ATR drift.

### Why incremental sizing (not full rebalance)
- Full rebalance generated 2696% turnover — absurd
- Winners that grow to 6-7% of portfolio should drift, not be trimmed
- Incremental: only buy new entrants with freed cash; continuing positions ride

### Why exit buffer 15 (rank > 40 = exit)
- Prevents month-to-month rank noise from causing unnecessary selling
- 10 was too tight (more churn), 20 was tested but no improvement

### Why 25 stocks (not 20 or 30)
- 20: too concentrated, single-stock risk
- 25: sweet spot
- 30: dilutes the signal, marginal CAGR loss

### Why positive return filter is needed
- Without it, OM25 picks high-capture stocks that have negative 252d returns
- These are usually beaten-down low-quality names with statistical artifacts
- Filter ensures structural quality even if signal looks great

---

## Risk-Off Mechanisms — Tested and Rejected

We tested four explicit risk-off filters on top of bi-weekly OM25 to see if we could systematically reduce drawdowns. All were rejected.

| Mechanism | CAGR | Max DD | Sharpe | Verdict |
|-----------|------|--------|--------|---------|
| Bi-weekly baseline | 60.6% | -25.1% | 2.61 | — |
| V1: Index < 200 DMA → 50% exposure | 55.3% | -19.1% | 2.64 | 200 DMA too coarse, costs 5.3% CAGR |
| V2: Breadth <30% → 50% exposure | 58.9% | -19.1% | 2.73 | Quietly defensive but barely activated when needed (2025) |
| V3: Skip entries when index < 50 DMA | 53.8% | -16.6% | 2.79 | Best DD but cost 12% YTD in 2026 (skipped recovery) |
| V4: Half-exit on weekly stops | 55.6% | -23.3% | 2.44 | More trades, worse Sharpe (whipsaw) |

### Why all four were rejected

1. **The baseline already has internal protection** — 4x ATR + 200 DMA exits handle most stock-specific risk
2. **DD character > DD depth** — baseline's -25% DD recovers in <1 year. V3's lower DD comes with sluggish 50 DMA filter that misses sharp recoveries
3. **Compound speed > drawdown reduction** — V3's -1.2% YTD vs baseline +36.4% in 2026 alone is a 12.6% gap. Compounded over years, this is catastrophic
4. **Cash drag is already implicitly providing risk management** in the monthly variant — adding another layer is double-counting
5. **Filter complexity invites overfitting** — every threshold (30% breadth, 50 DMA, etc.) is another parameter to fit to past data

The strategy stays clean. Both monthly and bi-weekly stand on their own merits. Cash drag (in monthly) is the only "filter" — and it emerges naturally from rebalance cadence, not from an added rule.

---

## Exit Analysis

| Exit Reason | % of Exits (Monthly) | % of Exits (Bi-weekly) | Avg P&L | Character |
|-------------|---------------------|------------------------|---------|-----------|
| ATR trailing stop | 70.8% | 59.9% | +4.3% | Protective but clips some winners |
| Close < 200 DMA | 20.9% | 28.4% | -4.3% | Crash protector |
| Rank drop | 8.3% | 11.7% | +17.6% | Healthy rotation |

The ATR stop fires most often because capture-ratio stocks are "quality beta" — they participate in market moves, which means they also participate in corrections (just less than the market). The stop catches those that overcorrect.

---

## Differentiation From Other Strategies

| Dimension | Momentum | TL25 | OM25 (Monthly) | OM25 (Bi-weekly) |
|-----------|----------|------|----------------|-------------------|
| Signal type | 6m return / vol | Trend structure | Composite capture | Same |
| What it asks | What went up most? | Cleanest uptrend? | Best asymmetric beta? | Same |
| Corr with momentum | 1.00 | 0.89 | 0.82 | 0.87 |
| Corr with TL25 | 0.89 | 1.00 | 0.87 | 0.88 |
| DD behavior | Holds through crashes | Trailing stop on extended | 4x ATR adaptive | Same |
| Max DD | -35% | -21% | -24% | -25% |
| Recent CAGR (2024+) | 1% | 20% | 27% | 22.5% |
| Best in | Strong bulls | Any trending market | Choppy/down | Clean trends |

---

## Robustness Concerns

### What could go wrong:
- **Capture ratio is backward-looking** — a stock's market sensitivity can change (management change, sector rotation, liquidity shift)
- **Market regime dependence** — in a prolonged bear market, "high upside capture" stocks have fewer up-days to capture
- **Survivorship bias** — using current NSE 500 constituents for full history
- **252-day lookback is long** — slow to react to regime changes

### What gives confidence:
- 0.82 correlation with momentum (genuinely different)
- Signal is structural (beta asymmetry) not just return-based
- 2.76 Sharpe + 3.04 universe-subset robustness suggests real predictive power
- -24% max DD is well-controlled
- Both tiers consistently outperformed across periods 2022, 2023, 2024
- Even in 2025 (worst recent year), monthly was only -4.4% vs momentum's -16.8%

---

## Why Risk-Off Filters Don't Help

This was a critical finding. We assumed adding risk-off filters would improve risk-adjusted returns. They didn't. Why?

1. **The trailing stop is already a risk-off filter** — at the stock level, not the portfolio level. When a stock breaks down, it gets sold. This is faster and more targeted than waiting for index/breadth signals.

2. **Cash piles up automatically when stocks break down** — during corrections, many stocks hit their stops and cash builds up to 30-80% (we observed 82% cash in March 2026). This IS the auto-defensive mechanism — no explicit filter needed.

3. **The filter slows down the recovery** — the worst part of any drawdown protection is missing the recovery rally. Index-based filters (200 DMA, 50 DMA, breadth) all signal LATE on recoveries. The strategy ends up sitting in cash while baseline is buying.

4. **In aggregate, missed recoveries cost more than avoided drawdowns** — over a 5+ year horizon, missing one V-shape recovery costs 10-15% CAGR, while a typical drawdown only costs 2-5% over the period.

The cleanest solution: **let the trailing stop do the work**. It's already doing risk management at the right level (per-stock, in real-time).

---

## Files

| File | Purpose |
|------|---------|
| `scripts/build_om25_signals.py` | Signal computation (omega + capture ratio) |
| `scripts/backtest_om25.py` | Backtest engine (monthly rebalance, equal weight) |
| `tasks/om25/README.md` | Summary, results, two-tier offering |
| `tasks/om25/DESIGN.md` | This file — decisions, rationale, lessons learned |

---

## Production Status

**Locked-in for production:**
- OM25 Monthly tier (NSE 500, 1st trading day of month)
- OM25 Bi-weekly tier (NSE 500, every other Friday)

Both share identical signal, eligibility, exit, and sizing logic. They differ only in entry cadence.

**Not pursuing:**
- Explicit risk-off filters (V1-V4 all tested and rejected)
- Sub-tier variations of frequency (weekly was tested earlier and adds correlation without adding diversification)
- Universe variants for subscriber product (NSE 500 is the primary; Nifty 250/100 are documented but not separately marketed yet)

**Open questions for future:**
- Should universe expand to include all NSE Eq 500 + 250 mid-caps with sufficient liquidity?
- Sector concentration analysis (does the strategy ever load up on one sector unintentionally?)
- Position sizing by composite score (signal-weighted) — was tested earlier, marginal benefit, not worth the complexity

---

*Last updated: May 2026*
