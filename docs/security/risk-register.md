# Risk Register — Kite-Lab

**Maintained by:** `/security-audit` skill (writes) + humans (review)
**Review cadence:** every `/security-audit` run; full re-review quarterly
**Last reviewed:** 2026-05-19

---

## Status legend

| Status | Meaning |
|---|---|
| `Open` | Risk identified, no control yet |
| `Mitigating` | Control in progress |
| `Closed` | Control in place + verified; row kept for history |
| `Accepted` | Risk acknowledged, not fixed by design; compensating control noted |
| `Won't-fix` | Out of scope / lower than effort cost |

## Severity rubric

| Severity | Criterion |
|---|---|
| Critical | Direct path to A1/A2/A3 (trading authority) or A5 (DB) |
| High | One chain step to a critical asset; or broad meta gap (no threat model) |
| Medium | Two-step chain; or moderate info disclosure |
| Low | Multi-step chain; or accepted defense-in-depth gap |

---

## Active rows

| ID | Title | Asset | Sev | Likelihood | Status | Control | Compensating | Opened | Last reviewed |
|---|---|---|---|---|---|---|---|---|---|
| R-001 | No SAST in pre-commit/CI | cross-cutting | Med | Med | Mitigating | This branch: pre-commit (gitleaks, ruff S, eslint-sec) + `/security-audit` skill | n/a | 2026-05-19 | 2026-05-19 |
| R-002 | `autobahn==19.11.2` abandoned transitive dep | A1, A3 (via supply chain) | Med | Low | Accepted | Hard-pinned by `kiteconnect==5.0.1` itself (`autobahn[twisted] ==19.11.2`). Cannot upgrade without changing the SDK. Monitor `kiteconnect` releases for a newer pin. | `pip-audit` flags CVEs; not directly imported in our code | 2026-05-19 | 2026-05-19 |
| R-003 | `/api/system/*` unauthenticated by design (OAuth bootstrap) | A2, A8 (state leak) | Med | Low | Accepted | Documented as AD-1. New routes under this prefix must pass review. | Endpoints return minimal state (status, login URL, callback handler only) | 2026-05-19 | 2026-05-19 |
| R-004 | OAuth callback (`/api/system/callback`) lacks state/nonce | A2 | Low | Low | Accepted | Documented as AD-1. Zerodha `request_token` is single-use, ~5 min TTL | Token exchange happens server-side only | 2026-05-19 | 2026-05-19 |
| R-005 | SSE token (`/api/positions/stream`) passed as query param | A3 | Med | Low | Accepted | EventSource API limitation; documented as AD-2 | Short JWT TTL (24h); audit log review; no logging of full URL | 2026-05-19 | 2026-05-19 |
| R-006 | No CSP header on Next.js frontend | A4 (XSS escalation) | Med | Low | Mitigating | `next.config.ts` now sets CSP + Permissions-Policy + HSTS + COOP/CORP (this branch). Verify after deploy: `curl -I https://kite-lab.vercel.app` shows `Content-Security-Policy`. Flip to `Closed` after verification. | Existing X-Frame-Options DENY + X-XSS-Protection | 2026-05-19 | 2026-05-19 |
| R-007 | No `eslint-plugin-security` on dashboard | A4 (XSS) | Low | Low | Mitigating | Plugin installed (`kite-dashboard/package.json`) and configured in `eslint.config.mjs` with `recommended` preset + eval/non-literal-require pinned to error. Verify: `npm run lint` finds no new errors and the plugin loads. | Pre-commit + `/security-audit` would catch on Python; gap is JS/TS only | 2026-05-19 | 2026-05-19 |
| R-008 | No codified threat model + register | meta | High | n/a | Closing | This branch delivers `docs/security/*` | n/a | 2026-05-19 | 2026-05-19 |
| R-009 | No CI security gates on PRs | cross-cutting | Med | Med | Open | Future: `.github/workflows/security.yml` running pre-commit hooks + `/security-audit` scanners | Pre-commit + skill catch locally; solo dev reduces risk window | 2026-05-19 | 2026-05-19 |
| R-010 | Job cancellation marks status but doesn't kill subprocess | A9 (DoS, not direct) | Low | Low | Accepted | Documented as AD-3 | Single-user, single-host; long-running jobs are bounded by `nohup` parent | 2026-05-19 | 2026-05-19 |
| R-011 | Branch protection on `main` not enforced (solo dev convention) | TB7 | Med | Low | Accepted | None | Small commit cadence; pre-commit on dev machine | 2026-05-19 | 2026-05-19 |
| R-012 | Logs ephemeral on Railway (no log shipping) | repudiation | Low | Med | Open | Future: ship to a log aggregator | Audit log written + read via `/api/jobs/logs` short-term | 2026-05-19 | 2026-05-19 |
| R-013 | `npm audit` reports 14 vulnerabilities (1 low / 4 moderate / 9 high) after eslint-plugin-security install | A4 | Med | Low | Open | Triage via `/security-audit` — likely all transitive deps of dev tooling (ESLint, build chain), not in runtime bundle | Vulns not in shipped JS; only affect build env on dev machine | 2026-05-19 | 2026-05-19 |

## Closed rows

(none yet — closures from this branch land here once verified end-to-end)

## How to add a row

1. Pick the next free ID (`R-013`, …).
2. Fill all columns; `Opened` and `Last reviewed` = today (UTC).
3. Reference the row in commit messages and PRs that touch related code.
4. If the row is closed by code in this PR, change status to `Mitigating`,
   then to `Closed` only after verification (per the PLAN's
   "Verification" section).

## How `/security-audit` maintains this file

- New findings that match an existing row's `fingerprint` → bump `Last reviewed`.
- New findings with no match → propose a new row in the report, ask the human to merge.
- Findings present last run, absent this run → mark candidate-for-Closed in the report; human flips status.
- The skill never auto-closes rows. Closure is human-only.
