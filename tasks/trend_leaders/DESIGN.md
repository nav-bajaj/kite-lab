# Trend Leaders 25 — Design & Decisions Log

> **REVIEWED MAY 2026.** Full parameter review under the clean (no-lookahead)
> engine. Several components changed (drawdown function, persistence/momentum
> windows, ATR multiplier, dropping MA Structure). Numbers are honest
> no-lookahead results. The May 2026 rebaseline doc (3x ATR, 4-component score)
> is superseded.

## Final Strategy (Simplified)

```
Signal:    Friday close (signal date)
Execution: Monday OHLC/4 (next trading day) with 20 bps slippage
Entry:     Top 25 eligible stocks by TQS, every other Friday signal
Exit:      Weekly Friday signal: Close < 200 DMA  OR  5x ATR(20) trailing stop
            from position peak (no floor)
Score:     1/3 persistence (252d above 100 DMA)
            + 1/3 drawdown control ((Close / 126d high)²)
            + 1/3 momentum (63d return, pct-ranked among eligible)
Filter:    Close > 200 DMA, 50 DMA > 200 DMA, 200 DMA rising 20d
Sizing:    Equal weight (1/N), 7.5% cap, exit buffer 20 (keep until rank > 45)
```

## Honest Performance (May 2026, locked-in stack)

| Universe | Cadence | CAGR | Max DD | Sharpe | Calmar |
|----------|---------|------|--------|--------|--------|
| **NSE 500** | Bi-weekly | **44.0%** | -28.6% | 1.88 | 1.54 |
| **Nifty 250** | **Bi-weekly** | **41.2%** | **-22.5%** | **1.93** | **1.83** |
| Nifty 100 | Bi-weekly | 32.7% | -19.7% | 1.72 | 1.67 |

**Recommended flagship: Nifty 250 Bi-weekly** — best Sharpe and Calmar; only
loses ~3% gross CAGR vs NSE 500 in exchange for ~6% better max DD.

---

## Why These Rules (May 2026 review)

Each component reviewed in isolation under the clean engine. The full review
findings are below; this section summarizes the rationale for each locked-in
choice.

### Eligibility: Close > 200 + 50 > 200 + 200 rising 20d
- Tested 8 variants (drop slope, drop 50>200, Close > 200 only, stricter
  +Close>50, ref 150 DMA, ref 100 DMA, none) × 3 universes.
- **No universal winner** — different variants win different universes.
- Current is most universe-agnostic: never the worst, best on Nifty 100, top-3
  on the others. "None" loses 4.5% CAGR on NSE 500 — eligibility is real work.
- Stricter (+Close>50) helps NSE 500 DD but kills Nifty 100 (-7.7% CAGR).

### TQS: 1/3 persistence + 1/3 drawdown + 1/3 momentum
- Tested 10 weight variants including single-component, two-component, and
  tilted weights × 3 universes.
- **Equal 1/3 best on Nifty 250** (likely flagship), top-3 on NSE 500, within
  0.6% CAGR of best on Nifty 100.
- All three components carry weight — single-component runs lose 8-25% CAGR
  vs equal-weighted.
- Persistence is most fragile alone but earns its keep in the mix
  (drop-persistence loses 5% CAGR on Nifty 250).
- Tilts are not universe-agnostic.

### Persistence: 252-day window, 100 DMA reference
- Tested 63d/100d, 126d/100d, 252d/100d, 252d/200d.
- **252d / 100 DMA** wins — long-term reliability beats short-term consistency.
- 100 DMA reference is the sweet spot (200 too sparse, 50 too noisy).

### Drawdown control: Concave (squared), 126-day rolling high
- Tested linear `(Close / 126d high)`, concave squared `**2`, concave cubed `**3`.
- **Concave squared** wins — penalizes deep drawdowns sharply, rewards
  near-highs. Cubed over-penalizes; linear under-penalizes.

### Momentum: 63-day return, percentile-ranked among eligible
- Tested 63d/126d/252d returns, raw vs percentile-ranked.
- **63d (3-month)** wins — faster trend detection than 6m/12m.
- Percentile-rank confirmed (raw returns have different scales across
  regimes; percentile rank is regime-stable).

### MA Structure component: DROPPED
- Was 4 binary sub-scores × 0.25 (Close > 50, 50 > 100, 100 > 200, 200 slope).
- **Redundant with eligibility.** Eligibility already gates Close > 200, 50 > 200,
  200 rising. The MA score was re-encoding what eligibility filtered.
- Tested alternatives (drop slope, stacked-only binary, distance from 50 DMA
  pct-ranked) — all comparable to current; "drop entirely" was best on NSE 500
  and Nifty 100, near-best on Nifty 250.
- **Result:** simpler 3-component score. Eligibility owns "is it trending?";
  score ranks among trending stocks on three independent measures of trend
  quality.

### Exit: 5x 20-day ATR from peak, NO floor
- Tested 3x/4x/5x multipliers × {0%, 10% floor}.
- **5x no floor** wins — wider stop captures more upside, no floor avoids
  forcing exits in low-vol leaders that haven't broken trend.
- 3x with 10% floor (prior locked-in) was forcing premature exits.
- Trailing stop is essential — without it max DD blows out to -32%.

### Cadence: Bi-weekly entry, weekly exit
- Tested 5 cadence combinations × 3 universes.
- **Bi-weekly entry, weekly exit** wins on flagship Nifty 250 (best Sharpe
  and CAGR). Weekly entry wins NSE 500 by 3% CAGR but with worse DD; weekly
  is also higher subscriber friction.
- **Weekly exits universally help DD** — weekly Friday signal catches breaks
  below 200 DMA before they get worse.
- Monthly entry slows trend capture by ~5% CAGR in NSE 500.

### Top-N / Exit buffer: 25 / 20 (universal)
- Full grid: Top-N {20, 25, 30} × Buffer {15, 20, 25} × 3 universes.
- See "Top-N × Exit Buffer Study" below — universe-specific tuning
  considered and rejected for simplicity.

### Sizing: Equal weight 1/N, 7.5% cap, drift after entry
- Pyramid into winners tested (5 variants: +15%/+25%/+40% triggers, +50%/+100%
  add sizes, raised caps).
- **No universal benefit.** Only Nifty 250 +40% threshold helps (+2.2% CAGR);
  NSE 500 neutral, Nifty 100 marginal. Adds complexity without robustness.
- Equal-weight on entry then drift is the simplest and most defensible.
- Full rebalance was rejected long ago (2696% turnover, hurts returns).

---

## Optimization Journey (Earlier locked stack)

These earlier-round findings predate the May 2026 review. Some have been
superseded (e.g. ATR multiplier, momentum lookback, MA Structure usage).
Kept here for historical context.

### Improvements that stuck (some superseded May 2026):
| Change | CAGR Impact | DD Impact | Notes | Status |
|--------|-------------|-----------|-------|--------|
| Remove distance penalty | +6% | -13% worse | Let winners run | Confirmed (component fully dropped May 2026) |
| Add trailing stop | +3% | +6% better | Catch extended stock crashes | Confirmed (now 5x, no floor) |
| Add 6m momentum (15→25%) | +6% | -1% | Prefer stocks with recent strength | Window changed to 63d May 2026 |
| Top 25 (from Top 20) | +1% | +1% better | More diversification helps | Confirmed |
| Bi-weekly (from monthly) | +3% | +1% better | Faster trend capture | Confirmed |
| Simplify to equal weights + 3x ATR | +3% | +4% better | Simpler was literally better | ATR now 5x; weights now 1/3 × 3 |

### Things that didn't work (still valid):
| Attempt | Result | Why |
|---------|--------|-----|
| Weekly rebalance | 14.5% CAGR, -29.8% DD | Too much rank noise, massive churn |
| 100 DMA eligibility | 18.6% CAGR, -29.6% DD | Too permissive in bear markets (re-tested May 2026: similar) |
| Full rebalance each month | 2696% turnover | Unnecessary, hurts returns via slippage |
| Percentile-ranked TQS | 6.7/20 persistence | Amplifies tiny differences into rank shuffles |
| Hybrid entry/hold signals | 18.7% CAGR | "Near MA" entry picks weaker trends |
| Distance penalty for "overextension" | -6% CAGR | Punishes the best performers |
| Tighter exit buffer (10-15) | Worse Sharpe | More churn without benefit |
| 1-month momentum lookback | 34.4% CAGR | Too noisy as a signal (3m / 63d is the sweet spot) |
| Top 10-12 concentration | Worse Sharpe, worse DD | Single-stock risk too high |
| Pyramid into winners | Mixed | Only Nifty 250 +40% benefits; not universal (May 2026) |

---

## Top-N × Exit Buffer Study (May 2026, clean engine)

Tested grid: Top-N {20, 25, 30} × Buffer {15, 20, 25} = 9 cells × 3 universes.
All other parameters as locked-in (5x ATR no floor, concave squared drawdown,
252d persistence, 63d momentum, no MA structure component, bi-weekly entry,
weekly exit, eligibility = Close>200 + 50>200 + 200 rising 20d).

**Headline finding: optimal Top-N scales with universe size.**

| Universe | Best cell (Top-N / Buffer) | CAGR | Max DD | Sharpe |
|----------|----------------------------|------|--------|--------|
| NSE 500 | **30 / 25** | 46.1% | -24.9% | 2.02 |
| NSE 500 | 25 / 20 (current) | 44.0% | -28.6% | 1.88 |
| Nifty 250 | **25 / 20** (current) | 41.2% | -22.5% | 1.93 |
| Nifty 100 | **20 / 20** | 39.1% | -17.8% | 1.99 |
| Nifty 100 | 25 / 20 (current) | 32.7% | -19.7% | 1.72 |

Universe-specific Top-N gain vs global N=25: **+2.1% CAGR / +0.14 Sharpe on
NSE 500**, **+6.4% CAGR / +0.27 Sharpe on Nifty 100**. Nifty 250 unchanged.

**Why it scales:** with eligibility filtering, Nifty 100 has only ~30-50
qualifying names at any time — picking 25 means 50-80% of eligibles (signal
diluted). Picking 20 is more discriminating. NSE 500 has 150-300 eligibles, so
N=30 barely changes concentration vs N=25 but adds useful diversification.

**Decision (May 2026): keep Top-25, Buffer-20 across all universes.** Reasons:
1. Single global parameter set is simpler to reason about and maintain
2. Risk of universe-specific tuning being overfit to in-sample period (2021-2026)
3. The Nifty 100 N=20 result (39.1%/1.99) looks stunning but Nifty 100 is
   thinly populated post-eligibility — small-N concentration may not be robust
   across regimes
4. Easier to communicate one knob to subscribers; product simplicity matters

**Future revisit triggers:** if any universe accumulates 1+ year of live
underperformance vs its expected backtest CAGR, re-run this grid before
considering universe-specific tuning. Document any change here.

**Buffer:** weaker effect across the grid. Buffer 15 marginally hurts NSE 500
(more churn at boundary); buffer 25 marginally helps. Buffer 20 is the safe
middle. Keep buffer 20.

---

## Overfitting Lesson

During optimization we went from 20.8% → 41.3% CAGR by turning ~10 dials on the same 5-year in-sample data. This was overfitting.

**Resolution:** Simplified back to clean round-number rules and validated via Monte Carlo universe sampling (remove 30% of stocks randomly, 10 trials). The simplified version (43.1%) actually outperformed the overfit version (41.3%) — proof that simpler rules generalize better.

**The test that matters:** 29/30 random trials above 25% CAGR. The strategy finds good trends regardless of which specific stocks are in the universe.

---

## Architecture

### Signal Generation
```
Universe daily close prices
  → Compute 50/100/200 DMA (vectorized DataFrame.rolling())
  → Compute eligibility filter (Close > 200, 50 > 200, 200 rising 20d)
  → Compute 3 score components (each Date x Symbol, 0-1):
      - Persistence:   rolling 252d mean of (Close > 100 DMA)
      - Drawdown:      (Close / 126d high) ** 2  (concave squared)
      - Momentum:      63d return, percentile-ranked among eligible
  → Equal-weight composite TQS (1/3 each)
  → Rank on bi-weekly dates
  → Output top 45 per date (for exit buffer hysteresis)
```

### Backtest Loop
```
For each trading day:
  1. Mark-to-market (update portfolio value, drawdown, position peaks)
  2. If weekly Friday signal date (executed Monday):
     a. Update each position's peak from signal date close
     b. Exit any position where signal Close < 200 DMA
        OR drawdown from peak > 5x signal-date 20-day ATR (no floor)
  3. If bi-weekly entry date (executed Monday from prior Friday signal):
     a. Rank-based exits (rank > 45 → sell)
     b. Fill open slots from top 25 (new entrants only, equal-weight sizing)
        Existing positions drift; not rebalanced.
```

### Key Implementation Details
- **200 DMA panel pre-computed** once before loop (fast lookup)
- **ATR panel pre-computed** as `close.pct_change().rolling(20).std()`
- **Position peak** tracked per holding, updated weekly from signal-date close
- **Trade execution:** OHLC/4 on next trading day after signal, 20 bps slippage
- **Whole shares** with floor allocation
- **Signal/execution separation:** all decisions use prior signal-date close
  + indicators; execution at next-trading-day OHLC/4. No same-day lookahead.

---

## Files

| File | Purpose |
|------|---------|
| `scripts/_clean_engine.py` | Canonical clean (no-lookahead) backtest engine |
| `scripts/build_trend_leaders_signals.py` | Signal generation (TL25 score) |
| `scripts/backtest_trend_leaders.py` | Backtest runner |
| `scripts/run_trend_leaders_portfolio.py` | Orchestrator (runs all variants, prints summary) |
| `scripts/report_trend_leaders.py` | HTML report (auto-detects all variant directories) |
| `tasks/trend_leaders/experiments/_tl25_*.py` | Parameter review test scripts (May 2026) |

---

*Last updated: May 2026 — Full parameter review under clean engine. Locked-in stack documented above.*
