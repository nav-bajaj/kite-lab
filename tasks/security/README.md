# Security Hardening Tasks

**Created:** April 7, 2026
**Branch:** `security`
**Status:** In Progress

## Overview

Security review identified 30 issues across critical, high, medium, and low severity levels. This task list tracks remediation efforts.

---

## Critical Issues (Must Fix)

| # | Task | Status | User Action Required |
|---|------|--------|---------------------|
| 1 | [Remove .env.production from git history](./01-remove-env-production.md) | `pending` | Yes - rotate DB password |
| 2 | [Secure Zerodha API credentials](./02-secure-zerodha-creds.md) | `pending` | Yes - rotate API keys |
| 3 | [Generate strong JWT secrets](./03-strong-jwt-secrets.md) | `pending` | Yes - update Railway env |
| 4 | [Remove SKIP_AUTH bypass](./04-remove-skip-auth.md) | `pending` | No |
| 5 | [Secure docker-compose credentials](./05-secure-docker-compose.md) | `pending` | No |

---

## High Priority Issues

| # | Task | Status | User Action Required |
|---|------|--------|---------------------|
| 6 | [Add authentication to API endpoints](./06-api-authentication.md) | `pending` | No |
| 7 | [Disable API docs in production](./07-disable-api-docs.md) | `done` | No |
| 8 | [Rate limit auth endpoints](./08-rate-limit-auth.md) | `done` | No |
| 9 | [Sanitize error messages](./09-sanitize-errors.md) | `done` | No |
| 10 | [Validate CORS configuration](./10-validate-cors.md) | `done` | No |
| 11 | [Disable debug mode in production](./11-disable-debug.md) | `done` | No |

---

## Medium Priority Issues

| # | Task | Status |
|---|------|--------|
| 12 | Add path traversal protection | `pending` |
| 13 | Validate subprocess arguments | `pending` |
| 14 | Secure NextAuth token handling | `pending` |
| 15 | Add security headers (CSP, HSTS) | `pending` |
| 16 | Reduce session timeout | `pending` |
| 17 | Add input length limits | `pending` |
| 18 | Require ALLOWED_EMAILS in production | `pending` |

---

## Low Priority / Hardening

| # | Task | Status |
|---|------|--------|
| 19 | Add request ID tracking | `pending` |
| 20 | Implement audit logging | `pending` |
| 21 | Add pagination limits | `pending` |
| 22 | Pin dependency versions | `pending` |
| 23 | Encrypt access_token.txt | `pending` |

---

## Progress Summary

| Severity | Total | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 5 | 5 | 0 |
| High | 6 | 6 | 0 |
| Medium | 7 | 0 | 7 |
| Low | 5 | 0 | 5 |

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

### User Actions Required

1. **Generate strong secrets** (if not already done):
   ```bash
   # Generate JWT_SECRET for Railway
   openssl rand -base64 32

   # Generate NEXTAUTH_SECRET for Vercel
   openssl rand -base64 32
   ```

2. **Update Railway environment variables:**
   - `JWT_SECRET` - use generated value

3. **Update Vercel environment variables:**
   - `NEXTAUTH_SECRET` - use generated value

4. **Ensure ALLOWED_EMAILS is set** in both Railway and Vercel

5. **Redeploy both services** after updating environment variables

---

## Breaking Changes Warning

The following fixes may cause temporary disruption:

1. **Database password rotation** - Backend will fail to connect until Railway env var is updated
2. **Zerodha API key rotation** - Pipeline scripts will fail until new keys are configured
3. **JWT secret change** - All existing sessions will be invalidated (users must re-login)
4. **API authentication** - Any external tools calling the API will need auth tokens

---

*Last updated: April 7, 2026*
