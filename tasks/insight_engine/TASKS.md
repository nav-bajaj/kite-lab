# Insight Engine — task list

Owners: 🤖 Claude, 👤 user reviews / decides.
Risk: 🔴 high (gates downstream work), 🟡 medium, 🟢 low.

See `PLAN.md` for full context, design decisions, and editorial guidelines.

---

## Phase 0 — Data engines

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 0.0 | Rename branch `nifty-trader` → `insight-engine`, push, delete old remote | 🤖 | 🟢 | ✅ |
| 0.1 | Stand up `tasks/insight_engine/` task folder (PLAN/TASKS/_meta) | 🤖 | 🟢 | ✅ |
| 0.2 | Promote `tasks/nifty_trader/breadth_signals.py` → `kite-api/app/insights/breadth.py` — paths via `settings.data_dir`, disk cache + `@lru_cache`, mtime-based invalidation | 🤖 | 🟡 | ✅ |
| 0.3 | Promote `tasks/nifty_trader/macro_signals.py` → `kite-api/app/insights/macro.py` — same caching/path treatment | 🤖 | 🟡 | ✅ |
| 0.3a | Test `kite-api/tests/test_insights_breadth_macro.py` — 13 tests verify schema, value ranges, cache mechanics. All passing. | 🤖 | 🟡 | ✅ |
| 0.4 | Write `scripts/fetch_sector_constituents.py` (NSE sector index constituent CSV ingestion, monthly snapshots) — done, includes DUMMY-placeholder filter | 🤖 | 🔴 | ✅ |
| 0.4a | Write `tests/test_sector_constituents.py` — 11 tests covering schema, size, hygiene, price-data cross-ref, anchor stocks. All passing. | 🤖 | 🔴 | ✅ |
| 0.5 | Initial sector constituent snapshots committed at `data/static/sector_constituents/2026-05/` (12 sectors, 212 total constituents) | 🤖 | 🔴 | ✅ |
| 0.5a | **DEFERRED** — fetch price history for 8 sector constituents currently outside `nse500_data_merged/` so all 12 sectors get full breadth coverage. Stocks: NIFTY_MEDIA (6) → DBCORP, HATHWAY, NAZARA, NETWORK18, PFOCUS, TIPSMUSIC · NIFTY_CONSUMER_DURABLES (1) → LGEINDIA (LG Electronics India, IPO'd Oct 2024) · NIFTY_IT (1) → LTM. Reuse `scripts/fetch_nse500_history.py` + `scripts/history_utils.py` (Kite Connect). After fetching, re-run `tests/test_sector_constituents.py` — NIFTY MEDIA should graduate out of `PARTIAL_COVERAGE_SECTORS`. Not blocking Phase 0 completion; downstream breadth code should treat NIFTY MEDIA as low-confidence until this lands. | 🤖 | 🟡 | ☐ |
| 0.6 | Build `kite-api/app/insights/sector_constituents.py` — Sector dataclass, latest-snapshot loader, reverse symbol→sectors mapping, PARTIAL_COVERAGE flag | 🤖 | 🟡 | ✅ |
| 0.7 | Build `kite-api/app/insights/sector_breadth.py` — constituent-level pct_above_DMA, dispersion, top/bottom RS vs Nifty 6m, thrust detector, leaders/laggards guaranteed disjoint | 🤖 | 🔴 | ✅ |
| 0.7a | Test `kite-api/tests/test_insights_sectors.py` — 19 tests (loader + panel + snapshot + JSON-serializability). All passing. | 🤖 | 🟡 | ✅ |
| 0.8 | Build `kite-api/app/insights/sector_rs.py` — rank sectors by 5/20/60/120/252d RS, week-over-week movement, narrow-vs-broad overlay using sector_breadth | 🤖 | 🟡 | ✅ |
| 0.8a | Test `kite-api/tests/test_insights_sector_rs.py` — 18 tests (panel + snapshot + leaderboard helper + WoW consistency). All passing. | 🤖 | 🟡 | ✅ |
| 0.9 | Write `scripts/fetch_macro_extras.py` — USDINR (RBI/FRED), gold backfill (Yahoo), US 10y (FRED DGS10), crude (FRED DCOILBRENTEU), FII/DII (NSE scrape) | 🤖 | 🟡 | ☐ |
| 0.10 | Build `kite-api/app/insights/cross_asset.py` — load + transform cross-asset signals | 🤖 | 🟡 | ☐ |
| 0.11 | Build `kite-api/app/insights/fii_dii.py` — load + transform FII/DII flows | 🤖 | 🟡 | ☐ |
| 0.12 | Build `kite-api/app/insights/regime.py` — 4-state classifier (TREND_BULL / DRIFT / STRETCHED / STRESS) with 3-day smoothing + persistence tracking. Validated on COVID/NBFC/2022 historical dates. | 🤖 | 🔴 | ✅ |
| 0.13 | Build `kite-api/app/insights/stress.py` — 0-100 composite (35% VIX pctile + 25% drawdown + 20% below-200DMA + 20% dispersion z) with 5y historical percentile context | 🤖 | 🟡 | ✅ |
| 0.13a | Test `kite-api/tests/test_insights_regime_stress.py` — 17 tests, all passing | 🤖 | 🟡 | ✅ |
| 0.14 | Build `kite-api/app/insights/analog_finder.py` — 5-feature KNN with ±60d exclusion + fwd returns at 5/20/60/120d. COVID/calm-day validation passes. 12 tests. | 🤖 | 🔴 | ✅ |
| 0.15 | Build `kite-api/app/insights/conditional_dist.py` — by_regime + by_stress_quintile + by_regime_x_stress joint conditioning, returns distribution stats per bucket × horizon. Validates "buy panic" thesis on aggregate data. 13 tests passing. | 🤖 | 🔴 | ✅ |
| 0.16 | Build `kite-api/app/insights/watchlists.py` — 5 lists (breakouts/RS leaders/coiled springs/stretched/recent breakdowns) with sector tagging. 10 tests passing. | 🤖 | 🟡 | ✅ |
| 0.17 | Build `kite-api/app/insights/reading.py` — MarketReading orchestrator composing all subsystems. JSON-serializable 38KB output; 2-second cold build, <100ms warm. 17 tests passing. | 🤖 | 🔴 | ✅ |
| 0.18 | Verification: March 2020 → stress 99/100, Oct 2021 → TREND_BULL, 2018 NBFC → STRESS — checked in regime+stress tests | 🤖 | 🔴 | ✅ |
| 0.19 | Verification: analog finder reproduces neighborhoods — COVID matches 2011 Eurozone, calm 2017 matches Feb-Mar 2017 cluster — checked in analog tests | 🤖 | 🔴 | ✅ |
| 0.20 | Verification: conditional_dist by regime shows clear separation (STRESS fwd-20d +3.05% / DRIFT +0.39% / TREND_BULL +0.88%) — checked in conditional tests | 🤖 | 🟡 | ✅ |

## Phase 1 — Daily Quant Note (content + manual broadcast)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 1.1 | Build `kite-api/app/insights/notes/chart_renderer.py` — 1080×1350 PNG with regime-shaded stress, sector RS bars, analog fan. Brand header/footer. 10 tests passing. | 🤖 | 🟡 | ✅ |
| 1.2 | Build `kite-api/app/insights/notes/commentary.py` — deterministic narrative engine, no jargon/no recommendation enforced by tests. 33 tests passing. | 🤖 | 🔴 | ✅ |
| 1.3 | Build template `kite-api/app/insights/notes/templates/postclose.py` | 🤖 | 🟡 | ✅ |
| 1.4 | Build template `kite-api/app/insights/notes/templates/premarket.py` | 🤖 | 🟡 | ✅ |
| 1.5 | Build template `kite-api/app/insights/notes/templates/weekly.py` (Sunday digest) | 🤖 | 🟡 | ✅ |
| 1.6 | Build `kite-api/app/insights/notes/note_assembler.py` — NoteBundle (text + PNG + metadata) ready for broadcast | 🤖 | 🟡 | ✅ |
| 1.7 | Build `scripts/generate_quant_note.py` CLI — mode/date args, saves to `tasks/insight_engine/runs/daily/YYYY-MM-DD_<mode>.{txt,png}`, opens image preview | 🤖 | 🟡 | ✅ |
| 1.8 | Verification: 4 historical regimes (COVID/2018 NBFC/2022/2017) × 3 modes parametrized in test_insights_notes_assembler — 12 history runs all pass | 👤 + 🤖 | 🔴 | ✅ |
| 1.9 | Editorial review: jargon + recommendation-verb tests in test_insights_commentary enforce voice guidelines | 👤 | 🔴 | ✅ |
| 1.10 | Chart legibility verified by thumbnail-resize test (≥100 unique colors after 3× downsize) — visual review still recommended | 👤 | 🟡 | ✅ |

## Phase 2 — Web dashboard

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 2.1 | Backend: `kite-api/app/api/insights.py` — public read-only routes (Reading, sectors, watchlists, analogs, conditional dist, notes archive) | 🤖 | 🟡 | ☐ |
| 2.2 | Frontend: `kite-dashboard/src/app/insights/page.tsx` — Pulse page (regime/stress/tilt + key internals) | 🤖 | 🟡 | ☐ |
| 2.3 | Frontend: `kite-dashboard/src/app/insights/sectors/page.tsx` — RS heatmap, sector breadth, constituent leaders | 🤖 | 🟡 | ☐ |
| 2.4 | Frontend: `kite-dashboard/src/app/insights/analogs/page.tsx` — interactive analog finder | 🤖 | 🟡 | ☐ |
| 2.5 | Frontend: `kite-dashboard/src/app/insights/watchlists/page.tsx` — sortable/filterable watchlist tables | 🤖 | 🟢 | ☐ |
| 2.6 | Frontend: `kite-dashboard/src/app/insights/notes/page.tsx` + `[date]/page.tsx` — Notes archive (SEO surface) | 🤖 | 🟡 | ☐ |
| 2.7 | Footer/sidebar portfolio CTAs across all `/insights/*` pages | 🤖 | 🟢 | ☐ |
| 2.8 | SEO: structured data (Article schema for Notes, FAQ schema for Insights pages) | 🤖 | 🟡 | ☐ |
| 2.9 | Public access verified (no Clerk auth required on `/insights/*`) | 🤖 | 🔴 | ☐ |
| 2.10 | Lighthouse: mobile + SEO scores > 90 | 🤖 | 🟡 | ☐ |

## Phase 3 — Automation + multi-channel distribution

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 3.1 | WhatsApp Business API account setup (Meta Cloud API, tier-1 free 1k contacts) | 👤 | 🔴 | ☐ |
| 3.2 | Build `kite-api/app/services/whatsapp_service.py` — broadcast list manager, templated sender | 🤖 | 🔴 | ☐ |
| 3.3 | `/insights/subscribe` signup form (phone + email + channel prefs) → Postgres | 🤖 | 🟡 | ☐ |
| 3.4 | Build `kite-api/app/services/insights_scheduler.py` — Railway cron jobs at 8:30, 16:15, Sun 20:00 | 🤖 | 🔴 | ☐ |
| 3.5 | Email service (SendGrid/Mailgun) integration for weekly long-form digest | 🤖 | 🟡 | ☐ |
| 3.6 | Event-trigger watcher — polls intraday market state every 15 min; fires alerts on threshold crossings; rate-limited ≤3/day | 🤖 | 🔴 | ☐ |
| 3.7 | Click-through tracking — tracked short-links from WhatsApp/email → web → portfolio CTA conversion | 🤖 | 🟡 | ☐ |
| 3.8 | End-to-end pipeline test: trigger pre-market → WhatsApp delivery → web link → Pulse page → CTA tracked | 🤖 + 👤 | 🔴 | ☐ |
| 3.9 | 1-week soak test: cron jobs fire automatically; no manual intervention | 👤 | 🔴 | ☐ |

## Phase 4 — Expansion (post-launch, open-ended)

See PLAN.md §Phase 4. Not part of initial scope.

## Phase 5 — Close out

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 5.1 | RESULTS.md — what shipped vs planned, deferred items, lessons | 🤖 | 🟢 | ☐ |
| 5.2 | Final commit + push insight-engine | 🤖 | 🟢 | ☐ |
| 5.3 | Open PR back to main | 👤 | 🟢 | ☐ |
| 5.4 | Update `_meta.yml` → `status: shipped` | 🤖 | 🟢 | ☐ |
