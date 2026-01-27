# Data Backup System

## Overview

Automatic backup of price data directories to an external location outside the repository for redundancy and data safety.

## Backup Location

**Path:** `/Users/navdeep/Documents/stock_data/`

**Contents:**
- `nse500_data/` - Daily NSE 500 price data (499 stocks, ~30MB)
- `nse500_data_hourly/` - Hourly NSE 500 data (90 days, ~13MB)
- `indices_data/` - Index data (Nifty 50, 100, 500, etc., ~2.5MB)

**Total size:** ~45MB

## Automatic Backup

The backup runs automatically as part of the daily pipeline:

```bash
python scripts/run_daily_pipeline.py --with-login
```

This will:
1. Login to Kite API
2. Fetch latest NSE 500 data
3. Fetch latest indices data
4. Update Nifty 100 benchmark
5. Build momentum rankings
6. **Sync backup to `/Users/navdeep/Documents/stock_data/`**

## Manual Backup

You can manually sync the backup at any time:

```bash
# Sync all data directories
python scripts/sync_data_backup.py

# Dry-run (show what would be synced)
python scripts/sync_data_backup.py --dry-run

# Custom backup location
python scripts/sync_data_backup.py --backup-dir /custom/path
```

## Backup Behavior

**Sync Strategy:**
- Complete directory replacement (not incremental)
- Old backup is removed before creating new one
- Ensures backup is always a clean, complete copy

**What Gets Backed Up:**
- All CSV files in each directory
- Directory structure is preserved
- File timestamps from source are maintained

**What Doesn't Get Backed Up:**
- Repository code (scripts, configs)
- Experiment results
- Generated reports
- Git metadata

## Data Safety

**Redundancy:**
- Primary: Repository working directory
- Backup: External location outside repo
- Remote: GitHub (code only, data is gitignored)

**Recovery:**
If repository data is corrupted or lost:

```bash
# Restore from backup
cp -r /Users/navdeep/Documents/stock_data/nse500_data ./
cp -r /Users/navdeep/Documents/stock_data/nse500_data_hourly ./
cp -r /Users/navdeep/Documents/stock_data/indices_data ./
```

## Monitoring

After each sync, the script reports:
- Number of CSV files synced per directory
- Success/failure status
- Total directories synced

Example output:
```
================================================================================
DATA BACKUP SYNC
================================================================================

Backup location: /Users/navdeep/Documents/stock_data
Timestamp: 2026-01-27 22:25:48


Daily NSE 500 price data:
Syncing /Users/navdeep/kite-lab/nse500_data -> /Users/navdeep/Documents/stock_data/nse500_data...
  ✓ Synced 499 CSV files

Hourly NSE 500 price data:
Syncing /Users/navdeep/kite-lab/nse500_data_hourly -> /Users/navdeep/Documents/stock_data/nse500_data_hourly...
  ✓ Synced 499 CSV files

Index data:
Syncing /Users/navdeep/kite-lab/indices_data -> /Users/navdeep/Documents/stock_data/indices_data...
  ✓ Synced 38 CSV files

================================================================================
SUMMARY: 3/3 directories synced successfully
================================================================================
```

## Notes

- Backup location is outside git repository (won't be committed)
- Sync is fast (~5-10 seconds for full backup)
- No compression used (data is already CSV, compresses poorly)
- Suitable for local machine backup only (not for cloud sync)

## Future Enhancements

Possible improvements:
- Incremental backup (only sync changed files)
- Compression for older data
- Cloud storage integration (S3, Google Drive)
- Backup rotation (keep last N backups)
- Verification checksums

---

**Created:** January 2026
**Script:** `scripts/sync_data_backup.py`
**Integration:** `scripts/run_daily_pipeline.py`
