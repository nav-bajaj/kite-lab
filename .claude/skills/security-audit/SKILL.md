---
name: security-audit
description: Run a project-wide security audit on kite-lab. Orchestrates gitleaks, ruff S-rules, bandit, semgrep, pip-audit, npm audit, trufflehog, and trivy; normalizes their output; diffs against the last run; triages new findings against the threat model and risk register; writes a dated markdown report under reports/security/<UTC-date>/; proposes risk-register updates. Invoke when you want a deeper-than-pre-commit audit or before a release.
---

# /security-audit

This skill performs a structured, project-wide security audit. It does
not modify production code or auto-close risks — every change to the
risk register is proposed and handed to the human for review.

Run from the repo root with the project venv activated.

## Procedure

Follow these steps in order. Do not skip steps unless the user explicitly
says to.

### Step 1 — Preflight

1. Confirm the working tree is clean *or* the user explicitly accepts an
   audit of uncommitted changes. Run `git status --short`. If dirty,
   ask the user before proceeding.
2. Confirm we're on `security-agent`, `security`, or another branch the
   user named. Run `git branch --show-current`. Warn if on `main`.
3. Activate the venv: `source .venv/bin/activate`.
4. Check each scanner binary is installed:
   - `gitleaks --version`
   - `ruff --version`
   - `bandit --version`
   - `pip-audit --version`
   - `semgrep --version`
   - `trufflehog --version`
   - `trivy --version`
   - `npm --version` (for `npm audit`)
   For any missing tool, print the install command from
   `tools/security/scanner-matrix.md` and *ask* whether to install before
   proceeding. Do not auto-install.
5. Create the output dir:
   ```bash
   DATE=$(date -u +%Y-%m-%d_%H%M)
   mkdir -p "reports/security/$DATE/raw"
   ```
6. Snapshot what's about to run: branch name, commit SHA, scanner
   versions. Write to `reports/security/$DATE/metadata.json`.

### Step 2 — Run scanners

Invoke `.claude/skills/security-audit/scripts/run_scanners.sh
reports/security/$DATE`. This writes one raw output file per scanner to
`reports/security/$DATE/raw/<tool>.json` (or `.txt` for trufflehog).

Individual scanner failures are NOT fatal — capture exit codes in
`metadata.json` and continue. A single failed tool is a *finding*, not a
blocker for the audit.

### Step 3 — Normalize findings

Run `.claude/skills/security-audit/scripts/parse_findings.py
--input reports/security/$DATE/raw --output reports/security/$DATE/findings.json`.

This produces a uniform schema:
```json
{
  "scanner": "gitleaks|ruff|bandit|semgrep|pip-audit|npm-audit|trufflehog|trivy",
  "rule": "<scanner-rule-id>",
  "severity": "critical|high|medium|low|info",
  "file": "<repo-relative-path>",
  "line": <int>,
  "message": "<short message>",
  "snippet": "<code or excerpt>",
  "fingerprint": "<sha256 of rule+file+line+snippet>"
}
```

### Step 4 — Diff against last run + suppressions

Find the previous audit dir (most recent under `reports/security/*/`
excluding the current one). Compare `findings.json` fingerprints:

- **New** — in current, not in previous, not in `suppressions.yml`
- **Carried over** — in current AND previous (not suppressed)
- **Newly suppressed** — in `suppressions.yml`, in current
- **Resolved** — in previous, not in current, not suppressed
- **Suppressions expiring** — in `suppressions.yml` with `expires < today`

### Step 5 — Triage new findings (LLM, this is you)

For each **new** finding (and any *carried over* finding aged > 30 days):

1. Read the offending file at the reported line.
2. Cross-reference `docs/security/threat-model.md` and
   `docs/security/attack-surface.md` and `docs/security/risk-register.md`.
3. Classify as one of:
   - `true-positive-needs-fix` — write a brief fix recommendation
   - `true-positive-accept` — propose a register row + suppression entry
   - `false-positive` — propose a suppression entry only (no register row)
   - `needs-human-judgement` — write what's ambiguous; ask the user

Write your triage into a working list, *do not* update any files yet.

### Step 6 — Generate the report

Render `reports/security/$DATE/report.md` from
`.claude/skills/security-audit/resources/report-template.md`. The
template has placeholders for:

- Run metadata (date, commit, branch, scanner versions, durations)
- Scanner summary table (count per scanner, exit code, raw file path)
- New findings (with your triage classification + recommendation)
- Carried-over findings + suppressions expiring
- Resolved findings (positive — show what was closed)
- Proposed register-row deltas (in markdown, ready to paste)
- Proposed suppressions.yml entries (in YAML, ready to paste)
- "Next actions" — ordered list with explicit owners

### Step 7 — Hand off to the user

1. Print a one-paragraph summary to the chat: scanner counts, # new
   findings by severity, # proposed register changes, link to
   `reports/security/$DATE/report.md`.
2. **Do NOT auto-commit anything.** The user reviews the report, applies
   proposed register/suppressions changes manually (or via a follow-up
   chat), and then commits.
3. If any finding was `CRITICAL` severity, surface it prominently in the
   summary line and recommend halting the release/merge.

## Behavior rules

- **Never** edit production code in this skill.
- **Never** auto-close a risk register row. Closure requires human
  verification.
- **Never** suppress a `CRITICAL` or `HIGH` finding without explicit user
  approval in the chat.
- When a scanner is missing, capture that as a finding (`SCANNER-MISSING`)
  and continue.
- Prefer recommending the smallest change that closes the finding.

## Tip for first runs

The very first run will report many "new" findings because there's no
prior `findings.json` to diff against. This is expected. After the user
reviews and the first wave of suppressions lands, subsequent runs should
be much quieter.

## Related

- `docs/security/README.md` — index
- `tools/security/scanner-matrix.md` — what each scanner catches + install
- `.claude/agents/security-reviewer.md` — sibling subagent for *diff-level*
  project-aware review (the audit is *project-level*; the subagent is
  *change-level*)
