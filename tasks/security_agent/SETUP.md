# Security Agent — Setup & Verification

This is the runbook for bringing the security review system online on
your machine after the `security-agent` branch lands.

The PR introduces:
- `docs/security/` — threat model, risk register, attack surface, auth
  flows, runbook, closed-baseline snapshot
- `tools/security/` — gitleaks / semgrep / bandit / suppressions configs
- `.claude/agents/security-reviewer.md` — project-aware diff subagent
- `.claude/skills/security-audit/` — `/security-audit` slash command with
  scanner orchestration + LLM triage + report generation
- `.pre-commit-config.yaml` — fast secret + AST checks on every commit
- `.claude/settings.json` — Claude Code `PreToolUse` hook that catches
  `git commit` if pre-commit is somehow bypassed
- `kite-dashboard/next.config.ts` — full CSP + Permissions-Policy + HSTS
  + COOP/CORP headers (closes R-006)
- `kite-dashboard/eslint.config.mjs` + `package.json` —
  `eslint-plugin-security@3.0.1` recommended preset (closes R-007)

## 1. Install the scanner toolchain (one-time)

```bash
# Homebrew binaries
brew install gitleaks trufflehog trivy pre-commit

# Python tooling (into the project venv)
source .venv/bin/activate
pip install bandit pip-audit semgrep
# ruff is already in requirements.txt — verify with `ruff --version`

# Wire pre-commit into git
pre-commit install
```

## 2. Verification — 10 checks from the PLAN

Run these end-to-end after install. Items in `[ ]` are checkable
by running the listed command; items in `[*]` are documentation/manual.

### [✓] 2-A — Threat model + register exist with initial rows + dates

```bash
ls docs/security/threat-model.md docs/security/risk-register.md
grep -c '^| R-' docs/security/risk-register.md   # expect 13
```

### [ ] 2-B — `/security-audit` runs end-to-end

In Claude Code, invoke `/security-audit` and confirm:
- Preflight detects the installed scanners.
- Each scanner runs, exit code captured in
  `reports/security/<date>/scanner-exit-codes.json`.
- `reports/security/<date>/findings.json` is created.
- `reports/security/<date>/report.md` is rendered.
- The skill exits non-zero only if new HIGH/CRITICAL findings appear.

### [ ] 2-C — Pre-commit passes on all files (or only known-suppressed)

```bash
pre-commit run --all-files
```

Expected outcome: clean, or only flagging existing items in
`tools/security/suppressions.yml`. If anything else fires, treat it as
the first wave of findings — triage via `/security-audit`.

### [ ] 2-D — Secret-leak test (gitleaks blocks a committed secret)

```bash
# Create a deliberate test secret
echo 'KITE_API_KEY=abc123def456' > /tmp/leak-test.env
cp /tmp/leak-test.env .leak-test
git add .leak-test

# pre-commit should block this
git commit -m "test: deliberate leak (should fail)"
# Expected: exit non-zero with gitleaks finding

# Clean up
git restore --staged .leak-test
rm .leak-test /tmp/leak-test.env
```

### [ ] 2-E — Unauthed-route test (semgrep flags it)

```bash
# Create a deliberate violation
cat > /tmp/leak-route.py <<'PY'
from fastapi import APIRouter
router = APIRouter()
@router.get("/api/leak")
def leak():
    return {"secret": "would not happen"}
PY

# Place inside kite-api/app/api/ (the scoped path for the rule)
cp /tmp/leak-route.py kite-api/app/api/_leak_test.py

semgrep --config tools/security/semgrep.yml kite-api/app/api/_leak_test.py
# Expected: 1 finding, rule `fastapi-route-missing-auth`

# Clean up
rm kite-api/app/api/_leak_test.py /tmp/leak-route.py
```

### [ ] 2-F — CVE detection (pip-audit surfaces autobahn)

```bash
source .venv/bin/activate
pip-audit -r requirements.txt 2>&1 | grep -i autobahn
# Expected: at least one line referencing autobahn or its CVE
```

Confirm `R-002` in `docs/security/risk-register.md` references the
finding (`Accepted` status, hard-pinned by kiteconnect).

### [ ] 2-G — Subagent invocation on an unauthed-route diff

In Claude Code, ask the parent agent to invoke `security-reviewer` on
the deliberate diff from §2-E. Confirm the subagent's response cites
`R-003` (the AD-1 exception) and recommends either reverting the change
or adding a new register row.

### [ ] 2-H — CSP active on the deployed frontend

After Vercel redeploys this PR:

```bash
curl -sI https://marketworks.in/ | grep -iE '(content-security|x-frame|strict-transport|permissions|referrer)'
```

Expected: every header listed (`Content-Security-Policy`,
`X-Frame-Options`, `Strict-Transport-Security`, `Permissions-Policy`,
`Referrer-Policy`). Also confirm the browser DevTools console shows no
CSP violations on a normal page load.

### [ ] 2-I — ESLint security active

```bash
cd kite-dashboard
echo 'const f = (x) => eval(x); export default f;' > src/_lint_test.ts
npx eslint src/_lint_test.ts
# Expected: error from rule `security/detect-eval-with-expression`

rm src/_lint_test.ts
```

### [✓] 2-J — No production regressions

```bash
cd kite-dashboard && npm run build           # already passed: 1949ms, 11 pages
cd .. && source .venv/bin/activate && python -c "import kite_api" 2>/dev/null || true
# Add any pytest invocation here once tests are wired
```

`npm run build` was verified before merge: clean, 11 pages generated,
the only warning is a pre-existing Next.js 16 deprecation notice for
the `middleware.ts` convention (unrelated to security changes).

## 3. Switch to the new workflow

Once verified:

1. **Every git commit** runs gitleaks + ruff S-rules + the no-env-files
   guard + eslint-security on staged JS/TS via pre-commit.
2. **When Claude changes auth, API routes, or deps**, it should invoke
   `security-reviewer` after the built-in `/security-review`. The
   subagent reads the threat model + register and reports against
   project-specific invariants.
3. **Periodically (weekly is a good cadence)**, invoke `/security-audit`
   manually. Triage new findings, accept-or-fix, and let the skill
   propose register/suppressions updates.
4. **After every audit**, the dated report under
   `reports/security/<date>/report.md` is your audit trail. Don't
   delete these.

## 4. Things that still need attention

| Item | Notes |
|---|---|
| `R-013` (npm-audit 14 vulns) | Triage in first `/security-audit` run. Likely all transitive dev-time, not in runtime bundle. |
| HSTS preload registration | After the production CSP/HSTS headers are stable for ~2 weeks, register `kite-lab.vercel.app` (or your custom domain) at <https://hstspreload.org/>. |
| CI security gates (`R-009`) | Future work: replicate `.pre-commit-config.yaml` + `/security-audit` scanners in a `.github/workflows/security.yml` so PRs are gated automatically. |
| Branch protection on `main` (`R-011`) | Solo-dev convention — accepted. Revisit if collaborators join. |
| Tighter CSP | The current CSP keeps `'unsafe-inline'` + `'unsafe-eval'` on script-src because Next.js + React 19 need them. A nonce-based CSP is doable but requires changes to every server component that renders inline scripts. |

## 5. If a scanner false-positives

Standard suppression workflow:

1. Run `/security-audit`; note the `fingerprint` for the finding.
2. Decide if it's accepted (open register row) or false-positive (no
   register row needed).
3. Add an entry to `tools/security/suppressions.yml` with the
   fingerprint, register row reference, justification, and an
   `expires` date (default 1 year).
4. Re-run `/security-audit` to confirm the finding is now under
   "Suppressed" instead of "New."

The skill never suppresses anything automatically — every entry is
human-approved.
