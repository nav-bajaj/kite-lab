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
| 0.2 | Promote `tasks/nifty_trader/breadth_signals.py` → `kite-api/app/insights/breadth.py` (with caching layer) | 🤖 | 🟡 | ☐ |
| 0.3 | Promote `tasks/nifty_trader/macro_signals.py` → `kite-api/app/insights/macro.py` | 🤖 | 🟡 | ☐ |
| 0.4 | Write `scripts/fetch_sector_constituents.py` (NSE sector index constituent CSV ingestion, monthly snapshots) — done, includes DUMMY-placeholder filter | 🤖 | 🔴 | ✅ |
| 0.4a | Write `tests/test_sector_constituents.py` — 11 tests covering schema, size, hygiene, price-data cross-ref, anchor stocks. All passing. | 🤖 | 🔴 | ✅ |
| 0.5 | Initial sector constituent snapshots committed at `data/static/sector_constituents/2026-05/` (12 sectors, 212 total constituents) | 🤖 | 🔴 | ✅ |
| 0.5a | **DEFERRED** — fetch price history for 8 sector constituents currently outside `nse500_data_merged/` so all 12 sectors get full breadth coverage. Stocks: NIFTY_MEDIA (6) → DBCORP, HATHWAY, NAZARA, NETWORK18, PFOCUS, TIPSMUSIC · NIFTY_CONSUMER_DURABLES (1) → LGEINDIA (LG Electronics India, IPO'd Oct 2024) · NIFTY_IT (1) → LTM. Reuse `scripts/fetch_nse500_history.py` + `scripts/history_utils.py` (Kite Connect). After fetching, re-run `tests/test_sector_constituents.py` — NIFTY MEDIA should graduate out of `PARTIAL_COVERAGE_SECTORS`. Not blocking Phase 0 completion; downstream breadth code should treat NIFTY MEDIA as low-confidence until this lands. | 🤖 | 🟡 | ☐ |
| 0.6 | Build `kite-api/app/insights/sector_constituents.py` (load + serve current mapping) | 🤖 | 🟡 | ☐ |
| 0.7 | Build `kite-api/app/insights/sector_breadth.py` — % above 50/200-DMA on constituents, internal dispersion, top/bottom by RS, sector thrust detector | 🤖 | 🔴 | ☐ |
| 0.8 | Build `kite-api/app/insights/sector_rs.py` — rank sectors by 5/20/60/120/252d RS, week-over-week movement, narrow-vs-broad overlay using sector_breadth | 🤖 | 🟡 | ☐ |
| 0.9 | Write `scripts/fetch_macro_extras.py` — USDINR (RBI/FRED), gold backfill (Yahoo), US 10y (FRED DGS10), crude (FRED DCOILBRENTEU), FII/DII (NSE scrape) | 🤖 | 🟡 | ☐ |
| 0.10 | Build `kite-api/app/insights/cross_asset.py` — load + transform cross-asset signals | 🤖 | 🟡 | ☐ |
| 0.11 | Build `kite-api/app/insights/fii_dii.py` — load + transform FII/DII flows | 🤖 | 🟡 | ☐ |
| 0.12 | Build `kite-api/app/insights/regime.py` — 4-state classifier with persistence tracking, reusing NIFTY 100 100-DMA + 3-conf gate from `scripts/combo_defensive.py` | 🤖 | 🔴 | ☐ |
| 0.13 | Build `kite-api/app/insights/stress.py` — 0-100 composite score (VIX percentile + drawdown depth + %200-DMA + dispersion z) | 🤖 | 🟡 | ☐ |
| 0.14 | Build `kite-api/app/insights/analog_finder.py` — KNN over multi-factor reading vs 16y history, returns top-5 most-similar dates + their forward returns | 🤖 | 🔴 | ☐ |
| 0.15 | Build `kite-api/app/insights/conditional_dist.py` — given regime/stress bucket, return historical fwd-return distribution (mean/median/IQR/5-95) over 5/10/20/60d | 🤖 | 🔴 | ☐ |
| 0.16 | Build `kite-api/app/insights/watchlists.py` — breakouts, RS leaders, coiled springs, stretched, recent breakdowns | 🤖 | 🟡 | ☐ |
| 0.17 | Build `kite-api/app/insights/reading.py` — orchestrator returning unified `MarketReading` per day | 🤖 | 🔴 | ☐ |
| 0.18 | Verification: spot-check March 2020 → stress > 90 percentile, Jan 2017 → Trend-Bull regime | 🤖 | 🔴 | ☐ |
| 0.19 | Verification: pass historical date to analog_finder; verify it recognizes its own historical neighbors | 🤖 | 🔴 | ☐ |
| 0.20 | Verification: conditional_dist histograms across regimes look meaningfully different | 🤖 | 🟡 | ☐ |

## Phase 1 — Daily Quant Note (content + manual broadcast)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 1.1 | Build `kite-api/app/insights/notes/chart_renderer.py` — matplotlib branded image, 1080x1350 PNG, WhatsApp-portrait | 🤖 | 🟡 | ☐ |
| 1.2 | Build `kite-api/app/insights/notes/commentary.py` — plain-English narrative engine per editorial guidelines (PLAN §Editorial voice) | 🤖 | 🔴 | ☐ |
| 1.3 | Build template `kite-api/app/insights/notes/templates/postclose.py` | 🤖 | 🟡 | ☐ |
| 1.4 | Build template `kite-api/app/insights/notes/templates/premarket.py` | 🤖 | 🟡 | ☐ |
| 1.5 | Build template `kite-api/app/insights/notes/templates/weekly.py` (Sunday digest) | 🤖 | 🟡 | ☐ |
| 1.6 | Build `kite-api/app/insights/notes/note_assembler.py` — combines text + chart into WhatsApp-ready package | 🤖 | 🟡 | ☐ |
| 1.7 | Build `scripts/generate_quant_note.py` CLI — admin workflow (run mode → preview → manual broadcast) | 🤖 | 🟡 | ☐ |
| 1.8 | Verification: generate notes for 5 historical days (COVID crash, demonetization, 2017 melt-up, 2018 NBFC, 2022 rate-shock); confirm each reads coherently | 👤 + 🤖 | 🔴 | ☐ |
| 1.9 | Editorial review: jargon-check pass on commentary outputs — ensure plain-English translation rules followed | 👤 | 🔴 | ☐ |
| 1.10 | Chart legibility check at WhatsApp thumbnail resolution (375px wide) | 👤 | 🟡 | ☐ |

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
