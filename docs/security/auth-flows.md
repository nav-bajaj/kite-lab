# Auth Flows — Kite-Lab

Text diagrams for the three auth flows. Used by `security-reviewer` to
reason about changes that touch any of these paths.

---

## 1. User login → backend session (Google + NextAuth + JWT)

```
User                Vercel (Next.js)         Google              Railway (FastAPI)
 │                       │                     │                      │
 │ GET / (login page)    │                     │                      │
 ├──────────────────────►│                     │                      │
 │                       │                     │                      │
 │ Click "Sign in with Google"                  │                      │
 ├──────────────────────►│                     │                      │
 │                       │ redirect to Google  │                      │
 │ ◄─────────────────────┤                     │                      │
 │                       │                     │                      │
 │ OAuth consent          │                     │                      │
 ├─────────────────────────────────────────────►│                      │
 │                       │ callback w/ code    │                      │
 │ ◄─────────────────────────────────────────────┤                      │
 │                       │                     │                      │
 │ GET /api/auth/callback│                     │                      │
 ├──────────────────────►│                     │                      │
 │                       │ exchange code       │                      │
 │                       ├────────────────────►│                      │
 │                       │ id_token + email    │                      │
 │                       │ ◄───────────────────┤                      │
 │                       │                     │                      │
 │                       │ Check email ∈ ALLOWED_EMAILS               │
 │                       │ NextAuth session cookie (jwt, 24h)         │
 │ ◄─────────────────────┤                     │                      │
 │                       │                     │                      │
 │ Navigate to /(dashboard)/portfolio          │                      │
 ├──────────────────────►│                     │                      │
 │                       │ POST /api/backend-token (server-side)      │
 │                       │ (verifies NextAuth session, mints JWT)     │
 │                       ├──────────────────────────────────────────► │
 │                       │                     │   POST /api/auth/token
 │                       │                     │  {email, signature}  │
 │                       │                     │                      │ Verify email ∈ ALLOWED_EMAILS
 │                       │                     │                      │ Sign JWT HS256 (24h)
 │                       │ ◄────────────────────────────────────────── │
 │                       │ JWT held in module-level globalAuthToken   │
 │                       │ (not localStorage, not cookies)            │
 │                       │                     │                      │
 │ Subsequent API calls (Bearer JWT)                                  │
 │                       ├──────────────────────────────────────────► │
 │                       │ Authorization: Bearer <JWT>                │
 │                       │                     │                      │ Depends(get_current_user)
 │                       │                     │                      │ Verify HS256, check exp,
 │                       │                     │                      │ re-check email ∈ ALLOWED_EMAILS
 │                       │                     │                      │ → response
```

**Code paths:**
- Vercel side: `kite-dashboard/src/lib/auth.ts` (NextAuth config),
  `kite-dashboard/src/app/api/backend-token/route.ts` (token mint),
  `kite-dashboard/src/lib/api-client.ts:6` (in-memory token store).
- Railway side: `kite-api/app/auth.py:56-60` (HS256, 24h),
  `kite-api/app/api/auth_routes.py:55-88` (token endpoint),
  `kite-api/app/auth.py:111-134` (whitelist check, two-tier:
  `AllowedUser` table → `ALLOWED_EMAILS` env fallback).

**Key invariants:**
- Two whitelist checks: at JWT issuance + at every request.
- JWT TTL 24h matches daily-rotation Zerodha session.
- `DEBUG=true AND DISABLE_AUTH=true` bypasses auth — startup logs warn,
  production deploy must have neither set (R-008/old-#11).

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

1. Every new authenticated endpoint must declare `Depends(get_current_user)` or an equivalent.
2. New endpoints outside `/api/system/*`, `/api/health`, `/api/positions/market-status` that lack auth are an automatic finding.
3. `JWT_SECRET`, `NEXTAUTH_SECRET`, `KITE_API_SECRET` must never be logged. Existing logger config in `kite-api/app/middleware/request_logger.py` excludes these — confirm on changes.
4. `access_token.txt` and `session.json` writes must use `Path.write_text` with mode 0o600. Existing pattern: `system_service.py:367, 376`.
5. ALLOWED_EMAILS check must run *both* at JWT issuance and per-request (defense in depth).
6. CSP header (closing R-006) must not be loosened without a register row.
