# Kite-Lab Security

This directory is the codified knowledge base for the project's security
posture. It exists so that automated reviewers (the `/security-audit`
skill, the `security-reviewer` subagent) and humans can evaluate changes
in context instead of rediscovering the threat model every time.

## Layers of defense

| Layer | Trigger | What runs | Where to look |
|---|---|---|---|
| 1 | every `git commit` | gitleaks, ruff `S`, eslint-security on staged files | `.pre-commit-config.yaml` |
| 2 | Claude reviews a diff | `security-reviewer` subagent (project-aware) | `.claude/agents/security-reviewer.md` |
| 3 | user invokes on a diff | built-in `/security-review` skill (generic) | Claude Code stock |
| 4 | user invokes `/security-audit` | bandit, semgrep, pip-audit, npm audit, trufflehog, trivy + LLM triage | `.claude/skills/security-audit/` |
| 5 | continuous | docs in this directory | `docs/security/` |

Layers 2-4 read from this directory. Layer 4 also writes back (updates
the risk register).

## Files

| File | Purpose |
|---|---|
| [`threat-model.md`](./threat-model.md) | Assets, actors, trust boundaries, STRIDE per surface |
| [`risk-register.md`](./risk-register.md) | Open / mitigating / closed / accepted risks with control + owner |
| [`attack-surface.md`](./attack-surface.md) | Every endpoint, auth status, intentional vs not |
| [`auth-flows.md`](./auth-flows.md) | Google OAuth, JWT, NextAuth, Zerodha OAuth — text diagrams |
| [`runbook.md`](./runbook.md) | Key rotation, token revocation, incident response |
| [`audits/`](./audits/) | Dated audit snapshots (`YYYY-MM-baseline.md`, `/security-audit` reports) |

## How to invoke

```bash
# Full project-wide audit (minutes)
/security-audit

# On-demand review of pending changes (generic)
/security-review

# Project-aware review (Claude invokes automatically on watched paths)
# — auth code, kite-api/app/api/**, requirements.txt, package.json
```

Pre-commit runs every commit; install once with `pre-commit install`.

## When to update this directory

- A new threat surface appears (new endpoint family, new external service,
  new data type) → update `threat-model.md` and `attack-surface.md`.
- A new risk is discovered or an existing risk's status changes → update
  `risk-register.md`. **The register is append-mostly**: closed rows stay
  in the file with a status of `Closed` and a closure date so the history
  is preserved.
- A key/secret is rotated or an incident occurs → update `runbook.md`
  with what was learned.
- After every `/security-audit` run → an audit report is auto-written to
  `audits/<UTC-date>.md`. Don't delete these — they're the audit trail.

## Out of scope

- Physical security of the developer machines (covered by macOS FileVault
  + 1Password; not codified here)
- Supply-chain attacks on Python/Node interpreters themselves
- Compromise of Railway / Vercel / GitHub platform infrastructure
- Zerodha-side breach affecting the user's account
- External penetration testing (future work, R-009 / TBD)
