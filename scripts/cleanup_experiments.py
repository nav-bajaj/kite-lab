#!/usr/bin/env python3
"""
Archive and clean up old experiment directories.

Usage:
    python scripts/cleanup_experiments.py --days 30 --dry-run
    python scripts/cleanup_experiments.py --days 30 --archive
    python scripts/cleanup_experiments.py --days 90 --delete

Examples:
    # See what would be cleaned up (30+ days old)
    python scripts/cleanup_experiments.py --days 30 --dry-run

    # Archive and delete directories older than 60 days
    python scripts/cleanup_experiments.py --days 60 --archive --delete

    # Just delete without archiving (90+ days old)
    python scripts/cleanup_experiments.py --days 90 --delete
"""

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

# Directories containing timestamped experiment runs
EXPERIMENT_DIRS = [
    "experiments/final_portfolio",
    "nifty_100_tests",
    "nifty_250_tests",
]

# Patterns for timestamped subdirectories
DIR_PATTERNS = {
    "experiments/final_portfolio": "final_portfolio_",
    "nifty_100_tests": "nifty100_portfolio_",
    "nifty_250_tests": "nifty250_portfolio_",
}


def parse_timestamp(dirname: str, prefix: str) -> Optional[datetime]:
    """Extract timestamp from directory name like 'final_portfolio_20260214135227'."""
    try:
        if not dirname.startswith(prefix):
            return None
        # Extract timestamp after prefix (14 chars: YYYYMMDDHHMMSS)
        ts_str = dirname[len(prefix):]
        if len(ts_str) < 14:
            return None
        return datetime.strptime(ts_str[:14], "%Y%m%d%H%M%S")
    except ValueError:
        return None


def get_dir_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    try:
        for f in path.rglob('*'):
            if f.is_file():
                total += f.stat().st_size
    except (OSError, PermissionError):
        pass
    return total


def find_old_directories(base_dir: str, days: int) -> List[Tuple[Path, datetime, int]]:
    """Find directories older than N days. Returns list of (path, timestamp, size)."""
    cutoff = datetime.now() - timedelta(days=days)
    old_dirs = []

    base = Path(base_dir)
    if not base.exists():
        return []

    prefix = DIR_PATTERNS.get(base_dir, "")

    for item in base.iterdir():
        if not item.is_dir():
            continue

        ts = parse_timestamp(item.name, prefix)
        if ts and ts < cutoff:
            size = get_dir_size(item)
            old_dirs.append((item, ts, size))

    return sorted(old_dirs, key=lambda x: x[1])


def archive_directory(dir_path: Path, archive_dir: Path) -> Path:
    """Create tar.gz archive of directory."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{dir_path.name}.tar.gz"
    archive_path = archive_dir / archive_name

    # Remove existing archive if present
    if archive_path.exists():
        archive_path.unlink()

    shutil.make_archive(
        str(archive_path).replace('.tar.gz', ''),
        'gztar',
        dir_path.parent,
        dir_path.name
    )
    return archive_path


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def main():
    parser = argparse.ArgumentParser(
        description="Clean up old experiment directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Age threshold in days (default: 30)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Archive directories before deleting"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete old directories"
    )
    parser.add_argument(
        "--archive-dir",
        default="archives",
        help="Archive destination directory (default: archives)"
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Just list old directories without any action"
    )
    args = parser.parse_args()

    # Validate arguments
    if not args.delete and not args.dry_run and not args.list_only:
        print("Specify --dry-run, --list-only, or --delete")
        print("Use --help for usage information")
        return 1

    total_size = 0
    total_dirs = 0

    print(f"Looking for directories older than {args.days} days...")
    print()

    for exp_dir in EXPERIMENT_DIRS:
        old_dirs = find_old_directories(exp_dir, args.days)

        if not old_dirs:
            continue

        print(f"=== {exp_dir}/ ({len(old_dirs)} directories) ===")

        for dir_path, ts, size in old_dirs:
            total_size += size
            total_dirs += 1
            age_days = (datetime.now() - ts).days

            if args.list_only:
                print(f"  {dir_path.name}  ({format_size(size)}, {age_days} days old)")
                continue

            if args.dry_run:
                action = "archive + delete" if args.archive else "delete"
                print(f"  [DRY RUN] Would {action}: {dir_path.name} ({format_size(size)})")
            else:
                if args.archive:
                    archive_path = archive_directory(dir_path, Path(args.archive_dir))
                    print(f"  Archived: {dir_path.name} -> {archive_path}")

                if args.delete:
                    shutil.rmtree(dir_path)
                    print(f"  Deleted: {dir_path.name} ({format_size(size)})")

        print()

    # Summary
    print("=" * 50)
    print(f"Total: {total_dirs} directories, {format_size(total_size)}")

    if args.dry_run:
        print("\nThis was a dry run. Use --delete to actually remove directories.")
    elif args.list_only:
        print("\nUse --dry-run to preview actions, --delete to remove.")
    elif args.delete:
        print(f"\nFreed {format_size(total_size)} of disk space.")

    return 0


if __name__ == "__main__":
    exit(main())
