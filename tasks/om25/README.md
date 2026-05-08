# OM25 — Composite Capture Score Portfolio

## Overview

Selects stocks with the best **upside-vs-downside market-sensitivity asymmetry** —
participates aggressively in rallies, structurally resists drawdowns. Different
lens from momentum (highest returners) and TL25 (cleanest trend structure).

**Branch:** `om25` (merged into `main`)

> **REVIEWED MAY 2026.** Full parameter review under the clean (no-lookahead)
> engine, with two material engine corrections this review:
> 1. **Daily-peak fix.** Trailing-stop peak now updated every trading day,
>    not just Fridays. The Friday-peak quirk had been quietly making the
>    trailing stop fire too rarely. Numbers below are post-fix.
> 2. **Locked-in stack changes.** Trailing stop dropped entirely, eligibility
>    return-filter dropped. See "Locked-in changes" below.
>
> Earlier numbers (54%-60% CAGR with 4x ATR / positive-return filter) are
> superseded.

---

## Strategy (3 sentences)

> Rank each stock by `0.5 × pct_rank(upside_capture) + 0.5 × pct_rank(capture_ratio)`
> over the past 252 trading days. Buy the top 25 (let winners run, exit
> buffer 15). Exit if Close < 200 DMA on a weekly check, or if rank drops
> below 40 at the next entry rebalance — no trailing stop.

Same signal, two cadences (Monthly and Bi-weekly).

---

## Configuration

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 / Nifty 250 / Nifty 100 |
| Target holdings | 25 |
| Entry frequency | Monthly (1st trading day) **or** Bi-weekly (every other Friday) |
| Exit checks | Weekly (Friday signal → Monday execution) |
| Hard exit | Close < 200 DMA on weekly check |
| Trailing stop | **None** (dropped May 2026 review — was 4x ATR no floor) |
| Rank exit | Drop below rank 40 (top-25 + buffer-15) at next entry rebalance |
| Position sizing | Equal weight (1/N), max 7.5% cap, drift after entry |
| Slippage | 20 bps (OHLC/4 pricing on next trading day) |

### Composite signal (locked-in 50/50)

```
upside_capture (UC)  = avg(stock_ret | market UP day) / avg(market_ret | UP day)
downside_capture (DC) = avg(stock_ret | market DOWN day) / avg(market_ret | DOWN day)
capture_ratio (CR)   = UC / DC

score = 0.5 × pct_rank(UC) + 0.5 × pct_rank(CR)
```

### Eligibility (locked-in: data-quantity only)

- ≥220 valid daily returns in the 252-day window
- ≥50 market-up days AND ≥50 market-down days

(No price/MA gate, no positive-return prefilter — the composite score does
the quality work.)

### Execution model

- All decisions use signal_date close + indicators (Friday for weekly check,
  bi-weekly Friday or 1st trading day of month for entries)
- All trades execute at next trading day's OHLC/4 (execution date)
- 20 bps slippage on every fill

---

## Honest Performance (clean engine, May 2026 stack)

| Universe | Cadence | CAGR | Max DD | Sharpe | Sortino | Calmar |
|----------|---------|------|--------|--------|---------|--------|
| **NSE 500** | Monthly | 58.9% | -35.0% | 2.17 | 2.77 | 1.68 |
| **NSE 500** | Bi-weekly | **62.7%** | -34.8% | **2.33** | **2.92** | **1.80** |
| **Nifty 250** | Monthly | 55.7% | -30.3% | 2.18 | 2.68 | 1.84 |
| **Nifty 250** | Bi-weekly | 51.9% | -30.9% | 2.03 | 2.49 | 1.68 |
| **Nifty 100** | Monthly | 35.4% | -31.7% | 1.47 | 1.83 | 1.12 |
| **Nifty 100** | Bi-weekly | 38.5% | -31.7% | 1.57 | 1.92 | 1.22 |

**Period:** 2021-02 to 2026-05 (5.3 years).

### Recommended Production Picks (preliminary — pending cadence study)

| Persona | Universe | Cadence | CAGR | DD | Sharpe |
|---------|----------|---------|------|-----|--------|
| **Highest CAGR + Sharpe** | NSE 500 | Bi-weekly | **62.7%** | -34.8% | **2.33** |
| **Best DD-adjusted** | Nifty 250 | Monthly | 55.7% | **-30.3%** | 2.18 |
| **Conservative large-cap** | Nifty 100 | Bi-weekly | 38.5% | -31.7% | 1.57 |

---

## Locked-in changes — May 2026 review

| Component | Old (prior locked-in) | New (May 2026) | Why |
|-----------|----------------------|----------------|-----|
| Engine peak tracking | Friday-only update | **Daily update** | Bug fix; previous trailing stop fired too rarely |
| Trailing stop | 4x ATR, no floor | **None (dropped)** | After peak fix, stop fired tighter; tested 0/3/4/5/6/8x × 0/5/10% — "no stop" wins CAGR universally and ties or wins Sharpe on flagship |
| Eligibility | Positive 252d return | **No filter** (data-quantity only) | Composite score does the quality work; positive-return filter actively hurt Sharpe and CAGR everywhere |
| Lookback | 252d | 252d (unchanged) | Confirmed: 63d too noisy, 504d too sluggish |
| Composite weights | 50/50 UC + CR | 50/50 UC + CR (unchanged) | V8 (UC + invDC) wins Sharpe by 0.05 but loses 7% CAGR — bad trade |

### Tested and rejected (May 2026)

| Idea | Verdict |
|------|---------|
| Trailing stop 3x/4x/5x/6x/8x × floor 0/5%/10% | All worse than no stop except Nifty 250 BW edge cases |
| ATR floor 5% or 10% | No mult benefits from a floor |
| Eligibility "+ Close > 200 DMA" | Reduces DD by ~3% but costs 5% CAGR — bad trade as default |
| Eligibility "+ 50 > 200 DMA" | Same shape — DD better, CAGR worse |
| Eligibility "TL25 trend gate" (3 conditions) | Worst on Sharpe; over-restricts pool |
| Eligibility "positive 126d return" | Marginally better Sharpe than 252d; not enough to flip |
| Lookback 63d, 126d, 189d, 378d, 504d | 252d wins avg Sharpe and CAGR |
| Weights 70/30, 30/70, UC only, CR only | All lose CAGR vs 50/50 |
| Weights 3-component (+ total return) | Wins on NSE 500 but lags smaller universes — not universe-agnostic |
| Weights UC + invDC | Best avg Sharpe by 0.05, but -7% CAGR cost |

---

## Strategy Differentiation

| Strategy | Question | Eligibility | Bias |
|---|---|---|---|
| Momentum | What went up the most? | None | High-vol, high-beta winners |
| TL25 | Cleanest uptrend right now? | Trend-gated (Close > 200 + stack + slope) | Confirmed trend leaders |
| **OM25** | **Best up-day-vs-down-day asymmetry?** | **Data-quality only** | **Asymmetric beta — can pick stocks in mild pullbacks** |

The locked-in V2 eligibility (no trend gate) makes OM25 genuinely orthogonal
to TL25 — it can hold quality names through pullbacks where TL25's eligibility
would have ejected them.

---

## Productization candidate — OM25 Defensive (V5 CR-only)

Worth offering as a **separate product** for risk-averse subscribers.

```
score = pct_rank(capture_ratio)        # CR only, no upside_capture term
```

The signal asks one question only — *how asymmetric is this stock?* — and
ignores absolute participation. Picks defensive low-beta names (FMCG, pharma,
quality IT) that resist downturns harder than they participate in upturns.

### V5 performance (averaged across 3 universes × 2 cadences)

| Metric | OM25 main (V1) | OM25 Defensive (V5) | Δ |
|---|---|---|---|
| CAGR | 50.5% | 32.3% | -18.2% |
| Max DD | -32.4% | **-25.5%** | +6.9% |
| Sharpe | 1.96 | 1.77 | -0.19 |
| Calmar | 1.56 | 1.27 | -0.29 |

**Best V5 cell:** Nifty 250 Monthly — 38.1% CAGR, -26.1% DD, Sharpe 2.10,
Calmar 1.46.

### Subscriber fit
- Risk-averse retail (people who pull money at -20% DDs and miss the recovery)
- Retirement-stage investors prioritizing preservation
- Bond-fund refugees seeking equity exposure with bond-like volatility
- First-time equity allocators as a stepping-stone

### Operational cost
Identical engine, identical pipeline — only the scoring weights change.
Single codebase, single monitoring.

### Open questions before productizing
- Sector concentration risk — likely loads on FMCG/pharma; may need a sector cap
- 2025 yearly returns specifically — claim is "wins choppy/down years," needs verification
- Turnover ~60% higher than V1 main — tax/transaction cost implications

---

## Files

| File | Purpose |
|------|---------|
| `scripts/_clean_engine.py` | Canonical clean (no-lookahead) backtest engine |
| `scripts/build_om25_signals.py` | V1 legacy omega-ratio script (pre-clean engine) |
| `scripts/backtest_om25.py` | V1 legacy monthly omega backtest |
| `tasks/om25/experiments/_om25_*.py` | May 2026 review test scripts |

---

## TODO

- [ ] **Min observations threshold** study (currently 220/252, scale variants)
- [ ] **Cadence study** (monthly vs bi-weekly head-to-head with locked-in stack — earlier rebaseline study used pre-fix engine)
- [ ] **Top-N × buffer grid** (20/25/30 × 10/15/20)
- [ ] **Sizing study** (equal-weight vs score-weighted vs pyramid-into-winners)
- [ ] **Universe choice** — finalize flagship (NSE 500 vs Nifty 250 — 2025 resilience favors Nifty 250)
- [ ] **OM25 Defensive (V5) sector concentration check + 2025 returns**
- [ ] Stock-level overlap analysis between OM25 main and TL25 (concrete diversification claim)
- [ ] Generate updated HTML report with locked-in stack
- [ ] Out-of-sample / walk-forward validation
- [ ] Paper trade 3 months before live deployment

---

## Interesting observations from the May 2026 review

1. **The Friday-peak engine quirk was performance-flattering.** Daily-peak
   correction reduced CAGR by 2-7% and Sharpe by 0.07-0.29 across variants.
   The pre-fix headlines were genuinely too rosy.

2. **The trailing stop wasn't earning its keep.** Across all universes and
   cadences, "no stop" (200 DMA only) wins CAGR universally and ties or wins
   Sharpe on the flagship NSE 500. The whole 4x ATR apparatus was squeezing
   out ~4% DD reduction in exchange for 5-12% CAGR loss.

3. **The positive-return filter was wrong empirically.** The DESIGN.md
   rationale said it screened out "beaten-down low-quality names with
   statistical artifacts." The data shows those names actually contribute
   positively when ranked via the composite score.

4. **Universe-size pattern in lookback.** NSE 500 prefers 378d, Nifty 250
   prefers 252d, Nifty 100 prefers 126d. Bigger universes can afford slower
   capture estimation; smaller ones need responsiveness. We chose 252d as
   universe-agnostic compromise.

5. **CR-only is a real alternative product, not just a weight variant.** V5's
   selection bias (defensive low-beta names) is genuinely different from V1's
   (asymmetric high-beta names). Same signal family, different question
   asked — clean basis for a "defensive" tier.

---

*Last updated: May 2026 — engine fixed (daily peak), trailing stop dropped,
eligibility filter dropped. Lookback and composite weights confirmed. Other
parameters under review.*
