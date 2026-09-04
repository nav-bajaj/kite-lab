# auth_stack_v2 — Phase 4 cutover runbook

Every step below encodes a gotcha we actually hit on the scratch
project. Do them in order. Stages A–B have ZERO production impact.
Stages C–D restart live services — market-hours freeze applies
(09:00–15:30 IST: do not proceed inside that window; also avoid
15:55–17:30 IST, which is the EOD proposal + daily pipeline window).

---

## ⚠ READ FIRST — this runbook predates the site gate

Written 2026-08-13. Since then `site_gate` shipped (2026-08-26) and
marketworks.in is **gated**: the public sees only the under-development
page, and everything else is admin-only pending SEBI registration.

**`auth_stack_v2`'s middleware does NOT contain the gate.** Verified
2026-08-27 — zero references to `siteMode` / `PUBLIC_WHEN_GATED`. A
merge that resolves `middleware.ts` in favour of this branch **silently
un-gates the entire site**, publishing the whole product while the RA
application is pending. That is the worst available outcome of this
cutover and it is a one-line mistake.

Nine files conflict between the branches:

    kite-dashboard/src/middleware.ts          ← carries the gate
    kite-dashboard/src/app/page.tsx           ← carries the gate
    kite-dashboard/next.config.ts             ← X-Robots-Tag noindex
    kite-api/app/auth.py                      ← PRIVATE_MODE lockdown
    kite-api/app/config.py                    ← both flags
    kite-api/app/models/models.py             ← waitlist table
    kite-api/tests/test_clerk_authz.py        ← replaced by supabase suite
    kite-dashboard/src/app/(legal)/privacy/page.tsx
    docs/security/risk-register.md

**Do the reconciliation BEFORE stage D**, in a worktree, as a merge of
`beta_gtm_mvp` INTO `auth_stack_v2` — not as a rushed conflict
resolution during the cutover merge itself. See Stage A0.

The port of the gate is small but must be deliberate: the Supabase
middleware needs the same first-block gate the Clerk one has, reading
the role from `app_metadata.role` via `getClaims()` instead of Clerk's
`sessionClaims.metadata.role`. Everything else about the gate —
`site-mode.ts`, the coming-soon page, `robots.ts`, the consent pages —
is auth-agnostic and ports unchanged.

## Stage A0 — reconcile the branches (🤖, BEFORE anything else)

- [x] A0.1 Land the `email_channel` branch on `beta_gtm_mvp` first, so
      this reconciliation happens once rather than twice.
- [x] A0.2 In a worktree, merge `beta_gtm_mvp` → `auth_stack_v2`.
- [x] A0.3 Resolve `middleware.ts` by porting the site gate onto the
      Supabase middleware. **The gate must survive.**
- [x] A0.4 Resolve `page.tsx` keeping the ComingSoon/LandingPage switch.
- [x] A0.5 Keep `PRIVATE_MODE` and the waitlist table from production;
      keep the Supabase auth from this branch. `require_admin` exists
      in both, so the waitlist endpoints port unchanged.
- [x] A0.6 Retire `test_clerk_authz.py` in favour of the Supabase authz
      suite, moving the waitlist/consent endpoint inventories across so
      no endpoint loses coverage.
- [x] A0.7 Verify with the gate ON: anonymous sees only the
      under-development page; admin sees the full site; the API refuses
      non-admin tokens. Then `pytest` + `npm run build` clean.

## Stage A — build the production Supabase project (👤, anytime)

- [ ] A1 Create the project. Org: yours. Region: **ap-south-1
      (Mumbai)** — closest to users; the scratch default was Stockholm
      only by accident. Plan: **Pro** (free tier pauses on inactivity;
      unacceptable for prod auth).
- [ ] A2 **JWT signing keys FIRST** (everything depends on it):
      Project Settings -> JWT Keys -> migrate -> create **ES256** key
      -> promote. (New projects still sign HS256 until this is done —
      the backend refuses HS256 by design.) Then hand me the project
      REF; I verify the JWKS serves an ES256 key before you continue.
- [ ] A3 Auth -> URL Configuration: Site URL `https://marketworks.in`;
      Redirect URLs: add `https://marketworks.in/**` and
      `https://www.marketworks.in/**`. (Do NOT add localhost — local
      dev keeps using the scratch project.)
- [ ] A4 Google provider: create a NEW OAuth client in Google Cloud
      Console (Web application, name `marketworks-prod-supabase`) with
      Authorized redirect URI
      `https://<prod-ref>.supabase.co/auth/v1/callback`; paste client
      ID + secret into Supabase -> Auth -> Providers -> Google.
      (Don't reuse the Clerk production client or the scratch client.)
- [ ] A5 Email provider: ENABLE (it ships enabled but VERIFY — on the
      scratch project it silently flipped off once). OTP expiry
      **600**, OTP length 6.
- [ ] A6 SMTP (Auth -> SMTP settings): host
      `email-smtp.eu-north-1.amazonaws.com`, port `587`, the same SES
      SMTP credential pair you saved (they're account-wide, not
      per-project). Sender: **`login@marketworks.in`**, name
      `Marketworks` — the domain is verified so any @marketworks.in
      sender works now; keep navdeep@ for your personal mail.
- [ ] A7 Email template (Auth -> Email Templates -> Magic Link):
      Subject: `Your Marketworks sign-in code`
      Body: `Your Marketworks sign-in code is {{ .Token }}. It expires
      in 10 minutes. If you didn't request this code, you can safely
      ignore this email.`
- [ ] A8 Rate limits: mirror what you set on scratch (send cooldown
      >=60s, review the per-IP limits page).
- [ ] A9 Tell me the **project ref + anon key** -> I run Stage B.
- [ ] A10 AFTER Stage B's SMTP smoke passes: enable **captcha**
      (provider turnstile, the SAME Turnstile secret — the site
      already covers marketworks.in). Captcha goes LAST because it
      blocks curl-based smoke tests.

## Stage A/B verification log — 2026-09-03

Production project ref: `jhvkfokskanbaiipvcqu`

| Check | Result |
|---|---|
| A2 / B1 — JWKS serves ES256 | **PASS.** Exactly one key, `alg=ES256`, `kty=EC`, `crv=P-256`. |
| anon key sanity | PASS. `role=anon`, ref matches, expires 2035. HS256 on the anon key is expected — it is a static project key, not a user session token; the ES256 requirement applies to session tokens, which is what the backend verifies. |
| B2 — auth settings | **PASS.** google=true, email=true, signups open, `mailer_autoconfirm=false` (OTP genuinely required). phone=false, correct — SMS is Phase 5. |
| B4 — captcha active | **PASS**, but early. A tokenless OTP request returns `captcha_failed`. |
| B3 — SMTP smoke | **PASS** (2026-09-03). Captcha toggled off briefly; OTP request returned 200 in 4s and the code arrived in the founder's inbox, correctly rendered. Captcha re-enabled after. The 4s round trip is consistent with a real connect/STARTTLS/auth/send — a bad credential fails fast, a bad host hangs. |

**Stage B is COMPLETE.** All four checks pass; the branded sign-in
template is pasted and verified in a real inbox. Remaining blockers are
Stage C (env vars) and Stage A0 (the site-gate reconciliation).

*Historical note on why B3 mattered:* SES SMTP itself is proven — the
email_channel welcome mail sends through those same credentials. What is
NOT proven is the SMTP block entered into the Supabase dashboard, which
is a separate copy of host/port/user/password. A typo there means nobody
can sign in, and without B3 we would not discover that until the cutover.

Two ways to close it:
- Toggle captcha off in Supabase for ~2 minutes, ask for a re-run, toggle
  back on. Preferred: it isolates SMTP before the cutover.
- Or accept the risk and let D3 (founder signs in through the browser,
  which supplies a captcha token) be the first real test.

**Sender address:** A6 specifies `login@marketworks.in`, which does not
exist as a mailbox. Use **`mail@marketworks.in`** — it is real, monitored,
and already confirmed receiving. Do not use a noreply address: a reply to
a sign-in email should reach a human.

## Stage B — remote verification (🤖, after A9)

- [x] B1 JWKS: exactly one ES256 key served.
- [x] B2 `/auth/v1/settings`: google=true, email=true, signups open.
- [x] B3 SMTP smoke: OTP request to founder address -> mail arrives
      (pre-captcha, so curl works). Then founder does A10; B4 re-curl
      confirms `captcha_failed` on a tokenless request.

## Stage C — environment variables (👤, OUTSIDE market hours)

Vercel -> kite-dashboard project -> Settings -> Environment Variables
(Production scope):
- [x] `NEXT_PUBLIC_SUPABASE_URL` = `https://<prod-ref>.supabase.co`
- [x] `NEXT_PUBLIC_SUPABASE_ANON_KEY` = prod anon key
- [x] `NEXT_PUBLIC_TURNSTILE_SITE_KEY` = `0x4AAAAAAENNy-QEJvBLRJJ2`
- [x] `NEXT_PUBLIC_SITE_URL` = `https://marketworks.in`
- Leave the Clerk vars in place (harmless; removed at C4.5).

Railway -> kite-lab service -> Variables (NOTE: saving triggers a
redeploy of the CURRENT code — old code ignores these vars, but do it
in the window anyway):
- [x] `SUPABASE_JWKS_URL` =
      `https://<prod-ref>.supabase.co/auth/v1/.well-known/jwks.json`
- [x] `SUPABASE_ISSUER` = `https://<prod-ref>.supabase.co/auth/v1`

## Stage D — merge, push, verify (🤖 merge + checks; 👤 approves push)

- [x] D1 Merge `auth_stack_v2` -> `beta_gtm_mvp` with `--no-ff`.
- [x] D2 Push (deploys BOTH services; Railway entrypoint runs
      `alembic upgrade head` -> creates the `users` table, migration
      0006, idempotent).
- [x] D3 Verify live **with the gate still up**: marketworks.in shows
      the under-development page to an anonymous visitor (NOT the
      product); `/library`, `/portfolios`, `/dashboard`, `/insights`
      all 307 to `/`; `/sign-in` shows the new card + Turnstile;
      founder signs in with Google and then sees the full site.
      If an anonymous visitor sees the product, the gate did not
      survive the merge — roll back immediately.
- [ ] D3.5 **Admin access is now load-bearing for the gate**, not just
      for `/admin`: until the founder's Supabase account carries
      `role: admin`, even the founder sees only the under-development
      page and cannot reach the product at all. Do D4 immediately, in
      the same window. (Recovery if it goes wrong: remove `SITE_MODE`
      in Vercel and redeploy — about two minutes.)
- [ ] D4 Grant founder admin (C4.2): Supabase SQL editor ->
      `update auth.users set raw_app_meta_data = raw_app_meta_data ||
      '{"role":"admin"}' where email = '<founder google email>';`
      then sign out/in (fresh token carries the claim). Verify /admin
      loads and /api/freshness responds.
- [~] D5 Client journey: second account (email OTP) sees the 4
      client portfolios, is bounced off /admin, cannot query an
      admin universe via API.
- [x] D6 Confirm a `users` row exists for both accounts (lazy
      provisioning proof, Railway PG or via admin panel logs).

## Stage D verification log — 2026-09-03

Merged `354cc37`, pushed 17:48 IST (outside the market-hours freeze and
outside the 15:55–17:30 EOD window). The A0 reconciliation meant the
merge carried no conflict resolution.

**Railway.** Migrations reached a single head on the first boot, which is
what the merge revision was for:

    Running upgrade 0005 -> 0006, Add users table
    Running upgrade 0006, 0007_waitlist_consent -> 0008_merge

`/api/health` returns `database: connected`.

**D3 — the gate survived.** This was the failure mode the runbook was
written around, so it was checked directly rather than inferred:

| Check | Result |
|---|---|
| `/` to an anonymous visitor | Coming-soon page. Zero references to any portfolio name, `/portfolios` or `/library`. |
| False "SEBI Registered" string anywhere on `/` | Absent. |
| `/portfolios` `/library` `/dashboard` `/insights` `/admin` `/account` `/sign-up` | All **307 → `/`**. |
| `/` `/terms` `/privacy` `/disclaimer` `/sign-in` `/unsubscribe` `/confirm` `/robots.txt` | All 200. |
| `/sign-in` | Serves the Supabase `SignInCard`. Supabase client in one chunk, Turnstile + Google in another, **zero Clerk strings in any of the six chunks the page loads**. |
| CSP | Carries the Supabase project origin and `challenges.cloudflare.com`. Clerk origins still present — they come out at E3. |
| `PRIVATE_MODE`, anonymous | `/api/portfolio` 401, `/api/insights/reading` 401, `/api/indices/returns` 401. |
| `/api/health` anonymous | 200, as intended. |
| `POST /api/waitlist` | 200 — the one public write still works, so the coming-soon form is not collateral damage. |

*Note on reading these checks:* the sign-in page's server HTML contains
none of the Supabase/Turnstile markers, because `SignInCard` is a client
component. Grepping the served HTML alone reads as a broken page; the
markers are in the JS chunks. Check the chunks, not the document.

**D4 is now the blocking step.** The gate reads `app_metadata.role`, and
a fresh Supabase account has no role — so the founder currently sees the
coming-soon page like everyone else. This is expected, not a fault.

## Stage D5/D6 log — 2026-09-03

**D6 — lazy provisioning PASSES.** One `users` row exists after the
founder's first sign-in:

    id 1 | sub c3bbb4c6-…(uuid) | provider=supabase
    first_seen 2026-09-03 12:38 UTC (18:08 IST) | last_seen 12:57 UTC

`provider=supabase` and a UUID `sub` rather than a Clerk `user_…` id are
the proof that the Supabase path provisioned it, not a leftover row. The
first_seen timestamp matches the founder's first sign-in exactly.

**D5 — NOT RUN.** It needs a second, client-role account, and creating
one requires the service-role key. Deferred to the founder. Until it
runs, "a client cannot query an admin universe" is verified only by the
backend test suite, not against production.

## ⚠ Production is running on the scratch Supabase project

`supabase projects list` returns exactly one project:

    ref jhvkfokskanbaiipvcqu | name "navthinks"
    region ap-southeast-1 (Singapore) | created 2025-09-15

That is the project this runbook records as production — and it is the
same ref `scripts/e2e-smoke.sh` hardcoded on 2026-08-11 as the *scratch*
project, under the comment "never point this at the production project
ref". Stage A1 (new project, ap-south-1 Mumbai, Pro plan) was never done;
the spike project was promoted in place.

Consequences, in order of severity:

1. **Plan tier: FREE, and that is a deliberate founder decision
   (2026-09-03).** A1 had specified Pro. Overruled on cost: Free covers
   50,000 MAU, and the pause rule is "a few user requests each day over
   the previous week", which daily founder sign-ins clear easily. Two
   residual exposures to keep in view, neither blocking:
   - A full week with nobody signing in pauses the project, and **resume
     is manual** — a dashboard click, not automatic. No data is lost, but
     sign-in stays down until someone notices. Relevant during travel or
     illness, not day to day.
   - **Free includes no backups at all** — no daily snapshots, no PITR.
     Immaterial today at one user; it becomes material as the waitlist
     converts. Revisit when real accounts exist.
   - Auth log retention is 1 day on Free (7 on Pro), so post-mortems on
     anything auth-related have a one-day window.
2. **`npm run test:e2e` pointed a user-mutating suite at the live auth
   store.** Fixed: the runner now refuses the production ref unless
   `ALLOW_PROD_E2E=yes-i-mean-production` is set. Note that no separate
   scratch project exists any more, so the suite has nowhere safe to run
   until one is created.
3. Region is Singapore, not Mumbai. Minor added latency on auth calls.
4. Any accounts left over from the August spike are now in the live auth
   store. Worth auditing — the app-side `users` table has only the one
   row, so nobody else has actually reached the product.

## Live auth-store audit — 2026-09-04

Six accounts exist in the production auth store. Five predate the
cutover, because production IS the promoted spike project.

| email | role | created | note |
|---|---|---|---|
| dev@navthinks.com | null | 2025-10-21 | spike, unused since creation |
| mail@navthinks.com | **admin** | 2025-10-21 | the intended founder admin |
| navdeep.bajajtravels@gmail.com | **admin** | 2026-08-10 | admin granted during the AUGUST SPIKE |
| navdeep@marketworks.in | null | 2026-08-10 | spike; correctly bounced by the gate |
| e2e-client@marketworks.test | client | 2026-08-11 | **E2E test fixture, live in production** |
| marketworks.in@gmail.com | null | 2026-09-03 | created during the cutover window |

**The finding is the mechanism, not the blast radius.** The second admin
is the founder's own account, so nothing was exposed. But it was granted
in a throwaway spike context on 2026-08-10, and promoting that project to
production silently promoted the privilege grant with it. Anything else
granted during the spike would have carried over the same way — this
audit is the only thing that would have surfaced it.

`e2e-client@marketworks.test` is the Playwright fixture. It is not
remotely usable (its domain receives no mail, and the suite drove it via
the admin API), but it should not exist in a production auth store. The
E2E runner guard added on 2026-09-03 is what stops it being recreated.

**D5 — the testable half PASSES.** An authenticated non-admin
(navdeep@marketworks.in) was bounced to the coming-soon page and never
reached the API, so it was never provisioned. That is the first proof the
gate handles an authenticated non-admin; every prior check covered only
anonymous visitors. The rest of D5 — that a client sees the 4 client
portfolios, and the check_universe_access matrix — remains UNTESTABLE
while the gate is up, because PRIVATE_MODE 403s clients before universe
access is ever evaluated. **Re-run D5 in full at ungating.**

A Clerk session was also still in use at 2026-09-04 05:36 UTC (users row
id=2, no email recorded). Expected — the legacy issuer is deliberately
retained — but that person is logged out when E3 removes Clerk.

## Stage E — after cutover

- [ ] E1 (C4.4) Notify the 10 beta users: sign in fresh with Google
      or email code; sessions now last 30 days of inactivity.
- [ ] E2 Monitor launch week: SES sending stats (bounces/complaints),
      Supabase auth logs, Railway logs for `user provisioning
      skipped` warnings.
- [x] E3 **DONE in code 2026-09-04** (brought forward: the soak existed
      only to avoid force-logging-out a live Clerk session, and the
      founder confirmed the one remaining session was disposable).
      Removed: `_decode_clerk` + dual-issuer routing in `auth.py`,
      the `clerk_*` settings, and `clerkOrigins` from all four CSP
      directives. `test_clerk_authz.py` was already gone. Register row
      **R-033** records the narrowing; R-024 marked superseded.

      *The path was NOT dead code.* `test_private_mode.py` and
      `test_waitlist.py` both authenticated with Clerk-shaped RS256
      tokens — 62 tests broke the moment the path was removed. Both
      migrated to Supabase ES256 tokens through new shared plumbing at
      `tests/supabase_token.py`, which is where that fixture should have
      lived all along. Suite back to 1041 passed / 3 pre-existing
      insights failures — no regressions.
      `test_clerk_issuer_is_no_longer_accepted` is the standing guard.

- [ ] E3.1 **FOUNDER, after this deploys:** delete `CLERK_ISSUER`,
      `CLERK_JWKS_URL`, `CLERK_SECRET_KEY` from Railway and the Clerk
      vars from Vercel, then delete the Clerk application. The code
      ignores them (`extra = "ignore"`), so nothing breaks either way —
      but `CLERK_SECRET_KEY` is a live `sk_live_` credential and stays
      live until the Clerk app is deleted.
- [ ] E4 If Supabase Pro exposes Sessions time-box/inactivity
      settings: leave off or set >=30d (matches the cookie window).
