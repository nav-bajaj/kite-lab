# Regime filter test: Nifty 500 42-day return < 0 -> no-invest

**Date:** 2026-07-25
**Verdict: rejected.** The filter cuts CAGR by 10-14 points on both
portfolios and does not improve max drawdown (it *worsens* it for
Defensive Blend). Do not deploy.

## Rule tested

- Risk-off when NIFTY 500 rolling 42-trading-day return < 0.
- 3-day confirmation window (state flips only after 3 consecutive
  opposite-signal days) to damp regime churn.
- Next-day execution; full liquidation to cash when off, full re-entry
  when on; 0.2% one-way slippage per switch (engine's slippage=0.002).

## Method

Overlay on the production backtest daily equity curves
(`om25_v3_portfolio_20260721_163735`, `combo_defensive_portfolio_20260721_163805`),
not a re-run of the engine. Cash earns 0%. Script: `regime_overlay.py`;
raw numbers: `overlay_results.json`; daily series: `filtered_equity_*.csv`.

## Results

| | OM25 v3 baseline | OM25 v3 + filter | COMBO baseline | COMBO + filter |
|---|---|---|---|---|
| CAGR | **42.5%** | 28.4% | **45.6%** | 35.8% |
| Sharpe (rf 5%) | **1.69** | 1.28 | **2.00** | 1.60 |
| Vol | 22.2% | 18.3% | 20.3% | 19.3% |
| Max DD | -25.3% | -25.5% | **-16.4%** | -21.8% |
| Time in cash | — | 33.6% | — | 30.9% |
| Regime switches | — | 32 | — | 32 |

Period: OM25 2021-01 -> 2026-07; COMBO 2020-07 -> 2026-07.

## Why it fails

The 42-day lookback + 3-day confirmation makes the signal structurally
late on both edges: it goes to cash only after ~2 months of decline are
already in the price, and it re-enters only after ~2 months of recovery
are already done. The result is that the filter mostly sits out
*rebounds*, not crashes:

- In **13 of 16** off-windows, OM25 v3 was **up** while the filter sat
  in cash — including +15.0% (Apr-May 2021), +15.5% (Dec 2021-Jan
  2022), +12.1% (Nov 2023). Cumulative portfolio return during cash
  periods: **+67%** for OM25, **+42%** for COMBO.
- Only 3 windows avoided losses, and they were modest: -7.3% (Jan-Apr
  2023) and -9.6% (Oct 2024-Apr 2025) for OM25; -4.9% and -1.6% for
  COMBO. COMBO barely fell in the windows the filter is designed to
  dodge — its drawdown control (the defensive sleeve + existing stops)
  already does that job.
- Max DD doesn't improve because the filter exits *after* the drawdown
  is mostly taken. For COMBO it gets worse (-21.8% vs -16.4%): take the
  initial leg down invested, miss the rebound in cash, re-enter, repeat.

Crediting cash at ~6% p.a. (liquid fund) would add only ~1.9%/yr for
~31% time in cash — nowhere near the 10-14 point CAGR gap.

## Caveats

- Overlay, not engine re-run: ignores that re-entry would buy a fresh
  top-N and that the gate would interact with drawdown stops. Neither
  effect is plausibly worth >10 CAGR points, so the verdict stands
  without an engine-integrated run.
- Single lookback tested (42d) at the user's spec. Note OM25 v3 already
  has a regime mechanism (NIFTY 100 vs 100 DMA, 3-day confirm) used to
  *tilt the score defensively* rather than exit — that design keeps
  participation in rebounds, which is exactly where this hard filter
  loses.
