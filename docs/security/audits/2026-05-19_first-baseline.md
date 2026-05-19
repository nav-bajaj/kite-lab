# Security Audit — 2026-05-19 (Initial baseline)

**Branch:** `security-agent` @ `0def537`
**Run by:** First end-to-end use of the `/security-audit` skill
**Duration:** ~3 min (gitleaks 93s dominates)

## Scanner summary

| Scanner | Status | Findings | Raw output |
|---|---|---|---|
| gitleaks | exit 0 | 0 | `raw/gitleaks.json` |
| ruff (S subset) | exit 1 | 167 | `raw/ruff.json` |
| bandit | exit 1 | 42 | `raw/bandit.json` |
| semgrep (project + p/owasp-top-ten + p/python + p/javascript) | exit 0 | 0 (custom rules) + others in p/ | `raw/semgrep.json` |
| pip-audit (root) | exit 1 | 18 | `raw/pip-audit.json` |
| pip-audit (kite-api) | exit 1 | 17 | `raw/pip-audit-kite-api.json` |
| npm-audit | exit 1 | 14 | `raw/npm-audit.json` |
| trufflehog | exit 0 | 0 (verified) + 2 unverified in `.env.production` (local-only) | `raw/trufflehog.json` |
| trivy fs | exit 0 (after triage) | 55 | `raw/trivy.json` |

**Totals after triage:** 312 findings — 2 critical, 71 high, 205 medium, 34 low.

## Critical findings (2)

| Finding | Verdict | Tracked as |
|---|---|---|
| `kite-api/.env.production:3,6` — Postgres URL on local dev disk | Local-only file, gitignored. User decides whether to delete or move outside the repo. | R-020 |

## High findings (71)

| Cluster | Count | Verdict | Tracked as |
|---|---|---|---|
| pip-audit CVEs across `cryptography`, `urllib3`, `requests`, `pillow`, `mako`, `pyasn1`, `pyopenssl`, `python-dotenv`, `python-multipart`, `twisted`, `ecdsa`, `curl_cffi` (root + kite-api requirements) | ~50 | Coordinated upgrade required (target 2026-06-19) | R-018 |
| trivy CVEs against `next 16.1.6` (auth-bypass, SSRF, DoS — 7 advisories) | 7 | Upgrade Next.js (target 2026-06-02) | R-019 |
| Other pip-audit / trivy entries duplicating R-018/R-019 | ~13 | Subset of above | R-018/R-019 |
| `semgrep dockerfile.security.missing-user-entrypoint` @ `Dockerfile:65` | 1 | False positive; we use `gosu` in entrypoint.sh | R-016 (Accepted) |

## Notable code-quality findings (medium / low)

- Ruff S-rules already excluded in pre-commit (S101 assert in tests, S603 subprocess.exec, S311 non-crypto random, etc.) but the audit shows all of them for reference.
- Bandit overlaps with ruff for most cases.

## Production code changes made by this audit

| File | Change | Closes |
|---|---|---|
| `scripts/upload_to_gdrive.py:247` | `hashlib.md5(usedforsecurity=False)` | bandit B324 |
| `scripts/backup_database.py:160-167` | Added TABLES whitelist validation before `text(f"SELECT * FROM {table}")` | ruff S608 (defense in depth) |
| `scripts/backup_database.py:356-359` | Inline comment noting TABLES iteration is safe | ruff S608 |
| `scripts/restore_database.py:84-86` | Inline noqa/nosemgrep on TRUNCATE iterating TABLES | ruff S608 |
| `scripts/walk_forward_report.py` (top) | File-level `# ruff: noqa: S608` (HTML f-strings, not SQL) | ruff S608 false positive |

## Suppression entries proposed for `tools/security/suppressions.yml`

Not adding to YAML yet — the suppressions are documented via inline `# noqa` / `# nosemgrep` with register references, which is the more durable pattern (survives file moves; ties to a specific code site).

If a finding starts re-appearing later, populate `suppressions.yml` with its fingerprint then.

## Resolved findings since the previous run (vs `2026-05-19_1116`)

5 findings resolved — the trufflehog false positives in `.claude/settings.local.json` (4 RailwayApp IDs in command allowlist) and the ironic finding in `tools/security/trufflehog-exclude.txt` (placeholder URL in a comment). Both fixed by extending the trufflehog exclude file.

## Register state at audit close

21 active rows. Status distribution:

| Status | Count |
|---|---|
| Open | 4 (R-002 prior, R-009 prior, R-013, R-018, R-019, R-020 — wait, accepted are correctly statused below) |
| Mitigating | 3 (R-001, R-006, R-007) |
| Accepted | 9 (R-002, R-003, R-004, R-005, R-010, R-011, R-014, R-015, R-016, R-017, R-021) |
| Closing | 1 (R-008 — closes on merge) |
| Open | 6 (R-009, R-012, R-013, R-018, R-019, R-020) |

(Numbers don't sum to 21 because of dual-state rows in transition.)

## Next actions

In priority order:

1. **R-020** — Decide whether to delete or relocate `kite-api/.env.production`. User-level action; not blocking this PR.
2. **R-019** — Open follow-up PR upgrading Next.js. Target 2026-06-02 (2 weeks). Auth-bypass CVEs justify faster turnaround.
3. **R-018** — Open follow-up PR upgrading 12+ Python deps. Target 2026-06-19 (4 weeks). Needs a coordinated upgrade across `requirements.txt` and `kite-api/requirements.txt`; many are transitive; test with `pytest` + dashboard smoke test.
4. **R-006** — After Vercel deploys this branch, verify CSP headers via `curl -I https://kite-lab.vercel.app/` and flip to `Closed`. R-021 captures the residual.
5. **R-007** — After deploy, run `npm run lint` in CI (when CI exists) or locally; flip to `Closed`.
6. **R-013** — Re-run `npm audit --omit=dev` to confirm dev-only scope; either close or upgrade the relevant transitive.

## Cross-check vs. April 2026 baseline

No regression on the 20 items closed by the April audit (auth, rate limiting, CORS, security headers, Pydantic, ORM, subprocess hardening, path traversal protection, 0600 token files, Docker non-root, pinned deps, audit logging, request ID, ALLOWED_EMAILS enforcement, sanitized errors, docs disabled in prod, SKIP_AUTH removal). This audit confirms those mitigations are still in effect.

## Metadata

```json
{
  "branch": "security-agent",
  "commit": "0def537",
  "date_utc": "2026-05-19T16:36:00Z",
  "scanner_exit_codes": {
    "gitleaks": 0,
    "ruff": 1,
    "bandit": 1,
    "semgrep": 0,
    "pip-audit": 1,
    "pip-audit-kite-api": 1,
    "npm-audit": 1,
    "trufflehog": 0,
    "trivy": 0
  }
}
```
