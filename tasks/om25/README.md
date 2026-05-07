# OM25 — Composite Capture Score Portfolio

## Overview

A portfolio strategy that selects stocks with both high upside market participation AND good upside/downside asymmetry. Uses a composite percentile rank of upside capture and capture ratio.

**Branch:** `om25` (merged into `main`)

**Status:** Production strategy with two tiers (Monthly + Bi-weekly).

> ⚠️ **REBASELINED MAY 2026.** Earlier numbers (54.4% CAGR / 2.76 Sharpe etc.) reflected a same-day-close → same-day-OHLC/4 lookahead bug in weekly exit logic. Strategy parameters are unchanged; numbers below are honest, no-lookahead results. Removing the lookahead reduced CAGR by 6-11% and Sharpe by 0.4-0.6 across variants.

---

## Strategy (3 sentences)

> Rank each stock by the average of its upside-capture percentile rank and its capture-ratio percentile rank over the past year. Buy the top 25 (let winners run, exit buffer 15). On weekly Friday signal → Monday OHLC/4 execution, exit if Close < 200 DMA or 4x ATR trailing stop from peak.

Same signal, two cadences.

---

## Two Production Variants — Honest Numbers

OM25 is offered as **two tiers** sharing the exact same signal but differing on entry cadence. The signal picks the same kinds of stocks; the cadence determines deployment speed and risk profile.

### Tier 1 — Monthly (Flagship by Sharpe)
> Entry: Monthly (1st trading day signal → 2nd trading day execution) | Exit: Weekly (Friday signal → Monday OHLC/4)

| Metric | NSE 500 | Nifty 250 | Nifty 100 |
|--------|---------|-----------|-----------|
| **CAGR** | **48.1%** | 40.6% | 28.6% |
| Max DD | -27.4% | -22.8% | -25.3% |
| **Sharpe** | **2.26** | 2.01 | 1.55 |
| Sortino | 2.77 | 2.40 | 1.79 |
| Calmar | 1.75 | 1.78 | 1.13 |
| Beta | 0.90 | 0.97 | 0.96 |
| Avg Cash | 16.9% | 18.2% | 20.5% |
| Trades / 5y | 1,367 | 1,358 | 1,375 |

### Tier 2 — Bi-weekly (Higher CAGR)
> Entry: Every other Friday signal → Monday execution | Exit: Same as monthly

| Metric | NSE 500 | Nifty 250 | Nifty 100 |
|--------|---------|-----------|-----------|
| **CAGR** | **49.2%** | 46.1% | 33.2% |
| Max DD | -32.2% | -25.5% | -27.0% |
| Sharpe | 2.02 | 2.01 | 1.62 |
| Sortino | 2.41 | 2.40 | 1.89 |
| Calmar | 1.53 | 1.80 | 1.23 |
| Beta | 1.10 | 1.15 | 1.13 |
| Avg Cash | 6.7% | 6.9% | 8.5% |
| Trades / 5y | 1,777 | 1,731 | 1,841 |

**Period:** 2021-02 to 2026-05 (5.3 years).

### Recommended Production Picks

| Persona | Universe | Cadence | CAGR | DD | Sharpe |
|---------|----------|---------|------|-----|--------|
| **Flagship (best risk-adjusted)** | NSE 500 | **Monthly** | 48.1% | -27.4% | **2.26** |
| **Mid-cap balanced** | Nifty 250 | Bi-weekly | 46.1% | -25.5% | 2.01 |
| **Conservative large-cap** | Nifty 250 | Monthly | 40.6% | -22.8% | 2.01 |
| **Risk-averse** | Nifty 100 | Monthly | 28.6% | -25.3% | 1.55 |

---

## Yearly Returns (Honest)

| Year | NSE 500 M | NSE 500 BW | Nifty 250 M | Nifty 250 BW | Nifty 100 M |
|------|-----------|------------|-------------|--------------|-------------|
| 2022 | -3.2% | -1.2% | +8.5% | +21.3% | +13.6% |
| 2023 | +79.4% | +96.9% | +73.9% | +81.3% | +69.0% |
| 2024 | +67.4% | +64.4% | +57.3% | +66.3% | +21.6% |
| **2025** | **-17.0%** | **-17.5%** | **-3.3%** | **-7.9%** | **-4.3%** |
| 2026 YTD | +8.7% | +5.4% | +9.3% | +9.3% | +3.6% |

### Critical 2025 Insight (REVISED)

The **lookahead was hiding 2025's pain** in NSE 500. Honest 2025 numbers:
- NSE 500 Monthly: **-17.0%** (was claimed -4.4% with lookahead)
- Nifty 250 Monthly: -3.3% (genuinely defensive)
- Nifty 100 Monthly: -4.3% (defensive)

**Implication:** Nifty 250 / Nifty 100 universes were genuinely more resilient in 2025 than NSE 500. The earlier "NSE 500 Monthly is the best Sharpe" recommendation needs re-thinking — Nifty 250 is competitive on Sharpe and meaningfully better in down years.

---

## Lookahead Correction Detail

The bug was in the weekly trailing-stop check:

```python
# OLD (buggy): same-day close decides same-day OHLC/4 execution
if date in weekly_dates:
    if close_panel.loc[date, sym] < sma_200_panel.loc[date, sym]:
        sell at trade_panel.loc[date, sym]  # SAME DAY — lookahead

# NEW (clean): prior signal-day close decides next-day OHLC/4 execution
if date in weekly_exec_to_signal:  # date = Monday (execution)
    signal_date = weekly_exec_to_signal[date]  # Friday (signal)
    if close_panel.loc[signal_date, sym] < sma_200_panel.loc[signal_date, sym]:
        sell at trade_panel.loc[date, sym]  # Monday OHLC/4
```

The fix is in `scripts/_clean_engine.py` (the engine used for all enhanced OM25 variants). Production `scripts/backtest_om25.py` (V1 pure omega, no weekly stops) was not affected because it had no weekly exit logic.

### Inflation Removed

| Variant | Old (claimed) | New (clean) | Δ CAGR | Δ Sharpe |
|---------|---------------|-------------|--------|----------|
| NSE 500 Monthly | 54.4% / 2.76 | 48.1% / 2.26 | -6.3% | -0.50 |
| NSE 500 Bi-weekly | 60.6% / 2.61 | 49.2% / 2.02 | -11.4% | -0.59 |
| Nifty 250 Monthly | 47.3% / 2.44 | 40.6% / 2.01 | -6.7% | -0.43 |
| Nifty 250 Bi-weekly | 52.4% / 2.40 | 46.1% / 2.01 | -6.3% | -0.39 |

---

## Parameter Re-validation (with clean engine)

| Parameter | Locked-in | Tested alternatives | Verdict |
|-----------|-----------|---------------------|---------|
| Top-N | 25 | 15, 20, 30 | **Keep 25** (clearly best) |
| Exit buffer | 15 | 10, 20 | Marginal: buf 20 slightly better (+1.2% CAGR, +0.03 Sharpe) |
| ATR multiplier | 4x | 3x, 3.5x, 4.5x, 5x | **Keep 4x** (clearly optimal: 48.1% vs 37.9% at 3x) |
| ATR floor | 0% | 10% | **Keep 0%** (no floor is cleaner for OM25) |
| Composite weights | 50/50 upside/ratio | 30/70, 70/30, 100/0, 0/100 | **Keep 50/50** (each component contributes) |

### Optional Refinement (within noise)
- Exit buffer 15 → 20 gives +1.2% CAGR, +0.03 Sharpe with similar DD

The core architecture (top 25, equal weight 4%, 4x ATR no floor, 50/50 composite, weekly trailing stop) is validated.

---

## Key Insight: Beta Decomposition (Updated with Clean Numbers)

| Measurement | Monthly | Bi-weekly | Gap |
|-------------|---------|-----------|-----|
| Headline beta | 0.90 | 1.10 | +0.20 |
| Avg Cash | 16.9% | 6.7% | -10% |
| Stock-portion beta (cash removed) | ~1.08 | ~1.18 | +0.10 |

The cash drag effect persists post-rebaseline but is somewhat smaller than originally claimed. Both tiers still pick stocks with similar deployed beta; cadence determines deployment level.

---

## Strategy Differentiation (Clean)

| | Momentum | TL25 | OM25 (Monthly NSE 500) |
|---|---|---|---|
| Signal | 6m return / vol | Trend structure + 6m mom | Capture asymmetry |
| Max DD | -35% | -26.2% | -27.4% |
| Sharpe (clean) | 1.92* | 1.52 | **2.26** |
| Recent CAGR (2024+) | 1% | ~30% | ~48% |
| Best in | Strong directional bulls | Steady trends | Asymmetric/quality markets |

*Momentum's 1.92 Sharpe is honest — momentum has no lookahead bug, was never affected.

---

## Risk-Off Mechanisms — Tested and Rejected (still valid)

The four risk-off mechanisms tested earlier (Index 200 DMA, Breadth filter, Skip-in-down-market, Half-exit) were rejected because:
1. The trailing stop already handles per-stock risk-off
2. Cash drag (in monthly tier) provides implicit defense
3. Adding filters cost more in lost recovery than they saved in drawdowns
4. Filter complexity invites overfitting

This conclusion still holds with clean numbers.

---

## Open Questions for Production

1. **Universe choice may need revisiting.** Nifty 250 has comparable Sharpe with much better 2025 performance (-3.3% vs NSE 500's -17%). Worth deeper analysis before locking flagship.

2. **Monthly vs Bi-weekly economics.** With clean numbers, bi-weekly's premium over monthly is smaller (~1% CAGR on NSE 500). May simplify product to monthly only.

3. **Subscriber experience of -27% DD.** A monthly strategy with -27% max DD is still a meaningful drawdown for retail subscribers. Worth explicit communication.

---

## Files

| File | Purpose |
|------|---------|
| `scripts/build_om25_signals.py` | Signal computation |
| `scripts/backtest_om25.py` | V1 production engine (monthly only, no weekly stops, no lookahead) |
| `scripts/_clean_engine.py` | Clean engine for all enhanced variants (composite, bi-weekly, weekly stops) |

---

*Last updated: May 2026 — rebaselined with no-lookahead engine.*
