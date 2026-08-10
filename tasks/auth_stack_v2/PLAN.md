# auth_stack_v2 — Clerk → Supabase Auth migration

Opened 2026-08-10. Branch: `auth_stack_v2` off `beta_gtm_mvp` (local tip
1eefa93, one commit ahead of origin — includes the universe_membership
replacement).

## Why

Marketworks goes from Private Beta (10 allowlisted users, Google SSO
only) to public beta at launch. Requirements the current Clerk stack
cannot meet natively:

1. **WhatsApp/SMS OTP login for Indian users** via MSG91. Clerk has no
   WhatsApp factor and no bring-your-own SMS provider; the only route is
   a bolted-on sign-in-token flow.
2. **Passwordless email OTP** as the primary email method.
3. **Cost at launch scale.** Clerk is ~$0.02/MAU past 10k. Supabase Auth
   is 50k MAU free, ~$0.00325/MAU after.
4. **Future entitlements** (paid dashboard/insights, courses, Razorpay
   subscriptions) need user rows and purchase state in *our* Postgres,
   not inside the auth vendor — the auth layer must stay thin and
   portable.

Decision record (2026-08-09 session): **Supabase Auth** chosen over
staying on Clerk (no WhatsApp/BYO-SMS, cost), Better Auth (self-hosted —
we'd own the full auth security surface; kept as documented fallback),
Auth0 (cost, enterprise-oriented), Firebase Auth (no custom SMS
provider, no WhatsApp). Deciding factors: Send-SMS Hook makes MSG91
WhatsApp a *native* phone factor; asymmetric JWT signing keys + JWKS
endpoint preserve our FastAPI verification seam; managed service keeps
OTP brute-force/token-rotation/CVE burden off a one-person team.

## Outcome

- Sign-in at marketworks.in offers **Google SSO** and **email OTP**
  (passwordless, 6-digit code); WhatsApp/SMS OTP slots in later by
  enabling the phone provider + Send-SMS hook (delivery-only change, no
  rework).
- Public sign-up open (allowlist retired), protected by Turnstile
  captcha + auth rate limits.
- `kite-api` verifies Supabase JWTs via JWKS exactly as it verifies
  Clerk today; all 17 `require_admin` and ~20 `check_universe_access`
  gates unchanged; authz test harness ported with coverage >= the
  current 277 assertions.
- A `users` row exists in Railway Postgres for every authenticated user
  (lazy provisioning), ready for the entitlements initiative.
- Clerk fully decommissioned after a soak period.

## Target architecture

```
Browser ── supabase-js ──> Supabase Auth (project <ref>.supabase.co)
   │                          - Google OAuth, email OTP (custom SMTP)
   │                          - later: phone OTP -> Send-SMS hook -> MSG91
   │                          - Custom Access Token Hook injects
   │                            role claim from app_metadata
   │  session.access_token (asymmetric JWT, kid in JWKS)
   ▼
Next.js middleware (@supabase/ssr)      FastAPI (Railway)
   route protection, admin gate         app/auth.py: JWKS fetch/cache,
   via verified claims                  pinned issuer, aud check, role
                                        from token claim, lazy user
                                        provisioning into Railway PG
```

Identity is thin and portable: Supabase issues tokens; everything
money-related (entitlements, subscriptions, Razorpay state) lives in our
own Postgres behind our own FastAPI checks — that is a **separate
follow-on initiative**, not this folder.

## Security invariants (drive the TDD specs)

- **SI-1 Role provenance.** Authz role comes exclusively from a claim
  populated by the Custom Access Token Hook out of `app_metadata`.
  `user_metadata` (client-editable) must never influence authz. Spec
  test: token with `role: admin` in user_metadata only -> treated as
  `client`.
- **SI-2 Algorithm/issuer pinning.** Accept only the project's
  asymmetric signing alg with `kid` resolving in the project JWKS and
  `iss == https://<ref>.supabase.co/auth/v1`. Tokens signed HS256 with
  the legacy shared JWT secret are rejected (alg-confusion spec test).
- **SI-3 Audience verified.** `aud == "authenticated"` enforced (Clerk
  setup ran `verify_aud: False`; that ends here).
- **SI-4 No authz regression.** Ported harness keeps the semantics of
  every current assertion in `kite-api/tests/test_clerk_authz.py`;
  endpoint inventories (17 admin, ~20 universe-gated) stay parametrized;
  never weakened.
- **SI-5 Key hygiene.** `service_role` key is server-side only (Railway
  env), never in `NEXT_PUBLIC_*`, never in the bundle, never committed.
  Anon key is public by design.
- **SI-6 CSP via register.** CSP changes (add Supabase origin, later
  remove Clerk origins) get risk-register rows before merge (R-006/R-007
  invariant; precedent R-024).
- **SI-7 Abuse controls at open sign-up.** Captcha on OTP send, Supabase
  auth rate limits configured, OTP expiry <= 10 min. Later: per-phone
  throttling before MSG91 goes live (every send costs money).
- **SI-8 SSE path parity.** `validate_token_string` (`?token=` for
  EventSource) revalidated under the new verifier; residual documented
  as with R-024.
- **SI-9 Provisioning discipline.** Lazy user upsert is idempotent,
  keyed by `sub`; stores only what's needed (email/phone, timestamps).
- **SI-10 Dev bypass stays double-gated.** `DEBUG && DISABLE_AUTH` both
  required; prod config spec test proves 401 without a valid token.

## TDD scope for this initiative

Extends `tasks/insight_engine/TDD_POLICY.md` discipline to the auth
surface. **Spec-test-first (red -> green -> refactor, failure witnessed
before implementation):**

- Everything in the `kite-api/app/auth.py` rewrite (SI-1/2/3/8/10).
- Lazy provisioning (SI-9).
- Any new FastAPI endpoint or hook-secret verification (Phase 5).

**Out of TDD scope** (per policy: UI layout doesn't map to assertions):
sign-in/account UI, middleware wiring, CSP config. Verified instead by
`npm run build`, the ported harness, and a Playwright E2E smoke suite
that must pass before cutover.

## Scope boundary

In: auth migration, public-beta hardening, docs/security updates,
cutover, MSG91 phone factor (when credentials exist).
Out: entitlements/Razorpay (follow-on initiative `entitlements_v1`),
any UI redesign beyond auth screens, main-branch merge mechanics.

## Constraints

- **Push freeze.** No pushes during market hours (09:00–15:30 IST —
  pushes restart live services). This branch stays local until the user
  approves a push. Nothing merges to `beta_gtm_mvp` or `main` from this
  initiative without explicit user sign-off; cutover env swaps and
  deploys are user-driven, outside market hours.
- Clerk stays fully operational until Phase 4 cutover — the migration is
  built and verified in parallel, not in place.
- Phase 5 is blocked on external approvals (MSG91 KYC, Meta WABA +
  authentication template, DLT registration for SMS fallback). Start the
  paperwork early; it has multi-week latency.

## Critical files

| Area | Files |
|---|---|
| Backend verifier | `kite-api/app/auth.py` (293 lines, the whole seam), `kite-api/app/config.py` |
| Authz harness | `kite-api/tests/test_clerk_authz.py` (277 assertions — port, don't weaken) |
| Frontend session plumbing | `kite-dashboard/src/contexts/api-auth-context.tsx`, `src/lib/api-client.ts` (Bearer + SSE `?token=`), `src/lib/swr-config.tsx` |
| Route protection | `kite-dashboard/src/middleware.ts` (public routes, admin gate, insights tri-state) |
| Auth UI to replace | `src/app/sign-in/`, `src/app/sign-up/`, `(dashboard)/account/` (Clerk prebuilt components), `navbar.tsx` UserButton, sidebar role reads |
| CSP / headers | `kite-dashboard/next.config.ts` (Clerk origins out, Supabase in) |
| Rate limiting | `kite-api/app/middleware/rate_limiter.py` (in-memory per-IP — insufficient alone for OTP abuse) |
| Stale docs to fix | `docs/security/auth-flows.md`, `docs/security/threat-model.md` (both still describe retired NextAuth), `kite-dashboard/.env.example` |

## Known hurdles (from the 2026-08-09 assessment)

1. All auth UI is hand-built from here — no prebuilt components outside
   Clerk. Server-side, never trust unverified session reads; FastAPI
   JWKS verification remains the source of truth.
2. Custom SMTP is mandatory before public beta (built-in Supabase email
   is dev-only, a few sends/hour). Email OTP code requires the
   `{{ .Token }}` template edit (default is magic link).
3. `user_metadata` is client-editable — SI-1 exists because this is the
   classic Supabase authz mistake.
4. Two databases: `auth.users` in Supabase PG, app data in Railway PG.
   Lazy provisioning chosen over Supabase database webhooks.
5. User IDs change format at migration; nothing in Railway PG references
   Clerk IDs today (verified 2026-08-09), so re-onboarding 10 users is
   the whole user-data migration.
6. Local `beta_gtm_mvp` carries unpushed commits during freeze windows —
   always branch/diff against the local tip, and re-verify integration
   points on *this* branch (the 08-09 code map was read from
   `options_data_v1`).
