# OM25 — Composite Capture Score Portfolio

## Overview

Selects stocks with the best **upside-vs-downside market-sensitivity asymmetry** —
participates aggressively in rallies, structurally resists drawdowns. Different
lens from momentum (highest returners) and TL25 (cleanest trend structure).

**Branch:** `main`

---

## v3 LOCKED IN (May 2026 OOS Retune) — current production

> Retuned with rigorous IS/OOS discipline: **2009-2016 in-sample**,
> **2017-2026 multi-window OOS** (split into 2017-19, 2020-22, 2023-26).
> Each candidate must pass per-sub-window robustness checks before we
> looked at full-OOS metrics. Full writeup: `tasks/oos_retune_2026/RESULTS.md`.

### Production-locked performance (2016-01-04 → 2026-05-08, 10.4 years)

| Metric | Value |
|---|---|
| CAGR | **39.34%** |
| Sharpe (rf=5%) | **1.66** |
| Max Drawdown | **-32.01%** |
| Total Return | ~3,500% |
| Trades | 729 buys / 685 sells |
| Avg position hold | ~118 days (rank exit) / ~159 days (drawdown stop) |

OOS-only validation (2017-2026 sliced from same run): 44.78% CAGR / 1.86 Sharpe /
-36.6% Max DD across 9.3 years; passes per-window pass criteria with sub-window
Sharpes of 1.57 / 2.10 / 1.80.

### v3 Configuration

| Parameter | Value |
|---|---|
| **Universe** | **NSE Nifty 250** (changed from NSE 500 / mixed in v2) |
| Cadence | Bi-weekly entry (every other Friday) + weekly exit checks |
| Score (bull regime) | 0.5 × pct_rank(UC) + 0.5 × pct_rank(CR) |
| **Score (bear regime)** | **pct_rank(CR) only — defensive tilt** |
| **Regime signal** | **NIFTY 100 close vs 100-DMA, 3-day confirmation** |
| Lookback | 252d, ≥220 obs, ≥50 up + ≥50 down market days |
| Return filter | Positive 252d total return required |
| Top-N / Exit-buffer | 25 / 20 (drop below rank 45) |
| **Drawdown stop** | **20% from running peak (weekly check)** |
| Position sizing | Equal 1/N, 7.5% max, drift after entry |
| Slippage | 20 bps (OHLC/4 next-day execution) |
| Allocation | Order-independent two-pass (per-entrant fair share) |

### What changed from v2

| Component | v2 (May 2026 review) | **v3 (May 2026 OOS retune)** |
|---|---|---|
| Universe | NSE 500 / Nifty 250 / Nifty 100 (multiple) | **Nifty 250 (single, locked)** |
| Score | Static 50/50 UC/CR | **Regime-tilted: 50/50 in bull, CR-only in bear** |
| Trailing stop | None | **20% from peak** |
| 200 DMA exit | Yes (weekly check) | **No** (tested and rejected — 39% hit rate, hurt CAGR) |
| Allocation engine | Greedy sequential | **Order-independent two-pass** |

### How to run (production)

```bash
# Backtest from 2016 (research-replication mode):
python scripts/run_om25_v3_portfolio.py --start 2016-01-01

# Live production (uses indices_data/ and current Kite prices):
python scripts/run_om25_v3_portfolio.py \
    --prices-dir nse500_data \
    --regime-index indices_data/NIFTY_100.csv

# Outputs: data/om25/v3/runs/<ts>/
#   - om25_signals.csv, om25_equity.csv, om25_trades.csv,
#     om25_exits.csv, metrics.json
```

Locked-in defaults are in `scripts/om25_v3.py:LOCKED`. See
`tasks/oos_retune_2026/RESULTS.md` for the full evidence trail.

---

## v2 history (May 2026 parameter review) — superseded by v3

> Below is the prior v2 documentation, kept for historical context.
> v2 is no longer the production stack; v3 supersedes it with the OOS
> retune work above.

### v2 strategy (1 sentence)

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

### Recommended Production Picks

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
| Engine OM25 score | Had positive-return filter | **No filter** | Codifies V2 eligibility into the canonical score function |
| Trailing stop | 4x ATR, no floor | **None (dropped)** | After peak fix, stop fired tighter; tested 0/3/4/5/6/8x × 0/5/10% — "no stop" wins CAGR universally and ties or wins Sharpe on flagship |
| Eligibility | Positive 252d return | **No filter** (data-quantity only) | Composite score does the quality work; positive-return filter actively hurt Sharpe and CAGR everywhere |
| Lookback | 252d | 252d (unchanged) | Confirmed: 63d too noisy, 504d too sluggish |
| Composite weights | 50/50 UC + CR | 50/50 UC + CR (unchanged) | V8 (UC + invDC) wins Sharpe by 0.05 but loses 7% CAGR — bad trade |
| Cadence | Monthly + Bi-weekly | Monthly + Bi-weekly (unchanged) | Weekly numerically better avg (Sharpe 2.05 vs 1.94/1.98); kept status-quo branding for subscriber continuity |
| Min observations | 220 / 252 | 220 / 252 (unchanged) | Robustness check: 150-252 all within Sharpe 0.04 — non-parameter |
| Top-N / Buffer | 25 / 15 | 25 / 15 (unchanged) | Universal best Calmar (1.56), top-2 on every other metric. Universe-specific optima diverge but small. |
| Sizing | Equal 1/N + drift | Equal 1/N + drift (unchanged, not re-tested) | TL25 review found pyramid-into-winners had no universal benefit |

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
| Weekly cadence | Best avg Sharpe/CAGR/DD/Calmar but kept Monthly+Bi-weekly for subscriber branding |
| Bi-monthly cadence | Worst on every metric — too slow to redeploy |
| Top-N × buffer 9-cell grid (20/25/30 × 10/15/20) | All within noise of 25/15; universe-agnostic compromise unchanged |
| Min obs 150/180/200/240/252 | All within Sharpe 0.04 of current 220 — non-parameter |

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

Parameter review is complete. Remaining items are larger productization
and validation tasks, not parameter tuning.

- [ ] **OM25 Defensive (V5) productization** — sector concentration check, 2025 yearly returns specifically, turnover/tax implications, branding
- [ ] **Sector concentration check on OM25 main** — does it ever load 8+ of 25 names in one sector?
- [ ] **Stock-level overlap analysis between OM25 main and TL25** — concrete diversification claim
- [ ] **Updated HTML report** on the locked-in stack (replace old reports)
- [ ] **Out-of-sample / walk-forward validation** before live
- [ ] **Paper trade 3 months** before live deployment
- [ ] Universe finalization deferred — offering all three (NSE 500, Nifty 250, Nifty 100) as subscriber-choice tiers

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

6. **Weekly cadence is numerically best but kept Monthly + Bi-weekly.**
   Weekly won avg Sharpe (2.05 vs 1.94/1.98), CAGR (51.9% vs 50.0%/51.0%),
   and DD (-31.2% vs -32.3%/-32.5%). Choice was branding/operational —
   subscribers already have Monthly/Bi-weekly tiers, +0.07-0.10 Sharpe
   wasn't worth the migration churn. The cash-drag-as-defense story for
   Monthly tier is dead under V2 + no trailing stop (avg cash now 0.4-0.9%
   vs 16-23% pre-fix); Monthly is just slower-redeploying now.

7. **min_obs and Top-N/buffer are robustness checks, not optimization knobs.**
   Both varied within Sharpe ±0.04 across the tested ranges. Universe-specific
   optima diverge with universe size (smaller universe → smaller Top-N) but
   the magnitudes don't justify universe-specific tuning. Same conclusion as
   TL25.

---

*Last updated: May 2026 — full parameter review complete. Engine fixed
(daily peak), trailing stop dropped, eligibility filter dropped. Lookback,
composite weights, cadence, min observations, and Top-N/buffer all
confirmed unchanged. Sizing and universe finalization deferred from the
parameter review (skipped intentionally — keeping equal-weight + drift,
offering all three universes).*
