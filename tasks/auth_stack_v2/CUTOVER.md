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

- [ ] A0.1 Land the `email_channel` branch on `beta_gtm_mvp` first, so
      this reconciliation happens once rather than twice.
- [ ] A0.2 In a worktree, merge `beta_gtm_mvp` → `auth_stack_v2`.
- [ ] A0.3 Resolve `middleware.ts` by porting the site gate onto the
      Supabase middleware. **The gate must survive.**
- [ ] A0.4 Resolve `page.tsx` keeping the ComingSoon/LandingPage switch.
- [ ] A0.5 Keep `PRIVATE_MODE` and the waitlist table from production;
      keep the Supabase auth from this branch. `require_admin` exists
      in both, so the waitlist endpoints port unchanged.
- [ ] A0.6 Retire `test_clerk_authz.py` in favour of the Supabase authz
      suite, moving the waitlist/consent endpoint inventories across so
      no endpoint loses coverage.
- [ ] A0.7 Verify with the gate ON: anonymous sees only the
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
| B3 — SMTP smoke | **BLOCKED.** Captcha was enabled before this ran (A10 says captcha goes last precisely because it blocks curl smoke tests). |

**B3 is the one gap and it matters.** SES SMTP itself is proven — the
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

- [ ] B1 JWKS: exactly one ES256 key served.
- [ ] B2 `/auth/v1/settings`: google=true, email=true, signups open.
- [ ] B3 SMTP smoke: OTP request to founder address -> mail arrives
      (pre-captcha, so curl works). Then founder does A10; B4 re-curl
      confirms `captcha_failed` on a tokenless request.

## Stage C — environment variables (👤, OUTSIDE market hours)

Vercel -> kite-dashboard project -> Settings -> Environment Variables
(Production scope):
- [ ] `NEXT_PUBLIC_SUPABASE_URL` = `https://<prod-ref>.supabase.co`
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY` = prod anon key
- [ ] `NEXT_PUBLIC_TURNSTILE_SITE_KEY` = `0x4AAAAAAENNy-QEJvBLRJJ2`
- [ ] `NEXT_PUBLIC_SITE_URL` = `https://marketworks.in`
- Leave the Clerk vars in place (harmless; removed at C4.5).

Railway -> kite-lab service -> Variables (NOTE: saving triggers a
redeploy of the CURRENT code — old code ignores these vars, but do it
in the window anyway):
- [ ] `SUPABASE_JWKS_URL` =
      `https://<prod-ref>.supabase.co/auth/v1/.well-known/jwks.json`
- [ ] `SUPABASE_ISSUER` = `https://<prod-ref>.supabase.co/auth/v1`

## Stage D — merge, push, verify (🤖 merge + checks; 👤 approves push)

- [ ] D1 Merge `auth_stack_v2` -> `beta_gtm_mvp` with `--no-ff`.
- [ ] D2 Push (deploys BOTH services; Railway entrypoint runs
      `alembic upgrade head` -> creates the `users` table, migration
      0006, idempotent).
- [ ] D3 Verify live **with the gate still up**: marketworks.in shows
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
- [ ] D5 Client journey: second account (email OTP) sees the 4
      client portfolios, is bounced off /admin, cannot query an
      admin universe via API.
- [ ] D6 Confirm a `users` row exists for both accounts (lazy
      provisioning proof, Railway PG or via admin panel logs).

## Stage E — after cutover

- [ ] E1 (C4.4) Notify the 10 beta users: sign in fresh with Google
      or email code; sessions now last 30 days of inactivity.
- [ ] E2 Monitor launch week: SES sending stats (bounces/complaints),
      Supabase auth logs, Railway logs for `user provisioning
      skipped` warnings.
- [ ] E3 (C4.5, ~1 week soak) Cleanup commit: remove Clerk CSP
      origins + clerk_* config fields + test_clerk_authz.py + Clerk
      env vars from Vercel; register row for the CSP narrowing; THEN
      delete the Clerk application.
- [ ] E4 If Supabase Pro exposes Sessions time-box/inactivity
      settings: leave off or set >=30d (matches the cookie window).
