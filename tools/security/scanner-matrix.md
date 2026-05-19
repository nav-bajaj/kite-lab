# Scanner Matrix

Quick reference for what each scanner catches, how to install it, and
how to suppress a finding. Used by `/security-audit` (which runs them)
and humans (who triage results).

---

## Overview

| Scanner | Domain | Mode | Block? |
|---|---|---|---|
| [gitleaks](https://github.com/gitleaks/gitleaks) | Secrets in code + git history | pre-commit + audit | Hard fail |
| [ruff](https://docs.astral.sh/ruff/) (`S` ruleset) | Python AST (Bandit-equivalent fast checks) | pre-commit | Hard fail on new |
| [bandit](https://bandit.readthedocs.io/) | Python AST (deeper, slower) | audit | Triage |
| [pip-audit](https://github.com/pypa/pip-audit) | Python dep CVEs | audit (+ optional weekly cron) | Triage |
| `npm audit` | Node dep CVEs | audit + pre-commit (warn) | Triage |
| [eslint-plugin-security](https://github.com/eslint-community/eslint-plugin-security) | JS/TS AST | pre-commit + audit | Hard fail on staged |
| [semgrep](https://semgrep.dev/) | Project-specific + OWASP rules | audit | Triage |
| [trufflehog](https://github.com/trufflesecurity/trufflehog) | Secrets (cross-check gitleaks) | audit | Triage |
| [trivy](https://github.com/aquasecurity/trivy) `fs` | Dockerfile + dep CVEs | audit | Triage |

All free, all local. No paid licenses required.

---

## Installation

```bash
# macOS (Homebrew)
brew install gitleaks trufflehog trivy

# Python tooling (into the project venv)
source .venv/bin/activate
pip install bandit pip-audit semgrep
# ruff is already in requirements.txt

# Node (per-project, in kite-dashboard)
cd kite-dashboard
npm install --save-dev eslint-plugin-security
```

The `/security-audit` skill's preflight step checks for each binary and
offers the install command if missing.

---

## What each scanner catches

### gitleaks

Secrets in source files and git history. Detects:

- AWS keys (`AKIA…`), GCP service accounts, Azure connection strings
- Stripe keys, Slack tokens, GitHub PATs
- Generic high-entropy strings near keywords like `password`, `secret`, `api_key`
- **Project-custom rules** (see `.gitleaks.toml`): Kite API key, Kite API secret, TOTP secret, JWT_SECRET, access_token content

Allowlist: `tools/security/.gitleaks.toml` → `[allowlist]` paths + regexes
covers template files, security docs, lockfiles, generated bundles.

### ruff (`S` ruleset)

A subset of Bandit, implemented in Rust. Fast enough for pre-commit.
Covers:

- `S105`-`S107` — hardcoded passwords
- `S301`-`S321` — insecure deserialization (pickle, marshal, exec)
- `S501`-`S506` — insecure SSL / certificate validation
- `S601`-`S612` — shell injection patterns

Run in pre-commit on staged `.py` files only (`--fix` is safe for most
`S` rules).

### bandit

Deeper Python AST analysis. Runs in the audit only because it's slower.
Config: `tools/security/bandit.yaml` (skips B101, B404, B603, B607, B105
— see file for rationale, each tied to a design decision).

### pip-audit

Cross-references `requirements.txt` versions against the OSV database
and PyPI advisory database. One finding per CVE.

Run weekly (via `/loop` or cron — out of scope for this branch but
documented in `docs/security/README.md`).

### npm audit

Built-in npm tool. We run with `--audit-level=high` so low/moderate
findings don't block. Run in `kite-dashboard/`.

### eslint-plugin-security

JS/TS AST checks. Covers:

- Detect non-literal regex (ReDoS)
- Detect non-literal `require`
- Detect `eval` with dynamic input
- Detect `Buffer.noAssert` etc.

Configured in `kite-dashboard/eslint.config.mjs` (added in chunk 5).

### semgrep

Both built-in registry rules (`p/owasp-top-ten`, `p/python`, `p/javascript`)
and project-specific rules in `tools/security/semgrep.yml`:

| Rule ID | What |
|---|---|
| `fastapi-route-missing-auth` | Routes outside `/api/system/*` + `/api/health` need `Depends(get_current_user)` |
| `next-public-secret-leak` | `NEXT_PUBLIC_*SECRET/KEY/PASSWORD/TOKEN` ships to browser |
| `subprocess-shell-true` | `shell=True` or `os.system(...)` |
| `token-file-write-no-mode` | Writing `access_token.txt` / `session.json` without 0o600 |
| `sql-string-interpolation` | f-string / concat / `%` formatting in `text()` or `.execute()` |
| `dynamic-code-execution` | `eval`, `exec`, dynamic `Function()`, string `setTimeout` |
| `log-emits-secret-field` | Logger call references a known sensitive field name |
| `react-dangerously-set-inner-html` | Audit and confirm sanitization |
| `ssrf-via-requests` | `requests.get(...)` with non-literal URL |
| `fastapi-body-raw-dict` | Endpoint takes raw `dict = Body(...)` instead of Pydantic model |

### trufflehog

Deeper secret scanning — runs git history + entropy heuristics +
verifier endpoints (network-active validation for some secret types).
Used as a cross-check against gitleaks; if either flags a secret, it's
worth investigating.

### trivy

`trivy fs` scans the filesystem for known CVEs in Python + Node deps,
plus Dockerfile best-practice issues (root user, no HEALTHCHECK, etc.).
We already use `appuser` + `gosu` so most Dockerfile rules pass; trivy
is mostly for deps.

---

## How to suppress a finding

1. **Confirm it's a genuine false positive or accepted risk.** Read the
   finding, the code, and the relevant rows in `risk-register.md`.
2. **Create or update a risk register row.** Set status to `Accepted` if
   it's a design decision, or `Mitigating` if you plan a fix.
3. **Add an entry to `tools/security/suppressions.yml`** with the
   fingerprint (from the audit report), rule ID, file + line,
   register row ID, justification, and an `expires` date (default 1 year).
4. **Re-run `/security-audit`** and confirm the finding is gone from
   the "new findings" section.

If `expires` is in the past, `parse_findings.py` re-surfaces the
suppression as a re-review item.

---

## Adding a new project-specific rule

When `/security-audit` triages a finding that isn't covered by existing
rules but should be enforced going forward:

1. Open `tools/security/semgrep.yml`.
2. Write a new rule. Test with:
   ```bash
   semgrep --config tools/security/semgrep.yml --test
   semgrep --config tools/security/semgrep.yml kite-api/  # spot-check
   ```
3. Document the rule in this matrix (the table under "semgrep" above).
4. Open a register row if the rule encodes a previously implicit invariant.
5. Commit. The next `/security-audit` run will enforce it.
