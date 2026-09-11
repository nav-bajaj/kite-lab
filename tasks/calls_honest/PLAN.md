# calls_honest — the two stock-call strategies re-run on the honest store

## Why

Two calls-product candidates were researched on survivorship-biased data:
the Stage-2 trend book (`tasks/stage2_portfolio`, branch `stage2_portfolio`;
found survivorship worth ~15pp of CAGR and its own "survivorship-free" basis
still had 166 of 1,020 symbols without prices) and the dip-timed momentum
feed (`tasks/dip_vs_breakout_calls`; 37.8% CAGR / 1.65 Sharpe on current
constituents). The master store (`data/master`, point-in-time membership,
price-return panels from 2005) now exists and OM25 and MM have been rebuilt
on it. This task re-runs both strategies there, unchanged, so they can be
read against the MM base rows in `tasks/mm_rebuild/RESULTS.md` §9.

## Outcome

One run per strategy per universe (NSE 500, Nifty 250), 2010-01-01 to the
store end, reported in the om25/mm format: IS 2010-15, OOS 2016-26 and its
three sub-windows, the Wright window, up/down capture against the MidSmall
400, bull/bear leg returns, and the trade-level statistics a calls product
needs (calls per month, win rate, winner/loser size net of slippage,
expectancy, hold time, exit mix, by year).

## Scope boundary

- No tuning. Frozen parameters from each source's RESULTS.md; where the
  source is ambiguous, the value its RESULTS.md reports as final, stated.
- Reads only the master store through `tasks/om25_rebuild/lib/run.py`.
  Nothing under `data/` is written; no production file is touched.
- Branch `index_reconstruction` is not switched; branch code is read with
  `git show`.

## Critical files

- `lib/common.py` — loaders (via the OM25 harness), windows, capture, legs, trade statistics
- `lib/s2.py` — Stage-2 gate, score and engine ported from the branch
- `lib/dip.py` — dip feed simulator ported from `experiment.py`
- `lib/run_all.py`, `lib/report.py`, `lib/selfcheck.py`, `lib/extra.py`, `lib/sens_rs.py`
- `runs/<strategy>_<universe>/` — equity.csv, calls.csv, config.json (csv gitignored)
