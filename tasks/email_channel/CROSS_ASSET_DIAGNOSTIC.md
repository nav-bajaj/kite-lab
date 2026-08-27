# Cross-asset "stale feed" alert — diagnostic, 2026-08-27

**Status: NOT CLOSED. The alert is probably FALSE, but two production
sources contradict each other and I could not settle which is wrong.**

Filed here rather than a new task folder because it was found while
working on email; it deserves its own folder when someone picks it up.

## What the alert says

`GET /api/freshness` reports, re-read live at 16:49 IST *after* today's
pipeline completed:

    USDINR   CRITICAL  last=2026-07-10  lag=34 trading days
    Gold     CRITICAL  last=2026-07-10  lag=34 trading days
    Crude    CRITICAL  last=2026-07-10  lag=34 trading days

## What the pipeline says, the same day

Today's 16:30 run (job `2e6b5a417af24299`, completed 16:36) logged:

    === fetch_cross_asset_history ===
    Mode: incremental
    Output dir: /data/indices_data_full
    [GOLD]     up-to-date (2026-08-26)
    [CRUDEOIL] up-to-date (2026-08-26)
    [USDINR]   up-to-date (2026-08-27)

"up-to-date" is not a guess — incremental mode reads the last row of the
existing CSV to decide. So the file it read has August data.

## Why this matters

**The data is very likely fine and the alert is very likely false.** That
is the opposite of what the ops map said this morning, and it matters:
acting on the alert means chasing a feed that is not actually broken,
while the real defect — a monitor that cries critical — stays.

It also undermines the monitor generally. Its whole job is to make a
silently frozen input visible (the INDIA_VIX incident). A false critical
that persists teaches everyone to ignore it.

## What was ruled out

- **Not the contract rollover.** The June 2026 fallback tokens did expire,
  but `_resolve_active_monthly_token` works: run locally it resolves
  GOLD26OCTFUT / CRUDEOIL26SEPFUT / USDINR26AUGFUT.
- **Not a missing pipeline step.** `INSTRUMENTS_STEP` runs unconditionally
  before the fetches and hard-exits on failure.
- **Not a silent step failure.** The step reports OK, and its stdout shows
  it read real dates. (It runs in 1.2s only because incremental finds
  nothing to do.)
- **Not committed stale data.** `indices_data_historical/` is not in git.
- **Not a freshness cache.** `freshness_service.py` has no caching; it
  reads `cross_asset_dir / csv_filename` directly. (`cross_asset.py` does
  have an mtime-keyed `lru_cache`, but freshness does not go through it.)
- **Not a filename mismatch.** Registry uses `USDINR.csv`, `GOLD.csv`,
  `CRUDEOIL.csv` — exactly what the fetcher writes.

## The remaining hypothesis

A **path divergence**: the fetcher subprocess and the API process resolve
`indices_data_full` differently, so they read different files of the same
name.

Both use the same ladder — `CROSS_ASSET_OUTPUT_DIR`, then
`KITE_BACKUP_SOURCE_ROOT/indices_data_full`, then `/data/indices_data_full`.
The fetcher printed `/data/indices_data_full`. The API's value was never
printed, and `KITE_BACKUP_SOURCE_ROOT` **is set on Railway** (name seen in
the variable list; value not read).

Note `_asset_path` in `cross_asset.py` prefers `indices_dir()`
(`indices_data_historical`, under `settings.data_dir` = `/app` in Docker)
and only falls back to `INDICES_DIR`. Its own comment says "locally both
resolve to the same folder, so behaviour is unchanged" — which is exactly
the shape of a bug that only appears in production. Freshness does not use
`_asset_path`, but the **insights cross-asset engine does**, so the engine
may be reading a different file again.

## How to close it

1. Print the resolved path. Add `cross_asset_dir` (and `indices_dir()`)
   to the freshness payload, or log both at startup. One deploy and the
   answer is unambiguous — cheaper than more reasoning.
2. Read `KITE_BACKUP_SOURCE_ROOT`'s value on Railway.
3. Compare the last row of the CSV each process actually opens.
4. If they diverge, collapse the resolution to ONE helper used by
   fetcher, freshness and engine alike, and delete the loser directory so
   a stale shadow cannot reappear.

## Also worth noting

The freshness reference date makes NSE500 read `CRITICAL` with
`last=2026-08-27, lag=76td` — a current last_date with a huge stated lag,
driven by three permanently-lagging tickers (GSPL, GUJGASLTD,
JBCHEPHARM). Those are expected and documented, but they keep the whole
report at `overall_status: critical` permanently, which is the same
cry-wolf problem. Worth separating "expected laggards" from real
staleness so the panel can go green.
