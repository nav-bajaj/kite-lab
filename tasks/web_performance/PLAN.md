# web_performance — make the dashboard fast and smooth

## Why

The Marketworks dashboard (`kite-dashboard`, Next.js on Vercel) is
functionally complete but the *experience* is rough in three ways the
user called out:

1. **A false "Session expired" / "not logged in" toast on login.** It
   appears intermittently even though the user is actually signed in.
   This is the top irritant and the first thing to fix.
2. **Pages and charts feel slow to appear.** Every reload starts from a
   blank state and re-fetches everything; heavy chart code loads eagerly.
3. **Live prices should update smoothly during market hours.** A few
   seconds of latency on the latest price is explicitly acceptable — the
   goal is *visual* smoothness, not freshness, on both PC and mobile.

This initiative is **tuning + a few targeted additions**, not a rewrite.
The backend already does a lot right (Cache-Control headers, a 2s quote
cache, SSE for positions). The work is mostly on the client, plus a
small backend caching layer.

## What the outcome looks like

- No false auth toasts on a normal login. A 401 toast appears *only* on a
  genuine session expiry, and it distinguishes the Clerk login session
  from the Zerodha broker token.
- Returning users see their last portfolio / charts **instantly** (from a
  persisted client cache), which then silently revalidate.
- Initial JS is smaller; charts load lazily with skeletons that match the
  final layout (no layout shift).
- Polling runs only when it should — during market hours and while the
  tab is visible — and price changes animate smoothly.
- We can *measure* the improvement (Web Vitals: LCP, INP, TTFB) rather
  than guess.

## Scope boundary

**In scope:** `kite-dashboard` client data-fetching, caching, loading
states, bundle splitting, polling behavior; a small `kite-api` caching
layer (ETag/304 + per-trading-day in-process cache for daily endpoints).

**Out of scope:** auth *correctness* / authz model (the Clerk JWKS +
`require_admin` / `check_universe_access` invariants in CLAUDE.md are NOT
to be weakened — Phase 0 only changes *when* the client fetches, never
*whether* the backend authenticates). No CSP/CORS widening. No universe
ID renames. No new `scripts/`. No Redis unless we later confirm >1
Railway dyno (tracked as an optional Phase 2 item).

## Root cause of the login error (confirmed)

A race between Clerk session readiness and SWR data fetching:

1. SWR hooks fire on mount; their keys (e.g. `["portfolio", universeId]`)
   have **no dependency on auth readiness** — `src/lib/hooks.ts:49`.
2. The fetcher reads `globalAuthToken` — `src/lib/api-client.ts:51` — but
   that global is only set *after* Clerk loads and `getToken()` resolves
   — `src/contexts/api-auth-context.tsx:57-59`.
3. First requests therefore go out with **no `Authorization` header** →
   backend returns **401** → SWR `onError` shows
   "Session expired. Please sign in again." — `src/lib/swr-config.tsx:18-19`.

Intermittent because it's timing-dependent. The toast also conflates the
Clerk login session with the Zerodha broker token
(`kite-api/app/api/positions.py:70-74`), making it misleading even when a
real token problem exists.

## Critical files

| File | Role in this work |
|---|---|
| `kite-dashboard/src/contexts/api-auth-context.tsx` | Clerk → global-token bridge; add `authReady`, stop refresh flicker |
| `kite-dashboard/src/lib/api-client.ts` | `apiFetch`; resolve token at call time |
| `kite-dashboard/src/lib/swr-config.tsx` | SWR provider; fix 401 toast, add persisted cache provider, `keepPreviousData` |
| `kite-dashboard/src/lib/hooks.ts` | all SWR hooks; gate keys on `authReady`, align intervals, market/visibility gating |
| `kite-dashboard/src/app/(dashboard)/positions/page.tsx` | SSE + poll overlap; visibility gating |
| `kite-dashboard/next.config.ts` | bundle / headers if needed |
| `kite-api/app/middleware/cache.py` | ETag/304 + daily in-process cache |

## Verification approach

- Local: `cd kite-dashboard && npm run build` must stay clean each phase.
- Backend touched (Phase 2): `pytest tests/` and the authz suite
  `kite-api/tests/test_clerk_authz.py` must stay green.
- Manual: log in repeatedly and confirm no false toast (Phase 0); compare
  Web Vitals before/after (Phase 4).
