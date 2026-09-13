# Agent brief — regime_first_2026

Read: this file, PLAN.md, TASKS.md. Then `tasks/trend_screen_2026/lib/breadth.py`
(92 lines) for how breadth was built. Nothing else. Do not explore.

**This task never touches a strategy's returns.** If you find yourself
computing a trade, stop — that is Phase 3 and a separate task.

## Budget and conduct
- Repo root `/Users/navdeep/kite-lab`, `source .venv/bin/activate`.
- Long computations (correlation, HMM fits) as background scripts writing to
  `data/`. Correlation on 100 names × 63-day rolling is fine; do not attempt
  full pairwise on 500.
- Report once, in RESULTS.md. Failures go under "Blocked"; continue.
- Write only inside `tasks/regime_first_2026/`. Do not commit.

## Data — exact
- `tasks/trend_screen_2026/data/breadth.parquet` — daily index; cols `n,
  pct_above_200, at_high, at_low, net_highs, pct_above_200_chg, net_highs_chg, phase`
- `tasks/regime_allocation_2026/data/signals.parquet` — daily index; cols
  include `pct_above_200, pct_leading, net_highs, pct_above_50, composite`
- `tasks/trend_screen_2026/data/features_t500_ranked.parquet` — month-end
  rows, cols include `date, symbol, close, state, s200, s200_21`
- `tasks/breakout_calls_2026/data/pit_universe.parquet` — `date, symbol, adv,
  eligible`; universe = rank(adv) ≤ 500 per date AND eligible; drop dup (symbol,date)
- `data/master/prices/adjusted_pr/<SYM>.csv` — `date, open, high, low, close,
  volume, traded_as, factor`; for dispersion / correlation / skew / trend
  quality, load only universe names, `close` only
- `data/master/benchmarks/NIFTY_500.csv` — `date, close`; the index and the calendar

## Turning points — re-derive
15% zigzag on NIFTY 500 close: walk forward, mark a peak when price falls 15%
from the running high, a trough when it rises 15% from the running low. Expect
14 of each over 2006-2026. Detection lag = sessions from the turning point to
the first day the candidate's state equals the post-turn state; negative if
already there.

## Libraries
`scikit-learn` and `scipy` are installed in the venv (added 2026-09-13 for
this task). `hmmlearn` is NOT installed — for C5/C6 use
`sklearn.mixture.GaussianMixture` (fit on 2006-2015, `predict` forward) with
a 21-session majority-vote smoother, and record that substitution in
RESULTS.md under §2. Fit anything with parameters on 2006-2015 only.

## RESULTS.md template
```
# Results — regime_first_2026
**Verdict:** <which candidates clear R1-R3 and §4; recommended frozen taxonomy, or none>
## §1 state variables  <one line each: mean, sd, first valid date>
## §2-3 gate table  <candidate | states | median run | ≤5d share | flips/yr | lag@peaks | lag@troughs | R1 | R2 | R3 | pass>
## §4 real-time identifiability  <survivor | agreement % | median catch-up lag | pass>
## §5 survivor characterisation  <per state: freq, duration, transition matrix, index stats, description>
## Recommended taxonomy  <exact definition, parameter count, or "none">
## Blocked
## Follow-ups
```
