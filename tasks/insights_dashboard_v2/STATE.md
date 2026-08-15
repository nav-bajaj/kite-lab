# STATE — read this first when resuming

Last updated: 2026-08-15, branch `insights_dashboard_v2` (19 commits
ahead of `auth_stack_v2`, its base). Working tree clean. Not merged,
not pushed. All verification: backend `pytest tests/` 1215 passed /
2 skipped; `npm run build` clean; every change click-verified in a
signed-in browser against the local backend (evidence PNGs in
`evidence/`).

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
  are dense at 3Y+; the other seven tabs still don't truncate their
  charts on a rewound snapshot.
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
invariant). Deep-dive round added universe-scoped regime:
`compute_regime_panel/get_regime_snapshot/get_regime_history(universe)`
(no-arg call keeps the legacy market-wide panel for notes/conditional
dist/calendar — see DECISIONS D5), episode `index_return_pct`, `GET
/regime/timeseries?universe=`, `?universe=` on /regime/history and
/reading. Stress engine untouched.

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
  notes left on the page itself. Regime is signed off; Stress is next.
- Regime rules were redefined to 50-day windows by eye, not by study.
  Founder's call: an independent study later should test whether a
  different rule set defines the current regime better, rather than
  tuning thresholds live.

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

1. Founder's indicator-by-indicator deep dive, tab by tab (TASKS.md
   Slice 2.6). **Regime signed off 2026-08-15. Stress is next**, then
   Breadth, A/D, Net new highs, McClellan, VIX, Concentration.
   Carry forward to each tab as it comes up: truncate its chart on a
   rewound snapshot (Regime does this; the other seven do not), and
   check its copy for "state"/"spell" leftovers.
2. D3 sign-off → Slice 3 (RRG per RRG_SPEC.md).
3. Slice 4 (Stock Lists detectors + daily cross-section persistence).
4. Slice 5 (intraday, posture C) — independent, can move earlier.
