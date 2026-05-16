# Disaster Recovery Runbook

What to do when something goes wrong. See `CRITICAL_DATA.md` for the
inventory of what's at risk.

This runbook covers three scenarios in order of likelihood:

1. **Railway DB corruption / data loss** (most likely)
2. **This Mac is lost / wiped**
3. **GitHub repo is lost** (least likely)

Each section ends with a "dry-run test" — a way to validate the
procedure works *before* you actually need it.

---

## Scenario 1 — Railway Postgres is dead

**Symptoms:** dashboard 500s on portfolio/trade endpoints; Railway
dashboard shows the Postgres service down or DB unrecoverable; a
recent deploy corrupted data.

### Restore from local `db_backups/`

```bash
# 1. Pick the most recent good backup
ls -lt ~/Documents/stock_data/db_backups/ | head -5

# 2. Confirm the contents (manifest + 10 csv.gz files)
LATEST=$(ls -t ~/Documents/stock_data/db_backups/kitelab_db_*.tar.gz | head -1)
tar -tzf "$LATEST"

# 3. Dry-run restore against a TEST DB first (do NOT skip this)
export DATABASE_URL='postgresql://USER:PASS@TEST_HOST:PORT/test_db'
python scripts/restore_database.py "$LATEST" --dry-run

# 4. Provision a fresh Postgres on Railway. Run Alembic migrations
#    to create the schema:
cd kite-api
DATABASE_URL='postgresql://USER:PASS@NEW_HOST:PORT/new_db' \
  alembic upgrade head

# 5. Restore into the empty new DB:
DATABASE_URL='postgresql://USER:PASS@NEW_HOST:PORT/new_db' \
  python scripts/restore_database.py "$LATEST" --truncate

# 6. Update Railway's DATABASE_URL env var to point at the new DB.
#    Backend redeploys automatically; verify /api/health is 200.
```

**Expected loss:** rows written between the last backup time and now.
If backups run daily at 20:00 IST and the disaster happens at 11:00
the next morning, you lose ~15 hours of activity (the morning's
daily-pipeline outputs). Trade execution itself is via Zerodha, so
actual market positions are unaffected — only the dashboard's record
of them is.

### Dry-run test

```bash
# Spin up a throwaway Postgres locally (e.g. via Docker) or use a
# Railway "throwaway" Postgres service:
docker run --rm -d --name pg_restore_test \
    -e POSTGRES_PASSWORD=test -p 55432:5432 postgres:15

# Apply migrations:
DATABASE_URL='postgresql://postgres:test@localhost:55432/postgres' \
  alembic -c kite-api/alembic.ini upgrade head

# Restore the latest backup:
LATEST=$(ls -t ~/Documents/stock_data/db_backups/kitelab_db_*.tar.gz | head -1)
DATABASE_URL='postgresql://postgres:test@localhost:55432/postgres' \
  python scripts/restore_database.py "$LATEST" --truncate

# Spot-check the restored data:
psql 'postgresql://postgres:test@localhost:55432/postgres' \
  -c 'SELECT COUNT(*) FROM trades; SELECT COUNT(*) FROM trade_matches;'

# Tear down:
docker stop pg_restore_test
```

If the counts after restore match the counts in
`backup_database.py --dry-run`, the procedure is good.

**Run this test at least once per quarter** — backups that haven't
been restored aren't really backups.

---

## Scenario 2 — This Mac is lost / wiped

**Symptoms:** laptop stolen, dead drive, OS reinstall without
restoring `~/Documents/stock_data/`.

### What's recoverable

- ✅ Repo: `git clone https://github.com/nav-bajaj/kite-lab.git`
- ✅ Current production data: pull from Railway Postgres
- ✅ Daily prices: `python scripts/fetch_nse500_history.py` after login
- ✅ Recent backtest outputs: re-run `run_daily_pipeline.py`

### What's lost (without offsite redundancy)

- ❌ `~/Documents/stock_data/nse500_data_historical/` — the 2009-2019
  GDF backfill, NOT refetchable from Zerodha
- ❌ Local `db_backups/` history — but that's redundant with the
  live Railway DB anyway
- ❌ Any local-only experiments in `experiments/` that weren't committed

### Recovery steps

```bash
# 1. Get a working environment back
git clone https://github.com/nav-bajaj/kite-lab.git
cd kite-lab
python3 -m venv .venv && source .venv/bin/activate
pip install -r kite-api/requirements.txt
cd kite-dashboard && npm install && cd ..

# 2. Restore credentials from password manager:
#    - .env (Kite API_KEY, API_SECRET, REDIRECT_URI)
#    - kite-api/.env (DATABASE_URL, JWT_SECRET, etc.)

# 3. Login and refetch live prices:
python scripts/login_and_save_token.py
python scripts/fetch_nse500_history.py
python scripts/fetch_indices_history.py

# 4. Take a fresh DB backup (your offsite redundancy is now empty)
#    Note: assumes Railway is alive. If Railway is also dead,
#    see Scenario 1 first.
export DATABASE_URL='postgresql://...@yamabiko.proxy.rlwy.net:.../railway'
python scripts/backup_database.py

# 5. For the 2009-2019 backfill — if Phase 2.5.4 cloud upload was
#    enabled, restore from Google Drive. If not, you must re-buy
#    from GDF or accept that retunes against 2009-2019 IS data are
#    no longer possible.
```

### Dry-run test

Hard to fully dry-run (you can't easily simulate "Mac gone"). The
practical test is: occasionally check that your password manager
actually has the credentials listed in step 2. A recovery that
needs the `.env` and you don't remember where it is = same as no
recovery.

**Quarterly check:** verify the password manager entries exist for
each of: KITE_API_KEY, KITE_API_SECRET, REDIRECT_URI,
DATABASE_PUBLIC_URL, JWT_SECRET.

---

## Scenario 3 — GitHub repo is lost / inaccessible

**Symptoms:** GitHub account suspended, repo deleted by mistake, the
nav-bajaj/kite-lab URL 404s.

### What's recoverable

- ✅ Every commit is mirrored on every clone — your Mac's local
  `.git/` is a complete history of the project. `git push` to a new
  remote.
- ✅ Production runtime: Railway already has the deployed image
- ✅ Postgres data: untouched

### Recovery steps

```bash
# 1. Create a new repo somewhere (GitHub alt account, GitLab, Bitbucket)
#    Then point the local clone at it:
cd ~/kite-lab
git remote remove origin
git remote add origin https://NEW_HOST/USER/kite-lab.git
git push -u origin main pipeline-improvements

# 2. Update Railway's deploy source to point at the new remote.
#    (Railway → Service → Settings → Source → reconnect.)

# 3. Re-issue the same JWT_SECRET to the Vercel project if Vercel
#    is also reconnected.
```

### Dry-run test

```bash
# 1. Add a second remote and push to it:
git remote add backup-remote https://gitlab.com/USER/kite-lab.git
git push backup-remote --all
git push backup-remote --tags

# 2. Now the same code is at two independent providers. If GitHub
#    dies tomorrow, gitlab.com/USER/kite-lab is already current.
```

A weekly cron that just runs `git push backup-remote --all` keeps the
mirror fresh. Optional polish for Phase 2.5.4 or later.

---

## What we test and how often

| Test | Frequency | Owner |
|---|---|---|
| Restore latest backup to throwaway Postgres | Quarterly | manual |
| Verify password manager entries | Quarterly | manual |
| Push to a second git remote | Weekly (cron) | optional, deferred |
| `backup_database.py` itself runs and produces a non-empty tarball | Daily at 20:00 IST | scheduled (Phase 2.5.4) |
| `backup_database.py --dry-run` succeeds with non-zero irreplaceable counts | After every Railway-config change | manual |

A backup you haven't restored from is not a backup. Run the quarterly
restore test on your calendar.
