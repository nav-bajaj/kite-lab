# Plan: Project-Aware Security Review System

## Context

Kite-Lab is a single-developer quantitative trading project that places real trades against the Zerodha API and stores user trade history in a hosted Postgres. The April 2026 security audit (`tasks/security/README.md`) closed 23 issues across critical/high/medium severities — the baseline is strong (JWT + OAuth + ALLOWED_EMAILS whitelist, rate limiting, security headers, Pydantic validation, ORM-only DB access, subprocess.exec with arg whitelisting, 0600 perms on token files, non-root Docker, pinned deps, audit logging).

What's missing is **the system that keeps the project secure going forward**: a codified threat model so changes can be evaluated in context, a risk register so deferred/accepted risks don't get forgotten, automated scanners so secret leaks and CVE-ridden deps are caught, and review machinery that knows this project specifically so it can complement the generic built-in `/security-review` skill.

The user wants "as secure as a project developed by the leading technology companies of the world" — for a one-person project that means **layered, automatable, low-friction**: pre-commit catches fast wins, an on-demand `/security-audit` skill does deep scans + LLM triage + updates the register, and a project-aware `security-reviewer` subagent reviews diffs against the codified threat model.

All work lands on a new `security` branch. Three small production fixes (CSP header, ESLint security plugin, evaluate `autobahn` removal) are bundled to demonstrate the end-to-end workflow closing real risks.

## Architecture

Five layers, increasing depth, decreasing frequency:

| Layer | Trigger | Tool | Latency |
|---|---|---|---|
| 1. Pre-commit | every `git commit` | gitleaks, ruff `S`, eslint security on staged files | <2s |
| 2. Subagent `security-reviewer` | Claude reviews a diff touching auth/api/deps | LLM with threat-model preloaded | seconds |
| 3. Built-in `/security-review` | user invokes on pending changes | generic Claude skill (already installed) | seconds |
| 4. Skill `/security-audit` | user invokes deliberately or weekly | bandit, semgrep, pip-audit, npm audit, trufflehog, trivy | minutes |
| 5. Living docs | continuous | threat-model.md, risk-register.md, attack-surface.md | n/a |

The skill and subagent both read the docs; the skill *updates* them.

## File layout

```
.claude/
  agents/
    security-reviewer.md                    # project-aware change-review subagent
  skills/
    security-audit/
      SKILL.md                              # /security-audit entrypoint procedure
      scripts/
        run_scanners.sh                     # orchestrates all scanners → reports/security/<date>/raw/
        parse_findings.py                   # normalizes scanner output → findings.json
        update_register.py                  # merges new findings into risk-register.md
      resources/
        scanner-matrix.md                   # which scanner catches what, install commands
        report-template.md                  # markdown skeleton for audit reports

docs/
  security/
    README.md                               # index, how to invoke, layer summary
    threat-model.md                         # STRIDE + assets + trust boundaries
    risk-register.md                        # the table (schema in §"Risk register")
    auth-flows.md                           # OAuth, JWT, NextAuth text diagrams
    attack-surface.md                       # every endpoint + auth status + intentionality
    runbook.md                              # key rotation, token revocation, incident response
    audits/
      2026-04-baseline.md                  # snapshot of the closed 23 items
      .gitkeep                              # future dated reports land here

tools/
  security/
    .gitleaks.toml                          # allowlist for known-safe matches
    semgrep.yml                             # project rules (e.g. FastAPI unauthed route detector)
    bandit.yaml                             # bandit config + intentional skips
    suppressions.yml                        # accepted risks, keyed to register row IDs

reports/
  security/
    .gitkeep                                # gitignored except .gitkeep; per-run dirs go here

.pre-commit-config.yaml                     # gitleaks, ruff S-rules, eslint-security
.gitignore                                  # add reports/security/* (except .gitkeep)

# Production fixes bundled to demonstrate the workflow
kite-dashboard/next.config.ts               # add CSP + security headers (closes R-006)
kite-dashboard/eslint.config.mjs            # add eslint-plugin-security (closes R-007)
kite-dashboard/package.json                 # add eslint-plugin-security dep
requirements.txt                            # evaluate removal of autobahn==19.11.2 (R-002)
```

## Threat model outline (`docs/security/threat-model.md`)

Sections:

1. **Assets** (ranked by impact)
   - Zerodha API key/secret + TOTP secret → ability to place trades on user's account
   - JWT_SECRET, NEXTAUTH_SECRET → session forgery
   - DATABASE_URL → trade history exfiltration, write access
   - `access_token.txt`, `session.json` → temporary trading authority (24h)
   - Google OAuth client secret → impersonation flow
   - User trade data in Postgres → PII (emails) + financial history

2. **Actors**
   - Authorized user (1 whitelisted email)
   - Internet attacker (unauthenticated, scanning Railway/Vercel)
   - Malicious dependency author (supply chain)
   - Compromised dev laptop / Mac mini
   - Compromised GitHub or CI account

3. **Trust boundaries** — browser↔Vercel; Vercel↔Railway API; Railway↔Zerodha; Railway↔Postgres; dev machines↔GitHub/Railway/Vercel.

4. **STRIDE applied to each boundary** — one bullet per category per boundary, cross-referenced to register rows.

5. **Out of scope** — physical, Python/Node interpreter supply chain, Zerodha-side breach, Railway/Vercel platform compromise.

## Risk register (`docs/security/risk-register.md`)

Markdown table; one row per risk. Columns:

```
ID | Title | Asset | Severity | Likelihood | Status | Control | Compensating control | Owner | Opened | Last reviewed
```

`Status` values: `Open`, `Mitigating`, `Closed`, `Accepted`, `Won't-fix`.

Initial rows:

| ID | Title | Sev | Status | Action |
|---|---|---|---|---|
| R-001 | No SAST in pre-commit/CI | Med | Mitigating | This PR adds pre-commit + skill |
| R-002 | `autobahn==19.11.2` abandoned transitive dep | Med | Mitigating | Evaluate removal; flag via `pip-audit` |
| R-003 | `/api/system/*` unauthenticated by design (OAuth bootstrap) | Med | Accepted | Documented; semgrep rule prevents *new* unauthed routes outside this prefix |
| R-004 | OAuth callback lacks state/nonce | Low | Accepted | Zerodha request_token is single-use; defense-in-depth tracked |
| R-005 | SSE token in query param (`/api/positions/stream`) | Med | Accepted | EventSource API limit; mitigations: short JWT TTL, audit log review |
| R-006 | No CSP header on Next.js frontend | Med | Mitigating | This PR: add CSP to `next.config.ts` |
| R-007 | No ESLint security plugin in dashboard | Low | Mitigating | This PR: add `eslint-plugin-security` |
| R-008 | No codified threat model / risk register | High (meta) | Closing | This PR delivers both |
| R-009 | No CI security gates | Med | Open | Documented as future; pre-commit lands first |
| R-010 | Job cancellation marks status but doesn't kill subprocess | Low | Accepted | Single-user, single-host; tracked |

## Tool integration matrix (`tools/security/scanner-matrix.md`)

| Tool | Scans | Mode | Install | Skill behavior |
|---|---|---|---|---|
| **gitleaks** | secrets in diff + git history | pre-commit + audit | `brew install gitleaks` | Hard fail; never auto-suppressed |
| **ruff** (`S` ruleset) | Python AST security checks | pre-commit | already in venv | Block on new; baseline existing |
| **bandit** | deeper Python AST + taint-ish | audit only | `pip install bandit` | Triage into findings.json |
| **pip-audit** | `requirements.txt` CVEs | audit (also weekly via `/loop`) | `pip install pip-audit` | One register row per CVE |
| **npm audit** | `package-lock.json` (level=high) | audit + pre-commit warn | bundled with npm | Same |
| **eslint-plugin-security** | JS/TS AST | pre-commit + audit | `npm i -D` | Block on staged files |
| **semgrep** | both stacks; project rules | audit | `pip install semgrep` | Triage; project rules in `tools/security/semgrep.yml` |
| **trufflehog** | deeper secret scan, cross-check gitleaks | audit only | `brew install trufflehog` | Cross-check |
| **trivy fs** | Dockerfile + deps | audit | `brew install trivy` | Container hardening |

All free, all local. Suppressions live in `tools/security/suppressions.yml` keyed to register IDs — no inline `# noqa` without a corresponding register row.

## `/security-audit` workflow

The SKILL.md procedure, executed step by step when invoked:

1. **Preflight** — verify scanners installed (gitleaks, bandit, pip-audit, semgrep, trufflehog, trivy, npm, ruff); warn + offer install commands for any missing. Verify on `security` branch or warn.
2. **Run** `scripts/run_scanners.sh` — each scanner writes raw output to `reports/security/<UTC-date>/raw/<tool>.json`.
3. **Normalize** — `parse_findings.py` produces `findings.json`: `{tool, severity, file, line, rule, message, fingerprint}`. `fingerprint = sha256(rule+file+line+snippet)` so we can dedupe across runs.
4. **Diff** new findings vs last run's `findings.json` and `suppressions.yml`.
5. **LLM triage** — for each new finding, cross-reference `threat-model.md` + `attack-surface.md`, classify `true-positive | false-positive | accepted-risk | needs-fix`, propose register row or fix.
6. **Register update** — `update_register.py` appends new rows for true-positives + accepted risks; bumps `Last reviewed` on re-confirmed rows.
7. **Report** — render `reports/security/<date>/report.md` from `resources/report-template.md`: scanner summary, new vs known findings, register delta, recommended next actions.
8. **Hand back** — print summary + register changes; do NOT auto-commit. User reviews.

## `security-reviewer` subagent

`.claude/agents/security-reviewer.md` frontmatter:

```yaml
---
name: security-reviewer
description: Project-aware security reviewer for kite-lab. Invoke after diffs touching kite-api/app/api/**, kite-dashboard/src/app/api/**, auth code, requirements.txt, or package.json. Knows the threat model, attack surface, and risk register.
model: opus
tools: Read, Grep, Glob, Bash
---
```

System prompt loads (read at invocation, not baked):
- `docs/security/threat-model.md`
- `docs/security/attack-surface.md`
- `docs/security/risk-register.md`
- The diff being reviewed (passed via prompt)

**Differentiator vs built-in `/security-review`:** built-in is generic ("is there SQL injection here?"). This subagent answers project-aware questions: *"This diff adds `/api/system/leak` — that namespace is intentionally unauthed per R-003, but the new route exposes JWT_SECRET in its response, which is a new state leak"*, *"This adds a dependency to `requirements.txt` — pip-audit should run before merge"*, *"This touches `/api/positions/stream` — does it worsen R-005?"*.

Claude invokes it automatically after diffs touching the watched paths; the user can also invoke explicitly. It runs *after* the built-in `/security-review` (generic checks first, project-aware second).

## Pre-commit (`.pre-commit-config.yaml`)

Tight scope, all fast (<2s on this repo):

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--select, S, --fix]
        files: \.(py)$
  - repo: local
    hooks:
      - id: eslint-security-staged
        name: ESLint security (staged files)
        entry: bash -c 'cd kite-dashboard && npx eslint --max-warnings 0 $(git diff --cached --name-only --diff-filter=ACM | grep -E "^kite-dashboard/.*\.(ts|tsx|js|jsx)$" | sed "s|kite-dashboard/||") 2>/dev/null || true'
        language: system
        pass_filenames: false
        stages: [commit]
      - id: gitignore-env-check
        name: Confirm .env files stay gitignored
        entry: bash -c '! git diff --cached --name-only | grep -qE "^\.env$|^\.env\.[^d]"'
        language: system
        pass_filenames: false
```

Also wire a PreToolUse hook in `.claude/settings.json` that runs `gitleaks protect --staged` before any Claude-issued `git commit` — defense in depth against an LLM that bypasses the local hook.

## Production fixes bundled (closes R-006, R-007, R-002)

1. **`kite-dashboard/next.config.ts`** — add CSP + missing security headers via `async headers()`. Tight CSP: `default-src 'self'`, allow `https://accounts.google.com` for OAuth, `https://kite-lab-production.up.railway.app` for API, `'unsafe-inline'` only for styles (Tailwind), `frame-ancestors 'none'`. HSTS + COOP/COEP/CORP set in production. Closes R-006.
2. **`kite-dashboard/eslint.config.mjs`** — add `eslint-plugin-security` recommended ruleset; baseline any existing findings into `eslint-disable` with register-row references. Closes R-007.
3. **`requirements.txt`** — run `pipdeptree` to confirm `autobahn==19.11.2` is a transitive dep, identify the parent, evaluate whether the parent can be updated/removed. If removable, remove and update register R-002 → Closed. If not, document the chain in register comment.

## Implementation steps (sequenced)

1. Create branch: `git checkout -b security`
2. Write threat-model.md, attack-surface.md, risk-register.md, runbook.md, auth-flows.md, README.md
3. Write 2026-04-baseline.md snapshot of the closed audit
4. Write `tools/security/` configs (gitleaks, semgrep, bandit, suppressions)
5. Write `.claude/agents/security-reviewer.md`
6. Write `.claude/skills/security-audit/SKILL.md` + supporting scripts + resources
7. Write `.pre-commit-config.yaml`; install pre-commit; run `pre-commit run --all-files` to baseline
8. Add PreToolUse gitleaks hook to `.claude/settings.json`
9. Add `reports/` to `.gitignore` except `.gitkeep`
10. Bundle production fixes: CSP in `next.config.ts`, eslint-plugin-security in `eslint.config.mjs`, evaluate autobahn
11. Run `/security-audit` end-to-end; confirm reports/security/<today>/report.md generates; register updates
12. Test the subagent: deliberately add an unauthenticated route to `kite-api/app/api/`, invoke subagent, confirm it cites R-003
13. Commit in logical chunks (docs first, tools, then agent+skill, then pre-commit, then prod fixes)
14. Open PR to main with summary referencing closed register rows

## Verification

End-to-end checks that prove the system works:

1. **`/security-audit` runs clean** — produces `reports/security/<today>/report.md`; exits non-zero only on *new* high-severity findings.
2. **Threat model + register exist** with all 10 initial rows; dates set.
3. **Pre-commit passes** `pre-commit run --all-files`, or fails only on items already in `suppressions.yml`.
4. **Secret-leak test** — create a commit with `KITE_API_KEY=test12345` in a file; gitleaks blocks the commit.
5. **Unauthed-route test** — add `@router.get("/api/leak")` with no `Depends(get_current_user)`; semgrep flags it; subagent cites R-003 when invoked on the diff.
6. **CVE detection test** — `pip-audit` finds `autobahn`; register R-002 reflects it (or shows Closed if removed).
7. **Subagent invocation test** — invoke `security-reviewer` on a diff that adds a `requirements.txt` line; confirm it requests `pip-audit` rerun.
8. **CSP active** — load deployed frontend, confirm CSP header present, no console violations.
9. **ESLint security active** — introduce `eval(userInput)` in a TS file; lint fails.
10. **No production code regressions** — `pytest` (if present) + `npm run build` + `npm run typecheck` all pass.

## Critical files

- /Users/navdeep/kite-lab/.claude/skills/security-audit/SKILL.md
- /Users/navdeep/kite-lab/.claude/agents/security-reviewer.md
- /Users/navdeep/kite-lab/docs/security/threat-model.md
- /Users/navdeep/kite-lab/docs/security/risk-register.md
- /Users/navdeep/kite-lab/docs/security/attack-surface.md
- /Users/navdeep/kite-lab/.pre-commit-config.yaml
- /Users/navdeep/kite-lab/tools/security/semgrep.yml
- /Users/navdeep/kite-lab/kite-dashboard/next.config.ts
- /Users/navdeep/kite-lab/kite-dashboard/eslint.config.mjs

## Reused existing assets

- `tasks/security/README.md` — source of truth for the closed-baseline snapshot
- `kite-api/app/middleware/error_handlers.py` — existing sanitized error pattern, referenced in threat model
- `kite-api/app/middleware/request_logger.py` — existing audit log pattern, referenced in runbook
- `kite-api/app/auth.py` — JWT + ALLOWED_EMAILS code path, documented in auth-flows.md
- Built-in `/security-review` Claude Code skill — kept; subagent runs *after* it
- `.gitignore` — already covers `.env`, `access_token.txt`, `session.json`; extend only for `reports/security/*`

## Out of scope (future work; tracked as register rows)

- GitHub Actions CI workflow that runs the same scanners on every PR (R-009)
- SBOM generation (cyclonedx)
- Sentry / log shipping integration
- External pen test
- Migrating off `autobahn` if parent dep is locked (depends on R-002 evaluation outcome)
