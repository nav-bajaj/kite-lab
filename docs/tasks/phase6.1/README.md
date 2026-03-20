# Phase 6.1: Repository Reconciliation

**Duration**: 1-2 days
**Status**: Pending
**Created**: 2026-03-20

## Objectives

- Fix documentation inconsistencies between task docs and actual completion status
- Commit outstanding portfolio data changes
- Establish sustainable workflow for daily portfolio updates
- Clean up experiment directories and establish archival process
- Update operational documentation

## Context

After completing all 6 phases of the production dashboard (Feb 12-18, 2026), the repository has:
- Stale documentation showing incomplete phases
- Uncommitted daily portfolio updates
- 46+ untracked experiment directories
- Outdated operational docs

This phase reconciles all work done and establishes clean workflows going forward.

## Task Progress

| # | Task | Status | Description |
|---|------|--------|-------------|
| 1 | [Fix tasks README](./01-fix-tasks-readme.md) | `completed` | Update docs/tasks/README.md to show all phases completed |
| 2 | [Commit portfolio data](./02-commit-portfolio-data.md) | `completed` | Stage and commit current holdings/signals |
| 3 | [Update CLAUDE.md](./03-update-claude-md.md) | `pending` | Add dashboard completion status and URLs |
| 4 | [Create cleanup script](./04-cleanup-script.md) | `pending` | Script to archive old experiment directories |
| 5 | [Update runbook](./05-update-runbook.md) | `pending` | Add dashboard operation procedures |
| 6 | [Review gitignore](./06-review-gitignore.md) | `pending` | Ensure experiment dirs properly handled |

## Deliverables

- [ ] `docs/tasks/README.md` shows all 6 phases as Completed
- [ ] Portfolio data committed with clear commit message
- [ ] `CLAUDE.md` includes dashboard URLs and status
- [ ] `scripts/cleanup_experiments.py` created
- [ ] `runbook.md` includes dashboard operations
- [ ] Clean git status (no unexpected modified/untracked files)

## Dependencies

None - this is cleanup/reconciliation work.

## After This Phase

With documentation reconciled, the next priorities are:
1. **Real Portfolio Tracking** (`docs/real_portfolio_tracking_plan.md`) - Track real vs model portfolio
2. **Code Quality** (`TODO_IMPROVEMENTS.md`) - Type hints, tests, CI/CD

---

*Status Key: `pending` | `in_progress` | `completed`*
