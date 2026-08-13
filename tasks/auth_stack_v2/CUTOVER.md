# auth_stack_v2 — Phase 4 cutover runbook

Every step below encodes a gotcha we actually hit on the scratch
project. Do them in order. Stages A–B have ZERO production impact.
Stages C–D restart live services — market-hours freeze applies
(09:00–15:30 IST: do not proceed inside that window).

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
- [ ] D3 Verify live: marketworks.in renders; /sign-in shows the new
      card + Turnstile; founder signs in with Google.
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
