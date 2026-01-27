"""
Sync price data to external backup location

This script creates and maintains a backup copy of price data directories
outside the repository for redundancy.

Usage:
    python scripts/sync_data_backup.py
    python scripts/sync_data_backup.py --backup-dir /custom/path
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def sync_directory(source: Path, dest: Path, dry_run: bool = False):
    """Sync source directory to destination using rsync-like behavior"""

    if not source.exists():
        print(f"Warning: Source directory does not exist: {source}")
        return False

    if dry_run:
        print(f"[dry-run] Would sync {source} -> {dest}")
        return True

    # Create parent directory if needed
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Remove old backup if exists
    if dest.exists():
        print(f"Removing old backup: {dest}")
        shutil.rmtree(dest)

    # Copy directory
    print(f"Syncing {source} -> {dest}...")
    shutil.copytree(source, dest)

    # Count files
    file_count = len(list(dest.rglob("*.csv")))
    print(f"  ✓ Synced {file_count} CSV files")

    return True


def main():
    parser = argparse.ArgumentParser(description="Sync price data to backup location")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("/Users/navdeep/Documents/stock_data"),
        help="Backup directory path (default: /Users/navdeep/Documents/stock_data)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without actually syncing"
    )

    args = parser.parse_args()

    # Directories to backup
    dirs_to_backup = [
        ("nse500_data", "Daily NSE 500 price data"),
        ("nse500_data_hourly", "Hourly NSE 500 price data"),
        ("indices_data", "Index data"),
    ]

    print(f"\n{'='*80}")
    print(f"DATA BACKUP SYNC")
    print(f"{'='*80}\n")
    print(f"Backup location: {args.backup_dir}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    success_count = 0
    total_count = len(dirs_to_backup)

    for dir_name, description in dirs_to_backup:
        source = ROOT / dir_name
        dest = args.backup_dir / dir_name

        print(f"\n{description}:")
        if sync_directory(source, dest, args.dry_run):
            success_count += 1

    print(f"\n{'='*80}")
    print(f"SUMMARY: {success_count}/{total_count} directories synced successfully")
    print(f"{'='*80}\n")

    if args.dry_run:
        print("Note: This was a dry-run. No files were actually copied.")

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
