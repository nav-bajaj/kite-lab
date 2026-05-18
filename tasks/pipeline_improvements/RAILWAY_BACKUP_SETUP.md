# Railway-Side Backup Setup (Phase 2.5.6)

Move the daily backup + cloud upload from Mac-local cron to Railway's
existing APScheduler. After this is done, your Mac no longer needs
to be on for the backups to happen.

The schedule that gets installed (matches `kite-api/app/scheduler/tasks.py`):

| Job | When (IST) | What |
|---|---|---|
| `daily_db_backup` | 20:00 every day | Dump Postgres → `/data/db_backups/` |
| `daily_cloud_upload` | 20:30 every day | Mirror `/data` backups + price-dir snapshots → Google Drive |

The 30-minute gap is so the cloud-upload step can pick up the freshly-
written DB tarball.

**Estimated time:** 20 minutes.

---

## Prerequisite: get a fresh refresh token with the narrower scope

Phase 2.5.6 switches the OAuth scope from `drive` to `drive.file`
(only files this app creates). This means:

- The Railway-installed app **cannot** see or modify any of your
  existing Drive contents — only what it uploads itself
- A new refresh token is needed (the old one with full `drive`
  scope can't be downgraded in place)
- Your existing `kite-lab-backups` folder in Drive (created during
  the Mac-local Phase 2.5.4 setup) **will remain visible to you in
  the Drive UI**, but invisible to the Railway app. The Railway app
  will create its own folder with the same name. Delete the old one
  from Drive when you're confident the new flow works.

### Step 1.1 — Delete the old token on the Mac

```bash
rm -f ~/.config/kite-lab/gdrive_token.json
```

### Step 1.2 — Re-run the OAuth flow

```bash
cd ~/kite-lab
source .venv/bin/activate
python scripts/upload_to_gdrive.py auth
```

Browser opens, you grant the `drive.file` scope (note the narrower
permission text vs the previous flow), and the new token is saved
back to `~/.config/kite-lab/gdrive_token.json`.

The script prints the JSON to copy into Railway:

```
[upload] saved refresh token to /Users/navdeep/.config/kite-lab/gdrive_token.json
[upload] scope granted: https://www.googleapis.com/auth/drive.file

To use this token on Railway, copy the JSON below into a new
env var named GDRIVE_REFRESH_TOKEN_JSON (single-line value):

  cat /Users/navdeep/.config/kite-lab/gdrive_token.json | tr -d '\n'
```

Run that `cat ... | tr -d '\n'` command — its output is the value
you'll paste into Railway in Step 2.

### Step 1.3 — Verify the new token works locally first

```bash
python scripts/upload_to_gdrive.py upload
```

This should run cleanly, create a NEW `kite-lab-backups` folder in
Drive (since the old one is invisible under `drive.file`), and
populate it with the five expected subfolders. Confirm via
`https://drive.google.com` before proceeding.

---

## Step 2 — Set Railway env vars

Railway → backend service → **Variables** tab. Add four new
variables (the existing `DATABASE_URL` stays; we want the **internal**
one Railway provides, not the public proxy — Railway-side connections
use `postgres.railway.internal` and avoid the public proxy egress fee).

| Variable name | Value |
|---|---|
| `KITE_BACKUP_OUTPUT_DIR` | `/data/db_backups` |
| `KITE_BACKUP_SOURCE_ROOT` | `/data` |
| `GDRIVE_CLIENT_SECRET_JSON` | contents of `~/.config/kite-lab/gdrive_client_secret.json` as one line — `cat ~/.config/kite-lab/gdrive_client_secret.json \| tr -d '\n'` |
| `GDRIVE_REFRESH_TOKEN_JSON` | contents of `~/.config/kite-lab/gdrive_token.json` as one line — same `cat ... \| tr -d '\n'` pattern |

Railway will redeploy the service automatically when you save the variables.

---

## Step 3 — Upload the 2009-2019 GDF backfill to Railway one-time

The Railway-side backup will mirror `/data/{nse500_data, indices_data,
nse500_data_hourly}`, but `nse500_data_historical/` doesn't exist on
Railway yet. Push it there once so future daily backups capture it.

The script is `scripts/upload_price_data.py` (note: in repo root, not
`kite-api/scripts/`). `nse500_data_historical` is allowed as a target
as of the same Phase 2.5.6 deploy.

First, get a JWT token. Easiest path: log in to
https://kite-lab.vercel.app, open DevTools → Network, click any
`/api/...` request, copy the `Authorization: Bearer ...` value (just
the token part after "Bearer ").

The script expects the source directory to live under your local
`kite-lab/` data dir, but `nse500_data_historical` lives under
`~/Documents/stock_data/`. Two options:

**Option A — temporary symlink (cleanest, easy to undo):**

```bash
cd ~/kite-lab
ln -s ~/Documents/stock_data/nse500_data_historical nse500_data_historical

python scripts/upload_price_data.py \
    --api-url https://kite-lab-production.up.railway.app \
    --token "YOUR_JWT_TOKEN_HERE" \
    --target nse500_data_historical

rm nse500_data_historical  # remove the symlink when done
```

**Option B — point `--data-dir` at the external location:**

```bash
python scripts/upload_price_data.py \
    --api-url https://kite-lab-production.up.railway.app \
    --token "YOUR_JWT_TOKEN_HERE" \
    --target nse500_data_historical \
    --data-dir ~/Documents/stock_data
```

Either way, expect output like:

```
Data directory: /Users/.../stock_data
API: https://kite-lab-production.up.railway.app
Targets: nse500_data_historical

[nse500_data_historical] 500 CSV files
  Compressing /Users/.../nse500_data_historical ...
  Archive: 33.4 MB
  Uploading to https://.../api/sync/upload-data?target=nse500_data_historical ...
  Success: 500 files written to /data/nse500_data_historical

Done.
```

---

## Step 4 — Confirm the schedule is registered

After Railway redeploys, the new APScheduler entries appear in
`Admin → Schedule`. You should see:

- `daily_pipeline` — 07:00 IST Mon-Fri (unchanged)
- `weekly_backup` — 03:00 IST Sundays (unchanged)
- **`daily_db_backup` — 20:00 IST every day** ← new
- **`daily_cloud_upload` — 20:30 IST every day** ← new

Next-fire times should be tomorrow 20:00 and 20:30 IST respectively.

---

## Step 5 — Smoke test: trigger db_backup manually

From the dashboard `Admin → Jobs` page, run the `db_backup` command
once. Logs should show:

```
[backup] connecting to postgresql://***:***@postgres.railway.internal:5432/railway
[backup] writing /data/db_backups/kitelab_db_<ts>.tar.gz
  allowed_users        rows=0
  jobs                 rows=...
  ...
[backup] smoke test OK

============================================================
Backup written: /data/db_backups/kitelab_db_<ts>.tar.gz  (X.YZ MB)
...
```

Then trigger `cloud_upload`. Should show:

```
[upload] source: /data
[upload] drive folder: My Drive/kite-lab-backups/ (id=...)

[mirror] /data/db_backups
  [up] kitelab_db_<ts>.tar.gz

[snapshot] /data/nse500_data
  nse500_data_<YYYYMMDD>.tar.gz: building tarball ...
  [up] nse500_data_<YYYYMMDD>.tar.gz

...

============================================================
Upload summary: 5 uploaded, 0 skipped, 0 old removed
============================================================
```

After this, your Drive `kite-lab-backups` folder has the new contents
written by the Railway-scoped OAuth client.

---

## What the Mac scripts now do (optional ongoing use)

The local `backup_database.py` and `upload_to_gdrive.py` still work
unchanged for Mac-local invocation:

```bash
python scripts/backup_database.py        # writes to ~/Documents/stock_data/db_backups/
python scripts/upload_to_gdrive.py       # uploads from ~/Documents/stock_data/
```

These are useful as a belt-and-suspenders second copy, especially
before/after risky changes. They're no longer required for daily
operation.

If you don't want them running on the Mac at all, just don't invoke
them. Nothing schedules them locally any more.

---

## What this DOESN'T cover (intentional gaps)

- **`nse500_data_historical/` updates**: This is the 2009-2019 GDF
  backfill. It doesn't change. After the one-time upload in Step 3,
  no further sync is needed. If you ever buy a longer history from
  GDF, repeat Step 3.
- **`/data/.env` files**: secrets live in Railway's env-var system
  (and your Mac's `~/.config/kite-lab/`), not on the volume. Nothing
  to back up.
- **Railway service config itself**: the Railway YAML / dashboard
  state isn't backed up. If your Railway account is gone, you
  recreate the service from the repo (which IS backed up via git).

---

## Failure modes & what to do

**APScheduler reports `daily_db_backup` failed in the Jobs page**

Check the job logs. Most likely causes:
- `DATABASE_URL` not set → Railway should always provide this; check
  Variables tab
- `/data/db_backups` not writable → check Railway volume mount
- `psycopg2` connection error → Postgres service health

**`daily_cloud_upload` fails with "no valid credentials"**

Re-do Step 1 and Step 2 — the env var values must be the **full
single-line JSON contents**, not paths or partial strings.

**Drive uploads succeed but you can't see them in the Drive UI**

Confirm you're looking under the right Google account (the one you
authed with in Step 1.2). The `drive.file` scope means files are
visible only via the Drive UI of that account.

**Quota exceeded**

Drive's free quota is 750 GB/day upload and 15 GB total storage on
free accounts. You'll never hit either with this setup unless something
is broken; investigate the failing job's logs.
