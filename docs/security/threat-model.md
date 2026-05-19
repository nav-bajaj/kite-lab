# Threat Model — Kite-Lab

**Methodology:** STRIDE applied per trust boundary, weighted against the
asset's blast radius. Single-developer project, real-money trading
authority over one Zerodha account.

**Last reviewed:** 2026-05-19

---

## 1. Assets

Ranked by blast radius (worst-case impact if compromised):

| # | Asset | Storage | Blast radius |
|---|---|---|---|
| A1 | Zerodha API key + secret + TOTP secret | `.env` on dev machines, Railway env | Place arbitrary trades on user's real-money account |
| A2 | Zerodha `access_token.txt` + `session.json` | Disk (0600), `/data` volume on Railway | Same as A1, but 24h TTL |
| A3 | `JWT_SECRET` (HS256) | Railway env, dev `.env` | Forge any session as the whitelisted user → all backend APIs |
| A4 | `NEXTAUTH_SECRET` | Vercel env | Forge dashboard sessions → call all `/api/*` (still bounded by JWT) |
| A5 | `DATABASE_URL` (Postgres) | Railway env | Read/write all trade history; data exfil; account takeover via auth tables |
| A6 | Google OAuth client secret | Vercel env | Impersonate the OAuth flow → mint sessions for whitelisted email |
| A7 | Google Drive OAuth token | `~/.config/kite-lab/gdrive_token.json` (laptop, Mac mini) | Read/write everything in `My Drive/kite-lab-backups/` |
| A8 | User PII + trade history in Postgres | Railway managed Postgres | Privacy harm; financial history disclosure |
| A9 | The trading authority itself | Logical — sum of A1, A2, A3 | Real-money loss |

A1–A3 are the "crown jewels." Compromise of any of them yields direct
trading authority. A4–A6 require chaining to reach trading authority.

## 2. Actors

| Actor | Capability | Motivation |
|---|---|---|
| Authorized user (you) | Full | Operate the system |
| Internet attacker (unauthenticated) | Network access to `kite-lab-production.up.railway.app` and `kite-lab.vercel.app` | Drain account, exfiltrate trades |
| Malicious dependency author | Code execution at install/runtime | Supply-chain compromise |
| Compromised dev machine | Full local + git push + Railway/Vercel CLI | Persist + exfil |
| Compromised GitHub account | Push to `main` → Vercel auto-deploys; Railway redeploys on push | Trojan release |
| Compromised Railway / Vercel account | Modify env, redeploy arbitrary code | Total compromise of the deployed services |
| Bystander on the same Wi-Fi | Traffic sniff (mitigated by HTTPS) | Token theft via TLS downgrade attempt |

Out of scope: nation-state, insider (n=1), physical access to powered-on
unlocked dev machines.

## 3. Trust boundaries

```
[Internet attacker]
       │
       ▼  TB1: TLS
┌──────────────────────┐         ┌──────────────────────┐
│  browser (Vercel)    │ ───────►│  Vercel edge / SSR    │
└──────────────────────┘  TB2    └──────────────────────┘
       │ TB3: NextAuth + Bearer JWT
       ▼
┌──────────────────────────────────────────────────────┐
│  Railway FastAPI (kite-api)                          │
│   ├── Pydantic validation                            │
│   ├── ALLOWED_EMAILS / JWT verify                    │
│   ├── rate limiter (slowapi)                         │
│   └── security headers (HSTS, X-Frame-Options, …)    │
└──────────────────────────────────────────────────────┘
       │              │                  │
       │ TB4          │ TB5              │ TB6
       ▼              ▼                  ▼
   Postgres       Zerodha API        Google Drive
  (Railway)      (kiteconnect)      (oauth tokens)

       ▲                              ▲
       │                              │
   TB7: dev machines (laptop, Mac mini)
   ── git push ──► GitHub ── webhook ──► Vercel / Railway redeploy
```

## 4. STRIDE per boundary

### TB1 — Internet ↔ Vercel/Railway (TLS)

- **Spoofing:** mitigated by HTTPS-only; HSTS preload eligible (not registered, R-TBD). Public DNS, no DNS hijack mitigation.
- **Tampering:** TLS integrity.
- **Information disclosure:** TLS confidentiality.
- **DoS:** Vercel/Railway absorb L4; slowapi covers L7 on app.
- **Elevation of privilege:** N/A at this boundary.

### TB2 — browser ↔ Vercel SSR/edge

- **Spoofing:** NextAuth session cookie (SameSite + HttpOnly).
- **Tampering:** CSP enforces script provenance (R-006: not yet active; this branch closes it).
- **Information disclosure:** No secrets in `NEXT_PUBLIC_*`. JWT held in-memory in React module-level var (`api-client.ts`), passed via Authorization header.
- **DoS:** Vercel rate limiting + slowapi downstream.
- **Elevation:** front-end has no privileged operations; all enforcement is backend.

### TB3 — Vercel ↔ Railway API (Bearer JWT)

- **Spoofing:** JWT signed HS256 with `JWT_SECRET` from Railway env. Issued by `/api/auth/token` after NextAuth session verification + ALLOWED_EMAILS check.
- **Tampering:** JWT signature.
- **Information disclosure:** SSE stream `/api/positions/stream` accepts token as query param (EventSource API limit) — token visible in browser history and HTTP referer. **R-005**.
- **DoS:** slowapi 60 req/min global, 5 req/min on `/api/auth/token`.
- **Repudiation:** Audit logger captures POST/PUT/DELETE with request ID + IP. No log shipping; logs ephemeral on Railway (R-009-adjacent).
- **Elevation:** ALLOWED_EMAILS whitelist enforced at JWT issuance; backend re-checks on every request via `get_current_user` dependency.

### TB4 — Railway API ↔ Postgres

- **Spoofing:** Railway internal network; DB only accepts internal hostname.
- **Tampering:** ORM-only access. Raw SQL only in `health.py:24` and `system_service.py:79` (no user input).
- **Information disclosure:** Connection string in env only; never logged.
- **DoS:** Postgres connection pool size; not exposed externally.
- **Elevation:** DB user has full schema rights — single-tenant, no separation. Accepted (single-app DB).

### TB5 — Railway API ↔ Zerodha API

- **Spoofing:** Zerodha OAuth `request_token` is single-use; subsequent calls use `access_token`. **R-004** notes the callback lacks `state`/nonce — accepted because `request_token` is single-use.
- **Tampering:** TLS to Zerodha.
- **Information disclosure:** `access_token.txt` and `session.json` stored 0600 on disk. Persisted to Railway `/data` volume.
- **DoS:** Zerodha enforces 3 req/s; `PriceClient` throttles.
- **Repudiation:** Zerodha's own audit logs.
- **Elevation:** Token is scoped to user's account; no admin scopes.

### TB6 — Railway API ↔ Google Drive

- **Spoofing:** OAuth refresh token in `~/.config/kite-lab/gdrive_token.json` (laptop) or Railway `/data` volume. Scoped to Drive only.
- **Tampering:** TLS.
- **Information disclosure:** Backups in `My Drive/kite-lab-backups/` accessible to whoever holds the OAuth token + the Google account. **A7**.
- **DoS:** Google quotas; not user-facing.
- **Elevation:** Token is scoped narrowly.

### TB7 — dev machines ↔ GitHub / Railway / Vercel

- **Spoofing:** GitHub auth via gh CLI; Railway/Vercel via CLI tokens stored locally.
- **Tampering:** Push to `main` triggers auto-deploy on both platforms. **High blast radius** — a single compromised commit lands in prod within minutes. Mitigation: branch protection (R-TBD: not currently enforced for solo dev).
- **Information disclosure:** Dev `.env` files contain everything. Laptop FileVault + 1Password are the only controls.
- **DoS:** N/A.
- **Elevation:** A compromised dev machine has total system compromise.

## 5. Design-time accepted risks

These are documented intentional decisions; the agent should not flag them
as findings but should flag *changes* to them.

| ID | Decision |
|---|---|
| AD-1 | `/api/system/*` is intentionally unauthenticated for OAuth bootstrap (login URL, callback, status). Tracked as R-003. **Constraint:** the only endpoints permitted under `/api/system/` are the OAuth/health surface; new routes added here must be reviewed. |
| AD-2 | SSE endpoint accepts token via query param (R-005). Constraint: SSE response bodies must never include the token verbatim; JWT TTL is bounded. |
| AD-3 | Job cancellation marks DB status but doesn't kill the subprocess (R-010). Constraint: only the single user can launch jobs, single-host. |
| AD-4 | Single Zerodha access token per user. Two machines can't both have a valid session (handover doc: "whoever logs in wins"). |
| AD-5 | Auto-deploy on push to `main` (no manual approval). Mitigation: small change cadence, security review of diffs before push. |

## 6. Mapping STRIDE to register rows

Every register row in `risk-register.md` references which STRIDE category
and trust boundary it sits in, so the agent can reason about coverage.

```
R-001 (no SAST)           ──► cross-cutting (T,I,E on all boundaries)
R-002 (autobahn old)      ──► E via supply chain (TB3, TB7)
R-003 (system/* unauthed) ──► AD-1 (accepted; I on TB3)
R-004 (OAuth no state)    ──► S on TB5 (accepted, single-use)
R-005 (SSE token in URL)  ──► I on TB3 (accepted)
R-006 (no CSP)            ──► T on TB2  ◄── closing this branch
R-007 (no eslint-security)──► cross-cutting on TB2
R-008 (no threat model)   ──► meta     ◄── closing this branch
R-009 (no CI gates)       ──► cross-cutting
R-010 (job kill)          ──► AD-3 (accepted)
```
