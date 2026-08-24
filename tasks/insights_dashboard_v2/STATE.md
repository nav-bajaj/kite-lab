# STATE — read this first when resuming

Last updated: 2026-08-21, branch `insights_dashboard_v2` (37 commits
ahead of `auth_stack_v2`, its base). Working tree clean. Not merged,
not pushed. All verification: backend `pytest tests/` **1244 passed /
1 skipped**; `npm run build` + `npx eslint` clean; every change
click-verified in a signed-in browser at **both 1440x900 and 390x844**
against the local backend (evidence PNGs in `evidence/`).

NOTE: `data/final_portfolio/*.csv` show as modified in the working
tree. That is daily-pipeline output, unrelated to this branch — left
uncommitted deliberately.

## Start here

```
cd kite-api && source ../.venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd kite-dashboard && npm run dev            # :3000
```
Then sign in and open /insights. Local data runs through the
2026-08-19 close.

## Copy review runs on the page, not in chat

The founder marks up wording directly on localhost via the Vercel
Toolbar (dev-only mount in `kite-dashboard/src/app/layout.tsx`):

```
python3 tasks/insights_dashboard_v2/read_comments.py      # his notes
... apply them ...
echo '{"<threadId>": "what changed"}' | python3 \
    tasks/insights_dashboard_v2/reply_comments.py         # reply + resolve
```

Auth is the Vercel CLI token (`vercel login`), NOT the claude.ai Vercel
MCP connector — that returns no teams for this account. Both REST
endpoints are undocumented; see DECISIONS.md. Notes pinned **after
selecting the text** carry `context.selection` and are unambiguous;
notes pinned without a selection only carry a React element path and
have to be inferred.

## What is BUILT and working (run it: backend uvicorn :8000 + `npm run
dev` in kite-dashboard; sign in; open /insights)

**Shell** — full-screen app skeleton identical to the portfolios
dashboard: fixed collapsible sidebar (Overview / Market Pulse /
Sectors & Rotation / Stock Lists / Screener / Learn), full-width top
bar with UNIVERSE selector (Nifty 500 default / 250 / 100 / 50) +
compact snapshot picker + Dashboard link + palette + user menu.
`?date=` and `?universe=` thread through all navigation.

**Overview (mission control)** — one hairline panel per section rather
than gap-separated cards. MARKET row 1: Regime, Stress, Breadth; row 2:
India VIX, 52-week highs, Advances/declines, Concentration (sparklines;
breadth-family + concentration follow the universe selector). SECTORS:
RS tornado. STOCK LISTS: four list cards (15+ cap shown honestly) +
movers strip. Every card expands to its detail. Section headers carry
the sidebar's own glyph in an accent chip.

**Market Pulse section** — ONE horizontal browser-style tab row
(active tab = raised card, each with a lucide glyph, short labels under
`sm`), identical on every page: Regime | Stress | Breadth | Advances &
declines | 52-week highs | India VIX | Concentration. **McClellan was
removed entirely** (founder, 2026-08-20) — its route 404s, though the
engine still computes the oscillator and the Learn explainer remains.
`/insights/market` redirects to the Regime tab. Detail views: chart on
lightweight-charts (**1Y default on every tab**, 6M→Max picker,
responsive height 260/320/400), reference bands at both extremes, a
hairline stat strip, a Learn panel and the disclaimer.
- **Regime — DONE, signed off 2026-08-15** (three rounds, 15 on-page
  comments). Index chart with a per-day regime tint, **line or
  candles**, crosshair readout (date + OHLC + regime), 1Y default.
  Regime is per universe on **50-day** trend + 50-day participation
  windows (VIX shared — no per-universe analog); history starts where
  that index's data starts: 2010 for Nifty 100/50, 2015 for Nifty 500,
  2020 for Nifty 250. Four cards **above** the chart (current /
  previous / index this regime / participation), then median regime
  length, then recent regimes with each one's index return. Rule text
  is generated from the engine's window constants so copy cannot drift
  from behaviour. The whole tab rewinds with `?date=`, chart included.
  NO forward-return content anywhere on it. The word "spell" is gone;
  so is "state".
  Open flags: STRETCHED fires only ~3 times in 11 years on the broad
  universes under the new rule (may want a looser threshold); candles
  are dense at 3Y+.
- **Stress — DONE** (13 notes over two rounds): three dual cards ABOVE
  the chart — band + score, VIX + its percentile, drawdown + breadth.
  **Bands are 35 / 60** (below 35 calm, 35-60 middle ground, above 60
  stressed), defined ONCE in `stress.py` as `CALM_BELOW` /
  `STRESSED_ABOVE` and shipped on the snapshot; chart lines, card label
  and explainer all render from that. Percentile window is 1 year, to
  match every other quantity on the tab. The drivers card's 0-100
  values are no longer multiplied by 100 again. "How the score is
  computed" bullets render from engine-shipped weights/windows.
- **Breadth — DONE** (3 notes): title follows the universe, per-metric
  one-line explainers, index overlay, rewinds in full. Four cards are
  now readings, not reference levels: current, its percentile, the
  20-session change, and the index's 20-session move with a divergence
  note beneath the strip. The % > 21-DMA chip was removed.
- **Advances & declines — DONE** (5 notes): the A-D line is available
  **in stocks** (`cumulative_ad_count`) as well as in percent —
  `cumulative_ad` alone was a running sum of ratios, i.e. neither.
  Today's split renders as coloured counts with arrows. Index overlay.
  **2026-08-21 — E/F chart upgrade shipped on this tab only** (founder
  picked experiments E+F, see DECISIONS): both A-D line variants carry
  a dashed "start" reference line at the first visible day's value
  (the green-above/red-below BaselineSeries fill was tried and pulled
  next day — recolouring on every pan read as noise, worse with the
  overlay; founder, 2026-08-22); the overlay moved to a VISIBLE left
  % axis (amber `--chart-series-2`, 2px); pan/zoom is on (wheel/pinch
  zoom, drag pan, axis drag + double-click reset, both edges fixed,
  wheel never scrolls the page) and the range pills set the initial
  window over the full 4000-day fetch, so panning left reveals
  history. Anchor + rebase follow the window via
  `subscribeVisibleLogicalRangeChange`. New opt-in props on
  `TimeseriesChart` (`anchor` / `overlayAxis="left"` /
  `interactive`) + pass-throughs on `MetricExplorer`; every other tab
  keeps the old defaults. Awaiting founder review before propagating.
- **52-week highs — REPLACED Net new highs** (founder, 2026-08-20).
  Headline is `avg_dist_from_52w_high`; chips add % within 5% of high
  and % more than 20% below; the old count is kept as a fourth chip.
  Slug is `52-week-highs` — the old URL 404s.
- **India VIX — partly reviewed**: percentile card, index 5-session
  move paired against the VIX 5-session change, bands at both extremes,
  tiles above the chart.
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
invariant). Deep-dive round added universe-scoped regime:
`compute_regime_panel/get_regime_snapshot/get_regime_history(universe)`
(no-arg call keeps the legacy market-wide panel for notes/conditional
dist/calendar — see DECISIONS D5), episode `index_return_pct`, `GET
/regime/timeseries?universe=`, `?universe=` on /regime/history and
/reading. Stress now ships `weights` + percentile/component windows on
its snapshot so the UI states the maths without retyping it; new `GET
/index/timeseries?universe=` powers the chart overlays.

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
- Indicator-by-indicator deep dive is IN PROGRESS, tab by tab, with
  notes left on the page itself. Regime, Stress and Breadth are done.
- Indicator charts carry an optional **index overlay** (rebased to % from
  the left edge of the visible window) behind a toggle — the founder
  wants it on every gauge, since the point is correlation with price.
- Regime rules were redefined to 50-day windows by eye, not by study.
  Founder's call: an independent study later should test whether a
  different rule set defines the current regime better, rather than
  tuning thresholds live.
- **The dashboard is deliberately denser than the marketing surface**
  and diverges from it (founder, 2026-08-21). Hairline grids, 2-up on
  mobile, tighter padding; the app scale is named in `--app-pad/-gap`
  on `.mw-app`. Reclaimed space goes to charts, not whitespace.
- **The display serif is gone from /insights** — sans + mono only.
  Fraunces stays on marketing, library, sign-in, portfolios, account.
- **Percentiles show the stat AND a sentence**: "42nd percentile" over
  "higher than 42% of the past year". Never a bare "p42".

## STANDING RULES learned the hard way on this branch

1. **If the UI states a number the engine owns, the engine ships it.**
   Displayed copy claimed 100/200-day regime windows and 30/30/25/15
   stress weights that were really 50/50 and 35/25/20/20. Weights,
   windows and band boundaries now travel on the snapshot.
2. **Never coerce "unknown" into a value.** `score or 0.0` rendered a
   missing percentile as a confident "p0"; `.fillna(0)` scored missing
   components as maximum calm.
3. **Timeseries endpoints take a `date`** — they return the most recent
   rows otherwise, which is how the Overview showed today's breadth
   under a 2020 header (46% vs a true 11%).
4. **Never put token-coloured text on a tint of the same token** —
   measured 4.06-4.16, below AA. `--chart-3` is the safe "notable, no
   valence" token at 5.66-5.86.
5. **Adding a breadth panel column?** Add it to
   `_SCHEMA_SENTINEL_COLUMNS` or mtime-fresh caches from older code
   silently lack it.

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

1. **Finish the tab deep dive.** Done: Regime, Stress, Breadth,
   Advances & declines, 52-week highs. Partly done: India VIX.
   **Not yet reviewed: Concentration.**
   Carry forward to each remaining tab: (a) truncate its chart on a
   rewound snapshot — Concentration still does not; (b) offer the index
   overlay (`indexOverlay()` + `TimeseriesChart overlay=`); (c) tiles
   above the chart; (d) percentile as stat + sentence; (e) never retype
   a number the engine owns.

2. **Two studies' leftovers** (full detail in DECISIONS 2026-08-21):
   - Replace the Overview cards' prose `foot` with a data line
     (`55% · +2pp 20d · 43rd pctile`) — denser AND more informative.
     Needs `pctRank`/`changeOver` lifted out of `market/[indicator]/
     page.tsx` into a shared helper; the Overview already fetches the
     series it needs, so no new endpoint.
   - Hide `InsightsMobileNav` on `/insights/market/*` — 104px of
     stacked nav chrome on every mobile detail page. A bottom nav bar
     is the better long-term answer.
   - `ReferenceBand.tone` is keyed to distribution position, so
     `atlasBands()` paints the top-5%-participation line ochre-caution
     and the bottom-5% line red — inverted for breadth. Make both
     `--chart-3` and let the labels do the work.
   - `ui.tsx` `RegimeCard`/`MetricCard`/`CardTakeaway` have NO importer;
     `REGIME_TAKEAWAY` holds four written, compliance-shaped "so what"
     lines that ship nowhere. The Overview regime card is their home.
   - `ScoreBar tone="positive"` is hardcoded on trend/consistency —
     a 12 and a 92 are the same green. Should be "default".
   - `shell.tsx` collapsed nav links have only a `title` as accessible
     name; add `aria-label`.

3. **Open questions for the founder** (asked, not answered):
   - STRETCHED fires only ~3 times in 11 years on the broad universes
     under the 50-day rules. Looser threshold, or accept?
   - Candles are dense at 3Y+ — cap the candle view to shorter ranges?
   - Daily net advances kept as the third A/D chip; he said "maybe we
     don't need it".
   - Regime rule set deserves an independent study rather than
     by-eye tuning.

4. D3 sign-off → Slice 3 (RRG per RRG_SPEC.md).
5. Slice 4 (Stock Lists detectors + daily cross-section persistence).
6. Slice 5 (intraday, posture C) — independent, can move earlier.
