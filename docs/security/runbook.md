# Security Runbook — Kite-Lab

Operational procedures for rotation, revocation, and incident response.
One person owns all of this; keep procedures short enough to execute
under stress.

---

## Rotation cadence

| Secret | Cadence | Triggered by | Procedure |
|---|---|---|---|
| Zerodha `access_token.txt` | Daily (forced by Zerodha) | Token expiry (06:00 IST) | `scripts/login_and_save_token.py` |
| `JWT_SECRET` | On suspected exposure only | Incident | §"Rotate JWT_SECRET" |
| `NEXTAUTH_SECRET` | On suspected exposure only | Incident | §"Rotate NEXTAUTH_SECRET" |
| Zerodha API key + secret | On rotation request or incident | User decision | §"Rotate Zerodha API key" |
| Google OAuth client secret | On suspected exposure | Incident | Google Cloud Console |
| Google Drive refresh token | Annual or on incident | Calendar | `python scripts/upload_to_gdrive.py auth` |
| Postgres password | On suspected exposure or annually | Calendar | Railway dashboard |
| `DATABASE_URL` | Same as Postgres password | Same | Railway dashboard |

---

## Rotate `JWT_SECRET`

**Effect:** all existing dashboard sessions invalidated. Users (you) must
re-login.

```bash
# 1. Generate new secret (32 bytes urlsafe)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Update Railway env
railway variables set JWT_SECRET=<new-value>

# 3. Update local .env (optional, for dev)
# Edit /Users/navdeep/kite-lab/.env

# 4. Redeploy
railway service redeploy --yes

# 5. Verify
curl -s https://kite-lab-production.up.railway.app/api/health | jq .
# Then re-login at https://kite-lab.vercel.app
```

If old sessions need to stay valid for grace, add `JWT_SECRET_PREVIOUS`
env var and update verifier to accept both for 24h (currently not
implemented; would need code change).

---

## Rotate `NEXTAUTH_SECRET`

**Effect:** all NextAuth sessions invalidated.

```bash
# 1. Generate
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Update Vercel env via dashboard or CLI
npx vercel env add NEXTAUTH_SECRET production
# (paste value when prompted, then remove old)

# 3. Trigger redeploy
npx vercel --prod
```

---

## Rotate Zerodha API key

**Effect:** existing `access_token.txt` becomes invalid; pipeline scripts
fail until updated.

1. Login to Zerodha Kite Connect developer console.
2. Generate new API key + secret.
3. Update `.env` on every machine that runs the pipeline (laptop + Mac mini):
   ```
   KITE_API_KEY=<new-key>
   KITE_API_SECRET=<new-secret>
   ```
4. Update Railway env:
   ```bash
   railway variables set KITE_API_KEY=<new-key>
   railway variables set KITE_API_SECRET=<new-secret>
   railway service redeploy --yes
   ```
5. Re-login on each machine:
   ```bash
   python scripts/login_and_save_token.py
   ```
6. Smoke test:
   ```bash
   python scripts/run_daily_pipeline.py
   ```

Note the "whoever logs in wins" rule still applies (`docs/handover.md`).

---

## Revoke `access_token.txt` (Zerodha session kill)

If you suspect the token was disclosed:

```bash
# 1. Force re-login on a single machine (invalidates the existing token
#    server-side — Zerodha issues a new one and revokes the old).
python scripts/login_and_save_token.py
```

There's no separate "revoke" endpoint; issuing a new token implicitly
invalidates the old. If you can't do step 1 immediately (e.g., abroad,
no internet), call Zerodha support to disable API access on the account.

---

## Revoke a dashboard user (remove from whitelist)

```bash
# Option A: Update env var (fast, no DB write)
railway variables set ALLOWED_EMAILS="user1@example.com"
# (omit the email you want to revoke)
railway service redeploy --yes

# Option B: Update AllowedUser table (persistent)
# Connect to Postgres via Railway, DELETE the row.
# Backend re-reads on every request; takes effect immediately.
```

Their existing JWT is still valid until expiry (24h). To force-revoke
the JWT itself, rotate `JWT_SECRET` (see above).

---

## Incident response

### 1. Suspected secret leak

**Signal:** secret value appears in a Slack/email/repo/log/etc.

1. **Identify scope** — which secret, which surface (logs, repo history, screenshot, …).
2. **Rotate immediately** per the applicable §Rotate procedure above.
3. **Audit usage** — search Zerodha trade history for unfamiliar trades;
   Railway logs for unauthorized API calls; Vercel logs for unfamiliar
   IPs/emails.
4. **Document** — open a register row (`R-XXX`), category = Incident,
   status = `Closed` once rotation verified.
5. **Postmortem** — what was the root cause; what new control prevents
   recurrence; update threat-model.md and risk-register.md.

### 2. Suspected unauthorized API call

**Signal:** unexplained trade, unexpected DB row, unfamiliar log entry.

1. **Freeze pipeline** — stop the Railway scheduled jobs:
   ```bash
   railway run --service kite-api -- pkill -f run_daily_pipeline || true
   ```
2. **Inspect audit log** — `/api/jobs/logs` for recent activity; Railway
   stdout for the past hour.
3. **Rotate `JWT_SECRET`** — invalidates all sessions, including the
   attacker's.
4. **Revoke Zerodha token** — `scripts/login_and_save_token.py` from a
   trusted machine.
5. **Audit DB** — `SELECT * FROM trades WHERE created_at > '<incident-time>'`.
6. **Document + postmortem** as in §1.

### 3. Dependency CVE disclosed

**Signal:** `pip-audit` or `npm audit` reports a new high/critical CVE.

1. **Triage** — read the CVE description; is this package on a code path
   we use? Check `attack-surface.md` for any reachable surface.
2. **Patch** — bump the version in `requirements.txt` or
   `kite-dashboard/package.json`.
3. **Test** — run `pytest` (backend) and `npm run build` (frontend).
4. **Update register** — bump `Last reviewed` on `R-002` or open a new
   row.
5. **Deploy** — small, reviewed PR; Railway/Vercel auto-deploy on merge.

### 4. Compromised dev machine

**Signal:** machine lost/stolen/suspect malware.

1. **Rotate everything that lived on that machine:** `.env`,
   `access_token.txt`, GitHub tokens, Railway CLI tokens, Vercel CLI
   tokens, `gdrive_token.json`.
2. **Revoke GitHub access**: GitHub → Settings → SSH/PAT → revoke the
   compromised machine's keys.
3. **Revoke Railway/Vercel CLI tokens** in their respective dashboards.
4. **Rotate `JWT_SECRET`** and `NEXTAUTH_SECRET` (invalidates all
   sessions, in case the attacker harvested cookies).
5. **Check `git log`** on the central repo for unexpected commits in the
   past 7 days.

---

## Pre-commit health check

If `pre-commit run --all-files` starts failing on items not in your diff,
it means the baseline has drifted. Inspect:

```bash
pre-commit run --all-files | tee /tmp/precommit.log
grep -E "(error|warning)" /tmp/precommit.log
```

If it's gitleaks finding a *real* leak that's not in the diff (e.g., a
historical commit), use:

```bash
gitleaks detect --source . --no-banner
```

For a finding tied to a known-safe match, add to
`tools/security/.gitleaks.toml` with a comment pointing at a register
row.

---

## Annual review checklist

Run this once a year (calendar reminder):

- [ ] Rotate `JWT_SECRET`, `NEXTAUTH_SECRET`, Postgres password (proactive)
- [ ] Renew Google Drive OAuth refresh token
- [ ] Re-read `threat-model.md` end to end — does anything still apply?
- [ ] Re-read every `Accepted` row in `risk-register.md` — still valid?
- [ ] `pip-audit` + `npm audit` on every requirements file
- [ ] Confirm Railway / Vercel / Google / GitHub accounts all have MFA
- [ ] Run `/security-audit` and compare against last audit; merge new
      rows into the register
- [ ] Update `Last reviewed` on every active row
