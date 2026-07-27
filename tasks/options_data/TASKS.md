# Options Data Engine V1 — Tasks

Phases per PLAN.md. Local-first: 1-3 run on the laptop; Railway is Phase 4.

## Phase 1 — Skeleton (local) — DONE 2026-07-27

- [x] `kite-api/app/workers/options/` package
- [x] Instrument loader: NFO normalize, current+next expiry, ATM±10 by
      grid position, contract_id scheme, widen-only `strikes_to_add`
- [x] Market-clock phase machine (market_service holidays)
- [x] Worker lifecycle loop: once-per-day selection, token-list crash
      recovery, health endpoint (loopback default)
- [x] 16 offline tests vs synthetic NFO dump; full suite green (846)

## Phase 2 — Market data (local)

- [ ] Save a real NFO dump + real selection on a live token morning;
      promote it to a test fixture alongside the synthetic one
- [ ] KiteTicker wrapper: connect, subscribe FULL, auto-reconnect, gap log
- [ ] Tick parser -> in-memory chain state (`state.py`)
- [ ] Intraday widen: spot drift >= 2 strikes -> dynamic subscribe
- [ ] Record one session's raw ticks to Parquet; build replay fixtures
- [ ] Exit: chain updates in memory through a live session, disconnects recovered

## Phase 3 — Aggregation + persistence (local)

- [ ] Minute-bar builder (OHLC, volume delta, OI o/h/l/c, spread, depth
      imbalance, quote count)
- [ ] Bulk insert `option_minute_bars` (unique contract_id+minute)
- [ ] `option_chain_snapshots` upsert <= 10s staleness
- [ ] `daily_sessions` EOD stats + flush
- [ ] Soak: 2-3 full sessions, exit criteria in PLAN.md

## Phase 4 — Production deploy

- [ ] `kite_session` migration + login upsert + worker reader fallback
- [ ] Second Railway service (same image, start command override) + volume
- [ ] Env wiring (OPTIONS_HEALTH_HOST=0.0.0.0 for container healthcheck)
- [ ] Parity check vs a local run

## Phase 5 — Monitoring

- [ ] Admin-only worker-status endpoints (require_admin; security-reviewer pass)
- [ ] /admin panel + staleness alerting; data-quality checks

## Phase 6 — Optimization + retention

- [ ] Partitioning, Parquet compression/archival, insert tuning
