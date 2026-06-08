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
_pending_

### Phase 3 — smooth live prices
_pending_

### Phase 4 — mobile + measurement
_pending_

### Phase 5 — security audit of the changes
_pending_

## Deferred / out of scope
- Redis distributed cache (only if >1 Railway dyno — see Phase 2.5).

## Verification log
- _pending_
