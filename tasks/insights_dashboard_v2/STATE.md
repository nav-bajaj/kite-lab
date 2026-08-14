# STATE — read this first when resuming

Last updated: 2026-08-14, branch `insights_dashboard_v2` (13 commits
ahead of `auth_stack_v2`, its base). Working tree clean. Not merged,
not pushed. All verification: backend `pytest tests/` 1197 passed /
2 skipped; `npm run build` clean; every change click-verified in a
signed-in browser against the local backend (evidence PNGs in
`evidence/`).

## What is BUILT and working (run it: backend uvicorn :8000 + `npm run
dev` in kite-dashboard; sign in; open /insights)

**Shell** — full-screen app skeleton identical to the portfolios
dashboard: fixed collapsible sidebar (Overview / Market Pulse /
Sectors & Rotation / Stock Lists / Screener / Learn), full-width top
bar with UNIVERSE selector (Nifty 500 default / 250 / 100 / 50) +
compact snapshot picker + Dashboard link + palette + user menu.
`?date=` and `?universe=` thread through all navigation.

**Overview (mission control)** — MARKET row 1: Regime, Stress,
Breadth cards; row 2: India VIX, Net new highs, Advances/declines,
McClellan, Concentration (sparklines; breadth-family + concentration
follow the universe selector). SECTORS: RS tornado. STOCK LISTS: four
list cards (15+ cap shown honestly) + movers strip (moved here from
Market by founder call). Every card expands to its detail.

**Market Pulse section** — ONE horizontal browser-style tab row
(active tab = raised card), identical on every page: Regime | Stress |
Breadth | Advances & declines | Net new highs | McClellan | India VIX
| Concentration. `/insights/market` redirects to the Regime tab (the
old "Daily read" page was removed as an Overview duplicate). Detail
views: chart on lightweight-charts (range picker 6M→Max), reference
bands, stat strip, "what this measures" learn panel, disclaimer.
- Regime: episode timeline to 2009, spell stats, recent spells,
  four-states legend. NO forward-return content (base-rates table
  removed — founder: suggestive).
- Breadth: metric explorer chips (% > 200/100/50/21-DMA + avg-dist).
- A/D: daily net advances + cumulative A-D line variants.
- Bands: Breadth-Atlas values label the Nifty 500 scope; other
  universes get percentiles computed from their own fetched history.
- Concentration: cap (actual index) vs equal-weighted constituents,
  20d-avg chart, per-universe; per-name attribution tiles only on
  nifty50 (weights exist only there — noted in UI).

**Backend added on this branch** (all TDD, spec tests first):
breadth panel universe param (`get_breadth_panel(universe)`, per-
universe disk caches, legacy path kept for nse500) + atlas columns
(pct_above_21dma, avg_dist_from_200dma, mcclellan_sum) + stale-schema
cache guard; `GET /macro/timeseries`;
`compute_concentration_panel(universe)` + `GET
/concentration/timeseries?universe=`; `?universe=` on
/breadth/timeseries. Two latent test bugs fixed (mixed-sign top-5
invariant). NO changes to reading/regime/stress engines.

**Not started**: Sectors & Rotation rebuild (RRG — Slice 3, needs D3
sign-off), Stock Lists detectors (Slice 4), intraday layer (Slice 5),
launch repositioning (Phase L). `/insights/sectors`, `/watchlists`
(retitled "Stock Lists", movers block added), `/screener`, `/learn`
still render their pre-branch content inside the new shell.

## Founder decisions this branch (full log in DECISIONS.md)

- Launch pivot: insight_engine IS the launch product; portfolios stay
  admin-only. D1 live-intraday route approved (posture C). D2 IA
  approved. D3 (RRG methodology) and D4 (compliance pass) still OPEN.
- Production design system is authoritative for visuals; the Pencil
  mock (mock_insights_dashboard.pen) was directional only.
- Development proceeds indicator-set by indicator-set.
- Regime: keep the detail, never show forward-return tables on it.
- Founder wants an indicator-by-indicator deep dive next.

## Environment notes

- Local data refreshed through 2026-08-13 close; refresh runbook in
  DECISIONS.md (run after market close only).
- Local sign-in for verification: E2E user via OTP — see
  tests/e2e/auth-smoke.spec.ts pattern (service key via supabase CLI).
- Gitleaks quirks: `.pen` fileToken allowlisted (R-028); avoid
  `key: "<snake_case_string>"` literals in TSX (use `metric:` etc.);
  the pre-commit hook scans the stage BEFORE the bash command runs —
  `git add` and `git commit` must be separate commands.
- No pushes 09:00-15:30 IST (live services restart on deploy).

## Next up (in order)

1. Founder's indicator-by-indicator deep dive (copy, bands, stat
   tiles, defaults — batch changes per his notes).
2. D3 sign-off → Slice 3 (RRG per RRG_SPEC.md).
3. Slice 4 (Stock Lists detectors + daily cross-section persistence).
4. Slice 5 (intraday, posture C) — independent, can move earlier.
