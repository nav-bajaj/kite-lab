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
| C1.1 | `stock_metrics.py` spec tests (fixtures, boundaries, canonical days) — authored FIRST | 🤖 | 🔴 | ☐ |
| C1.2 | `stock_metrics.py` implementation + pkl/memory caching + `clear_all_caches` hook | 🤖 | 🔴 | ☐ |
| C2.1 | Check `data_pipeline/` momentum methodology; document chosen RS composite | 🤖 | 🟡 | ☐ |
| C2.2 | `rs_rank.py` — composite rank, sector rank, 21d rank delta (TDD) | 🤖 | 🔴 | ☐ |
| C3.1 | `scores.py` — Trend / Extension Risk / Volume Confirmation / Momentum Consistency + insight tags (TDD, monotonicity invariants) | 🤖 | 🔴 | ☐ |
| C8.1 | Validity studies: inflection cohort, RS-top-decile, extension-high; badge per protocol | 🤖 | 🔴 | ☐ |
| C8.2 | Extend compliance lexicon tests to all new labels/tags/copy | 🤖 | 🔴 | ☐ |
| C4.1 | `GET /api/insights/screener` (+ tests, payload budget < 500 KB) | 🤖 | 🟡 | ☐ |
| C4.2 | `GET /api/insights/stocks/{symbol}` (+ timeseries + tests) | 🤖 | 🟡 | ☐ |
| C5.1 | `/insights/screener` page — table, filter rail, preset chips, URL-encoded state, mobile fallback | 🤖 | 🟡 | ☐ |
| C5.2 | `/insights/stocks/[symbol]` page — scores, sections, 1y chart, peer strip | 🤖 | 🟡 | ☐ |
| C5.3 | Nav integration + `?date=` snapshot support on both pages | 🤖 | 🟢 | ☐ |
| C6.1 | Pulse: fresh 52w highs/lows names card + RS-improvers mini-list → preset links | 🤖 | 🟢 | ☐ |
| C7.1 | 8 new Learn explainers + glossary additions + deep-links | 🤖 | 🟡 | ☐ |
| C9.1 | Perf: warm screener < 100 ms; cold-build measured + bounded | 🤖 | 🟡 | ☐ |

## Phase D — deferred (do not build)

Public flip (`access=all`), CTAs, SEO, notes archive, saved watchlists,
alerts, WhatsApp automation, heatmap, intraday layer, compliance review.

## Close-out

| # | Task | Owner | Done |
|---|---|---|---|
| Z1 | RESULTS.md | 🤖 | ☐ |
| Z2 | PR to main, `--no-ff` merge | 👤 | ☐ |
| Z3 | `_meta.yml` → shipped | 🤖 | ☐ |
