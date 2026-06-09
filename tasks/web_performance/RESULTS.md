# web_performance — results

> Filled in as phases ship. Planned vs. actual, commits, deferred items,
> verification log.

## Status

In progress. Phase 0 implemented, awaiting user sign-off before Phase 1.

## Per-phase log

### Phase 0 — false login error
- Planned: gate SWR on `authReady`, resolve token at fetch time, fix 401
  toast, stop refresh flicker.
- Actual (all done):
  - `api-auth-context.tsx` — added `authReady` (`isLoaded && isSignedIn &&
    token !== null`); registered an async token provider via
    `setTokenProvider(() => getToken())`; removed the `setIsLoading(true)`
    that the 50s periodic refresh used to fire (no more flicker).
  - `api-client.ts` — added `setTokenProvider`; `apiFetch` now resolves the
    token at request time (explicit → provider → global fallback), so a
    request can never go out with a stale/null token.
  - `hooks.ts` — added `useAuthedSWR` wrapper that passes a `null` SWR key
    until `authReady`, so authed endpoints never fire pre-token (no 401, no
    toast). Routed all 18 authed hooks through it; `useHealth` stays public.
  - `swr-config.tsx` — 401 toast now de-dupes via stable toast ids and
    distinguishes the Zerodha broker token from the Clerk login session.
- Commits: _pending (not committed — awaiting review)_
- Verification: `npx tsc --noEmit` clean; `npm run build` clean (32 routes).
  Manual login-loop check still to be done by user.
- Scope note: backend auth was NOT touched — only *when* the client fetches
  changed, never *whether* the backend authenticates. CLAUDE.md authz
  invariants intact.

### Phase 1 — perceived performance
- Planned: persisted SWR cache, keepPreviousData, route loading.tsx,
  dynamic Recharts, preload on hover.
- Actual (all done):
  - `swr-config.tsx` — localStorage-backed SWR cache provider, **namespaced
    by Clerk userId** (`mw-swr-cache:v1:<userId>`), flushed on
    beforeunload + tab-hidden, and **purged on sign-out / user-switch** so
    one user's data can't surface for another on a shared device. Signed-out
    sessions stay in-memory. `<SWRConfig key={userId}>` remounts per user.
    Added `keepPreviousData: true` globally (no blanking on universe switch
    / trade pagination).
  - `src/app/(dashboard)/loading.tsx` — route-level skeleton for nav
    transitions, sized to roughly match pages (minimize CLS).
  - `components/charts/chart-fallbacks.tsx` (new) + barrel changes in
    `performance/index.ts` and `portfolio/index.ts` — the three
    recharts-backed charts (EquityCurve, DrawdownChart, AllocationChart)
    now load via `next/dynamic` (`ssr:false`) with matching skeleton
    fallbacks, keeping recharts out of the initial route bundle.
  - `lib/preload.ts` (new) + `shared/sidebar.tsx` — hovering/focusing a nav
    link warms that route's primary SWR data (gated on `authReady`).
- Commits: _pending_
- Verification: `npm run build` clean (32 routes, dynamic chart chunks
  split). Runtime "feels instant on return" + no-blank-on-switch best
  confirmed by user on a preview deploy.
- Security note for Phase 5: persisted cache holds portfolio/holdings data
  in localStorage — namespaced + purged as above; flagged for the audit.

### Phase 2 — smart caching
- Planned: align refresh intervals, backend ETag/304, per-day in-process
  cache, Redis decision.
- Actual:
  - **Frontend interval alignment** (`hooks.ts`) — daily endpoints
    (portfolio, holdings, trades, rebalance-status) moved from 60s →
    `SLOW_REFRESH` (5 min); they're once-a-day pipeline data, and live P&L
    is on the SSE-backed Positions page. `REFRESH_INTERVAL` (60s) now only
    drives market open/closed status. Cuts background polling substantially.
  - **ETag / 304 middleware** (`middleware/etag.py`, wired in `main.py`) —
    JSON GET 200s get a weak ETag; a matching `If-None-Match` returns a
    bodiless 304. Scoped to `application/json` only, so SSE streams / CSV
    downloads / errors are untouched. Placed inside SecurityHeaders so those
    headers still apply to 304s.
  - **In-process response cache** (`services/response_cache.py`) applied to
    the daily DB endpoints in `portfolio.py` (summary/holdings/allocation)
    and `metrics.py` (metrics/equity-curve/monthly-returns). TTL 120s,
    keyed by (name, universe, params) — **never by user**. Access control
    (`check_universe_access`) runs in the handler BEFORE the cache is
    consulted, so it can't serve cross-universe data; error envelopes are
    never cached.
  - **Redis (2.5): deferred.** The in-process TTL cache is sufficient at
    current (private-beta) scale. If Railway scales to >1 instance each
    keeps its own cache — acceptable, since the cached payload is
    universe-scoped and identical across instances; staleness stays bounded
    by the 120s TTL. Revisit only if a shared invalidation signal is needed.
- Commits: _pending_
- Verification: backend `pytest tests/test_clerk_authz.py
  tests/test_response_cache.py tests/test_trade_matching.py` → **292
  passed** (277 authz assertions intact + 8 new + trade matching). New
  ETag/cache behaviour covered by `tests/test_response_cache.py` (8 tests).
  `npm run build` clean.
  - Env note: the full `pytest tests/` could not run locally — only Python
    3.14 is installed here, which has no wheels for the pinned numpy/pandas;
    the `test_insights_*` suite fails to import under the newer
    numpy 2.4/pandas 3.0 stand-ins + missing PIL. Those tests exercise
    `app/insights/*`, which this phase never touched. Recommend a final
    `pytest tests/` on a Python 3.12 venv (pinned deps) in CI before merge.
- Security note for Phase 5: verify the cache key never includes user
  identity and that the access-check-before-cache ordering holds.

### Phase 3 — smooth live prices
- Planned: gate polling on market hours + visibility, kill SSE/poll
  overlap, animate value changes + as-of stamp.
- Actual:
  - `usePositions({ enablePolling })` (`hooks.ts`) — `refreshInterval` is
    now a function: `0` when streaming (no double-fetch) or when polling is
    disabled; `10s` when market open; `60s` when closed (just to catch the
    open). SWR already pauses polling while the tab is hidden, so mobile
    battery/data are covered for the polled path.
  - Positions page SSE rewrite (`positions/page.tsx`) — stream opens only
    while market is open AND tab is visible; a `visibilitychange` listener
    closes it when hidden and reopens on return; reconnect after transport
    errors via a nonce-driven effect re-run. Polling is suppressed while the
    stream is healthy (`enablePolling: !isStreaming`).
  - `FlashOnChange` (`components/ui/flash-on-change.tsx`) — subtly
    highlights a value's *background* (composes with P&L red/green) for
    500ms when it changes, so live updates read as smooth. Applied to the
    Positions summary cards (Current Value / Total P&L / Day P&L).
  - As-of stamp already existed in `positions-summary.tsx` ("Updated
    HH:MM:SS" + market-status banner) — left as is.
- Commits: _pending_
- Verification: `npm run build` clean (32 routes).

### Phase 4 — mobile + measurement
- Planned: network-aware polling, responsive charts, Web Vitals, Lighthouse
  baseline.
- Actual:
  - **Speed Insights** — added `@vercel/speed-insights` and `<SpeedInsights/>`
    in the root layout. Collects real-user (field) LCP/INP/CLS/TTFB on Vercel
    once deployed — more representative for an authed app than a synthetic run.
  - **Network-aware polling** (`hooks/use-network-status.ts`) — progressive
    enhancement over the Network Information API; on data-saver / 2g the
    Positions poll backs off 3× (10s→30s open, 60s→180s closed). No-op where
    the API is unsupported (Safari/iOS) — falls back to normal cadence.
  - **Responsive charts** (`hooks/use-is-mobile.ts`) — equity-curve height
    400→280 and drawdown 250→180 on phones. Charts were already
    responsive-width + lazy-loaded (Phase 1).
  - **Lighthouse baseline: not captured locally.** A meaningful run needs the
    deployed, Clerk-authed app behind a live backend; a localhost run would
    be misleading and I won't invent numbers. Recommended: run Lighthouse
    (mobile preset) against a Vercel **preview URL** signed in, before/after,
    OR rely on Speed Insights field data which is now wired up. Procedure:
    `npx lighthouse <preview-url> --preset=desktop` and `--form-factor=mobile`,
    or Chrome DevTools → Lighthouse.
- Commits: _pending_
- Verification: `npm run build` clean (32 routes); ESLint clean on all
  touched files.

### Phase 5 — security audit of the changes
_pending_

## Deferred / out of scope
- Redis distributed cache (only if >1 Railway dyno — see Phase 2.5).

## Verification log

### Local end-to-end (Playwright + live backend), 2026-06-09
Ran the real frontend (`next dev`) + real backend (`uvicorn`, `DISABLE_AUTH=false`
→ real Clerk JWKS verification) against the local Postgres (real data: 1082
holdings, 12429 trades). Authenticated the Playwright browser as the admin
user via a Clerk sign-in **ticket** (Backend API), since the dev instance is
Google-OAuth-only and can't be scripted directly.

- **Phase 0** — `/dashboard` loaded with NO "session expired"/"token expired"
  toast. First `/api/portfolio` + `/api/portfolio/holdings` returned **200**
  (zero 401s) and carried `Authorization: Bearer <Clerk JWT>` — proving the
  token was attached before the request fired. Backend confirmed it 401s a
  tokenless request, so 200 means the gating worked.
- **Phase 1** — after navigating away from `/dashboard`, localStorage held the
  persisted SWR cache `mw-swr-cache:v1:user_<id>` with 2 real entries
  (portfolio + holdings, 5.2KB) → instant render on return. Cache is
  **namespaced by Clerk user id** (multi-user safe).
- **Phase 2** — real responses carried `Cache-Control: private, max-age=3600,
  stale-while-revalidate=86400` + `ETag`, with security headers intact.
  End-to-end conditional request: matching `If-None-Match` → **304**, stale →
  **200**. Stable ETag across requests confirms the in-process cache.
- **Phase 3** — `/positions` (market open) showed **SSE "Live"** connected,
  "Live prices from Zerodha", an advancing "Updated HH:MM:SS" stamp, **4
  `animate-value-flash` elements** mounted, 24 positions, no error banner.
- **Phase 4** — equity-curve chart height **400px @1200w → 280px @390w**
  (responsive); chart is a lazy Recharts chunk. Speed Insights is wired in the
  root layout. Note: in dev the SDK loads its debug script from
  `va.vercel-scripts.com` which the CSP blocks (console error) — but in
  production `@vercel/speed-insights` serves same-origin
  (`/_vercel/speed-insights/script.js`), covered by `script-src 'self'`, so
  **no CSP change is needed for prod**. Verified via the package source.

Non-issues observed locally: a Radix `aria-controls` hydration warning in the
Navbar (pre-existing, unrelated) and `429` on the SSE stream (rate-limit
exhaustion from the test run's own request volume on `127.0.0.1`, not a
product defect). No regression attributable to Phases 0-4.

### Backend unit tests
`pytest test_clerk_authz.py test_response_cache.py test_trade_matching.py`
→ **292 passed** (277 authz assertions intact + 8 new + trade matching).
Full `pytest tests/` not runnable on this Python 3.14 box (no pinned
numpy/pandas wheels); insights suite import-blocked — unrelated to this work.
