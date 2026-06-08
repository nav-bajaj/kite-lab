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
_pending_

### Phase 2 — smart caching
_pending_

### Phase 3 — smooth live prices
_pending_

### Phase 4 — mobile + measurement
_pending_

## Deferred / out of scope
- Redis distributed cache (only if >1 Railway dyno — see Phase 2.5).

## Verification log
- _pending_
