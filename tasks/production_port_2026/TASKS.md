# Tasks — production port 2026

Owners: 👤 founder, 🤖 agent. Risk tags: [prod] touches live services, [data] touches the store,
[gate] needs a register row or founder sign-off.

## P0 — engine hooks into the production engine 🤖 [prod]
- [ ] Port the five additive hooks from `tasks/mm_rebuild/lib/_engine_iv.py` into
      `scripts/_clean_engine.py` as default-off keyword arguments: `size_weights`, `top_n_fn`,
      `sector_of`/`sector_cap`, `fill_from_buffer`, `trim_to_target`. Byte-identity test: every
      existing production runner and `kite-api/tests` unchanged with the defaults (the mm copy
      already passed this at equal weight).
- [ ] Port the runner-level pieces into a shared research/production module (`data_pipeline/`):
      inverse-vol `size_weights` (63-day, 10% cap), `top_n_fn` from a regime series, sector map
      loader, `stop_check` and `rebalance_day` date builders (`monthly_on_or_after`).
- [ ] Move the two scores into `data_pipeline/`: vol-adjusted momentum with skip
      (`tasks/mm_rebuild/lib/momentum.py`) and the capture statistics
      (`tasks/om25_rebuild/lib/score.py`), plus the rank blend.
- [ ] Regime: `roc_regime` (NIFTY 100, ROC31, confirm 3, lagged) into `data_pipeline/`.
- [ ] Unit tests: the §8 look-ahead self-checks (regime and any exposure series rebuilt from
      data truncated the day before) as pytest.

## P1 — the master store as production source of record 🤖👤 [data][gate]
- [ ] Nightly refresh of `data/master` per `DATA_OPERATIONS.md` (Kite day candles for all-ever
      members; bhavcopy of the day; CA table; membership events) with the QA gate.
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
- [ ] Universe IDs (never renamed once in DB rows): propose `mm_v1`, `om25_v4` 👤.
- [ ] `check_universe_access` / admin gating: both admin-only until the founder opens them.
- [ ] `kite-dashboard/src/lib/universes.ts` display names 👤 ("MoMo", "Quality Momentum v4"?).
- [ ] Metrics service: the dashboard metric set plus up/down capture vs the MidSmall 400.
- [ ] Docs: `docs/portfolios.md` sections for both books, marked "parallel run".

## P4 — monitoring, forward gate, reports 🤖
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
