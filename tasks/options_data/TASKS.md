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
- [ ] Push alerting (beyond panel red-dot) — STILL THE TOP OPS GAP.
      The post-EOD recycle fix has now held 5 consecutive unattended
      sessions (2026-08-12..18, 0 db errors, full contract coverage),
      so the 08-11 incident is closed at n=5 — but the recycle fixed
      THAT failure mode, not the class of silent-death failures.
      PRIORITY RAISED by the
      2026-08-11 incident: capture was dead 09:15-11:33 on expiry morning
      with a green panel (heartbeat fine, last_error None) and the founder
      noticed before the system did. Minimum bar: alert when phase=capture
      and packets stay 0 for N minutes.
- [x] 2026-08-11 INCIDENT + fix: silent ticker death on the process's
      SECOND session (twisted global reactor cannot re-arm; every prior
      day accidentally got a fresh container from evening pushes; the
      first push-free weekend exposed it). Restored 11:33 by redeploy;
      permanent fix = deliberate post-EOD process recycle (exit 43,
      on_failure restart) + last_error stamped in the dead-ticker loop.
      Data gap 09:15-11:33 on the 08-11 expiry — journal day 10 must
      carry the caveat (morning gamma/OI/IV snapshots at 10:00 missing;
      paper-straddle 09:20 entry not computable from live bars).

## Phase 6 — Optimization + retention (archival DONE 2026-07-30)

- [x] EOD tick archival: day dirs > keep_raw_days tar.gz'd + verified +
      pruned; crash-resumable; volume runway ~3 weeks -> months
- [x] GDrive offload of archives (2026-09-02): EOD uploads `<date>.tar.gz`
      to `kite-lab-backups/options_ticks/`, md5-verified against Drive
      before the local copy is pruned; `keep_archive_days=5`,
      `offload_max_files=8` bounds one night's work. Backlog drain via
      `python -u -m app.workers.options.offload`. Steady state on the
      volume: ~3 raw days + 5 archives ~= 1.3GB of 5GB.
      Trigger: volume hit 89% (537MB free, ~3 sessions of runway) because
      archival shipped without offload — archives accumulated 25 deep.
- [ ] option_minute_bars partitioning + insert tuning — when size demands
- [ ] Disk usage in the worker heartbeat + /admin card, warn >85%. Nothing
      reports volume usage today, which is why the 89% was found by eye.
- [ ] `Recorder.flush()` pops the buffer before writing and the run loop
      swallows the exception, so a full volume silently drops every flush
      window's raw ticks instead of failing loudly. Restore-on-error.

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
- [x] Morning day-plan generator prototype (2026-08-05): advisory
      Judgment-layer module `microstructure/day_plan.py` — regime (shared
      concentration cutoffs) + IV percentile (vs gamma_profile_daily history)
      + gamma walls + ATM credit -> structure selection (short-straddle /
      iron-fly / directional-debit / defined-risk / reduced-size / aside),
      risk band QUOTED from the actual ledger (never fabricated), standing
      constraints. Pure `recommend_structure` core exhaustively unit-tested
      (tests/test_day_plan.py, 8 cases); wired into the EOD daily report so
      the advisory call is recorded each session (builds the track record).
      Live /admin path reuses recommend_structure — beta_gtm_mvp follow-up.
- [x] 2026-08-04 expiry (all three landed): ledger verdict #1 —
      realized BEAT implied across the compression week (0.69% vs
      1.02%); first LOSS row (-55.2, MAE -78.3 on 93 credit); NO pin
      (concentration fell 32->22%, pin sample 1/2). Settlement basis
      decoded: official close, established ~15:28-15:30; extended
      window trades at settlement values; greeks cutoff 15:30 CONFIRMED
- [~] Spot-vs-parity divergence monitor (2026-08-05): DAILY REPORT half
      done — `_divergence_section` measures spot vs chain parity-forward per
      minute, absorbs carry via the day's own median gap, flags dislocation
      beyond DIVERGENCE_FLAG_PTS (40); live compute field (`divergence` +
      `divergence_flag`) added to gamma_profile.compute_from_snapshot. Tests
      in test_paper_straddle_gamma.py (report + live). REMAINING (moved):
      surfacing the field on the /admin card is absorbed into
      tasks/options_dashboard Phase 1 (the card becomes a link into the
      real-time /options analytics page).
- [x] **Stage 2b — per-minute gamma profile (2026-08-18).** The
      3-snapshot profile made the concentration slope a two-point
      estimate across three hours, which is what stalled the positioning
      study. `option_greeks_minute` already carries gamma+IV per minute
      per contract, so the profile is computable at 1-minute resolution
      from data already stored — no new capture, and the 10s chain
      snapshots are not needed. New `gamma_profile_minute` table +
      `store_intraday()`, wired into the EOD hook after `store_daily()`.
      Both writers share one pure core (`profile_series`) so the two
      tables cannot drift; the refactor reproduces all 39 pre-existing
      gamma_profile_daily rows EXACTLY (validated against prod).
      15 spec tests, red-first. Backfilled over every session with
      greeks: 13,978 minute rows over 37 sessions, and the daily profile
      history grows 13 -> 37 sessions (option_greeks_minute reaches back
      to 06-29 while gamma_profile_daily began 07-31, so every
      history-based consumer had been reading a third of the record —
      day_plan.iv_percentile now ranks against ~36 prior days, not ~12).
      First act of the upgrade was to FALSIFY the concentration-slope
      risk finding that justified it (RESULTS gamma_positioning, Q3
      retraction) — the 3 recovered sessions include 07-28, the steepest
      building slope on record and the second-worst afternoon drawdown.
- [ ] **Threshold calibration — GATE MET 2026-08-18 (ledger n=15).** The
      MAE library now separates the catastrophic losers (-78.3, -72.3)
      from every winner (band -0.5..-28.2, median -12.2), but the two
      marginal losers (-16.7, -15.2) sit INSIDE the winner band — so
      the table must be state-conditioned, not a price level (founder
      framework, research/NOTE_risk_thresholds.md). Condition on
      regime AND days-to-expiry; see OBSERVATIONS obs. 42.
- [ ] **day_plan: DEMOTE the concentration regime from the primary
      branch (2026-08-18).** `recommend_structure` branches on the 10:00
      regime FIRST for 100% of sessions and concentration is the label's
      sole input — but against the 15 sessions with outcomes nothing is
      significant (conc vs P&L r=-0.281 |t|=1.06; vs MAE r=-0.230
      |t|=0.85), and the PIN-GRAVITY branch (short-straddle vs iron-fly,
      the thin-credit rule) fires on 3 of 37 sessions with ONE outcome
      behind it (07-28). Six tests, all negative — RESULTS
      gamma_positioning. What HAS earned evidence and should drive the
      advisory instead: overnight carry (59% of the trend cycle's damage
      arrived in gaps) and the implied-vs-realized regime across 4 cycles.
- [ ] **day_plan: cutoffs from the realized distribution, not intuition.**
      Across 37 sessions the 10:00 concentration runs 0.151-0.363
      (median 0.236): CONC_PIN=0.35 sits above 92% of all morning reads,
      CONC_DIFFUSE=0.25 splits at the 57th percentile. Terciles would fall
      at 0.200/0.259. Only worth doing if the label survives the demotion
      question above.
- [ ] **Stage 3 is now the only gamma thread with a defensible premise.**
      Our gamma is UNSIGNED: B76 gamma is positive and identical for CE
      and PE at a strike, so the profile cannot distinguish stabilizing
      (long-gamma, pins) from destabilizing (short-gamma, trends) — which
      is exactly the distinction every failed thesis needed. Unblocking
      signed_gex_probe.py step 4 is an OPS task (tick-file access on the
      worker volume: `railway ssh` or GDrive offload), not research.
- [ ] **day_plan: rewrite the DIFFUSE branch rationale.** The
      2026-08-18 cycle tested down-diffuse for the first time (n=3)
      and the "covering-fuel drift, writers re-form a rung up, 4/4
      up-drift days closed strong" text is now wrong on half its
      sample; the "zero down-diffuse tested" caveat is stale. Short
      premium was NOT punished on diffuse-down (+33.0/+13.7/-1.4).
      OBSERVATIONS obs. 35, 43.
- [ ] **day_plan: condition IV percentile and credit thinness on DTE.**
      `iv_percentile` compares ATM IV across all history at one snap
      and `credit_min_win` compares a 0-DTE credit against a 4-DTE
      one — both DTE-blind, and both produced the cycle's advisory
      misses. The 40-pt divergence flag band has the same problem
      (carry baseline collapsed -61.6 -> -7.1 into expiry).
      OBSERVATIONS obs. 38, 40, 41.
- [ ] Housekeeping: merge options_data_v1 -> main (closes R-025/R-026
      Alembic condition); prune old branches/stash
- [~] **Stage 3 — signed dealer gamma (GEX sign)** — STARTED 2026-08-08
      (founder pulled it forward): research/signed_gex_probe.py implements
      steps 1-3 (Lee-Ready aggressor classifier vs recorded book,
      passive-side writer attribution with dOI opened/closed split,
      per-strike signed gamma FLOW), 18 unit tests green, schema-verified
      on recorded ticks. REMAINING: run the sweep over all recorded
      sessions on the worker volume (needs `railway ssh` permission or
      GDrive offload) + write RESULTS with the out-of-sample sign test
      (step 4, the pass/fail gate). Original deferred spec below still
      governs the method. Sign the dealer/writer book from our
      own tick data (aggressor classification -> signed dOI ->
      signed gamma), NOT the US CE-long/PE-short assumption (NIFTY writers
      are structurally net short gamma). Out-of-sample test: does the
      empirical sign match the behavioural regime label on every logged
      day? Full detailed spec + build order + strategy hookup:
      research/NOTE_stage3_signed_gex.md. Do LAST, after the items above.
