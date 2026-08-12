# auth_stack_v2 — results (running log)

Close-out summary is written at ship time; until then this is the
running spike/findings log the plan asks for (S0.7).

## 2026-08-10 — Phase 0 started

- Branch `auth_stack_v2` cut from the LOCAL tip of `beta_gtm_mvp`
  (1eefa93 — one unpushed commit ahead of origin during freeze).
- Scratch Supabase project created by founder: ref
  `jhvkfokskanbaiipvcqu`, CLI 2.113.0 linked; `supabase/config.toml`
  committed (env()-only, no literals; `.temp` gitignored).
- **Finding: JWKS endpoint is empty** (`/auth/v1/.well-known/jwks.json`
  -> `{"keys":[]}`). New projects still sign with the legacy shared
  HS256 secret until migrated to asymmetric signing keys. SI-2 forbids
  accepting HS256, so the dashboard migration (JWT Keys -> create ES256
  -> promote) is a hard prerequisite for S0.6. Management API could do
  it, but extracting the CLI's keychain token was blocked by the
  permission classifier — founder does the 30-second dashboard step
  instead.
- Auth settings probe (`/auth/v1/settings`): email provider ON, Google
  OFF (needs OAuth client creds), phone OFF (expected until Phase 5),
  signups open, sms_provider twilio-default (unused).
- **Design simplification**: Supabase access tokens natively include
  `app_metadata` / `user_metadata` claims, so the app role can be read
  from `app_metadata.role` without a Custom Access Token Hook. Spec
  suite pins that; S0.6 verifies against a real token before the hook
  is declared dead (also pins that the native `role` claim —
  PostgREST's `authenticated`/`service_role` — never maps to app role).
- **S0.3 done — red witnessed**: `tests/test_supabase_jwt_spec.py`,
  17 tests. 6 failing exactly as intended (valid-token acceptance,
  app_metadata role extraction, user_metadata spoof ignored, PostgREST
  role claim ignored, unknown-role default, source label); 10 rejection
  guards trivially green (current verifier rejects all non-Clerk
  tokens) and become meaningful post-B1.3; SI-10 double-gate test
  green. Clerk harness unaffected: 291 passed alone and alongside.

- **Signing-key migration done** (founder, same day): JWKS now serves
  one ES256 P-256 key, kid `ec789fc4-0843-494f-a059-31438dab1549`.
  S0.7 alg decision settled: ES256 pinned, matching the spec suite.

- **Google SSO round-trip proven** (founder enabled provider + scratch
  OAuth client; spike page at `spike/serve_spike.py` on port 3000 to
  match the redirect allowlist): real access token captured and
  verified against the live JWKS — ES256, kid resolved, issuer +
  aud=authenticated enforced.
- **Hook question settled**: real tokens DO carry `app_metadata` /
  `user_metadata` claims. No Custom Access Token Hook needed. Google
  profile data lands in user_metadata (client-editable — exactly why
  SI-1 refuses to read the role from there).
- **Admin path proven** (the C4.2 mechanism): admin API
  `PUT /auth/v1/admin/users/{id}` with `app_metadata.role=admin` ->
  `refreshSession()` -> fresh token carries the claim -> spike
  verifier extracts app role `admin`. Client-role default (absent key
  -> `client`) observed on the pre-update token.
- Spike server stopped; `.captured_token` deleted after use (gitignored
  and mode 0600 while it existed).
- **Gotcha**: the email provider flipped to `false` in
  `/auth/v1/settings` at some point during dashboard work — re-enable
  alongside S0.2 SMTP setup.

Phase 0 exit state: architecture fully de-risked (JWKS/ES256/claims/
roles all proven against the real project). Remaining before Phase 0
closes: S0.2 — SMTP + `{{ .Token }}` template + re-enable email
provider, then the email-OTP leg of the spike. Backend Phase 1 (B1.x)
is unblocked regardless: the spec suite defines the verifier contract.

## 2026-08-10 (later) — S0.2: SES SMTP working end-to-end

Provider decision: **AWS SES, region eu-north-1** (founder's choice over
Resend; region is where the account was set up — kept, latency
immaterial for OTP mail). Chain proven: `POST /auth/v1/otp` -> 200 ->
mail delivered to the sandbox-verified recipient.

Debug trail worth remembering for the PROD project setup (C4.1):

1. **Namecheap doubled-domain gotcha** (predicted, confirmed): all 3
   DKIM CNAMEs + MAIL FROM MX/TXT were published under
   `<name>.marketworks.in.marketworks.in` because the full hostname was
   pasted into the Host field. Fix: Host field takes only the prefix
   (`<token>._domainkey`, `mail`). DKIM flipped SUCCESS ~40 min after
   the fix; MAIL FROM re-check still pending (non-blocking — affects
   bounce-domain alignment only).
2. **SMTP credential shape check**: SES SMTP username is an
   AKIA-prefixed 20-char access-key ID, password ~44 chars, minted
   region-specific by the console's "Create SMTP credentials" flow.
   First attempt had a non-SES credential pair (`inp-...`, 28/32
   chars) — direct STARTTLS probe (`spike/test_smtp.py`) returned 535
   and pinpointed it; second pair authed + sent clean.
3. Supabase Auth's 500 ("Error sending confirmation email") hides the
   SMTP error string; isolate with (a) direct SES API send — proves
   identity/sandbox side, (b) `spike/test_smtp.py` — proves the
   credential hop, (c) dashboard Logs -> Auth for the verbatim error.
4. **SES sandbox**: ProductionAccessEnabled=false, 200/day, verified
   recipients only. Production-access request submitted via
   `put-account-details` (transactional/OTP use case) — review PENDING,
   ~24h typical. Must be GRANTED before public beta.
5. Email provider had silently flipped off in the dashboard earlier —
   re-enabled by founder. Check `/auth/v1/settings` when auth flows
   misbehave.

Open S0.2 tail: template edit (`{{ .Token }}`), then the email-OTP
verify leg (`/auth/v1/verify` with a real code) closes Phase 0.

## 2026-08-10 (evening) — Phase 0 CLOSED

Template edited to `{{ .Token }}`; full passwordless email flow proven:
OTP requested -> 6-digit code delivered via SES -> `/auth/v1/verify`
-> session minted -> access token passes the spike verifier (ES256,
kid, issuer, aud; `app_metadata` present; app role defaults `client`
for the email-provider user, distinct from the Google admin user).

All Phase 0 exit criteria met. Both launch login methods (Google SSO,
email OTP) verified end-to-end against real infrastructure. Carried
forward: SES production-access review (PENDING), MAIL FROM re-check
(PENDING, non-blocking), Turnstile captcha + auth rate limits (Phase 3
by design). Next: Phase 1 backend migration, starting with B1.1
branch re-verification and the B1.2 harness port (red first).

Founder decision: NO Clerk-user port — the 10 beta users sign up fresh
at cutover (C4.4 stays notify-only; no migration script).

## 2026-08-10 (night) — Phase 1 backend migration COMPLETE

- B1.2: `test_supabase_authz.py` (294 tests) ports the full gate:
  same endpoint inventories (incl. the two options_worker admin routes
  this branch added), ES256 Supabase tokens, cross-issuer confusion
  cases, endpoint-level SI-1 spoof test. Red witnessed: 241 failures
  against the unmodified Clerk-only verifier.
- B1.3: `auth.py` rewritten as an issuer-routed dual verifier (design
  delta from the plan, so prod Clerk keeps working until C4.5): the
  token's unverified `iss` only ROUTES to a fully-pinned per-provider
  path; the path then verifies everything. Supabase = ES256 +
  require_aud("authenticated") + `app_metadata.role`; Clerk = RS256 +
  `metadata.role`; unknown issuer 401. Per-URL JWKS caches keep the
  stale-on-failure + kid-miss-refresh behavior.
- **TDD catch worth remembering**: python-jose does NOT validate `aud`
  when the claim is absent from the token — the spec suite's
  missing-aud test failed live and forced `options={"require_aud":
  True}`. Without TDD this would have shipped as a silent gap.
- B1.7: lazy provisioning — `User` model + `user_service.provision_user`
  (idempotent by sub, 15-min seen-cache, IntegrityError race-safe,
  fail-open by design since authz never reads this table) hooked into
  both auth entry points. Red witnessed (ImportError), 8 spec tests
  green. C4.3 must create the table on Railway PG (create_all, not
  auto-run at startup).
- B1.8: full suite 1173 passed / 1 skipped. Auth coverage 319 tests vs
  291 baseline; Clerk harness untouched semantically (fixture plumbing
  only: per-URL cache patch).

Next: Phase 2 frontend migration (@supabase/ssr middleware, sign-in UI
with Google + email OTP, token plumbing rewire, CSP + register row).

## 2026-08-10 (late night) — Phase 2 frontend migration built

Both mapping agents ran first (brand identity from marketworks-design;
file-level auth map of the dashboard). Brand decision: sanctioned
Mint/six-palette role tokens (Clay study is unmerged + homepage-scoped
per its own STATE.md); tokens-only styling so the sign-in re-skins per
palette for free. All F2 items done, `npm run build` clean, zero @clerk
references left in src/ (dependency kept for revertibility until C4.5).

Shape notes worth remembering:
- NEW `SupabaseAuthProvider` is the single session subscription; every
  former Clerk hook consumer reads it. Outermost provider.
- Middleware uses `getClaims()` — local ES256 JWKS verification at the
  edge, no per-request auth-server call; refreshed cookies are carried
  onto redirect responses. azp pinning has no Supabase equivalent —
  compensated by backend require_aud + issuer pin (R-027).
- `globalAuthToken` must stay eagerly populated on session change: the
  SSE URL builders (`getJobLogsStreamUrl`/`getPositionsStreamUrl`) are
  synchronous and read it directly.
- SWR cache prefix v1->v2 retires Clerk-keyed localStorage blobs.
- Palette preference roams via `user_metadata` (validated on read,
  never trusted server-side) — the one sanctioned user_metadata use.
- `/sign-up` kept as a page with beta copy (plan said redirect) —
  preserves the marketing CTA; same passwordless flow.
- Pre-existing, unrelated: Vercel Speed Insights debug script is
  CSP-blocked in dev (was never allowlisted; prod path is first-party).

Verified live against the scratch project: sign-in page rendered in
Ocean/Mint/Midnight (evidence/signin-*.png), real OTP sent from the new
UI (send -> code step -> resend cooldown). Full E2E (verify -> session
-> dashboard) lands with the Playwright smoke in H3.7.

Open: founder visual sign-off on the sign-in screen; F2.10 privacy-page
subprocessor update (fold into H3.4).

## 2026-08-11 — Phase 3 hardening + security review cycle

Founder deferred copy/visual amendments; direction approved to continue.

- Turnstile widget wired (env-gated); Playwright E2E smoke landed (4/4;
  admin-minted OTP -> real UI verify -> /dashboard; client off /admin).
  Send-click automation waits on SES production access + a real inbox.
- Docs debt cleared: auth-flows.md §1, threat-model (A3/A4/A6, TB2/TB3),
  .env.example, privacy page (subprocessors + truthful delete-account
  copy), attack-surface insights row.
- **security-reviewer verdict: REQUEST-CHANGES.** Headline finding
  (HIGH, genuinely caught): @supabase/ssr session cookies are
  JS-readable BY DESIGN (httpOnly:false — the browser client reads
  document.cookie); our threat model claimed HttpOnly. Net posture
  change vs Clerk: XSS now yields the rotating refresh token, not a
  ~60s access token. Response: doc corrected, R-029 opened (Accepted,
  with rationale), cookie maxAge capped 400d->7d in all three client
  factories, R-021 (CSP unsafe-inline/eval) re-rated as the
  highest-leverage XSS control. Other fixes same day: R-005 re-accepted
  at the honest 3600s SSE-token TTL; users-table Alembic migration 0006
  (idempotent — deploy runs `alembic upgrade head`, init_db is never
  called; without this, fail-open provisioning would silently no-op in
  prod); provisioning log now emits exception TYPE only (SQLAlchemy
  error text embeds emails); R-028 held at Open until Supabase-side
  captcha/limits exist (widget alone is bypassable via direct
  /auth/v1/otp POST); stock supabase/config.toml deleted (config-push
  clobber hazard vs dashboard-held secrets); @clerk/nextjs dropped from
  package.json (dead dep with a high js-cookie advisory); /auth/callback
  origin now prefers NEXT_PUBLIC_SITE_URL over the Host header; spec
  suite +2 adversarial cases (alg=none, RS256-signed supabase-issuer)
  -> 18; e2e dev-server child no longer inherits the service-role key.
  Deferred to pre-cutover: Next.js bump (R-019, 10 weeks overdue).
- Verification after fixes: backend 1175/1 skipped, build clean, E2E
  4/4. Reviewer also independently confirmed: SI-1 airtight on all
  three surfaces, issuer-routing sound, /auth/callback open-redirect
  check sound, Clerk harness semantically unweakened, no secrets in
  the diff.

AWS status: MAIL FROM verified (domain fully green). SES production
access DENIED on first review — founder to reply to the AWS support
case with the expanded use-case text (drafted in chat 2026-08-11);
production access remains a HARD BLOCKER for public beta.

Remaining founder items (Phase 3): H3.1 Turnstile keys + Supabase
captcha enable, H3.3 OTP expiry 600s + cooldown + rate limits ->
then R-028 flips to Mitigating. Remaining agent items: /security-review
skill pass, Next.js bump + re-smoke (pre-cutover), sign-in copy/visual
amendments when founder provides direction.

## 2026-08-12 — Phase 3 closed out (founder items landed)

- H3.1 (2026-08-11): Turnstile keys created, captcha enabled in
  Supabase. Enforcement VERIFIED: tokenless POST /auth/v1/otp -> 400
  captcha_failed; verify leg unaffected (E2E green); widget renders +
  auto-solves in managed mode. Widget-theme-vs-palette mismatch noted
  for the polish round.
- H3.3: founder configured OTP expiry 600s + cooldown + rate limits.
  R-028 flipped Open -> Mitigating. All public-beta abuse controls are
  now server-side enforced.
- Next.js 16.1.6 -> 16.3.0 (R-019 -> Mitigating; closes at cutover):
  prod-dep audit clean, build + E2E green. Gotcha: Next 16.3 generates
  AGENTS.md/CLAUDE.md — suppressed via agentRules:false.
- E2E suite isolated to port 3100 with reuseExistingServer:false after
  a stale dev server from the design_studies worktree (another Claude
  session) squatted :3000 serving pre-migration Clerk code and
  silently failed the suite against the wrong build.
- External waits: AWS production-access case — founder replied,
  awaiting AWS; MSG91 — founder's business registration applied for,
  W5.1 remains BLOCKED until it arrives.

Remaining before Phase 4 can start: SES production access GRANTED +
the generic /security-review pass (run in a fresh session). Then C4.1
prod-project setup per the recorded checklist.
