# Book verification 2026 — behavioural tests for the rebuilt books and the master store

Opened 2026-09-12 (founder). Status: in-progress.

## Why

The first week of the production port found bugs one at a time, each fixed and pushed live: a
sidecar file that broke the panel loader, last prices read from the wrong folder, a
corporate-action pass that could have touched store rows, and a stop exit that rebought the
same name on the same action day (mm_rebuild §23). The founder's call: stop finding bugs
incrementally and pushing each one live. Instead, write down what "working correctly" means
for the two rebuilt books and for the dataset they read, as a list of checkable tests, run
that list locally against the runner's own output and the local store, and only then
deploy. The list becomes the acceptance suite for every future change to the books, the
engine or the store.

## Outcome

1. `TESTS_BOOKS.md` — a numbered list of behavioural tests for `mm_v1` and `om25_v4`, one
   line per rule in `tasks/mm_rebuild/MECHANICS.md`, covering at least: stock selection
   (score, universe membership as of the signal date, minimum history, return filter for
   the blend), rebalance (monthly first session signal, next-session execution, one action
   day, entrants from the top 45 by rank, no trimming), exits (rank below 45, 20% trailing
   stop from the peak checked only at the monthly signal, sold-and-replaced never rebought
   the same day), sizing and cash (inverse-vol weights from returns up to the signal date,
   10% cap, renormalisation, cash never negative, no position resized once held),
   sector cap (5 per NSE sector, unlabelled names unconstrained), regime switching
   (NIFTY 100 ROC31 with 3-day confirmation, lagged one session, hold ≤ 15 names in a bear,
   exits at rank 35 in a bear, rebuild after a bear only as positions exit), and no
   look-ahead anywhere (every input used on signal date t is known at the close of t or
   earlier). Each test states: the rule, the exact check, the data it needs, the pass
   condition, and what a failure would mean.
2. `tests/` — the same list implemented as pytest, runnable locally in minutes against a
   fresh run of `scripts/run_rebuilt_book.py` (trades, exits, equity, signals) plus the
   engine on synthetic panels where a rule is easier to prove in isolation.
3. `TESTS_DATA.md` — integrity tests for the master store the books read (`data/master`):
   price files, corporate-action factors, membership, benchmarks, calendar, sector map,
   the panel view; complementing, not duplicating, the 13 fortnightly checks already
   specified in `tasks/production_port_2026/DATA_QUALITY_CHECKS.md`. Implemented alongside
   as pytest.
4. `RESULTS.md` — the first full run of both suites on the local store: every test's
   verdict, every failure explained, and a short list of what must change before the next
   deploy.

## Scope boundary

- In: the two rebuilt books (`mm_v1`, `om25_v4`), the shared engine hooks they use, the
  master store as they read it, the runner's outputs. Local only; nothing is deployed from
  this task.
- Out: the four legacy books (their own tests exist under `tests/`), the dashboard, the
  DB sync (covered by `scripts/sync_validation.py`), the nightly refresh internals (covered
  by `tests/test_refresh_master_store.py`), rule changes (any failing test that turns out
  to be a rule question goes to the founder, per the fixed-rules agreement).

## Critical files

| Purpose | File |
|---|---|
| Locked mechanics (the spec) | `tasks/mm_rebuild/MECHANICS.md`, `tasks/mm_rebuild/RESULTS.md` §23 |
| Book assembly and locked configs | `scripts/rebuilt_books.py`, `scripts/run_rebuilt_book.py` |
| Engine | `scripts/_clean_engine.py` (`run_strategy`; hooks `size_weights`, `top_n_fn`, `sector_of`/`sector_cap`, `fill_from_buffer`, `stop_reentry_block`) |
| Scores, regime, sizing, calendar, sectors | `data_pipeline/strategies/` |
| Store package and layout | `data_pipeline/master_store/`, `data/master/` (prices/adjusted_pr, prices/bhavcopy, prices/kite, corporate_actions.csv, membership/, benchmarks/, panels/pr, qa/) |
| Existing tests to build on | `tests/test_engine_hooks.py`, `tests/test_strategy_lookahead.py`, `tests/test_store_views.py`, `tests/test_rebuilt_books_wiring.py`, `tests/test_clean_engine_trailing_stop.py` |
| Existing data checks (fortnightly spec) | `tasks/production_port_2026/DATA_QUALITY_CHECKS.md` |
