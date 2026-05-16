# Google Drive Backup Setup (Phase 2.5.4)

One-time setup for ``scripts/upload_to_gdrive.py``. Closes the
single-Mac-risk loop from CRITICAL_DATA.md by mirroring everything in
``~/Documents/stock_data/`` to your Google Drive.

Total time: ~10 minutes.

---

## Step 0: Python dependencies

The script imports `google-api-python-client` + auth helpers. Already
installed in this Mac's `.venv` on 2026-05-16. On a fresh clone:

```bash
source .venv/bin/activate
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Step 1: Google Cloud Console — create the OAuth client

1. Go to https://console.cloud.google.com
2. Top bar → project selector → **NEW PROJECT**
   - Name: `kite-lab-backups` (anything works)
   - Click **CREATE**
3. Once the project is created, select it from the top bar.
4. Hamburger menu → **APIs & Services → Library**
5. Search for **"Google Drive API"** → click it → **ENABLE**
6. Hamburger menu → **APIs & Services → OAuth consent screen**
   - User Type: **External** → CREATE
   - App name: `kite-lab-backups`
   - User support email: your email
   - Developer contact: your email
   - SAVE AND CONTINUE through the remaining screens (no scopes
     needed yet on this screen, defaults are fine)
   - On the Test users page, click **+ ADD USERS** and add your own
     Google account email. SAVE AND CONTINUE.
7. Hamburger menu → **APIs & Services → Credentials**
   - **+ CREATE CREDENTIALS** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: `kite-lab desktop client`
   - **CREATE**
   - A dialog shows the client ID/secret. Click **DOWNLOAD JSON**.

## Step 2: Save the client secret on this Mac

```bash
mkdir -p ~/.config/kite-lab
mv ~/Downloads/client_secret_*.json ~/.config/kite-lab/gdrive_client_secret.json
chmod 600 ~/.config/kite-lab/gdrive_client_secret.json
```

## Step 3: First-time auth

```bash
cd ~/kite-lab
source .venv/bin/activate
python scripts/upload_to_gdrive.py auth
```

A browser will open. Pick your Google account → "Allow" the Drive
scope. (You may see a "Google hasn't verified this app" warning —
that's expected for a personal OAuth app. Click "Advanced" → "Go to
kite-lab-backups (unsafe)" → "Allow". The app is your own; the
warning is generic for unverified personal-project apps.)

On success: the script prints `saved refresh token to ~/.config/kite-lab/gdrive_token.json`.
Subsequent runs reuse this refresh token; no browser needed.

## Step 4: First upload

```bash
python scripts/upload_to_gdrive.py upload
```

You'll see something like:

```
[upload] source: /Users/navdeep/Documents/stock_data
[upload] drive folder: My Drive/kite-lab-backups/  (id=...)

[mirror] /Users/navdeep/Documents/stock_data/db_backups
  [up] kitelab_db_20260516_HHMMSS.tar.gz

[snapshot] /Users/navdeep/Documents/stock_data/nse500_data
  nse500_data_20260516.tar.gz: building tarball ...
  nse500_data_20260516.tar.gz: tarball 30.2 MB, uploading ...
  [up] nse500_data_20260516.tar.gz

[snapshot] /Users/navdeep/Documents/stock_data/nse500_data_historical
  ...

============================================================
Upload summary: 5 uploaded, 0 skipped, 0 old removed
============================================================
```

First upload takes ~2-5 min total (the 30-200 MB of price data is the
bulk; subsequent uploads are quick because mirror-mode dedups by
md5 and snapshot-mode skips if today's tarball is already in Drive).

## Step 5: Confirm in Drive

Open https://drive.google.com → **kite-lab-backups** folder. You
should see five subfolders:

- `db_backups/`                        ← all your DB tarballs
- `nse500_data_snapshots/`             ← one daily tarball
- `nse500_data_historical_snapshots/`  ← one daily tarball
- `nse500_data_hourly_snapshots/`      ← one daily tarball
- `indices_data_snapshots/`            ← one daily tarball

Or from the CLI:

```bash
python scripts/upload_to_gdrive.py status
```

## Daily schedule (optional but recommended)

Invoke after the daily backup completes. From cron on this Mac:

```cron
# 21:00 IST every weekday — runs AFTER backup_database.py at 20:00
0 21 * * 1-5 cd $HOME/kite-lab && \
  source .venv/bin/activate && \
  python scripts/backup_database.py && \
  python scripts/upload_to_gdrive.py upload >> $HOME/Library/Logs/kite-lab-backup.log 2>&1
```

Or wire it into the kite-api APScheduler (would run on Railway,
which means the local Mac doesn't need to be on at 21:00 — but
note that the Mac-local backup directory ``~/Documents/stock_data/``
isn't accessible from Railway, so this only makes sense if the
backup itself runs locally).

The simplest workable cron is the Mac-local one above. Replace
``/Users/navdeep/kite-lab`` with the right path if different.

## Rotation behavior (recap)

- ``db_backups/``: file-by-file mirror. **No deletion in Drive** —
  the local 14d+12w+12m rotation policy controls what exists locally;
  Drive accumulates every tarball that was ever produced. Manually
  clean Drive periodically if you want.
- Snapshot folders: keep the last **7** daily tarballs in Drive;
  older ones are deleted automatically.

If you want different retention, edit ``SNAPSHOT_RETENTION`` in
``scripts/upload_to_gdrive.py``.

## Troubleshooting

**"Missing ~/.config/kite-lab/gdrive_client_secret.json"** — you skipped
or misplaced Step 2. Re-download from Cloud Console → Credentials →
your OAuth client → DOWNLOAD JSON.

**"This app isn't verified"** — expected for personal OAuth apps.
Click Advanced → Go to (unsafe) → Allow. Your client secret is private
to you; "unverified" only means Google didn't review the app, not
that anything is wrong with it.

**Refresh token expired** — Google occasionally invalidates them.
Delete ``~/.config/kite-lab/gdrive_token.json`` and re-run
``python scripts/upload_to_gdrive.py auth``.

**Rate limits / quota exceeded** — Drive's free quota is generous
(750 GB/day, 10K files/day). You'll never hit these for daily backups.
If you do, the failed uploads show up in the script's "Errors:"
section; rerun and it'll skip what's already up there.
