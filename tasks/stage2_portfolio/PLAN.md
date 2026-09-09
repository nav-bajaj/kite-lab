# S2 (Stage 2) portfolio

## Why

The four production books are all momentum books. OM25 ranks by capture
asymmetry, TL25 by a persistence/drawdown/momentum composite, L6 by
volatility-scaled 6-month return, COMBO by a blend of two of them. They rank
the same universe by closely related trailing-return statistics, so they hold
closely related names.

The founder asked for a trend-following book built on a different primitive:
Weinstein/Minervini **stage-2 identification** - a hard pass/fail
classification of whether a stock is in a confirmed advancing stage - with the
ranking done on stage QUALITY rather than on return. NSE 500, weekly
rebalance, 20-25 names.

## Outcome

A tested S2 portfolio specification with an honest read on whether it earns a
place next to the momentum books, and on what it costs to run.

## Scope boundary

- Research only. Nothing is wired into `scripts/`, the daily pipeline, the
  dashboard, or the DB. Production code is untouched; the S2 engine is a
  task-local variant of `scripts/_clean_engine.py`.
- No fundamentals. There is no earnings or financials feed in the repo (still
  the open thread from the breakout-call research), so "growth" is proxied
  entirely by price and volume behaviour. Every growth claim in RESULTS.md is
  a price-behaviour claim, not a fundamentals claim.

## Method

- **Universe.** Survivorship-free by default: reconstructed NSE 500 membership
  from `tasks/index_reconstruction` (1,020 symbols, 1,319 spells, real
  effective dates) plus the ex-member price backfill. The production
  membership file is carried as a second basis so the results can be read
  against the published figures, which were produced on it.
- **Windows.** IS 2009-09-01..2016-12-31, OOS 2017-01-01..panel end - the same
  split OM25 v3 and TL25 v3 were tuned and validated on.
- **Pre-registration.** Scoring variants and the stop ladder were fixed in
  `lib/stage2.py:VARIANTS` and `lib/sweep2.py` before any result was read.
- **No-lookahead.** Signal-date close decides, next trading day at OHLC/4
  executes, 20 bps slippage - identical contract to the production engine.

## Critical files

| File | What |
|---|---|
| `lib/panels.py` | Calendar-safe OHLCV panel build (phantom rows, life masking) |
| `lib/stage2.py` | Stage-2 gate, hold gate, scoring variants |
| `lib/s2_engine.py` | Backtest engine: clean-engine contract + drift and sector controls |
| `lib/run_s2.py` | Context build, single-run entry point, metrics |
| `lib/compare.py` | Head-to-head vs TL25 v3 / L6 on identical data |
| `data/*.csv` | Every result table quoted in RESULTS.md |
