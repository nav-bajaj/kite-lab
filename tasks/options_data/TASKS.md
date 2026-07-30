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
- [x] Record full sessions' raw ticks (3 sessions, 2.0-2.3M ticks each);
      replay CLI turns any recorded day into fixtures/bars
- [x] Exit met 2026-07-28/29/30: full live sessions, 0 unrecovered
      disconnects (0 reconnects at all on all three days)

## Phase 3 — Aggregation + persistence (DONE 2026-07-28)

- [x] Minute-bar builder (OHLC, volume delta, OI o/h/l/c, tick-weighted
      spread + whole-book depth imbalance, end-of-bar book, tick count)
- [x] Bulk insert option_minute_bars (PK contract_id+minute, ON CONFLICT
      DO NOTHING; live/replay/hist sources); down-DB never blocks capture
- [x] option_chain_snapshots JSON upsert every 10s
- [x] daily_sessions EOD stats row + flush
- [x] Replay CLI: rebuilt day-one bars from raw ticks; VALIDATED vs
      Zerodha official candles (3,000 matched minutes, mean close err
      0.0062, all official minutes matched) — replaces the local soak
- [x] Historical backfill: 638k bars, 87 contracts, 2026-06-29..07-28
      (hist rows have NULL depth columns by design)
- [x] Postgres volume grown 500MB -> 5GB after backfill DiskFull spike
- [x] First live-source session 2026-07-29: 39,744 bars, db_errors=0,
      snapshots fresh to 10s of close; repeated cleanly 07-30

## Phase 4 — Production deploy (pulled forward 2026-07-27 for the 07-28 live test)

- [x] `kite_session` token handoff: login mirrors to Postgres (headless +
      OAuth paths), worker reads DB-first/file-fallback; R-025 register row;
      security-reviewer APPROVE-WITH-NOTES
- [x] entrypoint SERVICE_ROLE=options-worker dispatch; /data/options volume
      dir; railway.worker.toml (no healthcheck, on_failure restarts)
- [x] Dead-ticker self-heal: rebuild client with fresh token after 60s grace
- [x] Merged options-token-handoff -> beta_gtm_mvp; web deployed 2026-07-27
- [x] Railway worker service created + configured via CLI/GraphQL
      (branch options_data_v1, railway.worker.toml, env refs, 5GB volume)
- [x] Live test 2026-07-28 PASSED: full expiry-day session unattended
      (2.24M ticks, 87/87 contracts, 0 reconnects); api_key/token pairing
      bug found in pre-prod test and fixed (pair travels in kite_session)

## Phase 5 — Monitoring (DONE 2026-07-27/30)

- [x] GET /api/options/worker-status (require_admin; security-reviewer
      APPROVE-WITH-NOTES; R-026; authz suite 288 assertions)
- [x] /admin Options Worker panel: phase, heartbeat age, ws state,
      packets, staleness, bars counters, widen events, error strip
- [x] Error lifecycle 2026-07-30: 08:30 login race gets a 2-min grace
      window; success clears last_error; dot prefers live capture state
- [ ] Push alerting (beyond panel red-dot) — optional, not scheduled

## Phase 6 — Optimization + retention (archival DONE 2026-07-30)

- [x] EOD tick archival: day dirs > keep_raw_days tar.gz'd + verified +
      pruned; crash-resumable; volume runway ~3 weeks -> months
- [ ] GDrive offload of archives (worker needs own creds path) — later
- [ ] option_minute_bars partitioning + insert tuning — when size demands

## V1 SUCCESS CRITERIA (handover doc §22) — ALL MET as of 2026-07-30

Worker runs unattended through market hours (3/3 sessions) · accurate
1-min bars for every subscribed contract (validated vs official candles,
mean err 0.0062) · chain snapshots continuously available (<=10s) · data
survives restarts/network failures (proven live) · health monitoring
reports status + quality (/admin + heartbeat + daily_sessions) ·
analytics added WITHOUT touching ingestion (microstructure engine
consumes bars only) · proprietary dataset compounding daily.
**The Options Data Engine V1 is complete. Work continues as operations
+ the analytics/strategy program (see below + PROGRAM_NOTE.md).**

## Operations & analytics layer (post-V1, ongoing)

- [x] EOD auto-materialization of IV/Greeks (microstructure Stage 1)
- [x] Daily report generator at EOD (spot/session/gamma/OI/IV/friction)
- [x] Founder risk-threshold framework fixed (research/NOTE_risk_thresholds.md)
- [x] MAE ledger (2026-07-30): paper_straddle_ledger table + daily-report
      section + EOD hook; regime-at-MAE join queued with day-type library
- [x] Stage 2 gamma tables + LIVE VIEW (2026-07-30): gamma_profile_daily
      rows at 10:00/13:00/15:15; /api/options/live-analytics (R-026
      extended, authz 291) computing parity forward/ATM IV/GEX/regime
      from the 10s chain snapshot; /admin Options Analytics card
- [ ] Morning day-plan generator prototype (advisory; builds call track
      record for the autonomy gates)
- [ ] 2026-08-04 expiry: straddle-ledger first verdict; second pin-day
      MAE path; gamma-concentration signature out-of-sample test
- [ ] Threshold calibration once day-type library >= 15-20 sessions
- [ ] Housekeeping: merge options_data_v1 -> main (closes R-025/R-026
      Alembic condition); prune old branches/stash
