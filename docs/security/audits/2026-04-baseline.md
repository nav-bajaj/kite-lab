# Audit Baseline — April 2026

**Source:** `tasks/security/README.md` (the closed audit)
**Branch:** `security` (merged 2026-04-08)
**Status:** Closed — all 23 actionable items remediated

This file is a frozen snapshot of the closed-baseline audit. It exists so
that future audits can compare against a known good starting point
without consulting the original task folder.

The companion file `tasks/security/README.md` is the authoritative
detail; this is the summary.

---

## Severities at closure

| Severity | Total | Fixed | Skipped (already addressed / not applicable) |
|---|---|---|---|
| Critical | 5 | 5 | 0 |
| High | 6 | 6 | 0 |
| Medium | 7 | 6 | 1 |
| Low | 5 | 3 | 2 |
| **Total** | **23** | **20** | **3** |

## What was fixed

### Critical (5/5)
- `.env.production` verified never committed; `.gitignore` strengthened
- Zerodha API credentials verified never committed; `.gitignore` strengthened
- `JWT_SECRET` and `NEXTAUTH_SECRET` rotated to strong random values; documented
- `SKIP_AUTH` bypass removed in production (safeguard in auth middleware)
- `docker-compose` uses env vars, debug off by default

### High (6/6)
- API authentication added to all sensitive endpoints
- `/docs`, `/redoc`, `/openapi.json` disabled when `DEBUG=False`
- `/api/auth/token` rate-limited to 5 req/min per IP
- Error messages sanitized (no email or `JWTError` leakage)
- Wildcard CORS rejected in non-debug
- Startup warnings on debug/default-JWT

### Medium (6/7, 1 skipped)
- Universe param validated against whitelist before subprocess
- Subprocess args restricted to allowed keys with length limits
- NextAuth denies login if `ALLOWED_EMAILS` empty
- Security headers (X-Content-Type-Options, X-Frame-Options, HSTS, etc.)
- Input length limits on Pydantic fields; schedule ID restricted to alphanumeric
- Backend rejects token creation if `ALLOWED_EMAILS` unset in production
- *Skipped:* 24h session timeout matches daily workflow

### Low (3/5, 2 skipped)
- Request ID tracking (`X-Request-ID` header)
- Audit logging for jobs, schedule, sync, rebalance, auth
- All Python and Node deps pinned exact
- *Skipped:* pagination limits already bounded
- *Skipped:* (n/a)

## User actions completed at the time

- Generated strong `JWT_SECRET` and `NEXTAUTH_SECRET`
- Updated Railway env (`JWT_SECRET`)
- Updated Vercel env (`NEXTAUTH_SECRET`)
- Set `ALLOWED_EMAILS` in both Railway and Vercel

## What was deliberately left for future work

Not remediated as part of the April 2026 audit:

| Item | Why deferred | Current status |
|---|---|---|
| SAST / pre-commit / CI security gates | Out of scope for fix-list audit | R-001 (closing now), R-009 (open) |
| Codified threat model / register | Out of scope for fix-list audit | R-008 (closing now) |
| CSP header on Next.js | Frontend audit deferred | R-006 (closing now) |
| ESLint security plugin | Frontend audit deferred | R-007 (closing now) |
| OAuth state/nonce | Accepted (request_token single-use) | R-004 (accepted) |
| SSE token in query | Accepted (EventSource API) | R-005 (accepted) |
| Job cancellation kill | Accepted (single-user) | R-010 (accepted) |
| Old transitive `autobahn==19.11.2` | Not yet identified | R-002 (open) |

## Verification at closure

The original audit verified each item with a code-level fix and a manual
re-check. The current branch (`security-agent`) builds on this baseline
and does not re-verify the April items — they're assumed good.

If a regression is suspected in any of the closed items, the
`/security-audit` skill will catch it on its next run (the scanners
re-check from scratch every time).

## How to compare against this baseline

```bash
# Run /security-audit; the resulting report under audits/<today>.md
# will show new findings relative to suppressions.yml.
# Items closed at this baseline live in suppressions.yml keyed to
# register rows where applicable.
```
