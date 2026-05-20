# Ship a feature

End-to-end workflow for new product features that touch production code
(frontend, backend, or both). Optimised for "ship cleanly without
breaking anything," not for raw speed.

## Phase 1 — Scope and plan

1. Create the task folder: `tasks/<initiative_name>/` (snake_case).
2. Write `PLAN.md` covering:
   - Why this change — the problem or user need.
   - Outcome shape — what does "done" look like, observably?
   - Critical files to be modified (with paths).
   - Out of scope (explicit list).
   - Verification approach (manual + automated).
3. If scope is unclear, dispatch the `Plan` subagent or do an Explore pass
   before locking the plan.
4. Write `TASKS.md` once the plan is locked — phased breakdown with
   owner + risk tags (see `tasks/CONVENTIONS.md`).

## Phase 2 — Create a branch

```
git checkout -b <initiative_name>
```

Branch name matches the task folder. Commits prefixed with the same.

## Phase 3 — Implement

Per chunk in `TASKS.md`:

1. Read the existing code in the critical-files set before editing.
2. Make the change.
3. Run the relevant tests / typecheck / lint for the layer you touched
   (e.g. `cd kite-dashboard && npm run build && npm run lint` for
   frontend; `cd kite-api && pytest tests/` for backend).
4. Commit with the `<initiative_name>: …` prefix and a body that says
   *what changed and why*, not *what files changed*.

Pre-commit hooks run automatically (gitleaks, ruff `S`, no-env-files,
eslint-security on staged JS).

## Phase 4 — Security review

After all code chunks land on the branch:

1. Invoke the built-in `/security-review` skill for a generic pass on
   the diff.
2. Invoke the project-aware `security-reviewer` subagent for a
   project-specific pass (knows the threat model, register, attack
   surface):
   ```
   Agent: subagent_type="security-reviewer"
   prompt: "Review the diff main..HEAD on this branch."
   ```
3. If either flags a finding, decide: fix, accept (open register row),
   or suppress (inline + register row). Don't proceed with a HIGH
   unaddressed.

## Phase 5 — Pre-merge verification

Each layer that changed:

- **Frontend (kite-dashboard):** `rm -rf .next && npm run build && npm run lint` clean.
- **Backend (kite-api):** `pytest tests/` clean.
- **Manual smoke:** `npm run dev` + `uvicorn app.main:app --reload`, walk through the user-facing flow.

Update `tasks/<initiative_name>/TASKS.md` to reflect what landed in each
phase.

## Phase 6 — Merge and deploy

```
git checkout main
git pull --ff-only
git merge --no-ff <initiative_name> -m "Merge <initiative_name>: …"
git push origin main
```

Auto-deploy:
- Vercel rebuilds frontend on push to main.
- Railway rebuilds backend on push to main.

## Phase 7 — Verify production

Once Vercel + Railway show SUCCESS:

```bash
curl -sI https://marketworks.in/ | head -3
curl -s  https://kite-lab-production.up.railway.app/api/health
```

Walk through the user-facing flow on the deployed site.

## Phase 8 — Close out

1. Write `tasks/<initiative_name>/RESULTS.md` (what shipped vs. planned, commits, deferred items, verification log).
2. Update `_meta.yml` status → `shipped`.
3. Optional follow-ups → register rows or future task folders.
4. After ~1–2 months as recent reference, move the folder to the
   archive branch (see `tasks/CONVENTIONS.md` lifecycle).
