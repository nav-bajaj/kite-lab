# Stress-regime reversal calls — PLAN

Opened 2026-07-24. Status: in-progress. Spun out of `tasks/donchian_channel`
(H4 family) to diversify the call-feed offering away from momentum.

## Why

The breakout/momentum call feed is a bull-market product. The platform's
strongest validated forward-return content is the STRESS-regime
conditional claim ("buy panic") in `kite-api/app/insights/conditional_dist.py`.
This study tests whether that market-level claim converts into a
stock-level call product: buy structurally healthy names during panic
episodes, hold for the recovery.

## Pre-registered design (fixed before any run)

- **Stress trigger**: offline replica of the production stress composite
  (VIX 252d-percentile 0.35, Nifty-50 drawdown-from-252d-high 0.25,
  % NSE 500 below 200-DMA 0.20, cross-sectional dispersion z 0.20;
  0-100). Entries allowed only on days with score >= 70. An "episode"
  is a contiguous run of trigger days.
- **Selection (deliberately non-momentum)**: eligible if (a) persistence
  >= 0.60 (share of past 252d with close above 200-DMA — structural
  health, the TL25 ingredient), and (b) drawdown from 252d close-high
  in [15%, 40%] (hit, not broken). Rank by persistence, fill free slots
  by rank. Cap 50 concurrent, one call per symbol.
- **Exit grid (3 arms)**: time60 (unconditional 60 td), time120,
  rec50 (close regains 50-DMA, or 120 td, whichever first).
- **Execution**: next-day OHLC/4 +/- 20bps, P&L net of slippage.
  NSE 500 universe, window 2011-01-01..2026-05-08 (VIX percentile
  warmup consumes 2010). Same accounting as donchian_channel H4.
- **Evaluation**: per-call stats, per-episode stats, 50-slot curve,
  2023-07+ tail, and a two-benchmark validity dry run at 20/60/120d:
  (i) vs same-date universe mean (does selection beat the generic
  panic bounce), (ii) vs all-days universe mean (does timing add).
  Any subscriber-facing claim must later clear the full 6-check gate
  in `tasks/insight_engine/VALIDITY_PROTOCOL.md`.

## Scope boundary

No shorting, no leverage, no intraday. No momentum inputs in selection.
No production change; research only. Fundamental multi-factor filters
are explicitly deferred to a future task once a fundamentals feed
exists (founder to source).

## Critical files

`tasks/donchian_channel/channel_panels.py` (loaders),
`indices_data_historical/{INDIA_VIX,NIFTY_50}.csv`,
`data/breadth/breadth_daily.csv`, `kite-api/app/insights/stress.py`
(reference definition), `tasks/insight_engine/VALIDITY_PROTOCOL.md`.
