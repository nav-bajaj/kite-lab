# site_gate — results

**Shipped 2026-08-26.** Merge commit `5ab23cf` on `beta_gtm_mvp`
(9 commits + `--no-ff` merge). Vercel and Railway both deployed from it.

## What is live

marketworks.in shows only the under-development page with a launch
waitlist. Every product surface is admin-only, at two independent layers:

| Layer | Flag | Where |
|---|---|---|
| Vercel middleware | `SITE_MODE=under_development` | `kite-dashboard/src/middleware.ts`, allowlist in `src/lib/site-mode.ts` |
| kite-api | `PRIVATE_MODE=true` | `_enforce_private_mode` in `app/auth.py`; `require_admin_when_private` on the insights/indices routers |

Both env vars were set **before** the push, so the first deployed build
was already gated. Railway's var was set with `--skip-deploys` so it
applied on the same rebuild the push triggered (one restart, not two).

Note: `railway` CLI was linked to service `confident-upliftment` (the
options worker, branch `options_data_v1`). The API is service `kite-lab`.
Always pass `--service kite-lab`.

## Production verification (all passed, 2026-08-26 ~15:50 IST)

**Gate** — 307 → `/` for: `/portfolios`, `/library`, `/library/<slug>`,
`/insights`, `/dashboard`, `/positions`, `/performance`, `/trades`,
`/account`, `/admin`, `/sign-up`, `/rebalance`. A nonexistent path
returns the identical 307, so no route's existence leaks.

**Open** — 200 for `/`, `/terms`, `/privacy`, `/disclaimer`, `/sign-in`,
`/robots.txt`.

**Deindexing** — `robots.txt` serves `Allow: /` (deliberately crawlable)
and every page serves `X-Robots-Tag: noindex, nofollow`, so crawlers
revisit the already-indexed `/library` and `/portfolios` URLs and drop
them. A blanket `Disallow: /` would have frozen those entries in the
index instead — this was a security-review finding.

**Private mode (anonymous)** — 401 on `/api/insights/reading`,
`/api/indices/returns`, `/api/portfolio?universe=l6_v2`,
`GET /api/waitlist`. Still open: `/api/health`,
`/api/positions/market-status`.

**Waitlist** — new email 200 + row written (migration `0006_waitlist`
ran on deploy); duplicate 200 with an identical body (no enumeration
oracle); invalid email 422; unknown source 422; honeypot 200 with no
write.

**Leak scan** — served HTML of `/` and `/terms` contains no links to any
gated route, no `SITE_MODE` string, and not the false "SEBI Registered
Research Analyst" line.

**Admin path** — founder confirmed sign-in at `/sign-in` (unlinked, direct
URL only) and the full site rendering afterwards. Independently observed:
a signed-in admin browser gets the real landing (`h1` = "Indian markets,
the calm way") while an isolated anonymous context on the same build gets
the coming-soon page. The gate reuses the same `roleFromClaims()` helper
the pre-existing `/admin` route gate uses, so admin access could not have
been narrower than it already was.

**Light mode** (commit `f6b93fc`) — the coming-soon page renders light for
everyone. Verified on production from an anonymous context with the device
set to dark AND `html.dark` applied: white ground, `#f4f7f5` band,
computed `color-scheme: light`. Shipped CSS contains one
`color-scheme:light` and zero dark tokens. Rationale is in the file
header: the page has no theme toggle, so a dark variant would be a look
nobody chose and nobody reviewed on the brand's only public surface.

Careful with automated checks here: the string "Process over prediction."
appears on BOTH pages — it is the new gated headline and also a section
heading on the real landing page. Match on the `h1` ("Indian markets, the
calm way" = real landing) or on the absence of nav, not on that phrase.

## Unaffected by the lockdown (verified before the 16:30 pipeline)

- The in-process scheduler uses no FastAPI auth dependencies.
- `run_daily_pipeline.py` calls `clear_all_caches()` directly in-process;
  the admin HTTP cache-clear route is only referenced in a comment.
- The options worker reads the Kite token from Postgres (R-025), not via
  the web API.

## Test data left in production — REMOVE WHEN CONVENIENT

`waitlist_signups` contains one deliberate probe row inserted during
deploy verification:

    deploy.probe@marketworks.in   source=coming_soon

It is real inserted data, not a placeholder, and it is the only
non-genuine row. There is no DELETE endpoint; removing it needs a SQL
statement against the Railway Postgres. Read the list any time with an
admin token:

    curl -H "Authorization: Bearer <admin-jwt>" \
      https://kite-lab-production.up.railway.app/api/waitlist

## Known-good rollback

Reverse either layer independently, both are env-only:

- Ungate the site: remove `SITE_MODE` in Vercel → redeploy.
- Reopen the API: `railway variables --service kite-lab --set "PRIVATE_MODE=false"`.

Both flags silently default to OPEN when unset, which is why the deploy
runbook sets them before the push.

## Open items for launch

1. `footer-panel.tsx` still renders "SEBI Registered Research Analyst" in
   **live** mode. The gated chrome removes it, but this must be fixed
   before `SITE_MODE` is ever turned off.
2. Privacy policy should state waitlist email collection and
   deletion-on-request (R-027).
3. R-019 (Next.js 16.x middleware-bypass CVEs) is now load-bearing:
   `/library` and `/portfolios` are prerendered, so for those routes the
   middleware is the only layer (R-028 scope caveat). Treat the Next.js
   patch upgrade as a fast-follow.
4. Waitlist launch emails — SES is approved at the account level but not
   wired into kite-api. Separate task.
5. Check Search Console in a week or two to confirm the old `/library`
   and `/portfolios` entries have dropped out of the index.
