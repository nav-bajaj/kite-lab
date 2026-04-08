# Security Hardening Tasks

**Created:** April 7, 2026
**Branch:** `security`
**Status:** Complete

## Overview

Security review identified 23 issues across critical, high, medium, and low severity levels. All actionable items have been remediated. 3 items were skipped as already addressed or not applicable.

---

## Critical Issues (Must Fix)

| # | Task | Status | User Action Required |
|---|------|--------|---------------------|
| 1 | [Remove .env.production from git history](./01-remove-env-production.md) | `done` | No (was never committed) |
| 2 | [Secure Zerodha API credentials](./02-secure-zerodha-creds.md) | `done` | Optional - rotate keys |
| 3 | [Generate strong JWT secrets](./03-strong-jwt-secrets.md) | `done` | Done - secrets set in Railway/Vercel |
| 4 | [Remove SKIP_AUTH bypass](./04-remove-skip-auth.md) | `done` | No |
| 5 | [Secure docker-compose credentials](./05-secure-docker-compose.md) | `done` | No |

---

## High Priority Issues

| # | Task | Status | User Action Required |
|---|------|--------|---------------------|
| 6 | [Add authentication to API endpoints](./06-api-authentication.md) | `done` | No |
| 7 | Disable API docs in production | `done` | No |
| 8 | Rate limit auth endpoints | `done` | No |
| 9 | Sanitize error messages | `done` | No |
| 10 | Validate CORS configuration | `done` | No |
| 11 | Disable debug mode in production | `done` | No |

---

## Medium Priority Issues

| # | Task | Status |
|---|------|--------|
| 12 | Add path traversal protection | `done` |
| 13 | Validate subprocess arguments | `done` |
| 14 | Secure NextAuth token handling | `done` |
| 15 | Add security headers (CSP, HSTS) | `done` |
| 16 | Reduce session timeout | `skip` (24h matches daily workflow) |
| 17 | Add input length limits | `done` |
| 18 | Require ALLOWED_EMAILS in production | `done` |

---

## Low Priority / Hardening

| # | Task | Status |
|---|------|--------|
| 19 | Add request ID tracking | `done` |
| 20 | Implement audit logging | `done` |
| 21 | Add pagination limits | `skip` (already bounded) |
| 22 | Pin dependency versions | `done` |
| 23 | Secure access_token.txt | `done` |

---

## Progress Summary

| Severity | Total | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 5 | 5 | 0 |
| High | 6 | 6 | 0 |
| Medium | 7 | 6 | 1 (skipped) |
| Low | 5 | 3 | 2 (skipped) |

### Completed Fixes

**Critical:**
- [x] #1 - `.env.production` was never committed (verified) - `.gitignore` strengthened
- [x] #2 - Zerodha API credentials in `.env` were never committed - `.gitignore` strengthened
- [x] #3 - JWT secrets documented, templates created with generation commands
- [x] #4 - SKIP_AUTH now ignored in production (safeguard added to middleware)
- [x] #5 - Docker-compose uses env vars, debug off by default

**High:**
- [x] #6 - API authentication added to all sensitive endpoints
- [x] #7 - API docs (/docs, /redoc, /openapi.json) disabled when debug=False
- [x] #8 - Auth token endpoint rate limited to 5 req/min per IP
- [x] #9 - Error messages sanitized (no emails or JWTError details leaked)
- [x] #10 - Wildcard CORS origins blocked in production
- [x] #11 - Startup warnings for debug mode and default JWT secret

**Medium:**
- [x] #12 - Universe validated against whitelist before path/subprocess use
- [x] #13 - Subprocess args restricted to allowed keys with length limits
- [x] #14 - NextAuth denies login when ALLOWED_EMAILS is empty (was allowing all)
- [x] #15 - Security headers added (X-Content-Type-Options, X-Frame-Options, HSTS, etc.)
- [~] #16 - Session timeout already 24h (matches daily trading workflow, skipped)
- [x] #17 - Input length limits on all Pydantic string fields, schedule ID restricted to alphanumeric
- [x] #18 - Backend rejects token creation if ALLOWED_EMAILS not configured in production

**Low:**
- [x] #19 - Request ID tracking added (X-Request-ID header, logged per request)
- [x] #20 - Audit logging for sensitive endpoints (jobs, schedule, sync, rebalance, auth)
- [~] #21 - Pagination limits already bounded (trades le=500, jobs le=100) - skipped
- [x] #22 - All Python and Node dependencies pinned to exact versions
- [x] #23 - access_token.txt and session.json written with 0600 permissions

### User Actions Completed

- [x] Generated strong JWT_SECRET and NEXTAUTH_SECRET
- [x] Updated Railway environment variables (JWT_SECRET)
- [x] Updated Vercel environment variables (NEXTAUTH_SECRET)
- [x] ALLOWED_EMAILS set in both Railway and Vercel

### Post-Merge Action

- Redeploy both services after merging to main

---

## Breaking Changes Warning

The following fixes may cause temporary disruption:

1. **Database password rotation** - Backend will fail to connect until Railway env var is updated
2. **Zerodha API key rotation** - Pipeline scripts will fail until new keys are configured
3. **JWT secret change** - All existing sessions will be invalidated (users must re-login)
4. **API authentication** - Any external tools calling the API will need auth tokens

---

*Last updated: April 8, 2026*
