# Triage a production incident

Workflow for "something is broken in production right now". Optimised
for fast restoration, then root-cause once stable.

## Phase 1 — Confirm scope

1. Hit the user-facing endpoints to confirm what's broken:
   ```bash
   curl -sI https://marketworks.in/ | head -3
   curl -s  https://kite-lab-production.up.railway.app/api/health
   ```
2. Read the runtime logs of the affected service:
   ```bash
   railway logs --service kite-lab | tail -50
   railway logs --service Postgres | tail -50
   ```
3. Check deploy state:
   ```bash
   railway deployment list | head -5
   cd kite-dashboard && npx vercel ls | head -4
   ```

## Phase 2 — Restore first, diagnose second

If the failing deployment is a recent push:

```bash
# Redeploy the previous SUCCESS to restore service
railway deployment list      # find the most recent SUCCESS
# Then in Railway dashboard: Deployments → ⋯ → Redeploy on that one
# Or via CLI: railway redeploy --yes  (redeploys latest, may pick up new build)
```

If the failure is upstream (Postgres, third-party API):

- For Postgres: `railway service Postgres && railway redeploy --yes`
  (volume data preserved across redeploys).
- For Zerodha: `python scripts/login_and_save_token.py` to re-issue
  the access token if expired.
- For Clerk: check JWKS endpoint reachability and Clerk dashboard
  status page.

## Phase 3 — Root cause

Once service is restored:

1. Read the build + runtime logs of the FAILED deployment, not the
   one currently serving:
   ```bash
   railway logs --build <failed-deployment-id>
   railway logs --deployment <failed-deployment-id>
   ```
2. Identify the diff between last good and first bad commit:
   ```bash
   git log --oneline <last-good-sha>..<first-bad-sha>
   ```
3. Reproduce locally if possible: pull the bad commit, `npm run build`
   or `pytest`, observe the failure.

## Phase 4 — Fix

- Create a hotfix commit directly on main if the fix is small and
  obvious (this is the "production is down" case).
- Otherwise branch off main: `git checkout -b hotfix-<short-description>`
  and follow `ship-feature.md` from Phase 3 onwards.

## Phase 5 — Postmortem

Open or update a register row in `docs/security/risk-register.md` if
the incident has a security dimension. Otherwise:

1. Append a one-paragraph postmortem to the relevant `tasks/*/`
   folder, or create `tasks/incident_<date>/` if the cause crosses
   areas.
2. Note: what failed, what restored it, what the underlying cause
   was, and what would prevent recurrence.

## Phase 6 — Add a watchdog if recurrence is plausible

- A pytest assertion catching the bug class.
- A pre-commit hook check.
- An alert (TBD — no alerting infra in repo yet).

Don't skip this step if the same root cause has fired more than once.
