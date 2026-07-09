# Insights v2 — task list

Owners: 🤖 Opus 4.8 execution agents, 👤 founder reviews / prod actions.
Risk: 🔴 gates downstream, 🟡 medium, 🟢 low.
See PLAN.md for full context. Commit prefix: `insights_v2:`.

## Phase A — Admin visibility in production (P0)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| A1.1 | Tri-state `NEXT_PUBLIC_INSIGHTS_ACCESS` (off/admin/all) in `flags.ts`, legacy `INSIGHTS_ENABLED=true` ⇒ all | 🤖 | 🟡 | ☐ |
| A1.2 | `middleware.ts`: admin mode requires `metadata.role === "admin"` for `/insights*`; off/all unchanged | 🤖 | 🔴 | ☐ |
| A1.3 | Sidebar + mobile-sidebar "Insights" entry, visibility derived from access mode + role | 🤖 | 🟢 | ☐ |
| A1.4 | Marketing nav/footer show Insights only when access=all | 🤖 | 🟢 | ☐ |
| A2.1 | Add `nse500_data_merged` + `indices_data_historical` to `ALLOWED_UPLOAD_DIRS` (sync.py) | 🤖 | 🔴 | ☐ |
| A2.2 | Verify upload extract path == engine read path on Railway (`settings.data_dir` vs `_repo_root()`); align if not | 🤖 | 🔴 | ☐ |
| A2.3 | `init_persistent_storage.sh`: mkdir + symlink both dirs (+ `cache/` if cheap) | 🤖 | 🔴 | ☐ |
| A2.4 | `security-reviewer` subagent pass on the sync.py / init-script diff | 🤖 | 🔴 | ☐ |
| A3.1 | Shared indices-path resolver; remove hardcoded Documents paths from `macro.py`, `watchlists.py`, `sync_insights_panels.py`; 324 tests stay green | 🤖 | 🟡 | ☐ |
| A4.1 | Upload runbook `RUNBOOK_admin_launch.md` (tarball prep + upload commands + Vercel flag + verification) | 🤖 | 🟡 | ☐ |
| A4.2 | Founder: run data upload with prod admin JWT | 👤 | 🔴 | ☐ |
| A5.1 | Wire `sync_insights_panels.py` into `run_daily_pipeline.py` (late step) + in-process cache clear | 🤖 | 🟡 | ☐ |
| A5.2 | `POST /api/insights/cache/clear` behind `require_admin` | 🤖 | 🟡 | ☐ |
| A5.3 | Measure cold breadth-panel build; pre-warm after clear if slow | 🤖 | 🟡 | ☐ |
| A6.1 | Local verification: pytest + npm run build clean; role-gate behavior confirmed | 🤖 | 🔴 | ☐ |
| A6.2 | Founder: set `NEXT_PUBLIC_INSIGHTS_ACCESS=admin` on Vercel, redeploy, verify prod pages + redeploy-survival | 👤 | 🔴 | ☐ |

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
