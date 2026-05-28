# Insight Engine — task list

Owners: 🤖 Claude, 👤 user reviews / decides.
Risk: 🔴 high (gates downstream work), 🟡 medium, 🟢 low.

See `PLAN.md` for full context, design decisions, editorial guidelines, and
the knowledge-first roadmap. See `ANALOG_STUDY.md` for the validity failure
that drove the analog retirement and the resulting design principles.

---

## Current status snapshot

| Phase | Title | Status |
|---|---|---|
| 0 | Data engines | ✅ shipped (12 modules, 119 tests) |
| 1 | Daily Quant Note | ✅ shipped (8 modules + CLI, 72 tests) |
| 2 | Web dashboard | ✅ shipped (4 pages + API, 32 tests; design polish deferred to design-engine integration) |
| 3 | Automation + multi-channel | 🔲 not started |
| **4** | **Pattern + structural expansion** | 🔲 next — concentration widget queued |
| **5.A** | **Inline explainers (Learn layer)** | ✅ shipped 2026-05-28 — 12 explainers prerendered, "What is this?" links on Pulse/Sectors/Watchlists, Learn tab in nav |
| **5.B-D** | **Knowledge layer remainder** | 🔲 Learn hub, teach-while-broadcasting, validity protocol |
| 6 | Close-out | 🔲 not started |

**Retired:** the analog finder's forward-return user-facing content (page +
commentary section + template section). Module survives as a research
artifact. Trail: `ANALOG_STUDY.md` + `analog_validity_study.py`.

Total tests passing on this branch: **223**.

---

## Phase 0 — Data engines (✅ shipped)

| # | Task | Status |
|---|---|---|
| 0.0 | Branch rename `nifty-trader` → `insight-engine` + task folder | ✅ |
| 0.2 | Promote `breadth.py` into `kite-api/app/insights/` | ✅ |
| 0.3 | Promote `macro.py` into `kite-api/app/insights/` | ✅ |
| 0.4 | `scripts/fetch_sector_constituents.py` + monthly NSE snapshots | ✅ |
| 0.5 | Initial sector constituent snapshots committed (12 sectors, 212 stocks) | ✅ |
| 0.5a | **DEFERRED** — fetch price history for 8 stocks outside `nse500_data_merged/` (NIFTY_MEDIA × 6, LGEINDIA, LTM) so all sectors get full breadth coverage | ☐ |
| 0.6 | `sector_constituents.py` loader with PARTIAL_COVERAGE flag + reverse mapping | ✅ |
| 0.7 | `sector_breadth.py` — constituent-level metrics, RS leaders/laggards | ✅ |
| 0.8 | `sector_rs.py` — RS ranking + WoW deltas + narrow/broad overlay | ✅ |
| 0.9 | `scripts/fetch_macro_extras.py` (USDINR, gold, US 10y, crude, FII/DII) | 🔲 → moved to Phase 4.5 |
| 0.10 | `cross_asset.py` | 🔲 → moved to Phase 4.5 |
| 0.11 | `fii_dii.py` | 🔲 → moved to Phase 4.5 |
| 0.12 | `regime.py` — 4-state classifier with 3-day smoothing | ✅ |
| 0.13 | `stress.py` — 0-100 composite score | ✅ |
| 0.14 | `analog_finder.py` — KNN matcher | ✅ built; user-facing content retired (see ANALOG_STUDY.md) |
| 0.15 | `conditional_dist.py` — regime/stress-bucketed forward returns | ✅ |
| 0.16 | `watchlists.py` — 5 default lists | ✅ |
| 0.17 | `reading.py` — MarketReading orchestrator | ✅ |

## Phase 1 — Daily Quant Note (✅ shipped)

| # | Task | Status |
|---|---|---|
| 1.1 | `notes/chart_renderer.py` — 1080×1350 PNG | ✅ |
| 1.2 | `notes/commentary.py` — deterministic narrative engine (no jargon, no recommendation verbs, analog paragraph retired post-study) | ✅ |
| 1.3-1.5 | `templates/{postclose,premarket,weekly}.py` — three text templates | ✅ |
| 1.6 | `note_assembler.py` — NoteBundle (text + PNG + metadata) | ✅ |
| 1.7 | `scripts/generate_quant_note.py` — manual-broadcast CLI | ✅ |
| 1.8-1.10 | Verification (4 historical regimes × 3 modes, jargon enforcement, chart legibility) | ✅ |

## Phase 2 — Web dashboard (✅ structure shipped; visual design deferred)

| # | Task | Status |
|---|---|---|
| 2.1 | Backend API `app/api/insights.py` — 9 public read-only routes + cache headers + 32 tests | ✅ |
| 2.2 | Frontend Pulse page (`/insights`) | ✅ structure-only |
| 2.3 | Frontend Sectors page (`/insights/sectors`) | ✅ structure-only |
| 2.4 | ~~Frontend Analogs page~~ | ❌ retired post-validity-study |
| 2.5 | Frontend Watchlists page (`/insights/watchlists`) | ✅ structure-only |
| 2.6 | Frontend Notes archive (`/insights/notes`) | 🔲 deferred — needs note-storage layer first |
| 2.7 | Portfolio CTAs in `/insights` pages | 🔲 deferred to design integration |
| 2.8 | SEO structured data | 🔲 deferred to design integration |
| 2.9 | Auth gate — revised to require Clerk login but no role/sub check (free tier OK). Middleware updated; pages render server-side once signed in. | ✅ |
| 2.10 | Lighthouse polish | 🔲 deferred to design integration |
| 2.11 | `?date=YYYY-MM-DD` historical-snapshot navigation + 9 preset chips in shared layout | ✅ |
| 2.12 | Regime legend on Pulse page + "What do these mean?" anchor link from the regime stat card | ✅ |
| 2.13 | `scripts/sync_insights_panels.py` — appends daily live fetch into long-history panels so dashboard reflects today's data without manual stitching | ✅ |

---

## Phase 3 — Automation + multi-channel distribution (🔲 not started — paused pending design-engine integration)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 3.1 | WhatsApp Business API account setup (Meta Cloud API) | 👤 | 🔴 | ☐ |
| 3.2 | `kite-api/app/services/whatsapp_service.py` — broadcast list manager + templated sender | 🤖 | 🔴 | ☐ |
| 3.3 | `/insights/subscribe` form (phone + email + channel prefs) → Postgres | 🤖 | 🟡 | ☐ |
| 3.4 | `insights_scheduler.py` — Railway cron at 8:30, 16:15, Sun 20:00 | 🤖 | 🔴 | ☐ |
| 3.5 | Email service (SendGrid/Mailgun) integration | 🤖 | 🟡 | ☐ |
| 3.6 | Event-trigger watcher (15-min polling; rate-limited ≤3/day) | 🤖 | 🔴 | ☐ |
| 3.7 | Click-through tracking — WhatsApp/email → web → portfolio CTA | 🤖 | 🟡 | ☐ |
| 3.8 | End-to-end pipeline test (trigger note → WhatsApp delivery → web → CTA tracked) | 🤖 + 👤 | 🔴 | ☐ |
| 3.9 | 1-week unattended soak test | 👤 | 🔴 | ☐ |

---

## Phase 4 — Pattern + structural expansion (🔲 NEXT)

### 4.1 — Concentration / Reliance impact widget

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.1.1 | Build `kite-api/app/insights/concentration.py`. Daily computation of: each Nifty 50 constituent's contribution to today's Nifty move (using cap-weighted index methodology); top-3 / top-5 cumulative contribution; specific RIL share; cap-weighted vs equal-weighted spread (1d, 5d, 20d) | 🤖 | 🟡 | ☐ |
| 4.1.2 | Tests: covers historical days where the move was famously concentrated (e.g., RIL earnings days) vs broadly shared days; verify the contribution percentages sum to 100% within rounding | 🤖 | 🔴 | ☐ |
| 4.1.3 | Add `concentration` field to `MarketReading` orchestrator | 🤖 | 🟡 | ☐ |
| 4.1.4 | Add API route `/api/insights/concentration` (returns latest + 60d history) | 🤖 | 🟡 | ☐ |
| 4.1.5 | Surface on Pulse page header: "Today's Nifty move was X% real, Y% RIL-driven" or "8 of top 10 contributors aligned — broad participation" | 🤖 | 🟢 | ☐ |
| 4.1.6 | Update commentary engine — concentration_paragraph() that flags days where >50% of move came from top 3 names | 🤖 | 🟡 | ☐ |
| 4.1.7 | Inline explainer link "What is concentration?" → `/insights/learn/indicators/concentration` (created in Phase 5.A) | 🤖 | 🟢 | ☐ |

### 4.2 — Pattern-based watchlists (validity-checked)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.2.1 | Define 5 new detectors in `kite-api/app/insights/watchlists.py` (one function each): multi_year_breakout, pullback_to_50dma, golden_cross_5d_old, sustained_higher_highs_lows_60d, sector_thrust_day_constituents | 🤖 | 🟡 | ☐ |
| 4.2.2 | Per-pattern validity study script template (mirror `analog_validity_study.py`): for each detector, sample 200+ historical fire days, compute fwd 5/20/60/120d returns, compare against unconditional baseline. Honest report: IC, direction-lift, baseline-excess. | 🤖 | 🔴 | ☐ |
| 4.2.3 | Run validity study for each of the 5 new patterns; write findings into `tasks/insight_engine/PATTERN_VALIDITY/{name}.md` | 🤖 | 🔴 | ☐ |
| 4.2.4 | Promote validated patterns (those with baseline-excess > 1pp AND positive direction lift) to live watchlists; mark borderline/failed patterns as "names only, no forward stats" | 🤖 | 🔴 | ☐ |
| 4.2.5 | Update Watchlists page to add the new lists with brief explainers per-pattern | 🤖 | 🟡 | ☐ |
| 4.2.6 | Update commentary engine to surface notable pattern fires (e.g., "5 stocks just broke out of multi-year bases — a cluster like this last happened in...") | 🤖 | 🟡 | ☐ |

### 4.3 — Sector subgroup tracker

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.3.1 | Define subgroup membership manually in `data/static/sector_subgroups.yaml`: private banks (HDFCBANK / ICICIBANK / AXISBANK / KOTAKBANK / INDUSINDBK) vs PSU banks (SBIN / PNB / CANBK / BANKBARODA / UNIONBANK); large-cap pharma (SUNPHARMA / DRREDDY / CIPLA) vs mid-cap pharma (etc.); auto-OEMs (MARUTI / TATAMOTORS / M&M / TVSMOTOR) vs auto-ancillaries (MOTHERSON / BHARATFORG / etc.) | 👤 + 🤖 | 🟡 | ☐ |
| 4.3.2 | Build `kite-api/app/insights/subgroups.py` — for each subgroup: RS vs Nifty (5/20/60d), breadth (% above 200-DMA), today's chg, WoW delta. Pattern matches sector_rs.py / sector_breadth.py | 🤖 | 🟡 | ☐ |
| 4.3.3 | Tests verifying subgroup membership integrity + spot-check historical episodes (e.g., 2018 NBFC — PSU banks should show extreme weakness) | 🤖 | 🟡 | ☐ |
| 4.3.4 | Add to MarketReading + API endpoint `/api/insights/subgroups` | 🤖 | 🟡 | ☐ |
| 4.3.5 | Add to Sectors page — second section below sector cards | 🤖 | 🟢 | ☐ |
| 4.3.6 | Commentary integration — subgroup spread paragraph when >5pp divergence between sibling subgroups | 🤖 | 🟡 | ☐ |

### 4.4 — Anniversary / calendar content

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.4.1 | Build `kite-api/app/insights/calendar_content.py`. For any date D, finds: 1y / 3y / 5y / 10y ago today. For each anniversary, returns regime + stress + notable event tag (manual annotations file). | 🤖 | 🟡 | ☐ |
| 4.4.2 | Manual annotations file `data/static/historical_events.yaml` — ~50 notable dates with one-line event descriptors (COVID lockdown, demonetization, NBFC crisis, election results, RBI surprises, etc.) | 👤 + 🤖 | 🟢 | ☐ |
| 4.4.3 | Seasonality computation — historical median/IQR by calendar week + by trading-day-of-month | 🤖 | 🟡 | ☐ |
| 4.4.4 | Pre-event helper — given a known event-day (RBI dates, budget date, large earnings days), compute historical typical move + sector winners | 🤖 | 🟡 | ☐ |
| 4.4.5 | API endpoint `/api/insights/calendar?date=...` | 🤖 | 🟡 | ☐ |
| 4.4.6 | Commentary integration — "On this day" paragraph for weekly digest; pre-event paragraph for premarket on known event days | 🤖 | 🟡 | ☐ |
| 4.4.7 | Optional Pulse-page calendar strip: "5 years ago today: VIX 75 (COVID). Today: VIX 17." | 🤖 | 🟢 | ☐ |

### 4.5 — Cross-asset + FII/DII (formerly Phase 0.9-0.11)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.5.1 | `scripts/fetch_macro_extras.py` — USDINR (RBI/FRED DEXINUS), gold (Yahoo / Investing), US 10y (FRED DGS10), crude (FRED DCOILBRENTEU) | 🤖 | 🟡 | ☐ |
| 4.5.2 | `scripts/fetch_fii_dii.py` — scrape NSE T-1 FII/DII activity report | 🤖 | 🟡 | ☐ |
| 4.5.3 | `kite-api/app/insights/cross_asset.py` — z-scores, ROCs, distance-from-200DMA per asset | 🤖 | 🟡 | ☐ |
| 4.5.4 | `kite-api/app/insights/fii_dii.py` — daily/weekly/monthly cumulative flow, percentile vs history | 🤖 | 🟡 | ☐ |
| 4.5.5 | Tests for both modules + cross-asset validity check (does crude crossing 200-DMA actually predict Nifty energy sector performance?) | 🤖 | 🟡 | ☐ |
| 4.5.6 | Macro widget on Pulse page (4 mini cards: USDINR / Gold / US 10y / Crude with trend arrows) | 🤖 | 🟢 | ☐ |
| 4.5.7 | FII/DII flow widget on Pulse page (last 5 days + 20-day cumulative) | 🤖 | 🟢 | ☐ |
| 4.5.8 | Commentary integration — macro paragraph when one of the 4 assets makes an unusual move (z > 2) | 🤖 | 🟡 | ☐ |

---

## Phase 5 — Knowledge-first content layer (🔲 HIGHEST PRIORITY of new work)

### 5.A — Inline explainers (the "what is this?" connective tissue)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 5.A.1 | Content storage convention + loader (typed TS objects under `kite-dashboard/src/content/insights/learn/`, registry in `_index.ts`, loader at `lib/learn-content.ts`) | 🤖 | 🟡 | ✅ |
| 5.A.2 | Dynamic route `/insights/learn/[topic]/page.tsx` with `generateStaticParams` + `generateMetadata`. Index page at `/insights/learn`. Minimal inline-markup renderer (no new deps). | 🤖 | 🟡 | ✅ |
| 5.A.3 | 12 explainers authored: stress-score, regime, sector-rs, sector-breadth, mcclellan-oscillator, pct-above-200dma, dispersion, coiled-spring, breakout, rs-leader, drawdown, vix | 👤 + 🤖 | 🟡 | ✅ |
| 5.A.4 | "What is this?" links wired into Pulse (regime, stress, breadth, RS + breadth on leaderboard), Sectors (RS, breadth), Watchlists (breakouts/rs_leaders/coiled_springs); Learn tab added to layout nav; SnapshotPicker wrapped in Suspense | 🤖 | 🟢 | ✅ |
| 5.A.5 | Hover-card / popover for inline term definitions | 🤖 | 🟢 | 🔲 deferred to design integration |
| 5.A.6 | Coverage verification — `next build` prerenders all 12 explainer routes via `generateStaticParams`; broken slug references would fail prerender. Formal Jest/Vitest setup not installed in kite-dashboard yet; revisit if test-runner gets wired up. | 🤖 | 🟡 | ✅ (build-time) |

### 5.B — Standalone Learn hub

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 5.B.1 | Index route `kite-dashboard/src/app/insights/learn/page.tsx` — directory of all explainer pieces grouped by category (Indicators / Patterns / Concepts / Glossary) | 🤖 | 🟡 | ☐ |
| 5.B.2 | Glossary content — `kite-dashboard/src/content/insights/learn/glossary/<term>.md` files for ~40 terms (FII, DII, VIX, RS, breadth, regime, dispersion, basis, percentile, drawdown, coiled spring, golden cross, etc.) | 👤 + 🤖 | 🟢 | ☐ |
| 5.B.3 | Glossary index page `/insights/learn/glossary` — alphabetical list with 1-line snippets | 🤖 | 🟢 | ☐ |
| 5.B.4 | Indicator deep-dives — long-form versions of the inline explainers (5.A.3) for the 12 primary indicators. Each includes: definition, methodology, historical chart (uses chart_renderer primitives), extreme-readings table with dates, "how to read it" section | 🤖 + 👤 | 🟡 | ☐ |
| 5.B.5 | Pattern guides — one piece per pattern from Phase 4.2 + the existing 5 watchlists. Each includes: definition, visual diagram (server-rendered PNG), detection rule (transparent), validity-study findings (honest), historical case studies | 🤖 + 👤 | 🟡 | ☐ |
| 5.B.6 | Add "Learn" tab to the `/insights/*` layout navigation | 🤖 | 🟢 | ☐ |
| 5.B.7 | SEO: structured data (Article schema) on each deep-dive piece — content is the SEO engine of the funnel | 🤖 | 🟡 | ☐ |

### 5.C — Teach-while-broadcasting (Daily Note enhancements)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 5.C.1 | Add `learn_moment` field to `Commentary` dataclass — one rotating "teaching micro-moment" per note | 🤖 | 🟡 | ☐ |
| 5.C.2 | Build 3 rotating learn-moment generators: indicator_spotlight (fires when an indicator does something unusual), pattern_of_the_week (Sunday digest), on_this_day (anniversary content from 4.4) | 🤖 | 🟡 | ☐ |
| 5.C.3 | Integration with template engine — postclose gets indicator_spotlight (when applicable), weekly gets pattern_of_the_week, premarket gets on_this_day if a notable anniversary | 🤖 | 🟡 | ☐ |
| 5.C.4 | Tests: each generator produces non-empty output for ≥5 sample dates; jargon-check on learn_moment text | 🤖 | 🟡 | ☐ |

### 5.D — Validity-first design principle (cross-cutting governance)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 5.D.1 | Refactor `analog_validity_study.py` into a reusable harness — any new forward-return-claim feature uses it before publishing | 🤖 | 🟡 | ☐ |
| 5.D.2 | Add a `tasks/insight_engine/VALIDITY_PROTOCOL.md` document — the checklist any new "what historically happens after X" feature must pass before it's published with forward-return framing | 🤖 | 🟢 | ☐ |
| 5.D.3 | Audit existing live forward-return content (conditional_dist regime/stress baselines) against the protocol — confirm STRESS regime → +3% fwd 20d remains validated. Document in `VALIDITY_PROTOCOL.md`. | 🤖 | 🔴 | ☐ |

---

## Phase 6 — Close-out

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 6.1 | RESULTS.md — what shipped vs planned, deferred items, lessons learned (most importantly: the validity-first design principle from the analog retirement) | 🤖 | 🟢 | ☐ |
| 6.2 | Final commit + push insight-engine branch | 🤖 | 🟢 | ☐ |
| 6.3 | Open PR back to main | 👤 | 🟢 | ☐ |
| 6.4 | `_meta.yml` → `status: shipped` | 🤖 | 🟢 | ☐ |

---

## Priority order for the next push

When you say "let's keep going":

1. ~~**5.A** (inline explainers)~~ ✅ shipped 2026-05-28
2. **4.1** (concentration / Reliance impact) — **next up**. Small, unique, immediately resonant on Pulse page. Earns its own validity check (Phase 5.D protocol).
3. **5.B** (Learn hub) — long-form versions of the 12 inline pieces + glossary. Mostly authoring.
4. **4.2** (pattern watchlists with validity checks) — careful work; each pattern goes through the validity protocol before publishing fwd-return framing.
5. **5.C** (teach-while-broadcasting) — once 5.B exists, this is template work.
6. **4.3 / 4.4 / 4.5** (subgroups / calendar / cross-asset) — in any order; each is self-contained.
7. **Phase 3** (automation) — defer until design-engine integrates; manual broadcast workflow handles current scale.

Total estimated effort for remainder of Phase 4 + 5: ~8-12 working days.
