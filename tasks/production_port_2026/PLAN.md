# Production port 2026 — the two rebuilt books, the honest store, and day-to-day operations

## Why

Two books are research-locked on the honest master store (`tasks/mm_rebuild/MECHANICS.md`):
**MM** (vol-adjusted momentum on the risk stack) and **OM25** (the 50/50 blend of that
momentum with the capture ratio on the same stack). Neither exists in production. Production
still runs four books on the old price panel and a membership file whose history is
backdated (survivorship worth 13-23pp of CAGR, market_data_spine). The daily pipeline fetches
from Kite only; the spine established Kite + NSE bhavcopy + GDF as the source set and a
point-in-time membership that reproduces the real index. This task ports all of it and
defines how the repo runs day to day afterwards.

## Outcome

1. `run_daily_pipeline.py` builds MM and OM25 from the master store on the honest universe,
   syncs them to the DB, and the dashboard shows them under stable new universe IDs; the four
   legacy books keep running unchanged until the founder retires them.
2. The master store is the production price and membership source, refreshed nightly from
   the sources in `DATA_OPERATIONS.md`, with a QA gate that blocks a bad day.
3. A quarterly monitoring job produces the §22-grid report for both books (0.10 margin).
4. Repo streamlined per `REPO_STREAMLINE.md`: research harnesses archived, engine hooks in
   the production engine, one data path.

## Scope boundary

- The four legacy production books are not modified; they are retired by a separate founder
  decision after MM/OM25 have run in parallel for at least one quarter.
- No restatement of published numbers (spine D-5) — new books publish from their lock date.
- Options program, calls products (dip feed) and insights are out of scope; the store they
  read gets no format change without a register row.

## Phases (TASKS.md)

P0 engine hooks → P1 store as source of record → P2 runners + pipeline → P3 DB/dashboard →
P4 monitoring + forward gate → P5 parallel run and cut-over → P6 repo streamline.

## Critical files

`scripts/_clean_engine.py`, `scripts/update_all_portfolios.py`, `scripts/run_daily_pipeline.py`,
`scripts/universe_membership.py`, `data/master/**`, `tasks/mm_rebuild/lib/{_engine_iv,run,momentum}.py`,
`tasks/om25_rebuild/lib/{score,regime,run,windows}.py`, `kite-api/app/services/portfolio_service.py`,
`kite-dashboard/src/lib/universes.ts`, `docs/portfolios.md`.
