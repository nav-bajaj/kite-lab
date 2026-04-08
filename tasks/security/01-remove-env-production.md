# Task 1: Remove .env.production from Git History

**Severity:** CRITICAL
**Status:** `completed`
**User Action Required:** No (file was never committed)

## Problem

Production database credentials are committed to the repository:

```
kite-api/.env.production contains:
DATABASE_URL=postgresql://postgres:DGlIxvzTFFWDpUfRdStYwgbAwHrdORyM@yamabiko.proxy.rlwy.net:51214/railway
```

The password `DGlIxvzTFFWDpUfRdStYwgbAwHrdORyM` is exposed.

## Risk

- Anyone with repo access can connect to production database
- Read/write/delete all data
- Full database compromise

## Fix Steps

### Step 1: Add to .gitignore (Claude)
- Add `.env.production` to `.gitignore`
- Add `*.env.production` pattern

### Step 2: Remove from git history (Claude)
- Use `git filter-repo` or `git filter-branch` to purge the file
- This rewrites git history

### Step 3: Rotate database password (USER ACTION)
- Go to Railway dashboard
- Generate new database password
- Update `DATABASE_URL` environment variable in Railway

### Step 4: Force push cleaned history (Claude)
- Push the cleaned repository
- All collaborators must re-clone

## Breaking Changes

- **Git history rewrite** - collaborators need to re-clone
- **Database connection** - backend will fail until Railway env var is updated

## Verification

```bash
# Verify file is not in history
git log --all --full-history -- kite-api/.env.production
# Should return empty

# Verify backend connects with new password
curl https://kite-lab-production.up.railway.app/api/health
```
