# Auth Flows — Kite-Lab

Text diagrams for the three auth flows. Used by `security-reviewer` to
reason about changes that touch any of these paths.

---

## 1. User login → backend session (Supabase Auth, auth_stack_v2)

Two sign-in methods, one session model. Supabase Auth (project
`<ref>.supabase.co`) is the identity provider; it mints ES256 JWTs whose
public keys are served at `/auth/v1/.well-known/jwks.json`. During the
migration window the Clerk path remains verifiable (issuer-routed dual
verifier); it is removed at cutover C4.5.

```
User            Vercel (Next.js)       Supabase Auth          Railway (FastAPI)
 │                    │                     │                      │
 │ (a) Google SSO     │                     │                      │
 │ Click "Continue with Google"             │                      │
 ├───────────────────►│ signInWithOAuth     │                      │
 │ ◄─ redirect ────────────────────────────►│ /auth/v1/authorize   │
 │    Google consent → Supabase callback → 302 back to app         │
 │ GET /auth/callback?code=…                │                      │
 ├───────────────────►│ exchangeCodeForSession (PKCE)              │
 │                    ├────────────────────►│                      │
 │                    │ session cookies set │                      │
 │                                                                 │
 │ (b) Email OTP (passwordless; also the sign-UP path)             │
 │ Enter email → signInWithOtp ────────────►│ sends 6-digit code   │
 │                    │                     │ via SES SMTP         │
 │ Enter code → verifyOtp ─────────────────►│ session cookies set  │
 │                                                                 │
 │ Any protected route                       │                     │
 ├───────────────────►│ middleware: getClaims() — LOCAL ES256      │
 │                    │ verification vs JWKS; session refresh;     │
 │                    │ role from app_metadata for /admin +        │
 │                    │ insights tri-state (UX routing only)       │
 │                                                                 │
 │ API calls          │ Authorization: Bearer <access_token>       │
 │                    ├──────────────────────────────────────────► │
 │                    │ (SSE streams: ?token=<jwt> query param)    │
 │                    │                     │  Depends(get_current_user)
 │                    │                     │  iss routes → Supabase path:
 │                    │                     │  ES256 only, kid ∈ JWKS,
 │                    │                     │  issuer pinned, aud =
 │                    │                     │  "authenticated" REQUIRED,
 │                    │                     │  role := app_metadata.role
 │                    │                     │  (default "client");
 │                    │                     │  lazy upsert into users
 │                    │                     │  table (fail-open) → resp
```

**Code paths:**
- Vercel side: `kite-dashboard/src/middleware.ts` (route protection,
  getClaims), `src/app/auth/callback/route.ts` (PKCE exchange),
  `src/components/auth/sign-in-card.tsx` (both methods + Turnstile),
  `src/contexts/supabase-auth-context.tsx` (single session
  subscription), `src/contexts/api-auth-context.tsx` +
  `src/lib/api-client.ts` (Bearer + SSE token slots).
- Railway side: `kite-api/app/auth.py` (issuer-routed verifier;
  `_decode_supabase` ES256/issuer/require_aud; `_extract_role`
  app_metadata-only), `app/services/user_service.py` (lazy
  provisioning), `tests/test_supabase_jwt_spec.py` +
  `tests/test_supabase_authz.py` (the enforced spec).

**Key invariants (SI-1..SI-10 in tasks/auth_stack_v2/PLAN.md):**
- Role comes ONLY from `app_metadata.role` (server-controlled; set via
  admin API). `user_metadata` is end-user-editable and must never
  influence authz — it is used solely for the palette preference,
  validated on read. The native `role` claim is PostgREST plumbing.
- `aud="authenticated"` is REQUIRED (python-jose skips absent-aud
  validation — `require_aud` closes that; pinned by spec test).
- Access tokens ~1h TTL, auto-refreshed by supabase-js; refresh flows
  through onAuthStateChange (no polling).
- Clerk's edge `azp` pinning has no Supabase equivalent — superseded by
  backend per-request aud + issuer + ES256 enforcement (R-027).
- `DEBUG=true AND DISABLE_AUTH=true` (both) bypasses auth — spec test
  proves DISABLE_AUTH alone still 401s (SI-10).
- Sign-up is open (public beta) — abuse controls are Turnstile captcha
  on OTP send + Supabase auth rate limits + OTP expiry ≤10 min (R-028).

---

## 2. Zerodha OAuth (Kite Connect)

```
User              dev machine / Railway          Zerodha (Kite Connect)
 │                       │                              │
 │ scripts/login_and_save_token.py                      │
 │ (or POST /api/system/login-url + click)              │
 │                       │                              │
 │                       │ Build login URL              │
 │                       │   https://kite.zerodha.com/connect/login?api_key=…&v=3
 │                       │                              │
 │ Open in browser                                       │
 │ ◄─────────────────────┤                              │
 │                       │                              │
 │ Zerodha login + TOTP                                  │
 ├──────────────────────────────────────────────────────►│
 │                       │                              │
 │                       │  Redirect to REDIRECT_URI    │
 │                       │  with ?request_token=…&status=success
 │ ◄─────────────────────────────────────────────────────│
 │                       │                              │
 │ Browser hits REDIRECT_URI                             │
 │   (locally: scripts handle this)                      │
 │   (cloud: /api/system/callback)                       │
 │                       │                              │
 │                       │ generate_session(             │
 │                       │   request_token,              │
 │                       │   api_secret)                 │
 │                       ├─────────────────────────────►│
 │                       │ {access_token, public_token, │
 │                       │  refresh_token, user_id, …}  │
 │                       │ ◄─────────────────────────────│
 │                       │                              │
 │                       │ Write access_token.txt (0600)│
 │                       │ Write session.json    (0600) │
 │                       │                              │
 │ All subsequent kiteconnect calls use access_token    │
 │                       ├─────────────────────────────►│
 │                       │   (24h TTL, expires 06:00 IST)
```

**Code paths:**
- `scripts/login_and_save_token.py` — local CLI login
- `kite-api/app/api/system.py:118-159` — `/api/system/callback`
- `kite-api/app/services/system_service.py:341-378` — token exchange
- `kite-api/app/services/system_service.py:367, 376` — file writes (0600)

**Risks:**
- **R-004**: callback lacks state/nonce. Accepted because `request_token`
  is single-use with ~5 min TTL.
- **AD-4**: one access token per user. Logging in from machine B
  invalidates machine A's token.

---

## 3. Google Drive OAuth (backup uploads)

```
dev machine (laptop / Mac mini / Railway)          Google
 │                                                  │
 │ python scripts/upload_to_gdrive.py auth          │
 │ (first time only — browser flow)                 │
 │                                                  │
 │ Open browser to consent screen                   │
 │ ◄────────────────────────────────────────────────┤
 │ User grants Drive scope                          │
 │                                                  │
 │ Receive refresh_token                            │
 │ ◄────────────────────────────────────────────────┤
 │                                                  │
 │ Save to ~/.config/kite-lab/gdrive_token.json    │
 │ (Railway: /data/config/gdrive_token.json)       │
 │                                                  │
 │ Subsequent runs use refresh_token (no browser)   │
 ├─────────────────────────────────────────────────►│
 │   Drive API: upload tarballs                     │
```

**Scope:** Drive only. Token narrowly scoped.

**Code paths:**
- `scripts/upload_to_gdrive.py` (Phase 2.5.4)
- Client secret: `~/.config/kite-lab/gdrive_client_secret.json`
- Token: `~/.config/kite-lab/gdrive_token.json`

## Invariants the agent should enforce

1. Every new authenticated endpoint must declare `Depends(get_current_user)` or an equivalent, and appear in the `tests/test_supabase_authz.py` inventories (ADMIN_ENDPOINTS / CLIENT_READ_ENDPOINTS / PUBLIC_ENDPOINTS).
2. New endpoints outside `/api/system/*`, `/api/health`, `/api/positions/market-status`, `/api/insights/*` GETs (R-023) that lack auth are an automatic finding.
3. `KITE_API_SECRET`, the SES SMTP password, and the Supabase `service_role` key must never be logged or shipped to the browser (`service_role` never in `NEXT_PUBLIC_*`). Logger config in `kite-api/app/middleware/request_logger.py` — confirm on changes.
4. `access_token.txt` and `session.json` writes must use `Path.write_text` with mode 0o600. Existing pattern: `system_service.py:367, 376`.
5. Authz role must be read exclusively from `app_metadata.role` (backend `_extract_role`, middleware `roleFromClaims`, frontend cosmetic reads). Any code path reading a role from `user_metadata` is an automatic CRITICAL finding (SI-1).
6. CSP header (closing R-006) must not be loosened without a register row (precedents R-024, R-027).
7. The Supabase verification path must remain ES256-only with `require_aud` — accepting HS256 or absent-aud tokens is an automatic CRITICAL finding (SI-2/SI-3; spec: `test_supabase_jwt_spec.py`).
