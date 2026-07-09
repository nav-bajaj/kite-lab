# Insights v2 — task list

Owners: 🤖 Opus 4.8 execution agents, 👤 founder reviews / prod actions.
Risk: 🔴 gates downstream, 🟡 medium, 🟢 low.
See PLAN.md for full context. Commit prefix: `insights_v2:`.

## Phase A — Admin visibility in production (P0)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| A1.1 | Tri-state `NEXT_PUBLIC_INSIGHTS_ACCESS` (off/admin/all) in `flags.ts`, legacy `INSIGHTS_ENABLED=true` ⇒ all | 🤖 | 🟡 | ✅ |
| A1.2 | `middleware.ts`: admin mode requires `metadata.role === "admin"` for `/insights*`; off/all unchanged | 🤖 | 🔴 | ✅ |
| A1.3 | Sidebar + mobile-sidebar "Insights" entry, visibility derived from access mode + role | 🤖 | 🟢 | ✅ |
| A1.4 | Marketing nav/footer show Insights only when access=all | 🤖 | 🟢 | ✅ |
| A2.1 | Add `nse500_data_merged` + `indices_data_historical` to `ALLOWED_UPLOAD_DIRS` (sync.py) | 🤖 | 🔴 | ✅ |
| A2.2 | Verify upload extract path == engine read path on Railway (`settings.data_dir` vs `_repo_root()`); align if not | 🤖 | 🔴 | ✅ |
| A2.3 | `init_persistent_storage.sh`: mkdir + symlink both dirs (+ `cache/` if cheap) | 🤖 | 🔴 | ✅ |
| A2.4 | `security-reviewer` subagent pass on the sync.py / init-script diff | 🤖 | 🔴 | ✅ |
| A3.1 | Shared indices-path resolver; remove hardcoded Documents paths from `macro.py`, `watchlists.py`, `sync_insights_panels.py`; 324 tests stay green | 🤖 | 🟡 | ✅ |
| A4.1 | Upload runbook `RUNBOOK_admin_launch.md` (tarball prep + upload commands + Vercel flag + verification) | 🤖 | 🟡 | ✅ |
| A4.2 | Founder: run data upload with prod admin JWT | 👤 | 🔴 | ☐ |
| A5.1 | Wire `sync_insights_panels.py` into `run_daily_pipeline.py` (late step) + in-process cache clear | 🤖 | 🟡 | ✅ |
| A5.2 | `POST /api/insights/cache/clear` behind `require_admin` | 🤖 | 🟡 | ✅ |
| A5.3 | Measure cold breadth-panel build; pre-warm after clear if slow | 🤖 | 🟡 | ✅ |
| A6.1 | Local verification: pytest + npm run build clean; role-gate behavior confirmed | 🤖 | 🔴 | ✅ |
| A6.2 | Founder: set `NEXT_PUBLIC_INSIGHTS_ACCESS=admin` on Vercel, redeploy, verify prod pages + redeploy-survival | 👤 | 🔴 | ☐ |

### Phase A worklog (Opus 4.8 agent, 2026-07-09)

All 🤖 Phase A items done; the two 👤 items (A4.2 upload, A6.2 Vercel flag)
are prod actions documented in `RUNBOOK_admin_launch.md`.

- **A1**: `flags.ts` now exports tri-state `INSIGHTS_ACCESS` (off/admin/all)
  with `INSIGHTS_ENABLED` kept as a derived boolean; legacy
  `NEXT_PUBLIC_INSIGHTS_ENABLED=true` ⇒ `all`. Middleware gates `/insights*`
  by mode (admin mode enforces `metadata.role==="admin"` mirroring
  `isAdminRoute`). New `src/lib/nav.ts` owns the signed-in sidebar list so the
  Insights entry's mode+role visibility lives in one place (used by both
  `sidebar.tsx` and `mobile-sidebar.tsx`). Marketing nav/footer list Insights
  only on `all`.
- **A2**: verified path alignment — `settings.data_dir` is `/app` in the
  Railway image, and `breadth.py` already reads `settings.data_dir/
  nse500_data_merged` (no `_repo_root` special-casing needed). Upload
  extract path, volume symlink source, and engine read path all coincide.
  Added both dirs to `ALLOWED_UPLOAD_DIRS` + `cache/insights` and the two
  panel dirs to the init-script mkdir/symlink block.
- **A2.4**: security-reviewer PASS (approve-with-notes) — no upload code-path
  change, env override is operator-controlled, symlinks match the existing
  pattern. Bumped R-014 review date + residual note in the risk register.
- **A3**: single `app/insights/_paths.indices_dir()` resolver
  (env `INSIGHTS_INDICES_DIR` → local Documents → `settings.data_dir/
  indices_data_historical`) replaces three hardcoded Documents paths. Local
  dev behavior unchanged.
- **A5**: pipeline appends `sync_insights_panels` + clears insight caches as
  late POST_PORTFOLIO steps; `POST /api/insights/cache/clear` behind
  `require_admin` (added to authz gate's ADMIN_ENDPOINTS). Cold-build
  measured: breadth panel 1.9s, full MarketReading 3.6s — both under 5s, so
  no pre-warm hook added.
- **A6**: `pytest tests/` green (679 passed, 1 skipped); `npm run build`
  clean. Also extended `scripts/upload_price_data.py` with the two new
  targets + a `--source-dir` override (for the indices_data_full →
  indices_data_historical rename) so the runbook is a clean one-command
  upload per dir.
- **Deviations**: (1) extracted `src/lib/nav.ts` rather than duplicating the
  visibility logic across both sidebars — cleaner single source of truth.
  (2) extended `upload_price_data.py` (not strictly in the A-list) so the
  founder upload is script-driven rather than raw curl.
- **For Phase C agents**: indices-dir resolution is now
  `app.insights._paths.indices_dir()` — import that instead of hardcoding.
  The insights surface has one admin-only mutating route
  (`POST /api/insights/cache/clear`); keep new engine/mutation routes behind
  `require_admin` + add them to `ADMIN_ENDPOINTS` in `test_clerk_authz.py`.

## Phase B — v1 leftovers (P2)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| B1 | Seasonality engine (4.4.3) — TDD; descriptive-only unless validity passes | 🤖 | 🟡 | ☐ |
| B2 | Pre-event helper (4.4.4) | 🤖 | 🟢 | ☐ |
| B3 | Pulse calendar strip (4.4.7) | 🤖 | 🟢 | ☐ |
| B4 | US 10y via FRED — only if founder provides key | 👤+🤖 | 🟢 | ☐ |

## Phase C — Stock-level analytics (P1)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| C1.1 | `stock_metrics.py` spec tests (fixtures, boundaries, canonical days) — authored FIRST | 🤖 | 🔴 | ✅ |
| C1.2 | `stock_metrics.py` implementation + pkl/memory caching + `clear_all_caches` hook | 🤖 | 🔴 | ✅ |
| C2.1 | Check `data_pipeline/` momentum methodology; document chosen RS composite | 🤖 | 🟡 | ✅ |
| C2.2 | `rs_rank.py` — composite rank, sector rank, 21d rank delta (TDD) | 🤖 | 🔴 | ✅ |
| C3.1 | `scores.py` — Trend / Extension Risk / Volume Confirmation / Momentum Consistency + insight tags (TDD, monotonicity invariants) | 🤖 | 🔴 | ✅ |
| C8.1 | Validity studies: inflection cohort, RS-top-decile, extension-high; badge per protocol | 🤖 | 🔴 | ✅ |
| C8.2 | Extend compliance lexicon tests to all new labels/tags/copy | 🤖 | 🔴 | ✅ |
| C4.1 | `GET /api/insights/screener` (+ tests, payload budget < 500 KB) | 🤖 | 🟡 | ☐ |
| C4.2 | `GET /api/insights/stocks/{symbol}` (+ timeseries + tests) | 🤖 | 🟡 | ☐ |
| C5.1 | `/insights/screener` page — table, filter rail, preset chips, URL-encoded state, mobile fallback | 🤖 | 🟡 | ☐ |
| C5.2 | `/insights/stocks/[symbol]` page — scores, sections, 1y chart, peer strip | 🤖 | 🟡 | ☐ |
| C5.3 | Nav integration + `?date=` snapshot support on both pages | 🤖 | 🟢 | ☐ |
| C6.1 | Pulse: fresh 52w highs/lows names card + RS-improvers mini-list → preset links | 🤖 | 🟢 | ☐ |
| C7.1 | 8 new Learn explainers + glossary additions + deep-links | 🤖 | 🟡 | ☐ |
| C9.1 | Perf: warm screener < 100 ms; cold-build measured + bounded | 🤖 | 🟡 | ◑ (engine half done; screener endpoint is C4) |

### Phase C engines worklog (Opus 4.8 agent, 2026-07-09)

All engine-half items (C1–C3, C8.1, C8.2, C9.1-engine) done and green; the
C4–C7 API+UI work remains for the next agent. Suite: **741 passed, 1
skipped** (was 679/1). Four commits: C1 (`5c0b203`), C2 (`8ecf30a`),
C3 (`c18a8e7`), C8 (`02f6282`).

- **C1 `stock_metrics.py`** — one `StockMetrics` record per symbol per
  as-of date over the 16y OHLCV panel (`nse500_data_merged`). Returns
  1D/1W/1M/3M/6M/12M; DMA positions + distances + 20d slopes + 50>200
  alignment; 52w-high/low distance, days-since-high (most-recent
  occurrence), drawdown-from-peak, fresh-high flag; ATR(14)% , realized
  vol 20/60d annualized, vol percentile vs own 1y, beta vs Nifty 50 (60d),
  1y & 6m max drawdown, RSI(14), 5d-return percentile; volume ratio (vs
  prior-20 avg, today excluded), 5d ratio, 20d avg turnover (₹Cr),
  up/down-day volume ratio, liquidity tier. Insufficient history → `None`
  per field (never NaN). Cache: in-memory dict + pkl per resolved trading
  date under `cache/insights/stock_metrics_<date>.pkl`; wired into
  `reading.clear_all_caches()`.
  - **Design-choice cutoffs** (documented in the module docstring, NOT
    researched thresholds): liquidity Good ≥₹10 Cr / Moderate ≥₹1 Cr / Low;
    RSI is the simple-average 14 variant; ATR is simple mean of TR;
    `vol_ratio` divides by the prior-20 average so "2x" is meaningful.
- **C2 `rs_rank.py`** — composite RS = `0.10·pct(1m)+0.20·pct(3m)+
  0.30·pct(6m)+0.40·pct(12m)` where each horizon return is
  percentile-ranked cross-sectionally, matching the firm's production shape
  (percentile-then-blend, per `om25_v3`/`tl25_v3`/
  `build_momentum_signals_flexible`). Emits rank (1=strongest), percentile,
  sector-relative rank (via `sector_constituents`), 21td rank delta, and
  the momentum-inflection cohort. Full 12M history required to be ranked.
- **C3 `scores.py`** — four transparent 0-100 scores (Trend / Extension
  Risk / Volume Confirmation / Momentum Consistency), each a documented
  weighted checklist that renormalizes over available inputs so it stays
  monotone in its own drivers. Insight tags reuse the existing
  coiled-spring detector (full-universe membership) and the rs_rank
  inflection cohort — no duplication. Exact tag/band strings are the
  compliance surface (`INSIGHT_TAGS`, `EXTENSION_BANDS`, `VOLUME_BANDS`,
  `stock_metrics.LIQUIDITY_TIERS`).
- **C8.1 validity** (`tasks/insights_v2/VALIDITY/*.md`, runner
  `run_validity_studies.py` reusing the insight_engine harness):
  - `rs_top_decile` → **Validated** (20d excess +1.19pp, lift +2.3pp,
    sign-consistent). Forward-return narrative permitted with figures shown.
  - `inflection` → **Not surfaced as prediction** (20d excess -0.27pp, lift
    -1.7pp, sign flips 5/20d neg → 60/120d pos). Observation-only: the UI
    may say "rank improved N places", must NOT imply it predicts returns.
  - `extension_high` → **Names-only / descriptive** (risk-framed, but
    extended names did NOT underperform: 20d excess +0.79pp). "Extended"
    is a state label ("stretched vs its own history"); NO mean-reversion or
    forward claim.
- **C8.2 lexicon** — new `TestInsightsV2LabelLexicon` in
  `tests/test_insights_commentary.py` runs every tag/band/tier through the
  banned-verb + jargon lists and locks the tag/band sets.
- **C9.1 timing** — OHLCV panel cold load 1.96s; `stock_metrics` cold
  build (load+compute+pkl) 1.80s; `rs_rank` cold 0.28s; `scores` cold 1.57s
  (reuses cached metrics). **Warm access for all three is ~0ms** (in-memory
  dict) — the <100ms target is met at the engine layer. Full-history frame
  needs no windowing beyond the natural ≤252td lookbacks; no perf trimming
  required.
- **Deviations**: (1) `scores.get_scores()` composes coiled + inflection +
  RS per date, so its cold path is ~1.6s; warm is 0ms, and the C4 screener
  should call it once per request behind the existing cache. (2) The
  inflection cohort failed its validity study — this is a finding, not a
  bug; the C5/C6 UI must render it as observation-only (design already
  anticipated this via the "New momentum" tag being descriptive).

### CONTRACTS for the C4–C7 API/UI agent

Consume these; do not recompute. All dataclasses have `to_dict()` →
JSON-safe scalars (tags become a list). All accept an optional `asof`
(snapshot date) and degrade to `{}`/`[]` when the panel is unprovisioned.

- `app.insights.stock_metrics`
  - `get_stock_metrics(asof=None) -> dict[symbol, StockMetrics]` — the
    screener row source (per-stock feature frame).
  - `get_price_dma_volume_series(symbol, asof=None, lookback=252) -> dict`
    — detail-page timeseries: dates, close, sma_50, sma_200, vol_ratio.
  - `StockMetrics` — full field list in the dataclass; `LIQUIDITY_TIERS`.
- `app.insights.rs_rank`
  - `get_rs_table(asof=None) -> dict[symbol, RSEntry]` — rank, percentile,
    sector_rank/size, rank_21d_ago, rank_delta_21d.
  - `get_live_inflection_cohort(asof=None, top_n=25) -> list[RSEntry]` —
    biggest rank improvers (render observation-only per validity).
  - `RS_WEIGHTS` — the documented composite weights for the Learn explainer.
- `app.insights.scores`
  - `get_scores(asof=None) -> dict[symbol, StockScores]` — trend_score,
    extension_risk (+extension_band), volume_confirmation (+volume_band),
    momentum_consistency, tags.
  - `compute_scores(m, rs=None, is_coiled=False, is_inflection_top25=False)`
    — pure scorer if you need per-row control.
  - `extension_band(score)` / `volume_band(score)` — label helpers.
  - `INSIGHT_TAGS` / `EXTENSION_BANDS` / `VOLUME_BANDS` — the ONLY strings
    the UI may render for tags/bands (compliance-locked).
- Aggregates for Pulse (C6): derive fresh-52w-high names from
  `get_stock_metrics` (`fresh_52w_high`) and improvers from
  `get_live_inflection_cohort`. Keep `MarketReading` lean — do NOT attach
  the full 500-row table to it.
- Screener endpoint: build the payload by zipping `get_stock_metrics` +
  `get_rs_table` + `get_scores` for one `asof`; all three are warm-cached
  per date, so the request is O(500) dict lookups.

## Phase D — deferred (do not build)

Public flip (`access=all`), CTAs, SEO, notes archive, saved watchlists,
alerts, WhatsApp automation, heatmap, intraday layer, compliance review.

## Close-out

| # | Task | Owner | Done |
|---|---|---|---|
| Z1 | RESULTS.md | 🤖 | ☐ |
| Z2 | PR to main, `--no-ff` merge | 👤 | ☐ |
| Z3 | `_meta.yml` → shipped | 🤖 | ☐ |
