# Attack Surface — Kite-Lab

Enumeration of every externally-reachable endpoint and what protects it.
Used by `security-reviewer` to evaluate whether a diff introduces a new
surface or weakens an existing control.

**Last regenerated:** 2026-05-19 (manual — automate via `/security-audit`
in a future iteration)

---

## Backend (`kite-api`, Railway)

Base URL: `https://kite-lab-production.up.railway.app`

### Authenticated (require `Bearer <JWT>` via `Depends(get_current_user)`)

| Method | Path | Service | Notes |
|---|---|---|---|
| GET | `/api/auth/me` | auth_routes | Returns current user from JWT |
| GET | `/api/auth/verify` | auth_routes | Verify token still valid |
| GET, POST | `/api/portfolio/*` | portfolio_db_service | Holdings, P&L (backtest) |
| GET | `/api/positions` | positions_service | Live positions (real-time prices) |
| GET | `/api/positions/stream` | positions_service | **SSE — token in query param (R-005)** |
| GET | `/api/metrics/*` | metrics_service | Equity curves, CAGR/Sharpe |
| GET | `/api/trades` | trade_service | Trade history with pagination (≤500) |
| POST | `/api/rebalance/*` | rebalance_service | Preview + orders |
| GET, POST, DELETE | `/api/jobs` | job_service | Subprocess execution |
| POST | `/api/sync/upload-data` | sync_service | **tarball upload, validated members (R-TBD-no-size-limit)** |
| GET, POST, PATCH, DELETE | `/api/schedule/*` | schedule_service | Cron-like jobs |

### Unauthenticated by design (AD-1, R-003)

| Method | Path | Service | Rationale |
|---|---|---|---|
| GET | `/api/health` | health | Liveness probe for Railway |
| GET | `/health` | health | Same |
| GET | `/api/system/status` | system_service | Public deploy info — must not include secrets |
| GET | `/api/system/token` | system_service | **Token status only** (expiry timestamp) — no token value |
| GET | `/api/system/database` | system_service | Postgres reachability — must not include conn string |
| GET | `/api/system/sync` | system_service | Sync state — must not include row counts of sensitive tables |
| GET | `/api/system/login-url` | system_service | Builds Zerodha OAuth URL for the user |
| GET | `/api/system/callback` | system_service | **Zerodha OAuth callback (R-004)** — exchanges request_token for access_token |
| GET | `/api/positions/market-status` | positions_service | NSE market open/close — no user data |

### Rate-limited

| Path | Limit |
|---|---|
| Global (all routes) | 60 req/min per IP (slowapi) |
| `/api/auth/token` | 5 req/min per IP |

### Security headers (set globally in `main.py:92-100`)

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000   (production only)
```

CSP: **not set on backend** (frontend domain is what loads scripts;
CSP enforcement belongs on Vercel — R-006 closing now).

### CORS

- `allow_origins` from `ALLOWED_ORIGINS` env var (comma-separated)
- Wildcard `"*"` rejected in non-debug mode (`main.py:77-81`)
- `allow_credentials=True`

## Frontend (`kite-dashboard`, Vercel)

Base URL: `https://kite-lab.vercel.app`

### Routes

| Path | Auth | Notes |
|---|---|---|
| `/` (login) | none | NextAuth Google OAuth start |
| `/api/auth/*` | NextAuth-managed | OAuth callback, session, signout |
| `/api/backend-token` | session-required (NextAuth) | Mints Bearer JWT for backend from session |
| `/(dashboard)/*` | session-required | Portfolio, performance, trades, rebalance, admin |

### Auth chain

```
Google OAuth (Vercel)
  → NextAuth session (jwt strategy, 24h)
  → POST /api/backend-token (server-side, NextAuth-verified)
  → Bearer JWT (HS256, 24h)
  → Authorization header on all subsequent Railway API calls
```

### Token storage (client-side)

- In-memory module-level `globalAuthToken` in `kite-dashboard/src/lib/api-client.ts`
- **Not** in localStorage, **not** in cookies (NextAuth manages its own session cookie separately)
- SSE URLs include token as query param (`api-client.ts:356, 521`) — R-005

### Environment variables

- `NEXT_PUBLIC_API_URL` — backend base URL (intentionally public)
- `NEXTAUTH_SECRET` — server-only, never `NEXT_PUBLIC_*`
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — server-only
- `ALLOWED_EMAILS` — server-only

**Invariant:** no secret should ever be in a `NEXT_PUBLIC_*` var. Scanner
rule planned in `tools/security/semgrep.yml`.

## Out-of-app surfaces

| Surface | Auth | Notes |
|---|---|---|
| Railway dashboard | Railway login (MFA recommended) | Env var management; one click redeploy |
| Vercel dashboard | Vercel login (MFA recommended) | Env vars; one click redeploy |
| GitHub repo | gh auth | Push to `main` → auto-deploy on both platforms (R-011) |
| Zerodha account | TOTP-protected | Direct trading authority; outside our app |
| Google Drive | OAuth | Backups; scope limited to a folder |

## How to update this file

When you add/change/remove a route:

1. Open `kite-api/app/api/<file>.py` (or `kite-dashboard/src/app/api/`).
2. Locate the new/changed route.
3. Update the corresponding table here. Include auth status.
4. If unauthenticated **and** outside `/api/system/`, **/api/health**,
   or `/api/positions/market-status`: that's a new finding — open a
   register row.

The `security-reviewer` subagent will refuse to approve a diff that adds
an unauthenticated route outside the documented AD-1 exception without a
matching register row.
