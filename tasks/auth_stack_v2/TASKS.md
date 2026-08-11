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

- [x] 🤖 B1.1 Map re-verified on this branch 2026-08-10: matches, plus
      two `options_worker.py` admin endpoints (merged via options
      program) now in the inventories.
- [x] 🤖 B1.2 [TDD] Harness ported (`test_supabase_authz.py`, 294
      tests): same inventories/semantics, ES256 Supabase-shaped tokens,
      plus cross-issuer confusion cases and endpoint-level SI-1
      user_metadata spoof. Red witnessed: 241 failed pre-rewrite.
      [SEC:SI-4]
- [x] 🤖 B1.3 `auth.py` rewritten as an ISSUER-ROUTED dual verifier
      (design delta from plan, so Clerk stays green until C4.5):
      unverified `iss` routes to Supabase path (ES256,
      aud=authenticated required, `app_metadata.role`) or Clerk path
      (RS256, no aud, `metadata.role`); unknown issuer 401; per-URL
      JWKS caches with stale-on-failure + kid-miss refresh; return
      shape `{sub, role, metadata, claims, source}` preserved — zero
      route-layer changes. TDD catch: python-jose skips aud validation
      when the claim is absent -> `require_aud` enforced (the spec
      suite's missing-aud test caught it live). [SEC:SI-2,SI-3]
- [x] 🤖 B1.4 `config.py` + local `kite-api/.env` updated (scratch
      project JWKS/issuer; swap at C4.3).
- [x] 🤖 B1.5 [TDD] `validate_token_string` covered by the spec suite
      (all decode cases + `supabase_query_param` source label).
      [SEC:SI-8]
- [x] 🤖 B1.6 [TDD] Dev-bypass double-gate spec green. [SEC:SI-10]
- [x] 🤖 B1.7 [TDD] Lazy provisioning done: `User` model (sub unique,
      email, provider, first/last_seen — minimal per SI-9),
      `services/user_service.py` upsert hooked into get_current_user +
      validate_token_string. FAIL-OPEN (DB trouble never 401s; the
      future entitlements dependency is the fail-closed reader), 15-min
      seen-cache keeps the hot path write-free, IntegrityError race
      resolved to the surviving row, dev-bypass skipped. 8 spec tests,
      red witnessed (ImportError) first. NOTE for C4.3: schema is
      create_all-managed and NOT run at app startup — create the
      `users` table on Railway PG during cutover (init_db is
      idempotent). [SEC:SI-9]
- [x] 🤖 B1.8 Full `pytest tests/`: 1173 passed, 1 skipped. New auth
      coverage: 294 (harness) + 18 (JWT spec) + 8 (provisioning) = 320
      tests vs 291 baseline; Clerk harness intact alongside. [SEC:SI-4]

## Phase 2 — Frontend migration

- [x] 🤖 F2.1 Done 2026-08-10: `@supabase/supabase-js` 2.112 +
      `@supabase/ssr` 0.12; browser/server client factories
      (`src/lib/supabase/`); NEW `SupabaseAuthProvider`
      (`contexts/supabase-auth-context.tsx`) — single onAuthStateChange
      subscription, exposes {session,user,isLoaded,isSignedIn,userId,
      role,signOut}, sits OUTERMOST in providers.tsx; env in .env.local.
- [x] 🤖 F2.2 Middleware replaced: @supabase/ssr cookie refresh,
      `getClaims()` (LOCAL ES256 JWKS verification, no per-request
      network), same public routes + `/auth/callback`, insights
      tri-state + admin gate semantics preserved, refreshed cookies
      carried onto redirects. azp/authorizedParties has no Supabase
      equivalent — replaced by backend require_aud + issuer pin
      (noted in R-027). [SEC]
- [x] 🤖 F2.3 `/sign-in` rebuilt: brand shell + FlowGrid retained,
      `SignInCard` (Google SSO via PKCE -> /auth/callback route
      handler; email-OTP two-step with single one-time-code-autofill
      input, resend cooldown, error states), tokens-only styling so all
      six palettes work. DEVIATION from plan: `/sign-up` kept as a page
      (same card, beta copy) instead of a redirect — preserves the
      marketing "Get beta access" CTA; same flow either way.
- [x] 🤖 F2.4 `/account` rebuilt: identity summary, provider badges,
      admin badge, sign out.
- [x] 🤖 F2.5 `api-auth-context` rewired: session-driven token slots
      (no 50s poll; onAuthStateChange covers TOKEN_REFRESHED), async
      provider does getSession() at fetch time, `globalAuthToken`
      eagerly repopulated on every session change (the synchronous SSE
      URL builders read it), `authReady` tri-condition preserved.
- [x] 🤖 F2.6 All Clerk hook surfaces replaced: navbar + sidebar role
      reads, NEW `UserMenu` (avatar dropdown: account/sign-out —
      replaces UserButton in navbar + floating-nav), universe-context,
      palette-sync/picker (palette roams via `user_metadata` — the one
      legitimate user_metadata use, validated on read), landing page
      server-side read via getClaims. bottom-nav had no auth usage.
- [x] 🤖 F2.7 SWR cache prefix bumped v1->v2 (retires Clerk-keyed
      blobs); userId/isLoaded now from SupabaseAuthProvider; purge
      still gated on isLoaded.
- [x] 🤖 F2.8 CSP: `supabaseOrigin` (exact origin from
      NEXT_PUBLIC_SUPABASE_URL) added to connect-src only; register row
      R-027 added in the same commit (Clerk origins stay until C4.5,
      which then NARROWS the CSP). [SEC:SI-6]
- [x] 🤖 F2.9 `npm run build` clean; zero `@clerk` references left in
      src/ (grep-verified); `@clerk/nextjs` dependency retained for
      revertibility until C4.5. `clerk-appearance.ts` deleted. Visual
      evidence: `evidence/signin-{mint,ocean,midnight,code-step}.png`
      — sign-in card verified across palettes; real OTP sent through
      the new UI. Pending founder sign-off on the visual direction.
- [ ] 🤖 F2.10 (new) Privacy page (`(legal)/privacy/page.tsx`) still
      names Clerk as the auth subprocessor — legally must be updated to
      Supabase + AWS SES. Fold into H3.4 docs pass.

## Phase 3 — Public-beta hardening + review

- [x] 👤 H3.1 DONE 2026-08-11: Turnstile site created, captcha enabled
      in Supabase (provider turnstile). ENFORCEMENT VERIFIED: raw POST
      to /auth/v1/otp without a token -> 400 `captcha_failed`; /verify
      leg unaffected (E2E still 4/4); widget renders + auto-solves in
      managed mode (site key in .env.local; add to Vercel at C4.3).
      Polish note: widget theme follows OS scheme, not our palette —
      pass isDarkTheme to the theme prop in the copy/visual round.
      [SEC:SI-7]
- [x] 🤖 H3.2 Widget wired 2026-08-11 (`components/auth/turnstile.tsx`,
      env-gated on NEXT_PUBLIC_TURNSTILE_SITE_KEY; captchaToken passed
      to signInWithOtp). ENFORCEMENT lands only when 👤 enables captcha
      in Supabase Auth settings (provider turnstile + secret).
      Verification once enabled: unauthenticated curl to /auth/v1/otp
      must return captcha-required, not 200. [SEC:SI-7]
- [ ] 👤 H3.3 Configure Supabase auth settings in the dashboard: OTP
      expiry 600s (Auth -> Providers -> Email), per-address send
      cooldown >=60s, review rate limits (email/hr, sign-in+sign-up
      per-IP, verifications per-IP). 🤖 record chosen values in
      RESULTS.md, then flip R-028 to Mitigating. NOTE: config-as-code
      via `supabase config push` was evaluated and REJECTED (would
      clobber dashboard-held SMTP/Google secrets; stock config.toml
      deleted from repo per security-reviewer #5 — dashboard is the
      source of truth; CLI ops use --project-ref). [SEC:SI-7]
- [x] 🤖 H3.4 Done 2026-08-11: auth-flows.md §1 rewritten (Supabase
      flow + SI invariants + enforcement list), threat-model assets
      A3/A4/A6 + TB2/TB3 updated, .env.example rewritten, privacy page
      subprocessors Clerk->Supabase+SES+Cloudflare and delete-account
      copy made truthful (email request — F2.10 closed),
      attack-surface.md insights row updated.
- [x] 🤖 H3.5 Register rows: R-027 (CSP), R-028 (open sign-up, held at
      Open), R-029 (JS-readable session cookies — from review finding
      #1), R-005 amended + re-accepted at the 3600s TTL. [SEC:SI-6]
- [x] 🤖 H3.6 security-reviewer verdict 2026-08-11: REQUEST-CHANGES —
      1 HIGH (threat model claimed HttpOnly cookies; @supabase/ssr is
      structurally httpOnly:false), 4 MED, 2 LOW, 5 INFO; architecture
      explicitly endorsed (SI-1 "airtight", routing correct, harness
      unweakened, public routes tightened). ALL merge-blocking findings
      fixed same day: threat-model corrected + R-029 opened + 7-day
      cookie maxAge cap (#1); R-005/R-027 TTL honesty (#2); users-table
      Alembic migration 0006 + PII-safe provisioning log (#3); R-028 ->
      Open (#4); config.toml deleted (#5); @clerk/nextjs dependency
      dropped now — carried a high js-cookie advisory, git provides
      revertibility (#6); callback origin from NEXT_PUBLIC_SITE_URL not
      Host header (#8); alg=none + RS256-on-supabase-issuer spec tests
      added (#10); e2e webServer env scoped + scratch-only ref comment
      (#11); doc drift fixed (#12). Deferred to pre-cutover: Next.js
      patch for R-019 (#7). /security-review skill pass still pending.
- [x] 🤖 H3.7 Playwright smoke landed (`tests/e2e/auth-smoke.spec.ts`,
      `npm run test:e2e`): route protection (dashboard+admin), sign-in
      render, REAL email-OTP login via admin-minted code (no inbox —
      SES sandbox/bounce constraint) -> /dashboard, session survives
      navigation, client bounced off /admin. 4/4 green. Send-click
      path stays manual until SES production access + a real inbox.
- [x] 🤖 H3.8 Verification 2026-08-11 post-review-fixes: backend 1175
      passed/1 skipped (auth coverage 294+18+8=320 vs 291 baseline);
      `npm run build` clean; E2E 4/4. [SEC:SI-4]

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
