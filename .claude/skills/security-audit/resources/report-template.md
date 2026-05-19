# Security Audit — {DATE}

**Branch:** `{BRANCH}` @ `{COMMIT}`
**Duration:** {DURATION}
**Run by:** `/security-audit` skill

---

## Scanner summary

| Scanner | Status | Findings | Raw output |
|---|---|---|---|
| gitleaks | {STATUS_GITLEAKS} | {COUNT_GITLEAKS} | `raw/gitleaks.json` |
| ruff (S) | {STATUS_RUFF} | {COUNT_RUFF} | `raw/ruff.json` |
| bandit | {STATUS_BANDIT} | {COUNT_BANDIT} | `raw/bandit.json` |
| semgrep | {STATUS_SEMGREP} | {COUNT_SEMGREP} | `raw/semgrep.json` |
| pip-audit | {STATUS_PIP_AUDIT} | {COUNT_PIP_AUDIT} | `raw/pip-audit*.json` |
| npm-audit | {STATUS_NPM_AUDIT} | {COUNT_NPM_AUDIT} | `raw/npm-audit.json` |
| trufflehog | {STATUS_TRUFFLEHOG} | {COUNT_TRUFFLEHOG} | `raw/trufflehog.json` |
| trivy | {STATUS_TRIVY} | {COUNT_TRIVY} | `raw/trivy.json` |

**Totals:** {TOTAL_NEW} new · {TOTAL_CARRIED} carried over · {TOTAL_RESOLVED} resolved · {TOTAL_SUPPRESSED} suppressed.

---

## New findings

> Triage classification:
> - `🔴 needs-fix` — true positive requiring code change
> - `🟡 accept` — true positive, accepted (will open register row)
> - `⚪ false-positive` — scanner artifact (will add suppression only)
> - `❓ judgement` — needs human review

{NEW_FINDINGS_SECTION}

If the section above is empty: no new findings this run.

---

## Carried-over findings (still open from previous runs)

{CARRIED_FINDINGS_SECTION}

---

## Resolved since last audit

{RESOLVED_FINDINGS_SECTION}

---

## Suppressions past expiry

{EXPIRING_SUPPRESSIONS_SECTION}

---

## Proposed register changes

See `register-proposal.md` in this directory for ready-to-paste markdown +
YAML diffs.

Summary:

- **Bump `Last reviewed`** on {COUNT_BUMP} rows (carried-over findings).
- **Open** {COUNT_NEW_ROWS} new register rows for true-positive new findings.
- **Candidate-for-Closed**: {COUNT_CLOSE_CANDIDATES} rows in `Mitigating` status whose corresponding findings are no longer present (human verifies before closing).

---

## Next actions

In priority order:

{NEXT_ACTIONS_SECTION}

---

## Run metadata

```json
{METADATA_JSON}
```
