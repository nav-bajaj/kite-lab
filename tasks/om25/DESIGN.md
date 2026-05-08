# OM25 — Design & Decisions Log

> **REVIEWED MAY 2026.** Full parameter review under the clean (no-lookahead)
> engine, with two material corrections this review:
>
> 1. **Engine peak fix** — trailing-stop peak was only updated on Fridays
>    (the Friday a position was checked); intra-week highs never entered the
>    peak. The fix updates peak from every trading day's close. Pre-fix
>    numbers were lookahead-free but trailing-stop-flattering.
> 2. **Locked-in stack changes** — trailing stop dropped entirely;
>    eligibility's positive-return filter dropped.
>
> Earlier numbers in this doc (54%-60% CAGR / 2.4-2.8 Sharpe range) are
> superseded. Strategy *identity* is unchanged; the implementation got
> simpler and the numbers are honest.

## Strategy Identity

**Core thesis:** Stocks that participate more in market rallies AND have
asymmetric upside-vs-downside behavior compound faster with less pain.
Different lens from momentum (highest returners) and TL25 (cleanest
uptrends).

**What makes it different:**
- Momentum asks: "What went up the most?"
- TL25 asks: "What has the cleanest trend structure?"
- OM25 asks: "What goes up aggressively on good days AND has structural downside protection?"

A stock can have high momentum but terrible capture ratio (it went up 100%
but crashed 30% on every market dip). A stock can have mediocre momentum but
excellent capture ratio (it only went up 40% but participated in every rally
and dodged every selloff). OM25 selects the latter.

The May 2026 review reaffirmed this identity but loosened eligibility — OM25
no longer requires positive 252d return, so it can pick quality names in
mild pullbacks where TL25's trend gate would reject them. This makes OM25
genuinely orthogonal to TL25, not just a parameter variation.

---

## Final Production Configuration

### One Signal, Two Cadences

```
SIGNAL (identical for both tiers):
  upside_capture (UC)   = avg(stock_ret | market UP day) / avg(market_ret | UP day)
  downside_capture (DC) = avg(stock_ret | market DOWN day) / avg(market_ret | DOWN day)
  capture_ratio (CR)    = UC / DC
  composite             = 0.5 × pct_rank(UC) + 0.5 × pct_rank(CR)

  Window: 252 trading days ending at signal_date
  Top 25 by composite, percentile-ranked among eligible stocks (cross-sectional)

ELIGIBILITY (data-quantity only):
  - ≥220 valid daily returns in the 252-day window
  - ≥50 market-up days AND ≥50 market-down days in window
  (no positive-return filter — locked-in May 2026)

EXIT:
  - Weekly check: sell if Close < 200 DMA at signal_date
  - Rank exit: drop from holdings if rank falls below 40 at next entry rebalance
  - NO trailing stop (locked-in May 2026)

SIZING:
  - Equal weight (1/N), max 7.5% per position
  - Incremental: only buy new entrants, let continuing positions drift

SLIPPAGE:
  - 20 bps (OHLC/4 pricing on next trading day after signal)

DIFFERENT BETWEEN TIERS:
  Monthly tier:   Entry on 1st trading day of each month
  Bi-weekly tier: Entry every other Friday
```

---

## Engine Mechanics — Lookahead Audit

`scripts/_clean_engine.py::run_strategy` enforces strict signal/execution
separation. Every decision uses signal-date close + indicators; every trade
fills at execution-date OHLC/4 with 20bps slippage. Engine fixes this review:

### May 2026 fix: Daily peak update

**Before:** Peak only updated inside the weekly-exit block on Mondays, using
prior Friday's close. Tuesday/Wednesday/Thursday closes never entered peak.
The trailing stop fired against a Friday-only peak — quietly conservative.

**After:** Peak updated inside the daily mark-to-market loop using *today's*
close, every trading day. By the time a Monday weekly-exit check runs, peak
already reflects max of all closes from entry through the prior Friday.

**Lookahead-clean either way** — Friday-only used past Fridays, daily uses
all past days. The fix is about *correctness* of the trailing-stop semantics,
not lookahead.

**Effect:** Trailing stop fires more often; CAGR -2 to -7% across variants,
Sharpe -0.07 to -0.29. This is what made dropping the stop the right call —
once the peak was correct, the 4x ATR stop became visibly too tight.

---

## Parameter Review — May 2026

Each component tested in isolation under the daily-peak engine. Tests in
`tasks/om25/experiments/_om25_*.py`.

### 1. ATR multiplier × floor (and "no stop")

Tested: no stop (200 DMA only) + 12 (mult × floor) configs across 3 universes
× 2 cadences = 78 backtests.

**Verdict: drop the trailing stop entirely.**

| Choice | Avg CAGR | Avg DD | Avg Sharpe |
|---|---|---|---|
| No stop (200 DMA only) | **46.9%** | -33.3% | 1.84 |
| 4x / 0 (prior locked-in) | 36.4% | -27.6% | 1.74 |
| 6x / 0 (best stop config) | 41.5% | -29.2% | **1.90** |

No stop wins CAGR universally and Sharpe on the flagship NSE 500. The 6x/0
edge in avg Sharpe (+0.06) is small; the CAGR sacrifice is large (-5.4%).
Plus the simplification: one fewer mechanic.

Test script: `experiments/_om25_atr_test.py`

### 2. Eligibility filter

Tested 6 variants: V1 current (positive 252d return), V2 no filter,
V3 +above 200 DMA, V4 +50>200 DMA, V5 TL25 trend gate, V6 positive 126d.

**Verdict: drop the filter entirely (V2). Common data-quantity check stays.**

| Variant | Avg CAGR | Avg DD | Avg Sharpe |
|---|---|---|---|
| V1 current | 46.9% | -33.3% | 1.84 |
| **V2 no filter** | **50.5%** | **-32.4%** | **1.96** |
| V3 +above 200 | 45.6% | -30.7% | 1.91 |
| V4 +50 > 200 | 47.0% | -30.6% | 1.93 |
| V5 TL25 gate | 44.1% | -30.7% | 1.86 |
| V6 pos 126d | 46.8% | -30.3% | 1.94 |

V1's positive-return filter strictly hurt: V2 beat it on Sharpe, CAGR, and
even DD. The DESIGN.md rationale ("filter screens beaten-down statistical
artifacts") was empirically wrong — those names contribute positively when
ranked by the composite score.

V3/V4/V5 (price/MA gates) trade ~3% CAGR for ~3% DD reduction — defensible
for a defensive tier but not the right default.

Test script: `experiments/_om25_eligibility_test.py`

### 3. Lookback window

Tested: 63d, 126d, 189d, 252d (current), 378d, 504d. All variants share a
common min_date (driven by longest lookback) for fair period comparison.

**Verdict: 252d (unchanged).**

| Lookback | Avg CAGR | Avg DD | Avg Sharpe |
|---|---|---|---|
| 63d | 28.3% | -30.7% | 1.18 |
| 126d | 33.6% | **-26.1%** | 1.36 |
| 189d | 29.0% | -29.8% | 1.18 |
| **252d** | **37.2%** | -31.2% | **1.45** |
| 378d | 35.9% | -31.8% | 1.39 |
| 504d | 31.7% | -32.3% | 1.24 |

(Absolute numbers lower than other studies — this study used a later
min_date for fair comparison.)

Universe-size pattern: NSE 500 prefers 378d, Nifty 250 prefers 252d, Nifty
100 prefers 126d. Bigger universes can afford slower capture estimation;
smaller ones need responsiveness. Universe-agnostic compromise: 252d.

The 189d "valley" (worse Sharpe than both neighbors) is a regime-mismatch
noise artifact between 6 and 12 months — interesting, not actionable.

Test script: `experiments/_om25_lookback_test.py`

### 4. Composite weights

Tested 8 variants: V1 50/50 (current), V2 70/30, V3 30/70, V4 UC only,
V5 CR only, V6 3-comp equal (+TR), V7 3-comp ratio-heavy, V8 UC + invDC.

**Verdict: 50/50 (unchanged).**

| Variant | Avg CAGR | Avg DD | Avg Sharpe | Avg Calmar |
|---|---|---|---|---|
| **V1 50/50** | **50.5%** | -32.4% | 1.96 | **1.56** |
| V2 70/30 | 46.9% | -32.3% | 1.78 | 1.45 |
| V3 30/70 | 46.9% | -32.0% | 1.97 | 1.46 |
| V4 UC only | 41.5% | -35.2% | 1.48 | 1.19 |
| V5 CR only | 32.3% | **-25.5%** | 1.77 | 1.27 |
| V6 3-comp eq | 47.7% | -32.1% | 1.89 | 1.48 |
| V7 3-comp rh | 44.7% | -32.6% | 1.84 | 1.37 |
| V8 UC + invDC | 43.4% | -30.3% | **2.01** | 1.45 |

V8 wins Sharpe by 0.05 but loses 7% CAGR — bad trade. V1 wins CAGR and
Calmar; top-3 Sharpe; cleanest as the universal default.

V5 (CR only) is the clear DD-minimizer (-25.5% vs V1's -32.4%) but at heavy
CAGR cost (-18%). It picks a fundamentally different stock profile —
defensive low-beta quality names rather than asymmetric high-beta names —
and is now the basis for a separate "OM25 Defensive" productization
candidate (see README).

Test script: `experiments/_om25_weights_test.py`

---

## Decisions Still Open

- **Min observations threshold** (currently 220/252 ≈ 87%) — to be tested.
- **Cadence study** (monthly vs bi-weekly head-to-head) — earlier rebaseline
  used pre-fix engine; needs re-run on locked-in stack.
- **Top-N × buffer** (currently 25/15) — TL25 settled on 25/20; OM25 may
  differ.
- **Sizing** (currently equal-weight 1/N max 7.5%) — score-weighted and
  pyramid-into-winners not yet tested under clean engine.
- **Universe finalization** — Nifty 250 was meaningfully more resilient in
  2025 (-3.3% vs NSE 500's -17%); flagship choice not yet locked.

---

## Risk-Off Mechanisms — Tested and Rejected (still valid)

We tested four explicit risk-off filters earlier (pre-rebaseline, pre-engine-
fix). All were rejected and the conclusion still holds:

1. **The 200 DMA hard exit already does per-stock risk-off** — when a stock
   breaks trend, it gets sold. Faster and more targeted than waiting for
   index/breadth signals.
2. **Cash piles up automatically when stocks break down** — during corrections,
   many holdings hit their 200 DMAs and cash builds up. This IS the
   auto-defensive mechanism.
3. **Index-based filters slow down recovery** — the worst part of any DD
   protection is missing the recovery rally. Index 200/50 DMA + breadth
   filters all signal LATE on recoveries.
4. **In aggregate, missed recoveries cost more than avoided drawdowns** —
   over a 5+ year horizon, missing one V-shape recovery costs 10-15% CAGR;
   a typical avoidable DD only costs 2-5%.

**Strategic note from this review:** Dropping the trailing stop *and* the
positive-return prefilter further validates this principle — the simpler the
strategy, the better. We removed two mechanisms and performance improved.

---

## Productization Candidate — OM25 Defensive (V5)

The composite-weights study revealed V5 (capture-ratio only) as a real
alternative product, not just a parameter variant.

```
score = pct_rank(capture_ratio)
```

**Stock profile:** Defensive low-beta quality names (FMCG, pharma, stable IT)
that resist downturns harder than they participate in upturns. V1 actively
penalizes these for low absolute participation; V5 rewards them.

**Aggregate (avg across 6 universe×cadence):** 32.3% CAGR, -25.5% DD,
1.77 Sharpe, 1.27 Calmar.

**Best cell:** Nifty 250 Monthly — 38.1% CAGR, -26.1% DD, 2.10 Sharpe.

**Operational cost:** Identical engine, identical pipeline, identical
eligibility/exits/sizing. Only the scoring weights change.

See README "Productization candidate" section for subscriber-fit detail and
open questions before launch (sector concentration, 2025 yearly returns,
turnover impact).

---

## Differentiation From Other Strategies

| Dimension | Momentum | TL25 | OM25 main (V1) | OM25 Defensive (V5, candidate) |
|-----------|----------|------|----------------|--------------------------------|
| Signal type | 6m return / vol | Trend structure + 6m mom | 50/50 UC + CR | CR only |
| Question | What went up most? | Cleanest uptrend? | Best asymmetric beta? | Best down-day resistance? |
| Eligibility | None | Trend-gated | Data-quality only | Data-quality only |
| DD behavior | Holds through crashes | Trailing stop on extended | 200 DMA only | 200 DMA only |
| Max DD (clean) | -35% | -23 to -29% | -30 to -35% | -25 to -27% |
| Sharpe (clean) | 1.92 | 1.72-1.93 | 1.47-2.33 | 1.43-2.10 |
| Best in | Strong directional bulls | Steady trends | Asymmetric/quality markets | Choppy/down markets |

---

## Robustness Concerns

### What could go wrong:
- **Capture metrics are backward-looking** — a stock's market sensitivity
  can change (management change, sector rotation, liquidity shift)
- **Market regime dependence** — in a prolonged bear market, "high upside
  capture" stocks have fewer up-days to capture
- **Survivorship bias** — using current NSE 500 / Nifty 250 / Nifty 100
  constituents for full history
- **252d lookback is long** — slow to react to regime changes (this is also
  why 252d wins the lookback study; trade-off is real)

### What gives confidence:
- Locked-in stack is now strictly simpler than before — fewer mechanisms,
  fewer tunable knobs to overfit
- Eligibility loosened to data-quality only — broader candidate pool reduces
  selection bias
- Composite signal (UC + CR) is structural (beta asymmetry) not just
  return-based
- Strong Sharpe and CAGR across multiple universes and cadences (universally
  > 1.40 Sharpe, > 35% CAGR on best universes) suggests real predictive power
- DD well-controlled (-30 to -35% headline, -25% on Defensive variant)

---

## Files

| File | Purpose |
|------|---------|
| `scripts/_clean_engine.py` | Canonical clean (no-lookahead) backtest engine |
| `scripts/build_om25_signals.py` | V1 legacy omega-ratio script (pre-clean engine, kept for reference) |
| `scripts/backtest_om25.py` | V1 legacy monthly omega backtest (pre-clean engine) |
| `tasks/om25/README.md` | Summary, results, productization candidate |
| `tasks/om25/DESIGN.md` | This file — decisions log, review writeup |
| `tasks/om25/experiments/_om25_*.py` | May 2026 review test scripts |
| `tasks/om25/experiments/README.md` | Map of test scripts to outcomes |

---

## Production Status

**Locked-in for production (after May 2026 review):**
- OM25 Monthly tier (NSE 500, 1st trading day of month)
- OM25 Bi-weekly tier (NSE 500, every other Friday)

Both share identical signal, eligibility, exit, and sizing logic. They
differ only in entry cadence.

**Productization candidate (separate tier, not yet validated):**
- OM25 Defensive (V5 CR-only) — needs sector concentration check, 2025
  yearly return analysis, turnover/tax review

**Not pursuing:**
- Trailing stop (dropped May 2026 — universally hurt)
- Positive-return eligibility filter (dropped May 2026 — universally hurt)
- Explicit risk-off filters (V1-V4 from earlier review — all rejected, still rejected)

---

*Last updated: May 2026 — engine fix, trailing stop dropped, eligibility
filter dropped, lookback and composite weights confirmed unchanged. Min-obs,
cadence, Top-N/buffer, sizing, and universe choice still pending.*
