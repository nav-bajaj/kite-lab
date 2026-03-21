"""
Sync price data to external backup location

This script creates and maintains a backup copy of price data directories
outside the repository for redundancy. Uses incremental sync (only copies
changed files) for faster backups.

Usage:
    python scripts/sync_data_backup.py
    python scripts/sync_data_backup.py --backup-dir /custom/path
    python scripts/sync_data_backup.py --full  # Force full copy
"""

import argparse
import shutil
import sys
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def files_are_different(src: Path, dst: Path) -> bool:
    """Check if two files are different based on size and mtime."""
    if not dst.exists():
        return True

    src_stat = src.stat()
    dst_stat = dst.stat()

    # Different size = definitely different
    if src_stat.st_size != dst_stat.st_size:
        return True

    # Source is newer = likely different
    if src_stat.st_mtime > dst_stat.st_mtime:
        return True

    return False


def sync_directory_incremental(source: Path, dest: Path, dry_run: bool = False):
    """Sync source directory to destination using incremental rsync-like behavior.

    Only copies files that are new or have changed (based on size/mtime).
    Returns tuple of (success, stats_dict).
    """
    if not source.exists():
        print(f"Warning: Source directory does not exist: {source}")
        return False, {}

    stats = {"copied": 0, "skipped": 0, "deleted": 0, "errors": 0}

    if dry_run:
        print(f"[dry-run] Would sync {source} -> {dest}")
        return True, stats

    # Create destination directory if needed
    dest.mkdir(parents=True, exist_ok=True)

    # Get all source files
    source_files = set()
    for src_file in source.rglob("*"):
        if src_file.is_file():
            rel_path = src_file.relative_to(source)
            source_files.add(rel_path)
            dst_file = dest / rel_path

            if files_are_different(src_file, dst_file):
                # Create parent directories if needed
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src_file, dst_file)
                    stats["copied"] += 1
                except Exception as e:
                    print(f"  Error copying {rel_path}: {e}")
                    stats["errors"] += 1
            else:
                stats["skipped"] += 1

    # Remove files in dest that don't exist in source
    if dest.exists():
        for dst_file in dest.rglob("*"):
            if dst_file.is_file():
                rel_path = dst_file.relative_to(dest)
                if rel_path not in source_files:
                    try:
                        dst_file.unlink()
                        stats["deleted"] += 1
                    except Exception as e:
                        print(f"  Error deleting {rel_path}: {e}")
                        stats["errors"] += 1

    return True, stats


def sync_directory_full(source: Path, dest: Path, dry_run: bool = False):
    """Sync source directory to destination using full copy (original behavior)."""
    if not source.exists():
        print(f"Warning: Source directory does not exist: {source}")
        return False, {}

    stats = {"copied": 0, "skipped": 0, "deleted": 0, "errors": 0}

    if dry_run:
        print(f"[dry-run] Would sync {source} -> {dest}")
        return True, stats

    # Create parent directory if needed
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Remove old backup if exists
    if dest.exists():
        shutil.rmtree(dest)

    # Copy directory
    shutil.copytree(source, dest)

    # Count files
    stats["copied"] = len(list(dest.rglob("*.csv")))

    return True, stats


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
    parser.add_argument(
        "--full",
        action="store_true",
        help="Force full directory copy instead of incremental sync"
    )

    args = parser.parse_args()

    # Skip backup if the destination's parent doesn't exist (e.g., in Docker)
    if not args.backup_dir.parent.exists():
        print(f"Backup directory parent does not exist: {args.backup_dir.parent}")
        print("Skipping backup (likely running in Docker/production)")
        return 0

    # Directories to backup
    dirs_to_backup = [
        ("nse500_data", "Daily NSE 500 price data"),
        ("nse500_data_hourly", "Hourly NSE 500 price data"),
        ("indices_data", "Index data"),
    ]

    sync_mode = "full copy" if args.full else "incremental"

    print(f"\n{'='*80}")
    print(f"DATA BACKUP SYNC ({sync_mode})")
    print(f"{'='*80}\n")
    print(f"Backup location: {args.backup_dir}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    success_count = 0
    total_count = len(dirs_to_backup)
    total_stats = {"copied": 0, "skipped": 0, "deleted": 0, "errors": 0}

    sync_func = sync_directory_full if args.full else sync_directory_incremental

    for dir_name, description in dirs_to_backup:
        source = ROOT / dir_name
        dest = args.backup_dir / dir_name

        print(f"\n{description}:")
        print(f"  {source} -> {dest}")

        success, stats = sync_func(source, dest, args.dry_run)

        if success:
            success_count += 1
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)

            if not args.dry_run and not args.full:
                print(f"  ✓ Copied: {stats['copied']}, Skipped: {stats['skipped']}, Deleted: {stats['deleted']}")
            elif not args.dry_run:
                print(f"  ✓ Copied {stats['copied']} files")

    print(f"\n{'='*80}")
    print(f"SUMMARY: {success_count}/{total_count} directories synced successfully")
    if not args.dry_run and not args.full:
        print(f"  Total: {total_stats['copied']} copied, {total_stats['skipped']} unchanged, {total_stats['deleted']} removed")
    print(f"{'='*80}\n")

    if args.dry_run:
        print("Note: This was a dry-run. No files were actually copied.")

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
