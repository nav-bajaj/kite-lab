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
| **4.1** | **Concentration / Reliance impact widget** | ✅ shipped 2026-05-28 |
| **4.2** | **Pattern watchlists + validity studies** | ✅ shipped 2026-05-28 — 3 new detectors, reusable validity harness, honest findings (1 PASS / 1 MARGINAL / 1 FAIL), Watchlists UI with validity badges |
| **4.3** | **Sector subgroup tracker** | ✅ shipped 2026-05-28 |
| **4.4** | **Anniversary / calendar (on_this_day)** | ✅ shipped 2026-05-28 — calendar_content engine, 13 curated events, premarket commentary wired, /calendar/on-this-day API. **First fully TDD-driven phase on this branch.** |
| **4.5** | **Cross-asset feature engine** | ✅ shipped 2026-05-28 — `cross_asset.py` engine with TDD spec tests, India 10y series live; USDINR / gold / US10y / crude registered as `data_available=False` with documented fetch sources. **No fabricated data.** |
| **5.C** | **Teach-while-broadcasting** | ✅ shipped 2026-05-28 — learn_moment field on Commentary, indicator-spotlight + pattern-of-the-week generators, all 3 templates updated. Spotlight now also surfaces big sibling-subgroup spreads. |
| **5.A** | **Inline explainers (Learn layer)** | ✅ shipped 2026-05-28 — 13 explainers prerendered, "What is this?" links on Pulse/Sectors/Watchlists, Learn tab in nav |
| **5.B** | **Learn hub — glossary + deep-dives + pattern guides** | ✅ shipped 2026-05-28 — 38-term glossary, "Historical context" + "Common misreadings" on every indicator, transparent detection rules on patterns |
| **5.C-D** | **Knowledge layer remainder** | 🔲 teach-while-broadcasting, validity protocol |
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
| 4.1.0 | Static Nifty 50 weights snapshot CSV at `data/static/nifty50_weights.csv` (NSE factsheet, quarterly refresh) — auto-normalised to sum to 100 on load | 🤖 | 🟡 | ✅ |
| 4.1.1 | `kite-api/app/insights/concentration.py` — per-constituent contribution attribution (weight × return), top-3 / top-5 / Reliance shares, cap-vs-equal-weighted spread | 🤖 | 🟡 | ✅ |
| 4.1.2 | Tests at `tests/test_insights_concentration.py` — 14 covering weight normalisation, attribution math, sorting invariants, JSON serialisation, COVID-day shape, calm-day shape, weekend snap-forward, future-date clamp | 🤖 | 🔴 | ✅ |
| 4.1.3 | `concentration` field added to `MarketReading.to_dict()` + `clear_all_caches()` hook | 🤖 | 🟡 | ✅ |
| 4.1.4 | API route `/api/insights/concentration?date=YYYY-MM-DD` (single-date attribution; 60d history endpoint deferred — not needed for current Pulse widget) | 🤖 | 🟡 | ✅ |
| 4.1.5 | Pulse page widget "Who drove today's Nifty 50 move" — auto-narrated headline (narrow/concentrated/broad), 3 stat cards (cap-wt, cap-vs-eq spread, top-3 share), collapsible top-10 contributor table | 🤖 | 🟢 | ✅ |
| 4.1.6 | Commentary engine `concentration_paragraph()` for the Daily Quant Note | 🤖 | 🟡 | 🔲 deferred — Notes pipeline due for refresh alongside 5.C |
| 4.1.7 | Learn explainer `/insights/learn/concentration` + "What is this?" link on widget | 🤖 | 🟢 | ✅ |

### 4.2 — Pattern-based watchlists (validity-checked)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.2.1 | 3 new detectors in `watchlists.py`: `multi_year_breakout` (5y high + 50-DMA), `pullback_to_50dma` (above-200 trending stock within 2% of 50-DMA), `sustained_uptrend` (1y +20%, 60d max-DD ≤ 8%, above 200-DMA). golden_cross + sector_thrust deferred (lower-priority slow indicators) | 🤖 | 🟡 | ✅ |
| 4.2.2 | Reusable validity-study harness at `tasks/insight_engine/pattern_validity_study.py`. For any detector function, samples 165 historical dates (every 21 trading days), records top-25 fire stocks per date, compares fwd 5/20/60/120d returns to NSE 500 unconditional baseline. Produces ValidityReport with excess-pp + direction-lift per horizon. | 🤖 | 🔴 | ✅ |
| 4.2.3 | Validity studies ran on all 3 patterns; results in `PATTERN_VALIDITY/{multi_year_breakout, pullback_to_50dma, sustained_uptrend}.md`. **multi_year_breakout PASSES** (+1.41pp / +3.5pp at 20d). **pullback_to_50dma FAILS** (-0.28pp at 20d). **sustained_uptrend MARGINAL** (+0.75pp / +4.9pp at 20d). | 🤖 | 🔴 | ✅ |
| 4.2.4 | Promotion per validity findings: multi_year_breakout live with forward-return narrative ("validity-tested ✓" badge), sustained_uptrend live as "names-only · no fwd-return claims" badge, pullback_to_50dma intentionally not surfaced. | 🤖 | 🔴 | ✅ |
| 4.2.5 | Watchlists page renders 7 lists (was 5). Both new ones have validity badges and per-list validity notes. multi_year_breakout reuses the breakout Learn explainer; sustained_uptrend has its own at `/insights/learn/sustained-uptrend`. | 🤖 | 🟡 | ✅ |
| 4.2.6 | Commentary engine integration for "X stocks just broke out of multi-year bases" paragraph | 🤖 | 🟡 | 🔲 deferred — Notes pipeline due for refresh in 5.C |

### 4.3 — Sector subgroup tracker

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.3.1 | Subgroup membership defined in-code in `kite-api/app/insights/subgroups.py` (no YAML — single source of truth, no extra dep). 11 subgroups across 5 parent sectors: private vs PSU banks, large vs mid pharma, auto OEMs vs ancillaries, oil-marketing vs private vs PSU power, large vs mid IT. TATAMOTORS replaced with TMPV post-demerger. | 👤 + 🤖 | 🟡 | ✅ |
| 4.3.2 | `subgroups.py` module — per-subgroup: 5/20/60d RS vs Nifty (equal-weighted mean constituent return minus index return), % above 200-DMA breadth, today_chg_pct, rs_60d_prev_week, rs_60d_wow_delta, members_covered. `get_subgroup_snapshot(asof)` + `get_sibling_spreads(asof)` for the pair-level view. | 🤖 | 🟡 | ✅ |
| 4.3.3 | `test_insights_subgroups.py` — 13 tests covering membership integrity, snapshot shape, JSON serialisation, sibling-spread helper, **2018 NBFC historical-episode check (PSU banks must not outperform private banks on 2018-10-31)**. All passing. | 🤖 | 🟡 | ✅ |
| 4.3.4 | `MarketReading.subgroups` + `MarketReading.sibling_spreads` fields added; API route `GET /api/insights/subgroups?date=...` returns both. `clear_all_caches()` wired. | 🤖 | 🟡 | ✅ |
| 4.3.5 | Sectors page renders a new "Subgroup tracker" section with a sibling-spread leaderboard (sorted by magnitude) and per-parent-sector subgroup tables. Parallel `Promise.all` fetch so the page doesn't double its load time. | 🤖 | 🟢 | ✅ |
| 4.3.6 | Commentary `_indicator_spotlight` cascade now includes a "sibling-subgroup spread" branch — fires when any sibling pair has \|spread\| ≥ 7pp over 60d. Slots in between regime-transition and multi-year-breakout-cluster branches. | 🤖 | 🟡 | ✅ |

### 4.4 — Anniversary / calendar content

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.4.1 | `kite-api/app/insights/calendar_content.py` — `get_on_this_day(date)` returns `dict[horizon_years → AnniversarySnapshot]` for 1/3/5/10 years back, annotated with regime + stress + event_tag. **Built test-first per TDD policy** — tests authored at `tests/test_insights_calendar.py` before any implementation. 10 calendar tests passing. | 🤖 | 🟡 | ✅ |
| 4.4.2 | Curated events file at `data/static/historical_events.csv` — 13 well-documented Indian-market events (Lehman, demonetization, GST, 2019 + 2024 election results, COVID lockdown, vaccine news, Russia/Ukraine, RBI surprise, Hindenburg, multiple budgets). CSV with quoted tags so commas inside descriptors are safe. User-extensible. | 👤 + 🤖 | 🟢 | ✅ |
| 4.4.3 | Seasonality computation — calendar-week historical median/IQR | 🤖 | 🟡 | 🔲 deferred — scope grew past 4.4 hour budget; smaller follow-up |
| 4.4.4 | Pre-event helper for known event days | 🤖 | 🟡 | 🔲 deferred |
| 4.4.5 | API endpoint `GET /api/insights/calendar/on-this-day?date=...` returns anniversaries dict | 🤖 | 🟡 | ✅ |
| 4.4.6 | Commentary integration — `_on_this_day` generator wired into premarket routing. Falls through to `_indicator_spotlight` if no anniversary matches a curated event. End-to-end verified on 2025-03-24: premarket fires "**5 years ago today** (24 Mar 2020): Nationwide COVID-19 lockdown announced... stress at 99/100." | 🤖 | 🟡 | ✅ |
| 4.4.7 | Pulse-page calendar strip | 🤖 | 🟢 | 🔲 deferred to design integration |

### 4.5 — Cross-asset + FII/DII (formerly Phase 0.9-0.11)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 4.5.1 | `scripts/fetch_macro_extras.py` — documented stub with verified source URLs (FRED DEXINUS, DGS10, DCOILBRENTEU; Yahoo gold). No fabricated data committed. End-to-end fetch implementation deferred to a follow-up. | 🤖 | 🟡 | ✅ stub |
| 4.5.2 | `scripts/fetch_fii_dii.py` — NSE FII/DII scraper | 🤖 | 🟡 | 🔲 deferred |
| 4.5.3 | `kite-api/app/insights/cross_asset.py` — general per-asset feature engine (close, z_60d, z_252d, roc_5d/20d/60d, dist_from_200dma, pctile_252d). Asset registry pattern: add a CSV → engine picks it up. India 10y series wired with real data; USDINR/gold/US10y/crude registered but `data_available=False`. **Built test-first per TDD policy.** | 🤖 | 🟡 | ✅ |
| 4.5.4 | `kite-api/app/insights/fii_dii.py` | 🤖 | 🟡 | 🔲 deferred — needs scraped data first |
| 4.5.5 | Tests at `tests/test_insights_cross_asset.py` — 12 spec tests covering feature shape, z-score range, percentile bounds, dist-from-200DMA boundary, ROC arithmetic via fixture, multi-asset snapshot contract (incl. `data_available=False` graceful handling), integration on real India-10y series. Cross-asset validity study (does crude crossing 200-DMA predict Nifty energy?) deferred until crude data is sourced. | 🤖 | 🟡 | ✅ (12 spec tests; validity check deferred) |
| 4.5.6 | Macro widget on Pulse page | 🤖 | 🟢 | 🔲 deferred until ≥3 of the 4 deferred series have real data |
| 4.5.7 | FII/DII flow widget on Pulse page | 🤖 | 🟢 | 🔲 deferred |
| 4.5.8 | Commentary integration — macro paragraph when one of 4 assets makes an unusual move (z > 2) | 🤖 | 🟡 | 🔲 deferred until macro data sourced |

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
| 5.B.1 | Index route at `/insights/learn` — directory grouped by category (Indicators / Patterns / Concepts) plus a featured Glossary card | 🤖 | 🟡 | ✅ (shipped in 5.A; glossary card added) |
| 5.B.2 | Glossary content — `src/content/insights/learn/glossary/_data.ts` with 38 entries across 6 buckets (market-state, breadth-momentum, patterns, math, flows-structure, general). Each entry has term + anchor + plain-English definition + optional deep-dive link. | 👤 + 🤖 | 🟢 | ✅ |
| 5.B.3 | Glossary page at `/insights/learn/glossary` — bucket-anchored sections, per-term anchors for deep-linking | 🤖 | 🟢 | ✅ |
| 5.B.4 | Indicator deep-dives — added "Historical context" and "Common misreadings" sections to all 9 indicator/concept explainers (stress-score, regime, sector-rs, sector-breadth, mcclellan, pct-above-200dma, dispersion, vix, drawdown, concentration). Specific historical episodes referenced are qualitative (dated events, not invented numbers). Server-rendered historical charts deferred (chart_renderer primitives exist; integration is its own work). | 🤖 + 👤 | 🟡 | ✅ (text); 🔲 (charts deferred) |
| 5.B.5 | Pattern guides — added "How we detect it" (quoting the actual watchlists.py code rule) and "When it fails" sections to breakout, coiled-spring, rs-leader. Validity-study sidebars wait for Phase 4.2 work. | 🤖 + 👤 | 🟡 | ✅ |
| 5.B.6 | "Learn" tab in layout nav | 🤖 | 🟢 | ✅ (shipped in 5.A) |
| 5.B.7 | SEO: Article schema structured data on each deep-dive | 🤖 | 🟡 | 🔲 deferred — design integration phase |

### 5.C — Teach-while-broadcasting (Daily Note enhancements)

| # | Task | Owner | Risk | Done |
|---|---|---|---|---|
| 5.C.1 | `learn_moment: str` field added to `Commentary` dataclass | 🤖 | 🟡 | ✅ |
| 5.C.2 | Two generators built: `_indicator_spotlight` (fires on stress extremes, concentration extremes, VIX z-score extremes, regime transitions, multi-year breakout clusters) + `_pattern_of_the_week` (ISO-week rotation across 6 patterns from our Learn corpus). `_on_this_day` deferred to Phase 4.4 since it depends on the historical-events calendar engine. | 🤖 | 🟡 | ✅ (2 of 3 generators) |
| 5.C.3 | Templates wired: postclose + premarket get `*Indicator spotlight*` section when learn_moment fires; weekly digest always gets `*Pattern of the week*`. `compose()` signature now takes `mode` so the right generator runs. `note_assembler.assemble` passes the mode through. | 🤖 | 🟡 | ✅ |
| 5.C.4 | Tests added — pattern-of-the-week rotates across ISO weeks; jargon check applied to learn_moment text across 4 historical regime days × 3 modes; COVID-day asserts stress/panic spotlight fires; weekly always carries pattern-of-the-week; default mode is postclose. Editorial-voice fixture now includes learn_moment. 73 tests passing. | 🤖 | 🟡 | ✅ |

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
2. ~~**4.1** (concentration / Reliance impact)~~ ✅ shipped 2026-05-28
3. ~~**5.B** (Learn hub)~~ ✅ shipped 2026-05-28
4. ~~**4.2** (pattern watchlists with validity checks)~~ ✅ shipped 2026-05-28 — 1 passed, 1 marginal, 1 failed; UI reflects findings honestly
5. ~~**5.C** (teach-while-broadcasting)~~ ✅ shipped 2026-05-28 — Daily Notes now teach one micro-moment each
6. ~~**4.3** (sector subgroups)~~ ✅ shipped 2026-05-28
7. ~~**4.4** (calendar / anniversaries)~~ ✅ shipped 2026-05-28 — also unblocked the deferred `on_this_day` learn-moment in 5.C
8. ~~**4.5** (cross-asset engine)~~ ✅ shipped 2026-05-28 — engine + India 10y series live; rest of 4.5 (FII/DII engine, real data fetching for USDINR/gold/US10y/crude, Pulse widgets, commentary macro paragraph) deferred until real data is sourced — see fetch stub at `scripts/fetch_macro_extras.py` for URLs.
7. **5.D** (validity protocol document) — formalise the rule that's now embedded in the 4.2 harness. ~30 min of writing.
8. **Phase 3** (automation) — defer until design-engine integrates; manual broadcast workflow handles current scale.

## Actual development pace — calibration note

Original estimates assumed solo human-led development. Actual pace with
agentic execution + human review/steering has been much faster:

| Phase | Original estimate | Actual |
|---|---|---|
| Phase 0 (data engines, 12 modules, 119 tests) | 10-14 working days | ~1 day across two sessions |
| Phase 1 (Daily Note + 72 tests) | 8-10 days | ~half a day |
| Phase 2 (web dashboard + 32 API tests) | 12-15 days | ~half a day |
| Phase 4.1 (concentration widget) | 1-2 days | ~1 hour |
| Phase 5.A (12 inline explainers + wiring) | — | ~1 hour |
| Phase 5.B (glossary + deep-dives + pattern guides) | — | ~30 min |

**Estimates below are in working hours, not days.** Add roughly 30-50%
buffer for review, design polish, and any data-fetching that hits rate
limits or auth issues.

Total remaining (Phase 4.2-4.5 + 5.C-D): **~5-8 hours of focused work**,
spread across whatever cadence you want to run sessions at. Day-scale
work items are now Phase 3 (automation needs WhatsApp Business API
setup, which is people-time, not coding-time) and any open-ended
content authoring you'd rather drive yourself.
