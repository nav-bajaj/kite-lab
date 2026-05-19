"""Restore a Postgres backup tarball produced by scripts/backup_database.py.

Reads DATABASE_URL from the env, opens the tarball, and INSERTs each
parquet table into the target DB. Order matches scripts/backup_database.TABLES
so FK-bearing rows are inserted after their references.

By default this is a *strictly additive* restore — no DROP/TRUNCATE.
Pass --truncate to clear each target table before insert (DANGEROUS;
intended only for fresh DR-restored DBs).

The schema must already exist on the target DB — run Alembic migrations
first. This script does not attempt to recreate tables or constraints.

Usage:
  export DATABASE_URL='postgresql://USER:PASS@HOST:PORT/dbname'
  python scripts/restore_database.py \\
      ~/Documents/stock_data/db_backups/kitelab_db_20260516_011500.tar.gz

  # Validate-only (read tarball, count rows, no DB writes):
  python scripts/restore_database.py <file> --dry-run

  # Wipe-then-restore (use only on a freshly migrated empty DB):
  python scripts/restore_database.py <file> --truncate
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tarfile
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


# Import the canonical table order from the backup module so the two
# stay in lockstep if the schema grows.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backup_database import TABLES, _engine_from_env, _redact  # noqa: E402


def _read_manifest(tar: tarfile.TarFile) -> dict:
    member = tar.extractfile("manifest.json")
    if member is None:
        raise SystemExit("tarball has no manifest.json — not a backup_database.py output")
    return json.loads(member.read().decode())


def restore(tar_path: Path, truncate: bool, dry_run: bool) -> int:
    if not tar_path.exists():
        print(f"[restore] file not found: {tar_path}", file=sys.stderr)
        return 1

    engine = _engine_from_env() if not dry_run else None
    if engine is not None:
        print(f"[restore] target: {_redact(os.environ.get('DATABASE_URL', ''))}")

    with tarfile.open(tar_path, "r:gz") as tar:
        manifest = _read_manifest(tar)
        print(f"[restore] tarball captured at {manifest.get('captured_at', '?')}")
        print(f"[restore] backup schema version: {manifest.get('schema_version', '?')}")

        total_rows = 0
        for tbl in TABLES:
            fname = f"{tbl}.csv.gz"
            try:
                member = tar.extractfile(fname)
            except KeyError:
                print(f"  [skip] {fname} not in tarball")
                continue
            if member is None:
                print(f"  [skip] {fname} unreadable")
                continue
            df = pd.read_csv(io.BytesIO(member.read()), compression="gzip")
            print(f"  {tbl:<20s}  rows={len(df)}")
            total_rows += len(df)

            if dry_run:
                continue

            with engine.begin() as conn:
                if truncate:
                    # tbl is iterated from TABLES (line 67) — controlled whitelist,
                    # not user input. Safe to interpolate.
                    conn.execute(text(f"TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE"))  # noqa: S608  # nosemgrep: tools.security.sql-string-interpolation,python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
                if not df.empty:
                    df.to_sql(tbl, conn, if_exists="append", index=False,
                              method="multi", chunksize=1000)

    print()
    print(f"[restore] {'DRY-RUN' if dry_run else 'OK'}: would insert {total_rows} rows"
          if dry_run else f"[restore] OK: inserted {total_rows} rows")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tarball", type=Path)
    ap.add_argument("--truncate", action="store_true",
                    help="TRUNCATE each table before inserting (DANGEROUS)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Read tarball + count rows; no DB writes")
    args = ap.parse_args()

    if args.truncate and not args.dry_run:
        print("WARNING: --truncate will delete existing rows in each target table.")
        print(f"Target DB: {_redact(os.environ.get('DATABASE_URL', ''))}")
        resp = input("Type 'yes' to proceed: ").strip().lower()
        if resp != "yes":
            print("aborted")
            return 1

    return restore(args.tarball, args.truncate, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
