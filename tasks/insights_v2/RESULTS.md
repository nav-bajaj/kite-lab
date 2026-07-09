# Insights v2 — results

**Status:** code-complete on `insights-v2` (2026-07-09), pending founder
review + PR + the two prod actions in `RUNBOOK_admin_launch.md`.
Planned by Fable 5; executed by three sequential Opus 4.8 agents
(Phase A → Phase C engines → Phase C API/UI) plus one for Phase B.

**Branch state at close-out:**
- 20 commits ahead of `main` (`f8784f2..45fd1c4` + close-out)
- Backend: **783 passed / 1 skipped** (was 678 before this branch; +105)
- Frontend: `npm run build` clean; ESLint clean
- Security: three reviewer passes (A2 sync-path diff: approve-with-notes,
  R-014 register row updated; Phase C API diff: approve; Phase B diff:
  independent security-reviewer PASS-with-notes — its recommendation
  landed at close-out as register row **R-023** documenting the
  intentionally-unauthenticated `/api/insights/*` read surface, plus an
  `attack-surface.md` entry)

## What shipped

### Phase A — admin visibility in production

- Tri-state access flag `NEXT_PUBLIC_INSIGHTS_ACCESS` (off / admin / all;
  legacy `NEXT_PUBLIC_INSIGHTS_ENABLED=true` ⇒ all). In `admin` mode the
  middleware requires `publicMetadata.role === "admin"` for `/insights*`.
- Signed-in sidebar (desktop + mobile) gained an Insights entry via a new
  single-source nav list (`kite-dashboard/src/lib/nav.ts`); marketing
  nav/footer advertise Insights only in `all` mode.
- Prod data provisioning surface: `nse500_data_merged` +
  `indices_data_historical` added to `ALLOWED_UPLOAD_DIRS` and the Railway
  volume symlink script; path alignment verified (`settings.data_dir` =
  `/app`; upload, symlink, and engine reads coincide).
  `scripts/upload_price_data.py` extended (two targets + `--source-dir`
  for the indices_data_full → indices_data_historical rename).
- Path hygiene: hardcoded `/Users/navdeep/Documents/...` paths replaced by
  `app.insights._paths.indices_dir()` (env `INSIGHTS_INDICES_DIR` → local
  Documents → `settings.data_dir/indices_data_historical`).
- Freshness: `sync_insights_panels.py` + cache clear wired as late daily-
  pipeline steps; `POST /api/insights/cache/clear` behind `require_admin`
  (covered in `test_clerk_authz.py` ADMIN_ENDPOINTS).
- Cold-build timing: breadth panel 1.9s, full MarketReading 3.6s — under
  the 5s threshold, no pre-warm needed.
- Founder runbook at `RUNBOOK_admin_launch.md`.

### Phase C — stock-level analytics (the expansion)

**Engines** (all TDD spec-test-first, warm access ~0ms):
- `stock_metrics.py` — ~25 metrics per NSE 500 stock per date (returns
  ladder, DMA structure + slopes, 52w levels, ATR%, realized vol +
  percentile, beta, drawdown, volume/turnover, liquidity tier).
- `rs_rank.py` — composite RS rank 1..500 (weights documented, shape
  reused from the production momentum methodology), sector-relative rank,
  21-day rank delta → momentum-inflection cohort.
- `scores.py` — Trend / Extension Risk / Volume Confirmation / Momentum
  Consistency (transparent 0-100 checklists) + compliance-locked insight
  tag strings; monotonicity invariants tested.

**Validity studies** (`VALIDITY/`, matched NSE 500 baseline, 165 dates
2012-2025) — findings drove the UI framing:

| Cohort | 20d excess | Verdict |
|---|---|---|
| rs_top_decile | +1.19pp, consistent | Validated — forward-return narrative allowed with badge |
| inflection | −0.27pp, sign flips | Observation-only — no outperformance claim anywhere |
| extension_high | +0.79pp | Null: extended names did NOT underperform — "Extended" is a state label; no mean-reversion story |

**API** (read-only, unauthenticated like siblings, 15-min cache, degrade
gracefully when the panel is unprovisioned):
- `GET /api/insights/screener` — 496 rows, 442.6 KB, 37.7ms warm
- `GET /api/insights/stocks/{symbol}` — profile + 1y price/DMA/volume-ratio
  series + monthly RS-rank history + top-5 sector peers
- `GET /api/insights/movers` — Pulse aggregates (fresh 52w highs/lows,
  top RS improvers); `MarketReading` kept lean

**UI:**
- `/insights/screener` — sortable sticky-header table, filter rail,
  6 preset chips as URL-encoded shareable state, column-group toggles,
  mobile card fallback, per-column Learn links, disclaimer footer.
- `/insights/stocks/[symbol]` — header + tags, 5-score row, trend/
  momentum/volume/risk sections, peer strip, friendly not-found.
  Price chart on **TradingView `lightweight-charts@^5.2.0`** (founder-
  requested dep) — theme-aware via design tokens, resize-handled, with
  the license-required "Charts by TradingView" attribution caption.
- Pulse: fresh 52w highs/lows card + RS-improvers card (observation-only
  copy per the inflection verdict).
- Learn: 8 new explainers (rs-rank quotes RS_WEIGHTS; liquidity quotes
  tier cutoffs as design choices; extension-risk states the null finding
  honestly) + 6 glossary terms. 22 explainers prerender.

### Phase B — v1 leftovers closed

- Seasonality engine (4.4.3): month + ISO-week profiles (median, middle-
  half range, % positive, n). Descriptive-only by construction — n=16 per
  month can never clear the validity protocol's n≥100 bar; copy always
  discloses n and ends "A historical tendency across a small sample, not
  a forecast." Wired as the quiet-day fallback in the premarket
  commentary cascade.
- Pre-event helper (4.4.4): upcoming curated events within N days +
  same-event-type historical 1d/5d context. Forward-dated events must be
  hand-curated into `data/static/historical_events.csv` (documented in
  code + the card's empty state).
- Pulse market-calendar strip (4.4.7): on-this-day + month seasonality +
  upcoming events; each fetch null-degrades so the strip never breaks
  the page.
- Endpoints: `GET /api/insights/calendar/seasonality`,
  `GET /api/insights/calendar/pre-event` (window bounded 1-90 days).
- B4 (US 10y via FRED) skipped — no FRED key; nothing fabricated.

## Deliberately not done (Phase D — public launch prep)

Public flip (`access=all`), portfolio CTAs, SEO structured data, notes
archive, saved watchlists, alerts, WhatsApp automation, heatmap,
intraday/real-time layer (needs data-licensing review), compliance-
consultant copy review before any public exposure.

## Founder actions to go live (see RUNBOOK_admin_launch.md)

1. Merge PR (`--no-ff`), let Railway deploy the backend (init script
   creates the new symlinks; upload whitelist goes live).
2. Upload the two data panels with a prod admin JWT
   (`scripts/upload_price_data.py`, one command per dir, ~115 MB raw).
3. Set `NEXT_PUBLIC_INSIGHTS_ACCESS=admin` on Vercel + redeploy; run the
   verification checklist (admin sees all pages incl. screener + stock
   pages; client redirected; data survives a Railway redeploy).
4. Eyeball `/insights/screener` and a stock page with an admin login —
   neither execution agent could visually verify (Clerk gate blocks
   anonymous browsing; verified via clean builds + endpoint smoke tests).

## Notes / known gaps

- `docs/security/attack-surface.md` doesn't enumerate the `/api/insights/*`
  surface at all — pre-existing v1 gap, flagged by the Phase B security
  pass; add a line next time the register is touched.
- Stock-page score *history* was dropped by design (per-date rebuild too
  costly); RS-rank history is monthly-sampled.
- Screener payload trims fields to stay under 500 KB; dropped fields are
  detail-page-only or client-derivable.
- A screener column key was renamed `sortKey` → `sortField` to clear a
  gitleaks generic-api-key false positive.

## Verification log

- `pytest tests/` (kite-api): 783 passed, 1 skipped — run independently
  by the orchestrator at close-out, matching the agents' reports.
- `npm run build` (kite-dashboard): clean, all routes compile, 22 Learn
  pages prerender.
- Authz gate: 282 assertions passing incl. the new cache-clear endpoint.
- Canonical-day checks inside the suites: 2020-03-23 metrics extremes,
  2018 NBFC subgroup divergence, COVID anniversary firing, December
  seasonality n=16.
