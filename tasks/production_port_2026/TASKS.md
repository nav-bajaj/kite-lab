# Tasks — production port 2026

Owners: 👤 founder, 🤖 agent. Risk tags: [prod] touches live services, [data] touches the store,
[gate] needs a register row or founder sign-off.

## P0 — engine hooks into the production engine 🤖 [prod] — DONE locally 2026-09-11 (not pushed; freeze)
- [x] Port the five additive hooks from `tasks/mm_rebuild/lib/_engine_iv.py` into
      `scripts/_clean_engine.py` as default-off keyword arguments: `size_weights`, `top_n_fn`,
      `sector_of`/`sector_cap`, `fill_from_buffer`, `trim_to_target`. Byte-identity test: every
      existing production runner and `kite-api/tests` unchanged with the defaults (the mm copy
      already passed this at equal weight).
- [x] Port the runner-level pieces into a shared research/production module (`data_pipeline/`):
      inverse-vol `size_weights` (63-day, 10% cap), `top_n_fn` from a regime series, sector map
      loader, `stop_check` and `rebalance_day` date builders (`monthly_on_or_after`).
- [x] Move the two scores into `data_pipeline/`: vol-adjusted momentum with skip
      (`tasks/mm_rebuild/lib/momentum.py`) and the capture statistics
      (`tasks/om25_rebuild/lib/score.py`), plus the rank blend.
- [x] Regime: `roc_regime` (NIFTY 100, ROC31, confirm 3, lagged) into `data_pipeline/`.
- [x] Unit tests: the §8 look-ahead self-checks (regime and any exposure series rebuilt from
      data truncated the day before) as pytest.

P0 verification: OM25 harness (no hooks) and both new books (all hooks) reproduce their stored
runs byte-identically on the patched engine; `tests/test_engine_hooks.py` (5) and
`tests/test_strategy_lookahead.py` (4) pass; the rest of the suite is unchanged (2 failures and 3
errors pre-date the patch: `test_benchmark_data_accuracy`, `test_price_client` chunking, and three
data-file-dependent tests; `test_ta_indicators.py` has a collection error). The engine copy
`tasks/mm_rebuild/lib/_engine_iv.py` is deleted; the research `momentum.py`, `score.py` and
`regime.py` are re-exports of `data_pipeline/strategies/`. Still open from P0: the MM research
runner (`tasks/mm_rebuild/lib/run.py`) keeps its own sizing / regime wiring — the shared builders in
`data_pipeline/strategies/sizing.py` and `calendar.py` are what P2's runners use.

## P1 — the master store as production source of record 🤖👤 [data][gate] — code done locally 2026-09-11; deploy steps open
- [x] Nightly refresh of `data/master`: `scripts/refresh_master_store.py` (19:30 IST) runs, as
      subprocesses, the spine steps now packaged as `data_pipeline/master_store/` — bhavcopy of the
      day → symbol master + parquet → raw series → NSE CA filings → CA table → observed events → Kite
      append (`--since-days 20`, merged) → adjusted views → Kite-vs-raw verification → QA report →
      gate (`qa/nightly_latest.json`, ok | flagged). First local run 2026-09-11: 10 steps ok, 11.7
      minutes (Kite append 6 min, verification 3 min); gate flagged on 27 unexplained Kite steps in
      30 days (the standing review list, not new). Fixes found by the run: a 404 for a not-yet-
      published day was being recorded as a permanent holiday (10 and 11 Sep had been lost; fixed
      and re-fetched); the QA gate reads the named date column; the Kite step had reported "ok" while
      every symbol errored (no valid local token) and had overwritten the manifest's metadata with
      the error — now an error keeps the previous entry (`last_error`) and the runner fails the step
      when more than 5% of symbols error on the day. The Kite series on disk were verified intact
      (1,041 files, none shorter than the previous manifest). QA note: the other session's
      `extra_targets.csv` adds ~1,500 non-index names to the bhavcopy export, so `bad_prints.csv`
      now carries many rows with no Kite comparison (NaN); the gate counts only Kite disagreements.
      Scheduler entry `master_store_refresh` registered at 19:30 mon-fri, **enabled: False** until
      the store exists on the production volume; command `master_store_refresh` in `job_service`.
- [x] Merged to `beta_gtm_mvp` (459a17c) and deployed 2026-09-11 18:27 IST; health ok. Production
      behaviour unchanged (engine byte-identical with defaults; scheduler entry disabled).
- [x] Seeded 2026-09-11 22:24 IST via the admin upload endpoint (`master` target, 23,274 files, 1.8 GB on `kite-lab-volume`; volume 3.0 of 5 GB). Original plan below for the record: stream the archive (875 MB compressed; price-return view, raw bhavcopy, parquet,
      Kite, CA, membership, benchmarks, QA; the total-return view and GDF left out) over `railway ssh`
      into `/data/master` on `kite-lab-volume` (1.48 of 5 GB used before; ~3.9 GB after). Nothing
      already on the volume is touched — `/data/master` is a new directory beside the legacy
      `nse500_data*` and portfolio folders. Set `MASTER_STORE_DIR=/data/master` and
      `MASTER_STORE_SKIP_TR=1` on the service; grow the volume to 10 GB when convenient.
- [x] Hand runs on Railway 2026-09-11 (over `railway ssh`, `nohup`): three fixes surfaced — pyarrow/requests missing from the image, store paths built from the repo root instead of `MASTER_STORE_DIR`, Kite targets read from the reconstruction files; all deployed. Final run: every step ok (bhavcopy 71 s, series 89 s, Kite append 348 s with 0 of 1,045 errors, adjusted 62 s, verification 372 s); gate flagged on the standing unexplained-Kite-steps list (40 in 30 days after the append; the forced ex-date re-pull clears those). `enabled` flipped to True; first scheduled run Monday 2026-09-14 19:30 IST.
- [x] Full nightly verified on Railway 2026-09-11 23:46 IST after two more fixes (forced ex-date re-pull; Kite series deduped — Kite returned duplicate days for COALINDIA and ONGC on a full pull, which crashed the verification): every step ok, gate flagged on the standing list (33 unexplained Kite steps in 30 days, 1 stale tail, 0 Kite-disagreeing bad prints). `qa/nightly_latest.json` is the morning-review file.
- [ ] Morning review after the first scheduled run (Mon 2026-09-14 19:30 IST); grow the volume to 10 GB.
- [ ] Morning review of `qa/nightly_latest.json` when flagged: `kite_steps_unexplained.csv`
      (Kite adjustments with no CA filing), `bad_prints.csv` rows where Kite disagrees, stale tails.
      Surface the status on `/api/freshness` (P3).
- [ ] Membership events at reconstitution are still the `tasks/universe_membership` procedure; the
      nightly does not touch membership.
- [ ] Point-in-time membership: `data/master/membership/{nifty250,nse500}.csv` become the
      files the production runners read (schema already matches `scripts/universe_membership.py`).
      Decide with the founder whether the legacy books switch too (they were tuned on the
      backdated file; switching restates their track from the cut-over date only — D-5).
- [ ] Sector labels: `tasks/mm_rebuild/sector/sector_v2_lookup.csv` moves under
      `data/master/sectors/` with the scheme map; refresh procedure in `DATA_OPERATIONS.md`.
- [ ] Benchmarks: NIFTY 100/500, Midcap 150, LargeMidcap 250 (real, from 2020), and the
      synthetic MidSmall 400 builder as a script (the §4f construction, tail bug fixed).
- [ ] Register row for the source-of-record change (risk register) 👤.

## P2 — runners and the daily pipeline 🤖 [prod]
- [ ] `scripts/run_mm_portfolio.py` and `scripts/run_om25_v4_portfolio.py` (working names)
      with LOCKED configs from `tasks/mm_rebuild/MECHANICS.md`; outputs in the existing
      `data/<book>_portfolios/<stamp>/` layout (equity, trades, exits, metrics, latest.json).
- [ ] Both added to `update_all_portfolios.py`; rebalance day = first trading day; stop
      check at the monthly signal; one action day.
- [ ] EOD proposed-orders adapter (`run_eod_proposed_orders.py`) understands the two books.
- [ ] Recompute-from-lock-date discipline: the books' history starts at their lock date;
      the research equity (2010 →) is kept as `backtests/` reference only (D-4, D-5).

## P3 — DB, API and dashboard 🤖👤 [prod]
- [ ] Universe IDs (never renamed once in DB rows) — **proposal**: `mm_v1` and `om25_v4`;
      the version suffix follows the existing `om25_v3` / `l6_v2` pattern and leaves room for
      the quarterly-monitoring process to produce a v5 without renaming. 👤 to confirm.
- [ ] Display names — **proposal**: `mm_v1` → **"Momentum 25"** (the founder's working name
      "MoMo" as the internal nickname; clients see a plain name that says what it is);
      `om25_v4` → **"Quality Momentum"** once v3 retires; during the parallel run
      "Quality Momentum (v4)" and "Quality Momentum (v3)", and L6 v2 → "Core Momentum (v2)".
      One-line descriptions: "Vol-adjusted momentum, Nifty 250, monthly, risk-managed" and
      "Momentum blended with quality participation, Nifty 250, monthly, risk-managed". 👤
- [ ] Website line-up (founder 2026-09-11): in `kite-dashboard/src/lib/universes.ts` add a
      `retired: true` flag (hidden from every role) to `tl25_v3`, `combo_defensive`, `nse500`,
      `nifty250`, `nifty100`; keep `l6_v2` and `om25_v3` client-visible; `DEFAULT_UNIVERSE`
      stays `l6_v2` until MM is client-visible. API: `check_universe_access` unchanged (IDs
      stay valid for existing rows); the job runner still builds all seven. Ship via
      `.claude/workflows/ship-feature.md`, outside the market-hours push freeze. [prod]
- [ ] `check_universe_access` / admin gating: `mm_v1` and `om25_v4` admin-only until the
      founder opens them.
- [ ] Metrics service: the dashboard metric set plus up/down capture vs the MidSmall 400.
- [ ] Docs: `docs/portfolios.md` sections for both books, marked "parallel run".

## P4 — monitoring, forward gate, reports 🤖
- [ ] Fortnightly data-quality job per `DATA_QUALITY_CHECKS.md` (13 checks; every second Monday 07:00 IST;
      report under `reports/data_quality/`, status on `/api/freshness`) — founder request 2026-09-11.
- [ ] Quarterly monitoring script: rebuild the §22 grid (160 configs) on the trailing ten
      years for each book, report challengers beating the standing rules by > 0.10 Sharpe,
      write `reports/portfolios/<quarter>/monitoring.md`; founder sign-off before any change.
- [ ] Forward gate check (rolling 3-year Sharpe ≥ 0.6, drawdown ≥ −40%) in the same report,
      from 2026-10-01.
- [ ] Performance report generator (`tasks/mm_rebuild/lib/report.py`) generalised to any
      book and pointed at the production outputs.

## P5 — parallel run and cut-over 👤🤖 [gate]
- [ ] Run MM and OM25 alongside the four legacy books for ≥ one quarter (paper, then admin
      view).
- [ ] Founder decision: which legacy books retire; client display; `docs/portfolios.md`
      rewrite; CLAUDE.md invariants updated (universe IDs).

## P6 — repo streamline 🤖 (see REPO_STREAMLINE.md)
