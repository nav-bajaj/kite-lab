# Hourly dip swing — can the dip feed work at swing timescale?

## Why

dip_vs_breakout_calls (2026-08-23) showed a dip entry (5-day return
< -5%) into the top-quartile momentum sleeve beats the breakout entry
on every portfolio metric, with median hold 76 trading days. The
founder's question: can the same idea run on the HOURLY timeframe —
more signals, shorter holds — as a swing feed?

## Data reality (checked 2026-08-25)

- `nse500_data_hourly/`: 534 symbols, 60-minute bars (7/session,
  09:15–15:15), **2025-10-15 → 2026-08-21 only** (~215 sessions).
  Refreshed daily by the pipeline (rolling 90-day incremental fetch,
  accumulating since Oct 2025).
- **Hourly files are RAW** — `apply_corporate_actions.py` heals only
  `nse500_data/` (daily). Two known demergers fall inside the window
  (VEDL 2026-04-30 f=0.715, TRIVENI 2026-07-22 f=0.615), plus any
  Kite-adjusted splits/bonuses. A dip trigger on raw data buys every
  corporate action, so healing is a hard prerequisite.
- Healing approach: per symbol per day, factor = adjusted daily close
  / last hourly close of that day; where |factor-1| > 3% multiply the
  day's hourly OHLC by the factor. Aligns hourly levels to the healed
  daily panel, catching all adjustment classes at once. Residual
  overnight-gap scan afterwards as verification.

## Scope

- Momentum sleeve unchanged: 126d vol-scaled momentum rank from the
  **daily** panel (`nse500_data/`, healed, live), top quartile,
  mapped to hourly bars with a 1-day lag (prior day's rank — causal).
- Entry timer moves to hourly: dip = L-bar return < -thr on hourly
  closes. Grid over L ∈ {7, 14, 21} bars (1/2/3 sessions) and thr ∈
  {3%, 5%}.
- Swing exits: trailing stop 8% / 12% from peak hourly close, optional
  time stop (70 bars = 10 sessions), momentum-decay exit (rank < 0.35)
  kept as slow safety. Fills next bar at OHLC/4 ± 20bps, same
  execution convention as the daily study.
- Cap 25 slots, momentum-rank priority, one call per symbol — same
  slot mechanics as dip25_ts20.
- **Benchmark arm**: daily dip25_ts20 re-run on the SAME window
  (2025-10-15 → 2026-08-21) with the dip_vs_breakout_calls engine, so
  hourly arms are judged like-for-like, not against 16-year numbers.

## Boundary / caveats up front

- 10 months of hourly history = ONE regime slice. Whatever comes out
  is indicative, not a validation; the daily study had 16 years.
- Survivorship: current constituents only (same as daily study).
- More trades × 20bps/side means cost drag matters more; slippage
  sensitivity noted in results.

## Critical files

- `experiment.py` — heal + panels + hourly simulator + grid.
- Reuses `tasks/donchian_channel/h4c_combo_grid.build_score_rank` and
  the slot/curve conventions from `tasks/dip_vs_breakout_calls/`.
