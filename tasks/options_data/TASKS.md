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

- [x] Save a real NFO dump + real selection (2026-07-27, spot 23995.95,
      ATM 24000, 87 contracts); promoted to tests/fixtures/*.json.gz
- [x] KiteTicker wrapper: connect, subscribe FULL, auto-reconnect hooks,
      gap log (live-verified post-close: 87/87 contracts ticked, real
      depth/OI, staleness 0.09s)
- [x] Tick parser -> in-memory chain state (`state.py`, lock-guarded)
- [x] Intraday widen: spot drift >= 2 strikes -> dynamic subscribe,
      widen-only, selection file re-saved for crash recovery
- [x] Raw-tick Parquet recorder (size + time flush, replay-safe filenames)
- [ ] Record one full session's raw ticks; build replay fixtures from it
- [ ] Exit: chain updates through a full live session, disconnects recovered

## Phase 3 — Aggregation + persistence (local)

- [ ] Minute-bar builder (OHLC, volume delta, OI o/h/l/c, spread, depth
      imbalance, quote count)
- [ ] Historical backfill into option_minute_bars (OHLC/volume/OI only;
      depth columns NULL) — capability verified 2026-07-27, ~30d available,
      see research/RESULTS_2026-07-27_history_probe.md
- [ ] Bulk insert `option_minute_bars` (unique contract_id+minute)
- [ ] `option_chain_snapshots` upsert <= 10s staleness
- [ ] `daily_sessions` EOD stats + flush
- [ ] Soak: 2-3 full sessions, exit criteria in PLAN.md

## Phase 4 — Production deploy (pulled forward 2026-07-27 for the 07-28 live test)

- [x] `kite_session` token handoff: login mirrors to Postgres (headless +
      OAuth paths), worker reads DB-first/file-fallback; R-025 register row;
      security-reviewer APPROVE-WITH-NOTES
- [x] entrypoint SERVICE_ROLE=options-worker dispatch; /data/options volume
      dir; railway.worker.toml (no healthcheck, on_failure restarts)
- [x] Dead-ticker self-heal: rebuild client with fresh token after 60s grace
- [ ] USER: merge options-token-handoff -> beta_gtm_mvp (web deploy tonight)
- [ ] USER: create Railway worker service (branch options_data_v1, config
      railway.worker.toml, SERVICE_ROLE/DATABASE_URL/KITE_API_KEY, volume)
- [ ] Live test 2026-07-28: full-session capture on Railway (expiry day)

## Phase 5 — Monitoring

- [ ] Admin-only worker-status endpoints (require_admin; security-reviewer pass)
- [ ] /admin panel + staleness alerting; data-quality checks

## Phase 6 — Optimization + retention

- [ ] Partitioning, Parquet compression/archival, insert tuning
