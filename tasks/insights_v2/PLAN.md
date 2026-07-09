# Insights v2 — admin launch + stock-level analytics expansion

Planned by Fable 5 (2026-07-09); execution delegated to Opus 4.8 agents.
Branch: `insights-v2`. Builds on `tasks/insight_engine/` (see its PLAN /
RESULTS / TASKS for the full v1 history).

## Why this work

The insight engine (v1) is fully built and merged to `main`
(`7f4f797`, later branded by design_system) — 324 tests, 13 data-engine
modules, a Daily Quant Note generator, 4 dashboard pages, a 14-explainer
Learn hub, and a validity-governance protocol. But **nobody can see it**:
`/insights` is gated off in production behind
`NEXT_PUBLIC_INSIGHTS_ENABLED` because the engine reads CSV panels that
were never provisioned on Railway — the API 500s in prod
("No objects to concatenate").

Two goals, in priority order:

1. **Make /insights visible to admins in production** — provision the
   data, keep it fresh, and replace the binary feature flag with a
   role-aware access mode. This is the launch gate; everything else is
   additive.
2. **Expand from market-level to stock-level analytics** — the v1 engine
   answers "what is the market doing?" (breadth, regime, stress,
   sectors). The founder's product brainstorm
   (`/Users/navdeep/Documents/marketworks_insight_dashboard_brainstorm.md`)
   targets "what is each NSE 500 stock doing?" — RS ranks, trend scores,
   a screener, per-stock detail pages. That's the pre-RA-license product
   surface: quantitative decision-support data, never recommendations.

## v1 reconciliation — intended vs. done vs. left

### Done (merged on main, 324 insights tests)

| Layer | What exists |
|---|---|
| Data engines (`kite-api/app/insights/`) | breadth, macro (VIX/Nifty), sector constituents/breadth/RS, regime (4-state), stress (0-100), conditional distributions, 7 watchlists (2 validity-badged), concentration attribution, 11 sector subgroups, cross-asset (gold/crude/USDINR/India-10y), calendar/on-this-day, `MarketReading` orchestrator |
| Content (`app/insights/notes/`) | Deterministic commentary engine, 3 note templates, chart renderer, note assembler, `scripts/generate_quant_note.py` CLI, teach-while-broadcasting learn moments |
| API (`app/api/insights.py`) | 13 read-only endpoints, 15-min cache headers, unauthenticated (market analytics, nothing sensitive) |
| Web (`kite-dashboard/src/app/insights/`) | Pulse, Sectors, Watchlists pages + Learn hub (14 explainers, 38-term glossary), snapshot date picker, branded by design_system |
| Governance | TDD_POLICY.md (spec-test-first for engine work), VALIDITY_PROTOCOL.md (6-check gate before any forward-return claim), analog finder retired after failing validity, `pullback_to_50dma` built-but-not-surfaced after failing |

### Left from v1 (deliberately deferred)

- **Prod data provisioning** — the reason the gate exists. → **Phase A here.**
- Phase 3 automation (WhatsApp Business API, cron broadcast, email) —
  bottleneck is Meta approval, not code. Stays deferred.
- FII/DII layer (4.5.2/4.5.4) — founder explicitly skipped. Stays deferred.
- US 10y series (needs FRED key or yfinance; not on Kite) — small task,
  founder decision on FRED key. → Phase B (optional).
- Seasonality engine (4.4.3), pre-event helper (4.4.4), Pulse calendar
  strip (4.4.7) → Phase B.
- Notes archive (2.6, needs note-storage layer), portfolio CTAs (2.7),
  SEO structured data (5.B.7), Lighthouse polish (2.10) — all public-launch
  concerns; deferred until the surface opens beyond admins. → Phase D.

### Relation to the founder's brainstorm doc

The brainstorm's six modules map as follows:

| Brainstorm module | v1 coverage | Gap → this plan |
|---|---|---|
| 1. Market Pulse (regime, breadth) | ✅ Pulse page | minor enrichment (new-high/low names, movers) → C6 |
| 2. NSE 500 Screener | ❌ none | → C1–C5 (core of Phase C) |
| 3. Momentum & Trend (RS ranks, leaderboards, inflection) | partial (RS-leader watchlist only) | → C2, C3 |
| 4. Volume & Breakout | partial (breakout watchlists, no volume analytics) | → C1 (volume ratio), C3 (volume confirmation) |
| 5. Risk & Volatility | ❌ none per-stock | → C1 (ATR%, vol, beta, drawdown) |
| 6. Stock Detail Page | ❌ none | → C5 |

Brainstorm items **out of scope** here: real-time/intraday data (needs
exchange data licensing — EOD only for now, matching brainstorm "Layer 1"),
fundamental data (PE/ROE etc. — no data source in-house), delivery-volume
metrics (not in our Kite panel), alerts/watchlist-saving (post-admin-launch),
heatmap (design-heavy; Phase D), anything resembling buy/sell/target/SL
language (compliance).

## Compliance frame (pre-SEBI-RA — binding on all UI copy)

The product shows **conditions, not instructions**. Allowed: "Momentum
leader", "Near 52-week high", "Extended vs history", "Volume 2.4x average".
Forbidden: "Buy", "Sell", "Accumulate", "Target", "Stop loss",
"Best stocks", any implied recommendation. The v1 commentary engine
already enforces a closed lexicon via tests — **extend those tests to all
new Phase C UI strings and score labels.** Every new page carries the
standard educational disclaimer footer. Forward-return claims (e.g.
"stocks in this state historically returned X%") only after passing
VALIDITY_PROTOCOL.md; default posture is descriptive-only.

---

## Phase A — Admin visibility in production (P0, launch gate)

### A0. Verified current wiring (from review, 2026-07-09)

- Flag: `kite-dashboard/src/lib/flags.ts` → `INSIGHTS_ENABLED`
  (`NEXT_PUBLIC_INSIGHTS_ENABLED === "true"`, build-time).
- Gate: `src/middleware.ts:39` — when off, `/insights*` → redirect
  `/dashboard`. Marketing nav + footer conditionally show the link.
- Signed-in sidebar (`src/components/shared/sidebar.tsx` +
  `mobile-sidebar.tsx`) has `adminOnly` filtering via
  `user.publicMetadata.role`; **no Insights entry exists yet**.
- Engine data reads (Railway paths):
  - `breadth.py:51` → `<repo_root>/nse500_data_merged/` (105 MB, 501 files) — **absent in prod**
  - `macro.py:52` + `watchlists.py:62` → hardcoded
    `/Users/navdeep/Documents/stock_data/indices_data_full` with fallback
    `settings.data_dir/indices_data_historical` (8.7 MB) — **absent in prod**
  - `data/static/*` (events, constituents, index weights) — in Docker image ✅
  - `cache/insights/*.pkl` — derived caches, rebuildable on Railway
- Upload path exists: `POST /api/sync/upload-data` (require_admin) via
  `scripts/upload_price_data.py`, but `ALLOWED_UPLOAD_DIRS`
  (`kite-api/app/api/sync.py:61`) lacks both dirs, and
  `scripts/init_persistent_storage.sh` lacks their volume symlinks (so
  uploads would land on ephemeral `/app` and vanish on redeploy).
- Freshness: `scripts/sync_insights_panels.py` appends daily live fetch
  into the long-history panels; hardcoded to the local Documents path;
  not wired into `run_daily_pipeline.py`. The daily pipeline is runnable
  on Railway via the jobs API (`app/api/jobs.py` — `daily_pipeline`).
- `reading.clear_all_caches()` exists but is not reachable via any API.

### A1. Role-aware access mode (frontend)

Replace the binary flag with a tri-state:
`NEXT_PUBLIC_INSIGHTS_ACCESS` ∈ `off` (default) | `admin` | `all`.
Backward compat: legacy `NEXT_PUBLIC_INSIGHTS_ENABLED=true` ⇒ `all`.

- `flags.ts`: export `INSIGHTS_ACCESS`; keep `INSIGHTS_ENABLED` as a
  derived boolean (`access !== "off"`) for any existing imports.
- `middleware.ts`: `off` → current redirect; `admin` → require
  `sessionClaims.metadata.role === "admin"` (same pattern as
  `isAdminRoute`) else redirect to `/dashboard`; `all` → today's
  behavior (any signed-in user).
- Sidebar + mobile sidebar: add "Insights" item (icon: something like
  `LineChart`); visible when `access === "all"`, or when
  `access === "admin"` and the user is admin. Reuse the existing
  `adminOnly` filter shape — may need a small extension since this item's
  admin-only-ness depends on the env mode.
- Marketing nav/footer: show Insights **only when `access === "all"`**
  (marketing surface is for the public; admin-mode should not advertise it).
- Note: `NEXT_PUBLIC_*` is client-visible by design; the mode leaks
  nothing sensitive.

### A2. Backend provisioning surface

- Add `nse500_data_merged` + `indices_data_historical` to
  `ALLOWED_UPLOAD_DIRS` in `kite-api/app/api/sync.py`.
- **Verify the extract path matches the read path**: upload extracts to
  `settings.data_dir / target`; `breadth.py` reads `_repo_root() /
  "nse500_data_merged"`. Confirm `settings.data_dir` == repo root
  (`/app`) on Railway; if not, align (prefer fixing the reader to use
  `settings.data_dir` consistently rather than special-casing upload).
- `scripts/init_persistent_storage.sh`: `mkdir -p` both dirs on the
  volume + `link` them at exactly the paths the engine reads. Also
  persist `cache/` for insights pkl caches if cheap (else they rebuild).
- **Security invariant**: any `sync.py` / upload-path diff goes through
  the `security-reviewer` subagent before commit (CLAUDE.md, R-014-class
  change). Path traversal review on tar extraction for the new targets.

### A3. Path hygiene (kill the hardcoded Documents paths)

`macro.py`, `watchlists.py`, `sync_insights_panels.py` reference
`/Users/navdeep/Documents/stock_data/indices_data_full` directly. Replace
with a single resolver (e.g. in a shared `app/insights/_paths.py` or
settings): env override (`INSIGHTS_INDICES_DIR`) → local Documents dir if
it exists → `settings.data_dir/indices_data_historical`. Keeps local dev
behavior identical while making Railway first-class. TDD not required
(refactor), but keep the existing 324 tests green.

### A4. Data upload + runbook (founder action)

- Prep script (or documented one-liners) that tarballs the two dirs and
  calls `scripts/upload_price_data.py --api-url
  https://kite-lab-production.up.railway.app --token <ADMIN_JWT>
  --target <dir>` for each. ~115 MB raw; CSVs compress well.
- The indices tarball is built FROM
  `/Users/navdeep/Documents/stock_data/indices_data_full` but uploaded AS
  `indices_data_historical` (the prod fallback name) — make the runbook
  explicit about this rename.
- Founder runs it with their prod admin JWT (agent must NOT attempt this;
  needs founder credentials + is a prod mutation).

### A5. Freshness + cache lifecycle

- Make `sync_insights_panels.py` env-aware (per A3) so it can run on
  Railway after the daily pipeline populates `nse500_data`/`indices_data`.
- Wire it as a late step of `run_daily_pipeline.py` (after corporate-
  actions adjustment and index fetches; respect the documented step
  order in CLAUDE.md — it appends only, safe), followed by an insights
  cache clear.
- Add an admin endpoint `POST /api/insights/cache/clear` behind
  `require_admin` (mirrors existing admin-mutation patterns) so a
  refresh can be forced without a redeploy. Wire pipeline to call
  `clear_all_caches()` in-process where it runs.
- First-request warmup: the 16y breadth panel builds from 501 CSVs on
  first hit. Measure; if > a few seconds, pre-warm after cache clear
  (e.g. pipeline step or startup task computes today's `MarketReading`).

### A6. Verification (definition of done for Phase A)

- Local: `pytest kite-api/tests/` clean (esp. the 324 insights tests +
  277 authz assertions), `npm run build` clean.
- Middleware unit reasoning verified manually: admin sees /insights;
  client redirected to /dashboard; signed-out → sign-in.
- Prod (after founder actions): all 5 insights pages render with real
  data as admin; `/api/insights/reading` 200s; a client account cannot
  reach /insights; data survives a Railway redeploy (symlink check).
- Founder actions checklist: (1) upload data with JWT, (2) set
  `NEXT_PUBLIC_INSIGHTS_ACCESS=admin` on Vercel + redeploy, (3) confirm
  daily pipeline schedule includes the panel-sync step.

## Phase B — v1 leftovers worth closing now (P2, small)

- B1. Seasonality engine (4.4.3): calendar-month/week historical
  median/IQR from the 16y panel; TDD; surfaces in premarket note +
  calendar API. Forward-framing must pass validity protocol (seasonality
  claims are exactly the kind that usually fail — likely ships as
  descriptive-only: "median December: +X% over 16 years" is a historical
  observation, allowed with n disclosed).
- B2. Pre-event helper (4.4.4): known-event-day context (budget, RBI
  dates from `historical_events.csv`).
- B3. Pulse calendar strip (4.4.7): "on this day" chip on Pulse.
- B4 (optional, founder call): US 10y via FRED (`DGS10`, free API key).
  Skip if no key provided; do NOT fabricate or proxy the series.

## Phase C — Stock-level analytics (P1, the expansion)

The product thesis (from the brainstorm): traders get decision-support
data on all 500 names — what's moving, how strong the trend is, whether
the move has participation, how stretched it is — and form their own
conclusions. EOD data only (we have 16y split-adjusted daily panels);
"as of yesterday's close" is honest and licensing-safe.

All engine work is TDD per `tasks/insight_engine/TDD_POLICY.md` (this IS
`kite-api/app/insights/` work — spec tests first). All copy through the
compliance lexicon. No forward-return claims without a validity study.

### C1. `stock_metrics.py` — per-stock feature engine

One vectorized pass over the NSE 500 panel producing a per-stock,
per-date feature frame (cached like the breadth panel):

- Returns: 1D / 1W / 1M / 3M / 6M / 12M
- Trend structure: above/below 20/50/100/200-DMA, DMA slopes (20d change),
  50>200 alignment, distance from each DMA (%)
- Levels: distance from 52w high / 52w low, days since 52w high,
  drawdown from 252d peak
- Risk: ATR(14) as % of price, realized vol 20d/60d (annualized), vol
  percentile vs own 1y history, beta vs Nifty 50 (60d), max drawdown 1y
- Volume: volume / 20d avg volume ratio, turnover (₹ Cr, 20d avg),
  up-day vs down-day volume ratio (20d)
- Liquidity tier from avg turnover (Good/Moderate/Low buckets — thresholds
  documented in the explainer, not invented precision)

Spec tests: hand-computed fixtures for each metric family; boundary
cases (insufficient history → None, not NaN-propagation); a canonical
historical day cross-check (e.g. March 2020: median 1M return deeply
negative, vol percentiles extreme).

### C2. `rs_rank.py` — relative strength ranking

- Composite RS score per stock: weighted blend of 1/3/6/12M returns.
  **Before inventing weights, check `data_pipeline/` for the existing
  momentum-score methodology used by the production portfolios and reuse
  its shape where sensible** (consistency with the firm's own definition
  of momentum is a feature; document whatever is chosen).
- Rank 1..500 (1 = strongest) + percentile; sector-relative rank among
  sector constituents (reuse `sector_constituents.py`).
- Rank history: store/derive rank as-of any date so we can compute
  21-trading-day rank delta → "Momentum Inflection" list (biggest rank
  improvers, e.g. rank 312 → 88). This is observational (rank change is
  a fact); any "inflection predicts outperformance" claim requires a
  validity study first — run one via
  `tasks/insight_engine/pattern_validity_study.py` and badge accordingly.

### C3. `scores.py` — composite 0-100 scores + insight tags

Four scores, each a transparent weighted checklist (weights documented
in Learn explainers — auditability is the brand):

- **Trend Score**: DMA positions + alignment + slopes + proximity to
  52w high + drawdown control.
- **Extension Risk**: distance above 20/50-DMA in ATR units + 5d return
  percentile vs own history + RSI(14) extreme. Label bands: Low /
  Moderate / High / Very high ("Extended vs history" language).
- **Volume Confirmation**: today + 5d volume ratio + up/down-day volume
  balance. Labels: Weak / Neutral / Strong.
- **Momentum Consistency**: % positive weeks over 6M + max drawdown
  during the trailing 6M move + vol-adjusted return. (The brainstorm's
  "Move Quality" — separates smooth trends from one-spike wonders.)

Insight tags derived from metrics/scores (pure observation):
`Momentum leader` (RS top decile), `Near 52w high` (≤3%), `Fresh 52w
high`, `Volume expansion` (≥2x), `Extended` (Extension ≥ High), `Coiled`
(reuse existing coiled-spring detector), `New momentum` (inflection
top-25), `Quiet` (low vol percentile). Tags are the screener's currency
and reuse v1 watchlist detectors where they exist.

Spec tests: monotonicity invariants (raising a positive input never
lowers the score), band boundaries, canonical-day checks, and the
compliance lexicon test over every label string.

### C4. API additions (`app/api/insights.py`)

- `GET /api/insights/screener?date=` → one payload: all NSE 500 rows ×
  full metric/score/tag set + as-of date. ~500 rows; target < 500 KB
  JSON; 15-min cache headers like the rest. Filtering/sorting is
  client-side (500 rows is trivial for the browser).
- `GET /api/insights/stocks/{symbol}?date=` → everything the screener
  has for that stock, plus timeseries for the detail page: 1y of
  (close, 50/200-DMA, volume ratio), RS-rank history (1y), score history
  (6m). 404 on unknown symbol with the valid-universe hint.
- Extend `MarketReading` only if the Pulse page needs aggregates (e.g.
  count of fresh 52w highs with names — C6); don't bloat it with the
  full per-stock table.
- Same unauthenticated read-only posture as the other insights routes
  (frontend gates access; data is derived analytics, not client data).

### C5. Web UI (two new pages, brand-consistent with design_system)

- **`/insights/screener`** — the main product surface.
  - Sticky-header sortable table, all 500 rows, client-side.
  - Filter rail: sector multi-select, insight-tag chips, numeric range
    filters (RS rank, Trend score, 1/3/6M return, ATR%, distance from
    52w high, volume ratio, above/below 50/200-DMA toggles).
  - Preset views (chips): Momentum leaders · Fresh momentum (inflection)
    · Near 52w highs · Volume surges · Quiet compounders (consistency
    high + vol low) · Extended names. Each preset = a saved filter
    combo, URL-encoded (`?preset=` / query params) so views are
    shareable/bookmarkable.
  - Column groups toggle (Returns / Trend / Risk / Volume) so the table
    stays readable; sensible mobile fallback (card list, top metrics).
  - Every column header links its Learn explainer ("What is this?").
  - Disclaimer footer.
- **`/insights/stocks/[symbol]`** — per-stock detail.
  - Header: name, sector, close, 1D change, insight tags.
  - Score row: RS rank (with sector rank), Trend, Extension, Volume
    confirmation, Consistency — each with band label + explainer link.
  - Sections: Trend structure (DMA table + distance from 52w levels),
    Momentum profile (return ladder + RS rank sparkline 1y), Volume
    profile, Risk profile (ATR%, vol percentile, beta, drawdown).
  - Price chart: 1y close + 50/200-DMA (reuse the dashboard's existing
    charting approach from design_system; keep it server-data +
    lightweight client chart).
  - Peer strip: top-5 sector constituents by RS with links.
  - Screener rows link here; watchlist entries link here too.
- Navigation: "Screener" + (contextually) stock pages join the insights
  tab nav in the shared layout. Snapshot date picker keeps working on
  both new pages (`?date=` respected end-to-end).

### C6. Pulse enrichment (small)

- "Fresh 52-week highs / lows" card with the actual names (top 5 + count).
- "Biggest RS-rank improvers this month" mini-list (top 5, links to
  stock pages) — feeds the Momentum Inflection story.
- Both link to pre-filtered screener presets.

### C7. Learn layer additions

New explainers (same typed-TS pattern, `src/content/insights/learn/`):
`rs-rank`, `trend-score`, `extension-risk`, `volume-confirmation`,
`momentum-consistency`, `atr`, `beta`, `liquidity`. Each: what it is,
exactly how we compute it (transparent weights), how to read it, common
misreadings. Glossary entries for new terms (ATR, beta, RSI, turnover,
inflection). Every score surfaced in UI deep-links its explainer.

### C8. Validity + compliance gates (cross-cutting)

- Run the pattern-validity harness on: momentum-inflection cohort,
  RS-top-decile cohort, extension-risk-high cohort (as a *risk* framing:
  do extended names underperform? even a null result is publishable as
  honest education). Badge outcomes per VALIDITY_PROTOCOL.md tiers.
- Extend the closed-lexicon/recommendation-verb test to cover: all
  insight-tag strings, score band labels, preset names, and both new
  pages' static copy.
- No fabricated thresholds passed off as researched: where a threshold
  is a design choice (e.g. "2x volume = expansion"), the explainer says
  "we use 2x as a round, transparent cutoff", not fake empirics.

### C9. Performance

- The per-stock feature frame computes once per date and caches
  (memory + pkl under `cache/insights/`), invalidated by
  `clear_all_caches()`. Screener endpoint must serve warm in <100 ms.
- Measure cold-build time on the 16y panel; if the full-history feature
  frame is slow, compute only trailing windows needed for current
  metrics (most need ≤ 252d of history + 5y for multi-year levels).

## Phase D — Public-launch prep (explicitly deferred, do not build now)

Free-tier public launch (flip to `access=all`), funnel CTAs to
/portfolios, SEO structured data + Lighthouse, notes archive +
note-storage, saved watchlists + alerts, WhatsApp automation (v1 Phase 3),
heatmap visualization, real-time/delayed intraday layer (needs data-
licensing legal review first), compliance-consultant copy review before
any public flip. Listed so nothing is forgotten; none of it gates the
admin launch.

## Execution plan (agent handoff)

Sequential Opus 4.8 agents on this branch, each with a bounded scope:

1. **Agent A — Phase A** (admin visibility). Touches middleware/flags/
   sidebars, sync.py + init script, path resolver, pipeline wiring,
   cache endpoint, runbook. Must invoke `security-reviewer` on the
   sync.py diff. Ends with: tests + build green, founder runbook in
   `tasks/insights_v2/RUNBOOK_admin_launch.md`, commits prefixed
   `insights_v2:`.
2. **Agent C1 — engines** (C1–C3 + C8 validity studies). TDD-first.
3. **Agent C2 — API + UI** (C4–C7). Depends on C1's engine contracts.
4. **Agent B — leftovers** (B1–B3; B4 only if FRED key appears). Can run
   any time after A.

Each agent: keep the 324-test suite green, `npm run build` +
`pytest tests/` before any push, no pushes to main, PR at the end with
`--no-ff` merge by founder.

## Founder decision points (non-blocking for code, blocking for launch)

1. Run the data upload with prod admin JWT (runbook will have exact commands).
2. Set `NEXT_PUBLIC_INSIGHTS_ACCESS=admin` on Vercel + redeploy.
3. FRED API key for US 10y — yes/no (B4).
4. When Phase C lands: review score labels/copy from a compliance lens
   before any future `access=all` flip (admin-only exposure is the safe
   sandbox until then).

## Out of scope

Real-time data, fundamentals, options/F&O analytics, alerts, portfolio
recommendations of any kind, Hindi content, mobile app, per-user
personalization, `pullback_to_50dma` resurrection (it failed validity),
analog finder resurrection (ditto).
