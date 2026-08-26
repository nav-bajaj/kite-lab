# site_gate — site-wide "under development" gate + launch waitlist

## Why

The SEBI Research Analyst registration application is pending. Until it is
approved, marketworks.in must show only an under-development home page with
a waitlist email form. Everything else — portfolios, dashboard, insights,
library, sign-up — must be invisible to everyone, including existing beta
users and especially a visiting regulator. Only the founder (admin role)
sees the full site after signing in.

Branch: `site_gate`, cut from `beta_gtm_mvp` (the real production branch
for both Vercel and Railway — NOT `main`; ship-feature.md's "merge to main"
is stale on this point, and NOT `insights_dashboard_v2`, whose Supabase
auth stack has not been cut over).

## Design

Two independent layers (see risk register R-027/R-028):

1. **Frontend gate** — `kite-dashboard/src/lib/site-mode.ts` defines
   `siteMode()` (server-side env `SITE_MODE`, default `live`) and
   `PUBLIC_WHEN_GATED` (the allowlist: `/`, legal pages, `/sign-in(.*)`).
   `src/middleware.ts` runs the gate as its first block: non-admin sessions
   on any other route get a redirect (not rewrite) to `/`, so no route's
   existence is revealed. `src/app/page.tsx` is a thin switch: gated
   non-admin visitors get `<ComingSoon/>` (wordmark, placeholder copy,
   waitlist form, legal-only footer — no nav, no sign-in link, no SEBI
   claim); admins and live mode get the untouched real landing, extracted
   verbatim to `src/components/marketing/landing-page.tsx`.
2. **Backend lockdown** — kite-api env `PRIVATE_MODE=true`:
   `_enforce_private_mode` in `app/auth.py` 403s every non-admin token in
   `get_current_user` AND `validate_token_string` (the SSE query-param
   path); `require_admin_when_private` is attached at mount time to the
   normally-public insights/indices routers. Health, `/api/system/*`
   bootstrap, market-status, and `POST /api/waitlist` stay open.

Waitlist: `waitlist_signups` table (migration `0006_waitlist` — id chosen
to avoid colliding with `insights_dashboard_v2`'s `0006`; convergence is a
standard two-head `alembic merge`), public rate-limited
`POST /api/waitlist`, admin-only `GET /api/waitlist`. Storage only — no
email sending (SES wiring is a later task).

## Static-bake caveat

Legal-page chrome and `robots.ts` evaluate `SITE_MODE` at build time.
That is safe on Vercel only because an env-var change requires a redeploy
(rebuild) anyway. Do not flip `SITE_MODE` anywhere without redeploying.
`/` itself stays fully dynamic (unconditional `auth()` per request).

## Modularity notes (for later)

- **Open /library while still gated:** add `"/library(.*)"` to
  `PUBLIC_WHEN_GATED` in `src/lib/site-mode.ts` and optionally a Library
  link in `GatedFooter`. One line + redeploy.
- **Beta subdomain:** second Vercel project on the same repo/branch with
  `SITE_MODE=live` and `CLERK_AUTHORIZED_PARTIES=https://beta.marketworks.in`
  (middleware already merges that env var). Conflict to resolve then: the
  shared Railway backend runs `PRIVATE_MODE=true`, which blocks the very
  beta users the subdomain would serve — either flip it off (public site
  stays gated by SITE_MODE) or evolve `_enforce_private_mode` into an
  origin-aware allowlist.
- **Supabase-branch port:** only two files are auth-stack-specific — the
  middleware gate block (swap Clerk `auth()`/`roleFromClaims` for the
  Supabase claims read) and the `_enforce_private_mode` call sites in
  whatever `auth.py` becomes. `site-mode.ts`, the coming-soon components,
  `robots.ts`, the waitlist router/model/migration, and
  `test_private_mode.py` port unchanged.

## Launch-day reversal

Vercel: remove/blank `SITE_MODE`. Railway: `PRIVATE_MODE=false`. Redeploy
both. Also fix before launch: `footer-panel.tsx`'s "SEBI Registered
Research Analyst" line (false until registration is granted — the gated
chrome removes it, but live mode still renders it).
