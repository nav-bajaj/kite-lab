# Marketworks Insight Engine — quant-driven market intelligence + learning platform

## Context

Marketworks currently sells four long-only momentum portfolios via marketworks.in. The nifty-trader exploration confirmed that *directional* alpha extraction on Nifty 50 at retail latency is hard. But the same data pipeline (NSE 500 daily panel, 141 indices, India VIX, sector indices — all 16+ years deep) is **exactly what's needed to build market-intelligence content**, a separate product surface from portfolios.

The opportunity: Indian retail platforms (Zerodha, Groww, Smallcase, MoneyControl, ETMoney) show prices and basic technicals but offer almost no quantitative breadth/regime context. Bloomberg has institutional content at institutional prices. **There's clear white space at the retail tier** for analytical depth at retail price.

## Strategic re-orientation (2026-05-28)

After Phase 0-2 shipped and the analog feature was retired (see `ANALOG_STUDY.md` for the validity failure that drove this), we reframed the product's intent. The four things subscribers actually want from this surface, in order of importance:

1. **Gauge the state of the market** — single-glance "where are we right now?" context
2. **Discover interesting names** — what's quietly happening that they wouldn't see on price-only platforms
3. **Recognise interesting patterns** — technical setups they can apply to their own thinking
4. **Build market knowledge** — they walk away understanding more than they did before reading

**Knowledge-building (4) is the leg most subscribers undervalue and competitors don't address — and the one we're best positioned to own.** Every observation we publish should teach as well as inform: "what is this indicator, why does it matter, how do you read it, what's the historical context." Done well, this turns the dashboard into a daily-habit destination, not a one-shot data screen.

Two design rules tightened by the analog study:

- **Show observation, not prediction.** "Stock X broke out of a 200-day base" is observation — true, useful, no claim about tomorrow. "Stocks in this setup gained 4% next month" is prediction — and unless that 4% beats the unconditional baseline by ~3pp+ it's drift dressed as insight. New features go through a validity check before any forward-return framing is published.
- **Educate the underlying mechanic, not just the output.** When we surface "stress is elevated", we link to a short explainer of what stress means, what its components are, and how readers should think about it. Teaches the indicator AND builds trust in the platform.

## Strategic pillars (locked)

| # | Pillar | Status | Where it lives |
|---|---|---|---|
| 1 | **State-of-market** — regime / stress / sector leaderboard | ✅ shipped | Pulse + Sectors pages, all notes |
| 2 | **Interesting names** — quant-driven watchlists | ✅ shipped (5 lists) | Watchlists page, Watch section of notes |
| 3 | **Interesting patterns** — pattern-detection watchlists with validity checks | 🟡 partial (coiled springs only) | Phase 4 — expansion |
| 4 | **Market knowledge** — educational explainers + glossary + case studies | 🔲 not started | Phase 5 — NEW (highest priority) |
| 5 | **Structural observations** — concentration, subgroup spreads, FII/DII | 🔲 not started | Phase 4 — expansion |
| 6 | **Anniversary / calendar** content — "X years ago today", event seasonality | 🔲 not started | Phase 4 — expansion |

User decisions locked from earlier discussion (unchanged):

| Choice | Locked value |
|---|---|
| Primary goal | Acquisition funnel — free content drives portfolio conversions |
| Killer hook | **Daily Quant Note** auto-broadcast on WhatsApp |
| Primary channel | WhatsApp (highest Indian penetration / open rates) |
| Surface | New "Insights" tab in existing kite-dashboard app — **gated behind Clerk login** (free tier visible to all signed-in users; no paid-sub gate) |
| Content cadence | Pre-market (8:30) + post-close (4:15) Mon-Fri + Sunday weekly digest |
| Editorial voice | **Plain-English, broadly accessible, lightly actionable, EXPLICITLY teaching where natural** — see editorial section below |
| Update cadence on web | Intraday (15-30 min) during market hours |
| Cross-asset data | Add: USDINR, gold, US 10y, crude (deferred — Phase 4) |
| Flow data | Add: FII/DII daily flows (deferred — Phase 4) |
| Sectoral analysis | **Constituent-level**, not just sector-index level — already shipped |
| Branch | **insight-engine** (renamed from `nifty-trader`) |

**Retired (with study trail):** the original Phase 0 vision of an analog finder with forward-return projections — failed its validity check (IC ≈ +0.04 at 20d, direction lift NEGATIVE at 20d/60d). See `ANALOG_STUDY.md`. The KNN match module survives as a research artifact but is not consumed anywhere user-facing.

## Knowledge-first roadmap (Phase 4 + 5 — locked direction 2026-05-28)

The largest near-term build is a **learning layer**, not more data. Phase 0-2 already give us deep state-of-market content; what's missing is the connective tissue that turns those data points into things subscribers UNDERSTAND, not just consume. Three product surfaces will carry it:

### A. Inline explainers (Phase 5.A)

Every indicator the dashboard mentions gets a short, plain-English "what / why / how to read it" panel reachable from the indicator itself. Examples:

- **Stress score** → "What is the stress score? It blends VIX percentile (35%), drawdown depth (25%), how many stocks are below their 200-day average (20%), and cross-sectional dispersion (20%) into a 0-100 reading. Below 30 = calm. 60-80 = elevated stress. 80+ = panic/capitulation, historically the strongest forward-return zone in our data."
- **Sector RS** → "Relative strength compares a sector's 3-month return against Nifty's. Positive RS means the sector beat Nifty. Sustained RS leadership often precedes broader rally participation. Falling rank is sometimes more informative than absolute leadership."
- **Coiled spring** → "Stocks in tight trading ranges (volatility in own bottom 25%) above their 50- and 200-DMAs. Historically the setup that precedes either a continuation breakout or a fast failure — high signal-to-noise direction is determined by the broader regime."

These are author-once-reuse-everywhere. We'll write them as Markdown files under `kite-dashboard/src/content/insights/learn/` and the dashboard renders them via a `/insights/learn/<topic>` route. Each Pulse / Sectors / Watchlists page gets contextual deep-links ("What's this?" / "How is this computed?").

### B. Standalone Learn section (Phase 5.B)

A dedicated `/insights/learn` hub with three content types:

- **Glossary** — alphabetical, 1-paragraph definitions of every term used elsewhere (FII, DII, VIX, RS, breadth, regime, dispersion, basis, percentile, drawdown, etc.). 30-50 entries.
- **Indicator deep-dives** — longer pieces (5-10 minute reads) for the marquee indicators. Each includes:
  - What it measures (plain-English)
  - How we compute it (transparent methodology)
  - Historical chart showing how it has behaved over 16 years
  - "What does this look like at extremes?" — real historical episodes with dates
  - "How readers should think about it" — uses, limits, common misreadings
- **Pattern guides** — one piece per technical pattern (breakouts, golden cross, coiled springs, pullback to 50-DMA, multi-year breakouts). Each includes:
  - Definition + visual diagram
  - How we detect it (so subscribers can replicate the screen on their own data)
  - Validity-study sidebar — what does the historical hit-rate actually look like? does this beat baseline? (lessons from the analog study apply: be honest about edge or absence thereof)

### C. Teach-while-broadcasting (Phase 5.C)

Modify the Daily Quant Note + weekly digest so each one **embeds one small learning moment**. Three formats rotated:

- *"Indicator spotlight"* — when an indicator does something unusual today, one sentence explaining what it means: "Stress jumped from 42 to 58 today — a 16-point single-day move is the largest since [date]. Big single-day stress jumps historically resolve within 5-15 days as either a clear breakdown or a reversal."
- *"Pattern of the week"* — Sunday digest names one pattern from the watchlists and explains it in 2-3 sentences. Rotates through breakouts / coiled springs / pullback-to-50-DMA / etc.
- *"On this day"* — calendar anchor (Phase 4): "5 years ago today, India VIX was at 75 (COVID lockdown announcement). Today's stress reading of 58 is the 89th percentile of the last 5 years but is nowhere near that level."

## Pattern + structural expansion (Phase 4 — locked direction 2026-05-28)

Five concrete additions in priority order:

### 1. Concentration / Reliance impact widget (Phase 4.1)
Surfaces what % of any given day's Nifty 50 move came from the top 3/top 5 stocks, and what RIL contributed alone. Used in the Pulse page header and in the commentary engine. Turns "Nifty +0.4%" into "Nifty +0.4%, but 72% of the move was RIL + HDFC Bank — a narrow tape."

### 2. Pattern-based watchlists (Phase 4.2)
New entries alongside the existing 5 lists. Each pattern goes through a validity study (per the analog lesson) BEFORE its forward-return content is published — if it doesn't beat the unconditional baseline meaningfully, we publish the names but not the predictions.

- Multi-year breakout (close above 5-year high)
- Pullback to 50-DMA in established uptrend
- Golden cross / death cross (50-DMA crossing 200-DMA)
- Higher-highs-and-higher-lows over 60 days
- 52-week-high cluster days (sector-level "thrust" signal)

### 3. Sector subgroup tracker (Phase 4.3)
Public-sector vs private-sector banks. Large-cap vs mid-cap pharma. Auto-OEMs vs auto-ancillaries. The default sector index hides these splits; they're often where the actual story lives. Each subgroup gets RS + breadth tracked like a sector.

### 4. Anniversary / calendar content (Phase 4.4)
- "X years ago today" generator using historical regime + stress at that date
- Pre-event-day commentary (RBI, budget, earnings clusters) with historical move statistics
- Seasonality patterns (e.g., "Median December performance: +X% over 16 years")

### 5. Cross-asset + FII/DII data layer (Phase 4.5)
Was originally Phase 0 task 0.9-0.11. USDINR, gold, US 10y, crude as macro context. FII/DII daily flows from NSE T-1 report. Once landed, enables a "macro" widget on the Pulse page and adds richer commentary on cross-asset moves.

## Editorial voice — plain English, lightly actionable

The audience is broader Indian retail — not quants, not full-time traders, not necessarily Marketworks subscribers. Most readers won't know what "cross-sectional dispersion z-score" means. Jargon kills shareability and makes the content feel inaccessible. But pure feel-good summaries feel spammy and don't justify the analytical work behind them.

**The target balance:** every note should read like a smart friend who watches markets carefully explaining today in a few short bullets. Specific enough to be useful, simple enough that anyone can follow.

**Translation rules** — every quantitative reading gets surfaced as plain English with one concrete takeaway:

| Quant input | ❌ Bad (jargony) | ✓ Good (plain + light action) |
|---|---|---|
| `pct_above_200dma = 0.64` | "Cross-sectional 200-DMA breadth at 64%" | "About 2 in 3 NSE 500 stocks are trading above their long-term trend — a healthy sign of broad participation." |
| `vix_zscore_252d = +1.8` | "VIX in the 96th percentile of trailing 252d" | "Volatility is unusually elevated — markets are nervous. In similar past episodes, the next few weeks have often seen sharp moves either way; size positions accordingly." |
| `regime = Trend-Bull, week 4` | "Regime classifier output: Trend-Bull, persistence 19d" | "Markets remain in 'trend mode' — uptrend is intact and broad. Historically these phases last around 12 weeks; we're roughly a third in." |
| `sector_rs: Banks +3 places` | "Banks Δ-rank +3 in 6m RS" | "Banks have quietly become the strongest sector this week, jumping into the top 2. Worth watching if you hold financial names." |

**Editorial guidelines built into templates:**

- **Lead each note with a one-line plain-English headline** (e.g., "Markets are calm but a few sectors are quietly rotating") — must be understandable without any chart
- **No jargon without translation** — if we have to use a term (e.g., "breadth"), define it inline once: "breadth (how many stocks are moving together)"
- **No percentile speak in body text** — say "the highest in 6 months" instead of "92nd percentile of 252d window"
- **One concrete takeaway per section** — typically a "what to watch" or "what this means for you" line at the end. Never a recommendation; always an observation or a thing to keep an eye on.
- **Specificity over abstraction** — name actual stocks/sectors, not "various names." If 17 stocks hit 52w highs, list 3-5 by name.
- **Show, don't tell** — historical comparisons ground the claim ("last time this happened was X; here's what followed"). Without that backing, claims feel like opinion.
- **Disclaimer footer on every note** — "Educational content; not investment advice. Past performance is not indicative of future results."
- **Charts must work at WhatsApp thumbnail size** — no more than 2-3 series per chart, big labels, no axis clutter.

**Tone calibration:** somewhere between Zerodha Pulse (clear but light on analysis) and Capital Mind (analytical but accessible). Avoid Bloomberg-style density; avoid clickbait-style hyperbole.

## Sector intelligence — constituent-level, not just sector-index level

The default approach is to use NIFTY sector indices (NIFTY BANK, NIFTY IT, NIFTY PHARMA, etc.) as composite series. But a sector index hides what's actually going on inside the sector — when NIFTY BANK is up 1% it could be all 12 banks up 0.8-1.2% (broad strength) or 2 mega-caps up 3% while 10 mid/small banks are flat (narrow rally).

**To unlock the next layer of insight, the engine pulls current sector constituents and computes breadth metrics WITHIN each sector.** For each sector:

- **Constituent count and current membership** (refreshed periodically from NSE)
- **Sector breadth:** % of sector constituents above 50/200-DMA
- **Internal dispersion:** stdev of constituent daily returns within the sector
- **Top/bottom 3 by 6m relative strength** within the sector
- **Sector "thrust" days:** when >80% of sector constituents moved together
- **Crowding inside the sector:** are gains concentrated in 1-2 names or broadly shared

This gives much richer content: instead of "Banks are leading", we can say "Banks are leading, but it's mostly HDFCBANK and ICICIBANK doing the work — only 4 of the 12 sector constituents are outperforming Nifty over 3 months." That's a meaningfully different (and more honest) read.

**Source:** NSE publishes constituent lists for each sector index (downloadable CSV from `archives.nseindia.com/content/indices/`). We snapshot these monthly and store dated CSVs (`data/static/sector_constituents/NIFTY_BANK_2026-05.csv` etc). A small script (`scripts/fetch_sector_constituents.py`) refreshes them.

**Sector universe to cover (Phase 0):**
- NIFTY BANK, NIFTY FIN SERVICE
- NIFTY IT
- NIFTY PHARMA
- NIFTY FMCG
- NIFTY AUTO
- NIFTY METAL
- NIFTY REALTY
- NIFTY ENERGY
- NIFTY MEDIA
- NIFTY CONSUMER DURABLES
- NIFTY CONSUMPTION (broader)

Each sector typically has 10-15 constituent stocks, all of which are in our NSE 500 panel, so price data is already in hand.

## Branch rename: `nifty-trader` → `insight-engine`

The branch was created for the directional strategy exploration; that line of work is closed. The new product is fundamentally different — a content/intelligence engine, not a trading strategy. **First execution step is to rename the branch** (`git branch -m nifty-trader insight-engine` locally + force-push + delete old remote branch). All work from here happens on `insight-engine`. Any final commits left on `nifty-trader` from the prior exploration are already pushed and can stay there (the branch history is intact, only the name changes).

## Architecture overview

```
┌────────────────────────────────────────────────────────────┐
│  Phase 0: data engines (mostly Python in kite-api)         │
│  - breadth_signals (reuse existing)                        │
│  - macro_signals + cross_asset_signals (extend existing)   │
│  - sector_rs_engine (new)                                  │
│  - regime_classifier (new)                                 │
│  - stress_composite (new)                                  │
│  - analog_finder (new)                                     │
│  - conditional_distribution (new)                          │
│  - watchlist_generator (new)                               │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│  Phase 1: content generator (kite-api/app/insights/)        │
│  - daily_quant_note generator (templated)                  │
│  - 3 templates: premarket / postclose / weekly             │
│  - chart_image_renderer (matplotlib → branded PNG)         │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│  Phase 2: web dashboard (kite-dashboard/src/app/insights/)  │
│  - Pulse page · Sectors page · Analogs page · Watchlists   │
│  - Archive of past Notes (SEO surface)                     │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│  Phase 3: distribution (WhatsApp + Email + Alerts)         │
│  - WhatsApp Business API integration                       │
│  - Scheduled cron: pre/post-close/Sunday digest            │
│  - Event-triggered intraday alerts                         │
│  - Email digest (weekly long-form)                         │
│  - Signup forms across channels                            │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│  Phase 4: expansion content (open-ended)                   │
│  - Pre-event content (RBI, earnings, budget)               │
│  - Concentration / crowding indicators                     │
│  - Calendar / anniversary series                           │
│  - Personalised subscriber content                         │
└────────────────────────────────────────────────────────────┘
```

## Phase 0 — Foundations (data engines)

**Deliverable:** every signal needed by the Daily Quant Note is computable from a single Python entry point that returns a `MarketReading` object containing every metric needed for the day.

**New modules to build (location: `kite-api/app/insights/`):**

| Module | Reuses | Builds |
|---|---|---|
| `breadth.py` | `tasks/nifty_trader/breadth_signals.py` ✓ | promote to kite-api, add caching |
| `macro.py` | `tasks/nifty_trader/macro_signals.py` ✓ | promote to kite-api |
| `cross_asset.py` | – | new: USDINR, gold (MCX + intl), US 10y (FRED), crude. Initially daily-EOD; phase-3 intraday |
| `fii_dii.py` | – | new: ingest NSE daily FII/DII activity reports (T-1) |
| `sector_constituents.py` | – | new: maintains current sector → constituent stocks mapping (sourced from NSE; snapshot dated monthly under `data/static/sector_constituents/`) |
| `sector_breadth.py` | – | new: for each sector, compute breadth ON its constituents (not just sector index) — % above 50/200-DMA, internal dispersion, sector "thrust" days, top/bottom 3 by RS within the sector |
| `sector_rs.py` | – | new: rank ~12 NIFTY sector indices over 5/20/60/120/252-day windows, track week-over-week movement (uses sector index series for the rank; uses constituent breadth for the "is this rally broad or narrow" overlay) |
| `regime.py` | partial (`scripts/combo_defensive.py` regime gate) | new: 4-state classifier (Trend-Bull / Drift / Stretched / Stress) with persistence tracking |
| `stress.py` | – | new: 0-100 composite score from VIX percentile + drawdown depth + %200-DMA + dispersion z |
| `analog_finder.py` | – | new: KNN over multi-factor reading vs 16y history, returns top-5 most-similar dates with their forward returns |
| `conditional_dist.py` | – | new: given current regime/stress bucket, return historical forward-return distribution (mean/median/IQR/5-95) over 5/10/20/60d |
| `watchlists.py` | – | new: breakouts (close > 20d high), RS leaders (top 25 by 6m RS vs Nifty), coiled springs (low realised vol + above 50DMA + near 200DMA), stretched (>20% above 200DMA), recent breakdowns |
| `reading.py` | – | new: orchestrator — returns one `MarketReading` per day combining all of the above |

**Data sources to add (Phase 0):**
- USDINR: RBI reference rate or FRED (free)
- Gold: MCX (we have a sparse file; need to backfill via Yahoo or Investing.com)
- US 10y yield: FRED (free, daily series `DGS10`)
- Crude: FRED `DCOILBRENTEU` (free)
- FII/DII: scrape from NSE daily report URL (T-1 cadence)
- **Sector constituents:** NSE publishes downloadable CSVs per sector index (e.g., NIFTY BANK constituents at `archives.nseindia.com/content/indices/ind_niftybanklist.csv`); fetch and store dated snapshots monthly

Two small data ingestion scripts:
- `scripts/fetch_macro_extras.py` — refreshes USDINR, gold, US 10y, crude, FII/DII daily
- `scripts/fetch_sector_constituents.py` — refreshes sector membership lists monthly; writes dated snapshots to `data/static/sector_constituents/`

**Verification of Phase 0:**
- `python -m kite_api.insights.reading` prints today's `MarketReading` with all fields populated
- Spot-check analog finder: pass historical date 2018-04-15, verify it recognizes its own neighbors
- Conditional distribution sanity: histograms of forward returns in each regime should look distinct

**Phase 0 estimated effort:** ✅ already shipped — actual: ~1 day across two sessions. Original estimate of 8-12 days was 10× over.

## Phase 1 — Daily Quant Note (content generation + manual broadcast)

**Deliverable:** an admin clicks a button (or runs `python scripts/generate_quant_note.py [premarket|postclose|weekly]`), gets a PNG + a text blurb, manually broadcasts to a WhatsApp list. Three notes per market week + Sunday digest.

**New modules (`kite-api/app/insights/notes/`):**

| Module | Builds |
|---|---|
| `templates/premarket.py` | template: yesterday's regime + Asian/US overnight + 1 chart + today's calendar |
| `templates/postclose.py` | template: today's regime delta + key internals changes + 1 chart + watch tomorrow |
| `templates/weekly.py` | template: week recap + sector rotation map + analog of the week + Sunday outlook |
| `chart_renderer.py` | matplotlib-based image generator with Marketworks branding; outputs 1080x1350 PNG (Instagram/WhatsApp portrait) |
| `commentary.py` | given a `MarketReading`, produces **plain-English** narrative paragraphs following the Editorial voice guidelines (see top of plan). Every quant input gets translated into accessible language with one concrete takeaway. E.g., "Most NSE 500 stocks (about 2 in 3) are above their long-term trend — broad strength. The last time we saw similar conditions was October 2023; markets gained 5% over the next month from that setup." |
| `note_assembler.py` | combines text + chart into a delivery package (WhatsApp-ready text + image URL) |

**Editorial guidelines built into templates:**
- No "buy / sell / recommend" verbs
- All claims framed as historical observation
- Every number annotated with its historical context
- Disclaimer footer on every note
- Charts must be readable at WhatsApp thumbnail size (mobile first)

**One-script daily workflow:**
```
$ python scripts/generate_quant_note.py postclose
  → reading computed at 4:00 PM close
  → note.png written to runs/daily/2026-05-26_postclose.png
  → note.txt written alongside
  → preview opens in browser for admin review
  → admin copies image + text, broadcasts via WhatsApp Web
```

**Verification of Phase 1:**
- Generate 5 days of historical notes (e.g., for last week) and verify they read coherently
- Run notes for several distinct regime days (COVID, calm, post-election) and confirm the templates produce sensible output
- Check chart legibility at WhatsApp-share resolution (375px wide)

**Phase 1 estimated effort:** ✅ already shipped — actual: ~half a day.

## Phase 2 — Web dashboard

**Deliverable:** a new `/insights` route on the existing kite-dashboard app, publicly accessible, with four pages + an archive of past Notes.

**New Next.js routes (`kite-dashboard/src/app/insights/`):**

| Route | Page |
|---|---|
| `/insights` | Pulse — regime/stress/tilt gauges + key internals timeseries |
| `/insights/sectors` | Sector RS heatmap + sector breadth + sector dispersion |
| `/insights/analogs` | Interactive analog finder: pick a date, see top-5 historical matches + their forward paths |
| `/insights/watchlists` | All quant-driven lists with sorting/filtering |
| `/insights/notes` | Archive of past Daily Quant Notes (SEO + repeated-visitor surface) |
| `/insights/notes/[date]` | Individual note page (SEO-friendly URL) |

**Backend (`kite-api/app/api/insights.py`):** read-only public endpoints serving the day's `MarketReading`, sector RS tables, watchlists, analog candidates, conditional distribution snapshots, archive.

**Acquisition funnel:** every page has a sidebar/footer CTA — "See our portfolios →" linking to `/portfolios`. The /insights pages are SEO-optimised with structured data so they get indexed (this is what makes the funnel work as a free acquisition channel long-term).

**Verification of Phase 2:**
- All four pages load and render with real Phase 0 data
- Public access (no auth required for /insights/*) verified
- Lighthouse: mobile + SEO scores > 90
- Each Daily Quant Note has a stable URL (e.g., `marketworks.in/insights/notes/2026-05-26`)

**Phase 2 estimated effort:** ✅ already shipped (structure-only) — actual: ~half a day. Visual design polish + Notes archive deferred to design integration phase.

## Phase 3 — Automation + multi-channel distribution

**Deliverable:** Notes go out automatically without manual broadcast. Event-triggered alerts fire intraday.

| Component | Builds |
|---|---|
| WhatsApp Business API | integrate via Meta Cloud API (Tier 1: 1k contacts free); broadcast list manager; templated message sender |
| Subscriber signup | `/insights/subscribe` form → captures phone + email + channel preferences; stored in Postgres |
| Scheduling | cron-based: 8:30 (premarket), 4:15 (postclose), Sun 8 PM (weekly); Railway scheduled jobs |
| Email service | SendGrid/Mailgun integration; weekly long-form email digest (different from WhatsApp; different audience) |
| Event-trigger watcher | polls intraday market state every 15 min during market hours; fires alerts when thresholds cross (VIX spike, breadth thrust, sector regime change, 52w-high cluster, analog match strong); rate-limited to ≤3 alerts/day |
| Funnel CTAs | every WhatsApp/email broadcast ends with portfolio CTA + tracked short-link |

**Verification of Phase 3:**
- WhatsApp test broadcast to a 5-person list succeeds end-to-end
- Cron jobs fire on schedule for a full week without manual intervention
- Event-trigger detects a known historical signal correctly on simulated playback
- Click-through tracking captures conversion funnel

**Phase 3 estimated effort:** Code-time ~half a day; calendar-time bottlenecked by WhatsApp Business API approval (Meta) and SendGrid/Mailgun setup. Not worth scheduling until 4.x is wrapped and the design integration lands.

## Phase 4 — Expansion (open-ended, post-launch)

Listed for completeness; not part of initial scope.

- Pre-event content (RBI / earnings / budget calendar)
- Concentration & crowding indicators
- Calendar / anniversary content series
- Personalized subscriber content ("how your portfolios are positioned for current regime")
- Earnings reaction tracker (needs earnings calendar feed)
- F&O OI flow proxy (NSE bhavcopy ingestion)
- "Indicator of the month" educational long-form

## Critical files to be modified or created

**New (kite-api):**
- `kite-api/app/insights/breadth.py`
- `kite-api/app/insights/macro.py`
- `kite-api/app/insights/cross_asset.py`
- `kite-api/app/insights/fii_dii.py`
- `kite-api/app/insights/sector_constituents.py`
- `kite-api/app/insights/sector_breadth.py`
- `kite-api/app/insights/sector_rs.py`
- `kite-api/app/insights/regime.py`
- `kite-api/app/insights/stress.py`
- `kite-api/app/insights/analog_finder.py`
- `kite-api/app/insights/conditional_dist.py`
- `kite-api/app/insights/watchlists.py`
- `kite-api/app/insights/reading.py`
- `kite-api/app/insights/notes/templates/{premarket,postclose,weekly}.py`
- `kite-api/app/insights/notes/{chart_renderer,commentary,note_assembler}.py`
- `kite-api/app/api/insights.py` (public read-only routes)
- `kite-api/app/services/whatsapp_service.py` (Phase 3)
- `kite-api/app/services/insights_scheduler.py` (Phase 3)
- `scripts/generate_quant_note.py` (CLI for Phase 1 manual workflow)
- `scripts/fetch_macro_extras.py` (cross-asset + FII/DII ingestion)
- `scripts/fetch_sector_constituents.py` (monthly sector membership refresh)
- `data/static/sector_constituents/` (dated CSV snapshots per sector)

**New (kite-dashboard):**
- `kite-dashboard/src/app/insights/page.tsx`
- `kite-dashboard/src/app/insights/sectors/page.tsx`
- `kite-dashboard/src/app/insights/analogs/page.tsx`
- `kite-dashboard/src/app/insights/watchlists/page.tsx`
- `kite-dashboard/src/app/insights/notes/page.tsx`
- `kite-dashboard/src/app/insights/notes/[date]/page.tsx`
- `kite-dashboard/src/app/insights/subscribe/page.tsx`

**Reuses (existing):**
- `tasks/nifty_trader/breadth_signals.py` → promote to `kite-api/app/insights/breadth.py`
- `tasks/nifty_trader/macro_signals.py` → promote to `kite-api/app/insights/macro.py`
- NSE 500 daily panel at `nse500_data_merged/` (16y, split-adjusted)
- Indices at `/Users/navdeep/Documents/stock_data/indices_data_full/` (141 indices)
- NIFTY 100 regime infra from `scripts/combo_defensive.py` (`LOCKED` config) — reuse the 100-DMA + 3-day confirm gate for the regime classifier

## Out of scope (deferred)

| Item | Why deferred |
|---|---|
| Live deployment / production go-live | Phased per phases above |
| SEBI Registered Investment Advisor (RIA) license | Required only if voice moves to opinionated recommendations (currently locked to neutral framing) |
| Multi-language content (Hindi notes) | Phase 5+ once English version validates |
| Custom mobile app | Web + WhatsApp covers Phase 0-3 entirely |
| Per-stock fundamental data | Out of scope; we're a quantitative dashboard |
| Real-time tick data | Phase 3 intraday is 15-min cadence; tick-level not required |

## Verification — end-to-end testing for the full product

Once Phase 0-3 are complete:

1. **Data integrity:** spot-check 10 random historical dates that each indicator produces sensible output (e.g., March 2020 stress should be ≥ 90th percentile; January 2017 should be Trend-Bull regime).
2. **Content quality:** generate notes for 5 specific historical days (COVID crash, demonetization, 2017 melt-up, 2018 NBFC, post-2022 rate shock). Each note should read like a thoughtful market analyst — neutral, data-grounded.
3. **Full pipeline test:** trigger pre-market note manually → confirm WhatsApp delivery → click web link → confirm Pulse page loads with same data → confirm CTA to portfolios works.
4. **Event-alert test:** simulate a VIX spike condition; confirm event-trigger fires within 15 min; confirm WhatsApp delivery.
5. **Funnel measurement:** for 4 weeks post-launch, instrument: WhatsApp send → click rate → web visit duration → portfolio CTA click → portfolio signup. Target ≥3% end-to-end conversion.
6. **Editorial review:** at least the first 2 weeks of generated notes are reviewed manually before broadcast to catch tone/accuracy issues; iterate templates as needed.

## Open questions to revisit during execution

- WhatsApp Business API approval timeline — may delay Phase 3; if it slows down, extend Phase 1 manual broadcast as a bridge
- Whether to gate any content behind subscription (current plan: nothing gated; revisit if engagement is low)
- Voice/branding consistency: who reviews notes for tone (currently the user; may need a content lead long-term)
- Pricing tier: this is currently free; revisit if engagement is high enough to support a premium tier

## Timeline (revised 2026-05-28)

The original estimates assumed solo human-led development. Actual pace
with agentic execution + human steering has been much faster than those
assumptions. As of this revision, Phases 0-2 and 4.1 + 5.A + 5.B are
already shipped on `insight-engine`. Remaining estimates below are in
working **hours**, not days.

| Phase | Original estimate | Actual / remaining |
|---|---|---|
| 0 — Data engines (12 modules, 119 tests) | 10-14 days | ✅ ~1 day actual |
| 1 — Daily Note + manual broadcast (72 tests) | 8-10 days | ✅ ~half a day actual |
| 2 — Web dashboard (4 pages + API, 32 tests) | 12-15 days | ✅ ~half a day actual |
| 4.1 — Concentration widget | — | ✅ ~1 hour |
| 5.A + 5.B — Knowledge layer (13 explainers + glossary + deep-dives) | — | ✅ ~2 hours combined |
| 4.2 — Pattern watchlists + validity studies | 2-3 hours |
| 4.3 — Sector subgroup tracker | 1 hour |
| 4.4 — Anniversary / calendar | 1-2 hours |
| 4.5 — Cross-asset + FII/DII | 2-3 hours (data fetching is the heavy bit) |
| 5.C — Teach-while-broadcasting | ~1 hour |
| 5.D — Validity protocol doc + harness refactor | 30-60 min |
| 3 — Automation (WhatsApp / cron / alerts) | 1-2 days of *people-time* (Meta API approval is the bottleneck, not coding) |

**Phase 4+5 remainder: ~7-11 focused hours.** That can land in 2-3
sessions. Phase 3 timeline depends entirely on Meta Cloud API approval
turn-around, which is outside our control.

## Execution order — first steps once plan mode exits

1. **Rename branch** `nifty-trader` → `insight-engine` and force-push; delete old remote branch
2. **Stand up task folder** `tasks/insight_engine/` with PLAN.md (copy of this file), TASKS.md (Phase 0 task list), _meta.yml
3. **Begin Phase 0** — start with sector_constituents (depends on external data) + breadth/macro promotion (mechanical), then build sector_breadth on top; analog and conditional engines come later in Phase 0
