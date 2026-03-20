# Task 05: Update Runbook

**Status**: `pending`
**Priority**: MEDIUM
**Estimated Time**: 25 minutes

## Problem

`runbook.md` may not include dashboard-related operations. Need to add:
- Dashboard monitoring procedures
- Database sync operations
- Job management via admin panel
- Troubleshooting dashboard issues

## Current State

Review `runbook.md` to determine what's missing.

## Changes Required

### 1. Add Dashboard Monitoring Section

```markdown
## Dashboard Monitoring

### Health Checks

**Backend Health:**
```bash
curl https://kite-lab-production.up.railway.app/api/health
# Expected: {"status": "healthy", "version": "1.1.0"}
```

**Frontend Health:**
- Visit https://kite-lab.vercel.app
- Should load without errors
- Universe selector should work

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| 500 errors on API | Database connection | Check Railway PostgreSQL status |
| Stale data | Sync not run | Run sync from admin panel |
| Auth failures | Token expired | Re-authenticate via Kite Login |
| Frontend 404 | Deployment issue | Check Vercel deployment status |
```

### 2. Add Database Sync Procedures

```markdown
## Database Sync

### Manual Sync (Admin Panel)

1. Go to https://kite-lab.vercel.app/admin
2. Click "Daily Pipeline" quick action
3. Monitor job logs in real-time
4. Verify data updated in Portfolio view

### Manual Sync (CLI)

```bash
cd kite-api
source .venv/bin/activate

# Sync all universes
python scripts/sync_to_production.py \
  --database-url "$DATABASE_URL" \
  --data-dir /path/to/kite-lab
```

### Verify Sync Success

1. Check latest holdings date in Portfolio view
2. Compare row counts with local CSV files
3. Verify equity curve extends to current date
```

### 3. Add Job Management Section

```markdown
## Job Management

### Running Jobs via Admin Panel

1. **Quick Actions** - One-click for common operations
   - Daily Pipeline: Fetch data + build signals + sync
   - Generate Portfolio: Build signals + run backtest
   - Kite Login: Refresh API token
   - Backup Data: Sync to backup folder

2. **Portfolio Generator** - Custom parameters
   - Select universe (NSE 500, Nifty 100, Nifty 250)
   - Choose lookback (6, 9, 12 months)
   - Set rebalance frequency

3. **Job List** - View recent jobs
   - Click job to view logs
   - Cancel running jobs if needed

### Scheduled Jobs

Default schedule:
- **Daily Pipeline**: 9:30 AM IST (after market open)
- **Data Backup**: 6:00 PM IST (after market close)

Modify schedules in Admin > Schedule Table.
```

### 4. Add Troubleshooting Section

```markdown
## Dashboard Troubleshooting

### API Not Responding

1. Check Railway dashboard for service status
2. View Railway logs for errors
3. Restart service if needed:
   ```bash
   # Via Railway CLI
   railway up --detach
   ```

### Database Issues

1. Check PostgreSQL status in Railway
2. Verify DATABASE_URL is set correctly
3. Run migrations if needed:
   ```bash
   cd kite-api
   alembic upgrade head
   ```

### Frontend Build Failures

1. Check Vercel deployment logs
2. Verify environment variables set
3. Trigger redeploy if needed

### Data Sync Failures

1. Check job logs in admin panel
2. Verify local CSV files exist
3. Check for schema mismatches
4. Re-run sync with `--force` flag
```

## Verification

After changes:
1. Dashboard monitoring procedures documented
2. Sync operations explained
3. Job management guide included
4. Troubleshooting covers common issues

## Files Modified

- `runbook.md`

---

*Task created: 2026-03-20*
