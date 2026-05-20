# Close a research task

Workflow for taking a `tasks/<name>/` folder from in-progress to
shipped-or-archived. Run when the research line reaches a decision
point.

## Phase 1 — Decide the outcome

Three exits for any research task:

| Outcome | Means |
|---|---|
| **Shipped** | The result landed in production code (strategy locked, parameter changed, system deployed). |
| **Negative result** | The research showed the approach doesn't work. The lesson is the artifact. |
| **Inconclusive** | Ran out of time / signal; not actionable. |

All three are valid closures. The point is to stop holding the folder
open.

## Phase 2 — Write RESULTS.md

Required sections:

```markdown
# <Task name> — Results

**Outcome:** shipped / negative / inconclusive
**Closed:** <date>

## What was actually done
(vs. what PLAN.md proposed)

## Headline numbers
(if a strategy: CAGR, Sharpe, DD, sub-window pass-rates)

## Decision
(what this changes in production, or — for negative results — what we should not retry, and why)

## Open follow-ups
(register rows, future task folders)

## Commit log
(chronological list of commits on the branch)
```

## Phase 3 — Update `_meta.yml`

```yaml
status: shipped         # or: archived (for negative/inconclusive)
closed: <date>
related_commits:
  - <sha>
  - <sha>
```

## Phase 4 — Cite from CLAUDE.md *only if load-bearing*

If the result defines a production parameter or invariant
(e.g. a locked strategy config), add a one-line reference in
`CLAUDE.md` pointing at `tasks/<name>/RESULTS.md`. Otherwise the
folder doesn't need a citation.

Threshold for citation: would a future agent wonder *why* production
is configured this way and want the evidence? If yes — cite. If the
result is "we tried X, it didn't work, we moved on" — no citation
needed.

## Phase 5 — Sit on main for ~1-2 months

The folder stays on main while the result is fresh and may need to be
re-consulted. After enough time has passed that nobody is asking about
it, move to archive.

## Phase 6 — Move to archive branch (eventually)

When the time comes:

```bash
# On main, remove the folder
git rm -r tasks/<name>
git commit -m "tasks: Archive <name> (closed <date>; on snapshot branch)"

# The folder remains accessible at the snapshot/archive branch
# repo-snapshot-2026-05-20 (or whichever archive branch is current).
# Update MAP.md "archive branch" section if the moved folder is
# load-bearing enough to mention by name.
```

There's no "delete completely" exit — everything lives somewhere
forever (snapshot branch). The question is just where it lives.
