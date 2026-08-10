# auth_stack_v2 — task list

Owners: 👤 founder (dashboards, credentials, deploys) · 🤖 agent (code,
tests, docs). Tags: [TDD] spec-test-first per PLAN.md · [SEC] touches a
security invariant · [PROD] touches live services — freeze rules apply ·
[BLOCKED] waiting on external party.

Phases 0–3 run entirely on this branch with Clerk still live. Phase 4 is
the cutover. Phase 5 lands whenever MSG91 credentials clear.

## Phase 0 — Spike: prove the three risky integrations

Exit criteria: a scratch Supabase project issues a JWT carrying a
role claim from `app_metadata`, delivered via email OTP through custom
SMTP, and a minimal FastAPI verifier accepts it via JWKS with the SI-1/
SI-2/SI-3 spec tests green.

- [x] 👤 S0.1 Create scratch Supabase project (free tier) — done
      2026-08-10, ref `jhvkfokskanbaiipvcqu`, CLI linked, anon key
      readable via `supabase projects api-keys`. OPEN sub-items:
      (a) enable Google provider (needs Google OAuth client creds);
      (b) migrate to asymmetric JWT signing keys — dashboard: Project
      Settings -> JWT Keys -> migrate, create ES256 key, promote
      (JWKS endpoint is currently EMPTY = legacy HS256 signing, which
      SI-2 forbids us to accept). [SEC:SI-2,SI-5]
- [x] 👤 S0.2 Custom SMTP done 2026-08-10 via **AWS SES eu-north-1**
      (not Resend): domain DKIM verified, Supabase SMTP wired and
      proven end-to-end (POST /auth/v1/otp -> 200 -> mail delivered).
      Template edited to `{{ .Token }}` and the email-OTP verify leg
      completed same day: code -> /auth/v1/verify -> session -> token
      passes the spike verifier (client role default). SES production
      access request submitted, review PENDING — must be granted
      before public beta. [SEC]
- [x] 🤖 S0.3 [TDD] Failing spec suite
      `kite-api/tests/test_supabase_jwt_spec.py` written 2026-08-10:
      17 tests; 6 red as intended (positive path + SI-1 role
      provenance), 10 rejection guards trivially green until the
      positive path exists, SI-10 bypass gate green. Red witnessed;
      existing Clerk harness still 291 green alongside.
      [SEC:SI-1,SI-2,SI-3,SI-10]
- [x] 🤖 S0.4 RESOLVED 2026-08-10: real tokens carry `app_metadata`
      natively — Custom Access Token Hook NOT needed. Role read from
      `app_metadata.role`; admin path proven (admin API set ->
      refreshed token carries the claim -> extracted as admin).
      [SEC:SI-1]
- [x] 🤖 S0.5 Spike verifier (`spike/verify_spike_token.py`) verifies
      real tokens against the LIVE JWKS with the pinned rules; the
      production implementation lands at B1.3 (spec suite stays red
      until then, by design).
- [x] 🤖 S0.6 Google-SSO leg done via `spike/serve_spike.py` (real
      OAuth round-trip -> token captured -> verified, client AND admin
      roles). Email-OTP leg deferred to S0.2 completion (SMTP +
      template + re-enable email provider, which flipped off during
      dashboard work).
- [x] 🤖 S0.7 Running log live in RESULTS.md. Signing alg observed and
      pinned: ES256, kid `ec789fc4-...`. [SEC:SI-2]

## Phase 1 — Backend migration (TDD)

- [ ] 🤖 B1.1 Re-verify the 08-09 code map against THIS branch (auth.py,
      middleware, api-auth-context, CSP block) — the map was read from
      `options_data_v1`; adjust plan details if beta_gtm_mvp diverges.
- [ ] 🤖 B1.2 [TDD] Port `test_clerk_authz.py` ->
      `test_supabase_authz.py` preserving every assertion's semantics
      (RSA-keypair fixture -> project-key fixture, issuer/JWKS
      monkeypatch, parametrized ADMIN_ENDPOINTS + universe inventories),
      plus the S0.3 cases and SI-10 prod-config case. Witness red
      against unmodified auth.py. [SEC:SI-4]
- [ ] 🤖 B1.3 Rewrite `kite-api/app/auth.py`: Supabase JWKS URL +
      pinned issuer from config; `aud="authenticated"` enforced; role
      from hook claim (default `client`); keep the
      `{sub, role, metadata, claims, source}` return shape so all 37
      route gates are untouched; JWKS cache + stale-on-failure + forced
      refresh on kid miss preserved. [SEC:SI-2,SI-3]
- [ ] 🤖 B1.4 `config.py`: add `supabase_jwks_url`, `supabase_issuer`;
      mark `clerk_*` deprecated (removed in Phase 4); update
      `kite-api/.env` locally.
- [ ] 🤖 B1.5 [TDD] `validate_token_string` (SSE `?token=`) under the
      new verifier — same spec cases as Bearer path. [SEC:SI-8]
- [ ] 🤖 B1.6 [TDD] Dev bypass: spec test proving prod-shaped config
      (DEBUG=false) returns 401 regardless of DISABLE_AUTH. [SEC:SI-10]
- [ ] 🤖 B1.7 [TDD] Lazy user provisioning: `users` table in Railway PG
      (follow the existing kite-api schema-management pattern — confirm
      how migrations are done first), idempotent upsert keyed by `sub`
      on first authenticated request; spec tests: created once, updated
      not duplicated on repeat, minimal fields only. [SEC:SI-9]
- [ ] 🤖 B1.8 Full `pytest tests/` green; assertion count of the new
      harness >= 277 baseline; note the count in RESULTS.md. [SEC:SI-4]

## Phase 2 — Frontend migration

- [ ] 🤖 F2.1 Add `@supabase/supabase-js` + `@supabase/ssr`; client
      factories (browser/server); env `NEXT_PUBLIC_SUPABASE_URL`,
      `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- [ ] 🤖 F2.2 Replace `clerkMiddleware` in `src/middleware.ts`:
      cookie/session refresh per @supabase/ssr, same public-route list,
      admin gate + insights tri-state read from VERIFIED claims (no
      unverified session reads server-side). [SEC]
- [ ] 🤖 F2.3 Rebuild `/sign-in`: brand shell retained; Google SSO
      button + email-OTP two-step (send code -> enter code). Sign-up
      collapses into the same passwordless flow; delete `/sign-up` route
      (redirect to `/sign-in`).
- [ ] 🤖 F2.4 Rebuild `/account`: minimal panel (email, linked Google,
      sign out) replacing `<UserProfile/>`.
- [ ] 🤖 F2.5 Rewire `api-auth-context.tsx`: token provider returns
      `session.access_token`; refresh via `onAuthStateChange` +
      `autoRefreshToken` instead of the 50s Clerk poll; `authReady`
      semantics preserved so `useAuthedSWR` still blocks pre-token
      fetches.
- [ ] 🤖 F2.6 Replace `UserButton`/`useUser` surfaces (navbar, sidebar,
      mobile-sidebar, universe-context): role from session claims, same
      cosmetic-only gating (backend remains the real gate).
- [ ] 🤖 F2.7 SWR localStorage cache namespaced by new user id; purge on
      sign-out unchanged.
- [ ] 🤖 F2.8 CSP in `next.config.ts`: add `https://<ref>.supabase.co`
      to connect-src (Clerk origins stay until Phase 4). Draft the
      risk-register row BEFORE the config change lands. [SEC:SI-6]
- [ ] 🤖 F2.9 `npm run build` clean with `@clerk/nextjs` still installed
      but unreferenced (dependency removal happens at Phase 4 cutover so
      the branch stays revertible).

## Phase 3 — Public-beta hardening + review

- [ ] 👤 H3.1 Turnstile site/secret keys for Supabase captcha.
- [ ] 🤖 H3.2 Enable captcha on auth endpoints + wire the widget into
      the sign-in UI (challenges.cloudflare.com already in CSP).
      [SEC:SI-7]
- [ ] 👤 H3.3 Configure Supabase auth rate limits + OTP expiry (<=10
      min) + sends-per-hour caps in the dashboard; 🤖 record chosen
      values in RESULTS.md. [SEC:SI-7]
- [ ] 🤖 H3.4 Rewrite `docs/security/auth-flows.md` +
      `docs/security/threat-model.md` for the Supabase flow (both still
      describe retired NextAuth); fix `kite-dashboard/.env.example`.
- [ ] 🤖 H3.5 Risk-register rows: CSP widening, open sign-up posture
      change (allowlist retirement), SSE residual re-noted. [SEC:SI-6]
- [ ] 🤖 H3.6 Run `security-reviewer` subagent on the full branch diff;
      then `/security-review`. Address findings before Phase 4.
- [ ] 🤖 H3.7 Playwright E2E smoke: email-OTP login end-to-end (scratch
      project + SMTP test inbox), Google login, admin route granted for
      admin / redirected for client, client denied an admin-only
      universe via API. Must pass before cutover.
- [ ] 🤖 H3.8 Full verification pass: `pytest tests/` + `npm run build`
      + harness-count check. Log in RESULTS.md.

## Phase 4 — Cutover [PROD] (user-driven, outside market hours)

- [ ] 👤 C4.1 Create the PRODUCTION Supabase project (separate from
      scratch): Google OAuth redirect URIs, production SMTP domain
      (auth mail from marketworks.in, SPF/DKIM), template, hook, captcha,
      rate limits replicated. 🤖 provide a config checklist from the
      scratch project.
- [ ] 👤 C4.2 Set `app_metadata.role = admin` for the admin accounts;
      leave everyone else defaulting to client. [SEC:SI-1]
- [ ] 👤 C4.3 Env swap: Vercel (NEXT_PUBLIC_SUPABASE_*) + Railway
      (SUPABASE_JWKS_URL, SUPABASE_ISSUER). Merge branch ->
      `beta_gtm_mvp` and deploy OUTSIDE market hours per freeze rules.
      Verify `/api/auth/me` + one admin + one client journey live.
- [ ] 👤 C4.4 Notify the 10 beta users to sign in fresh (Google or email
      OTP); confirm roles and universe visibility.
- [ ] 🤖 C4.5 Post-cutover cleanup commit: remove `@clerk/nextjs`,
      Clerk CSP origins, `clerk_*` config fields, Clerk env vars from
      `.env.example`; retire `test_clerk_authz.py` (superseded by the
      ported harness). [SEC:SI-6 register row for CSP narrowing]
- [ ] 👤 C4.6 Soak ~1 week -> delete the Clerk application; 🤖 write
      RESULTS.md close-out; flip `_meta.yml` to shipped.

## Phase 5 — WhatsApp/SMS OTP via MSG91 [BLOCKED: credentials]

Start the paperwork NOW (multi-week external latency), build when it
clears.

- [ ] 👤 W5.1 MSG91 account + KYC; WhatsApp Business Account via Meta
      Business Manager; authentication-category template approval; DLT
      registration for SMS fallback. [BLOCKED]
- [ ] 🤖 W5.2 [TDD] Send-SMS hook receiver: verify the hook secret,
      relay `{phone, otp}` to MSG91 WhatsApp API with SMS fallback per
      MSG91 routing; spec tests for signature rejection + payload
      shape before implementation; decide hosting (FastAPI route vs
      edge function) at build time. [SEC]
- [ ] 👤 W5.3 Enable phone provider + attach hook + per-phone rate
      limits (every send costs money) + captcha on send. [SEC:SI-7]
- [ ] 🤖 W5.4 Sign-in UI: phone tab (E.164 +91 entry -> code entry);
      Playwright smoke with a test number.
- [ ] 🤖 W5.5 `security-reviewer` pass on the phone-auth diff +
      register row for the MSG91 egress. [SEC:SI-6]

## Follow-on (separate initiative — NOT this folder)

`entitlements_v1`: entitlements/subscriptions tables in Railway PG,
`require_entitlement()` FastAPI dependency, Razorpay Subscriptions +
webhook receiver (idempotent, signature-verified), renewal/expiry date
handling, course product rows. Depends on B1.7 (users table).
