# Task folder conventions

One folder per initiative under `tasks/`. Designed to be navigable both
by humans and by an AI agent reading the repo for context.

## Lifecycle

```
new task              tasks/<name>/                  scope unclear → PLAN.md
                         PLAN.md
                         _meta.yml                   status: planned

execution             + TASKS.md                     plan locked → start work
                                                     status: in-progress

close-out             + RESULTS.md                   work shipped
                                                     status: shipped

stays on main         ~1-2 months as ongoing
                      reference, then →
                      archive branch                 status: archived
```

## Required files

| File | When | Contents |
|---|---|---|
| `PLAN.md` | Day 1 | Why the work, what the outcome looks like, scope boundary, critical files. |
| `TASKS.md` | As soon as scope is locked | Phased breakdown with owners (👤/🤖) and risk tags. |
| `RESULTS.md` | Within ~1 week of merge | What was actually shipped vs. planned, commits, deferred items, verification log. |
| `_meta.yml` | Optional but recommended | Machine-readable status — see schema below. |

## `_meta.yml` schema

```yaml
name: client_portal
status: shipped              # planned | in-progress | shipped | archived
opened: 2026-05-19
closed: 2026-05-20           # null while in-progress
related_commits:
  - fdf4a39                  # merge commit
  - 6833d3c                  # R-022 close
supersedes: []               # list of task names this replaces
depends_on: []               # list of task names this builds on
register_rows:               # if relevant
  - R-022
```

Agents can grep `tasks/*/_meta.yml` to reason about task history without
reading 5 markdown files each.

## Active tasks on main

| Folder | Status | Purpose |
|---|---|---|
| `client_portal/` | shipped (recent) | Clerk auth + role-gated client portal v1. |
| `rebalance_page/` | planned | Backlog of 12 items to make `/rebalance` fully functional across all 7 portfolios. |
| `security_agent/` | shipped (reference) | Runbook for the `/security-audit` skill + `security-reviewer` subagent. |
| `streamline/` | in-progress | The repo declutter pass producing this set of conventions. |

Anything else → archive branch.

## Naming

- snake_case for folder names: `client_portal`, not `client-portal` or `ClientPortal`.
- A folder name should describe the *initiative*, not the artifact (`client_portal`, not `add_clerk`).
- For research lines: include the date if multiple iterations are expected (`oos_retune_2026`, not just `oos_retune`).

## Commit messages for task work

Prefix the commit subject with the task folder name:

```
client_portal: Phase 1 backend Clerk JWKS verification
rebalance_page: R-1 v3 strategy changes_*.csv emitter
streamline: Archive 26 closed task folders
```

This makes `git log --grep="<folder>"` find the trail.
