# MM rebuild — a core momentum book built from scratch on the honest universe

## Why

OM25 (`tasks/om25_rebuild`) rebuilt the quality-momentum book on the honest
store and found one process that meets the out-of-sample gates. This task
does the same for the core momentum book: price momentum, absolute and
volatility-adjusted, the family production L6 v2 belongs to.

## Method — identical to OM25

1. Gates pre-committed in TASKS.md §0, signed by the founder before the
   first search run. Proposed as OM25's final gate set.
2. Windows: IS 2010-01-01 → 2015-12-31. OOS 2016-01-01 → today, sub-windows
   2016-19 / 2020-22 / 2023-26, opened once. Walk-forward on top.
3. Build order, each step decided on IS only:
   §1 score × lookback × universe (the founder's opening grid);
   §2 mechanics (top-N, buffer, cadence); §3 devices (skip-month,
   eligibility filters, stop, regime tilt, exposure overlay) one at a time;
   §4 OOS and walk-forward.
4. Every trial registered; deflation reported at the observed cross-trial
   variance.

## Scope boundary

Reads the master store only. Writes nothing under `data/`. Does not touch
production or the four running portfolios.

## Critical files

- `tasks/om25_rebuild/lib/` — the harness (run_candidate, windows, regime)
- `lib/momentum.py` — the two scores
- `lib/run.py` — thin runner: swaps the score, keeps everything else
