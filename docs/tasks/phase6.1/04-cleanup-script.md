# Task 04: Create Cleanup Script

**Status**: `pending`
**Priority**: LOW
**Estimated Time**: 30 minutes

## Problem

Daily pipeline runs create timestamped experiment directories:

```
experiments/final_portfolio/final_portfolio_20260214135227/
experiments/final_portfolio/final_portfolio_20260215120857/
... (26+ directories)

nifty_100_tests/nifty100_portfolio_20260214164622/
... (17+ directories)

nifty_250_tests/nifty250_portfolio_20260214164643/
... (16+ directories)
```

These are already gitignored but accumulate disk space over time.

## Current State

```bash
$ ls experiments/final_portfolio/ | wc -l
26

$ du -sh experiments/
~500MB  experiments/
```

## Solution

Create a cleanup script that:
1. Archives old experiment directories (older than N days)
2. Optionally compresses archives
3. Removes very old archives
4. Provides dry-run mode

## Implementation

### Create `scripts/cleanup_experiments.py`

```python
#!/usr/bin/env python3
"""
Archive and clean up old experiment directories.

Usage:
    python scripts/cleanup_experiments.py --days 30 --dry-run
    python scripts/cleanup_experiments.py --days 30 --archive
    python scripts/cleanup_experiments.py --days 90 --delete
"""

import argparse
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

EXPERIMENT_DIRS = [
    "experiments/final_portfolio",
    "nifty_100_tests",
    "nifty_250_tests",
]

def parse_timestamp(dirname: str) -> datetime | None:
    """Extract timestamp from directory name like 'final_portfolio_20260214135227'"""
    try:
        # Extract last 14 chars as timestamp
        ts = dirname[-14:]
        return datetime.strptime(ts, "%Y%m%d%H%M%S")
    except ValueError:
        return None

def find_old_directories(base_dir: str, days: int) -> list[Path]:
    """Find directories older than N days."""
    cutoff = datetime.now() - timedelta(days=days)
    old_dirs = []

    base = Path(base_dir)
    if not base.exists():
        return []

    for item in base.iterdir():
        if not item.is_dir():
            continue
        ts = parse_timestamp(item.name)
        if ts and ts < cutoff:
            old_dirs.append(item)

    return sorted(old_dirs)

def archive_directory(dir_path: Path, archive_dir: Path) -> Path:
    """Create tar.gz archive of directory."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{dir_path.name}.tar.gz"
    archive_path = archive_dir / archive_name

    shutil.make_archive(
        str(archive_path).replace('.tar.gz', ''),
        'gztar',
        dir_path.parent,
        dir_path.name
    )
    return archive_path

def main():
    parser = argparse.ArgumentParser(description="Clean up old experiment directories")
    parser.add_argument("--days", type=int, default=30, help="Age threshold in days")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--archive", action="store_true", help="Archive before deleting")
    parser.add_argument("--delete", action="store_true", help="Delete old directories")
    parser.add_argument("--archive-dir", default="archives", help="Archive destination")
    args = parser.parse_args()

    if not args.delete and not args.dry_run:
        print("Specify --dry-run or --delete")
        return

    total_size = 0
    total_dirs = 0

    for exp_dir in EXPERIMENT_DIRS:
        old_dirs = find_old_directories(exp_dir, args.days)

        for d in old_dirs:
            size = sum(f.stat().st_size for f in d.rglob('*') if f.is_file())
            size_mb = size / (1024 * 1024)
            total_size += size
            total_dirs += 1

            if args.dry_run:
                print(f"[DRY RUN] Would delete: {d} ({size_mb:.1f} MB)")
            else:
                if args.archive:
                    archive_path = archive_directory(d, Path(args.archive_dir))
                    print(f"Archived: {d} -> {archive_path}")

                if args.delete:
                    shutil.rmtree(d)
                    print(f"Deleted: {d} ({size_mb:.1f} MB)")

    print(f"\nTotal: {total_dirs} directories, {total_size / (1024*1024):.1f} MB")

if __name__ == "__main__":
    main()
```

### Usage Examples

```bash
# See what would be cleaned up (30+ days old)
python scripts/cleanup_experiments.py --days 30 --dry-run

# Archive and delete directories older than 60 days
python scripts/cleanup_experiments.py --days 60 --archive --delete

# Just delete without archiving (90+ days old)
python scripts/cleanup_experiments.py --days 90 --delete
```

## Verification

1. Script runs without errors
2. Dry-run shows expected directories
3. Archive creates valid tar.gz files
4. Delete removes directories

## Files Created

- `scripts/cleanup_experiments.py`

## Optional: Add to Daily Pipeline

Consider adding cleanup to `run_daily_pipeline.py`:

```python
# At end of pipeline
if args.cleanup:
    subprocess.run([
        sys.executable, "scripts/cleanup_experiments.py",
        "--days", "60", "--delete"
    ])
```

---

*Task created: 2026-03-20*
