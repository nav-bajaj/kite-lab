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
| R-006 | No CSP header on Next.js frontend | A4 (XSS escalation) | Med | Low | Closed (2026-05-19) | Vercel deploy verified — CSP + HSTS + Permissions-Policy + X-Frame-Options + COOP/CORP all present in response headers. Residual `'unsafe-inline'`/`'unsafe-eval'` on script-src tracked separately as R-021. | n/a (closed) | 2026-05-19 | 2026-05-19 |
| R-007 | No `eslint-plugin-security` on dashboard | A4 (XSS) | Low | Low | Closed (2026-05-19) | Plugin installed (`kite-dashboard/package.json`), configured in `eslint.config.mjs` with `recommended` preset + eval/non-literal-require at `error`. Verified locally during merge: `npx eslint src/lib/api-client.ts` loaded the plugin and reported only pre-existing unused-var warnings. | n/a (closed) | 2026-05-19 | 2026-05-19 |
| R-008 | No codified threat model + register | meta | High | n/a | Closing | This branch delivers `docs/security/*` | n/a | 2026-05-19 | 2026-05-19 |
| R-009 | No CI security gates on PRs | cross-cutting | Med | Med | Open | Future: `.github/workflows/security.yml` running pre-commit hooks + `/security-audit` scanners | Pre-commit + skill catch locally; solo dev reduces risk window | 2026-05-19 | 2026-05-19 |
| R-010 | Job cancellation marks status but doesn't kill subprocess | A9 (DoS, not direct) | Low | Low | Accepted | Documented as AD-3 | Single-user, single-host; long-running jobs are bounded by `nohup` parent | 2026-05-19 | 2026-05-19 |
| R-011 | Branch protection on `main` not enforced (solo dev convention) | TB7 | Med | Low | Accepted | None | Small commit cadence; pre-commit on dev machine | 2026-05-19 | 2026-05-19 |
| R-012 | Logs ephemeral on Railway (no log shipping) | repudiation | Low | Med | Open | Future: ship to a log aggregator | Audit log written + read via `/api/jobs/logs` short-term | 2026-05-19 | 2026-05-19 |
| R-013 | `npm audit` reports 14 vulnerabilities (1 low / 4 moderate / 9 high) after eslint-plugin-security install | A4 | Med | Low | Open | Triage via `/security-audit` — likely all transitive deps of dev tooling (ESLint, build chain), not in runtime bundle | Vulns not in shipped JS; only affect build env on dev machine | 2026-05-19 | 2026-05-19 |
| R-014 | `tarfile.extractall()` in `/api/sync/upload-data` | A2, A8 | Med | Low | Accepted | Member names validated against path traversal at `kite-api/app/api/sync.py:100-102` (April audit #12); extraction is sandboxed in a temp dir before files are copied into the target | Endpoint requires authenticated upload; only `.tar.gz`/`.tgz` accepted; target dir is whitelisted via `ALLOWED_UPLOAD_DIRS` | 2026-05-19 | 2026-05-19 |
| R-015 | `pickle.load()` of pipeline shared-state cache | A9 (RCE via untrusted pickle) | Med | Low | Accepted | Cache file is written by `save_to_cache` in the same process tree onto local disk under our control; never loaded from network or user-supplied paths; schema-version check at `scripts/pipeline_core.py:118` rejects malformed objects | If an attacker can write to the cache path they already have local file write — bigger problem | 2026-05-19 | 2026-05-19 |
| R-016 | Dockerfile lacks `USER` directive (semgrep `missing-user-entrypoint`) | TB7 (host privilege) | Low | Low | Accepted | The Dockerfile creates `appuser` and the `/entrypoint.sh` runs storage init as root then drops to appuser via `gosu`. This is intentional — Railway's persistent `/data` volume needs root for initial chown before runtime. False positive against the naive "must have USER directive" rule. | App runs as `appuser` at runtime; verified at `kite-api/Dockerfile:50` + `scripts/entrypoint.sh` | 2026-05-19 | 2026-05-19 |
| R-017 | Semgrep `ssrf-via-requests` flags HTTP calls in API clients | A1, A8 (data exfil via redirected calls) | Low | Low | Accepted | All 4 flagged callsites (`eodhd_client.py:73`, `truedata_client.py:46,83`, `upload_price_data.py:52`) derive their URL from a fixed module-level `BASE`/`AUTH_URL`/`HISTORY_BASE` constant or a CLI arg controlled by the operator — the host component is never user-supplied. SSRF requires control of the host; only the path varies. | Inline `# nosemgrep` comments at each callsite reference this row | 2026-05-19 | 2026-05-19 |
| R-018 | 30+ Python dep CVEs surfaced by pip-audit + trivy (May 2026) | A1, A3, A5 (varying paths) | High | Med | Open | Required upgrades: `cryptography 46.0.3→46.0.5+`, `urllib3 2.6.3→2.7+`, `requests 2.32.5→2.33+`, `pillow 11.3.0→latest`, `mako 1.3.10→latest`, `pyasn1 0.6.1→latest`, `pyopenssl 25.3.0→latest`, `python-dotenv 1.2.1→latest`, `python-multipart 0.0.20→latest`, `twisted 25.5.0→latest`, `ecdsa 0.19.1→latest`, `curl_cffi 0.13.0→latest`. Coordinated upgrade PR with `pytest` + smoke test. **Target: 2026-06-19** (4 weeks). | All vulnerabilities require attacker-controlled input (e.g. crafted PSD images for Pillow, malicious DNS for cryptography); attack surface is bounded. Internet exposure is via `/api/sync/upload-data` (auth-gated tarball) and `/api/system/callback` (single-use Zerodha token). | 2026-05-19 | 2026-05-19 |
| R-019 | Next.js 16.1.6 has 7 CVEs (trivy + npm-audit, May 2026) | A4 (auth bypass, SSRF, DoS) | High | Med | Open | Upgrade Next.js to the latest 16.x patch release that resolves: middleware/proxy bypass (CVE-2026-44573/-44574/-44575/-45109), WebSocket-upgrade SSRF (CVE-2026-44578), Cache Components DoS (CVE-2026-44579), Server Components DoS (GHSA-8h8q-6873-q5fj, GHSA-q4gf-8mx6-v5v3). Coordinated upgrade — run `npm run build` + manual flow checks. **Target: 2026-06-02** (2 weeks; auth-bypass CVEs warrant faster turnaround). | Auth is enforced at the backend (Railway FastAPI) via JWT; even if a Next.js middleware bypass occurs, downstream `Depends(get_current_user)` still gates the data. | 2026-05-19 | 2026-05-19 |
| R-020 | `kite-api/.env.production` exists on local dev disk with real Postgres URL | A5 | High (if leaked) | Low | Closed (2026-05-19) | File deleted by user — was stale (Feb 14, no code referenced it; Railway injects `DATABASE_URL` via its own env-var system). Trufflehog re-scan on `kite-api/` clean. If sync scripts need the URL in the future, fetch it on-demand from Railway dashboard or pass via `--database-url` CLI arg. | Gitignore present (`kite-api/.gitignore:41`); file no longer exists on disk | 2026-05-19 | 2026-05-19 |
| R-021 | CSP allows `'unsafe-inline'` + `'unsafe-eval'` on `script-src` | A4 (XSS execution) | Low | Low | Accepted | Next.js + React 19 require both directives — `'unsafe-eval'` for client-side route prefetching and dev HMR; `'unsafe-inline'` for hydration scripts. A nonce-based CSP would require restructuring every server component that renders inline scripts and is significant work. Current CSP still provides origin allowlist (`script-src 'self' https://accounts.google.com https://*.gstatic.com`), `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`, and `connect-src` origin restriction — defense in depth without script-execution containment. | XSS prevention also relies on React's default escaping, `eslint-plugin-security` (closes R-007), no `dangerouslySetInnerHTML` usage, and CSP `connect-src` blocking exfiltration to attacker-controlled hosts. | 2026-05-19 | 2026-05-19 |
| R-022 | Universe filter is frontend-only — clients can fetch admin-only universes (`nse500`, `nifty100`, `nifty250`) via direct API call | A8 (cross-product data exposure; UX-consistency gap, not a secret leak) | Low | Low | Open | Phase 2 of the client portal hides legacy research universes from the UI selector (`getVisibleUniverseIds` in `kite-dashboard/src/lib/universes.ts`). The backend `get_current_user` does not reject `universe=nse500/nifty100/nifty250` from a client-role caller. Planned fix (TASKS.md item 2.2 in `tasks/client_portal/`): add a `require_client_universe` helper that 403s non-admin requests to admin-only universes; apply to all 20 client-read endpoints. | The legacy-universe data is not secret — it's the same L6 momentum algorithm with different stock-list slices, already documented in `docs/security/attack-surface.md`. Admin-mutation endpoints (job, sync, schedule) remain backend-gated via `require_admin` and are unaffected. | 2026-05-20 | 2026-05-20 |

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
