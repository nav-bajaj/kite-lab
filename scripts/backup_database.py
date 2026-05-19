"""Offsite backup of the Railway Postgres database to a local tarball.

Reads DATABASE_URL from the environment, dumps each known table to
CSV.gz, tarballs the lot with a timestamp, runs a smoke-test pass to
re-open the tarball, then applies a 14-daily + 12-weekly + 12-monthly
rotation.

CSV.gz chosen over parquet to avoid a pyarrow dependency. Slightly
larger files (1-10 MB total at current scale, negligible) but tooling-
free: any text editor or `gzip -d` opens them.

Default output dir: ``~/Documents/stock_data/db_backups/``
Output filename:    ``kitelab_db_<YYYYMMDD_HHMMSS>.tar.gz``

The full table inventory (matches kite-api/app/models/models.py):

    allowed_users, trades, trade_matches, equity_curve, holdings,
    metrics, rebalances, signals, open_positions, jobs

A subset is flagged "irreplaceable" — derived from live execution and
not regenerable from a backtest: trades, trade_matches, open_positions,
rebalances. The smoke test verifies each of these has > 0 rows (a backup
where all four are empty is almost certainly a misconfigured connection
to a fresh DB, not a real production snapshot).

Usage:

  # Set DATABASE_URL once (Railway dashboard → variables → DATABASE_URL):
  export DATABASE_URL='postgresql://USER:PASS@HOST:PORT/railway'

  # Backup:
  python scripts/backup_database.py

  # Validate only (read connection, count rows, skip writing):
  python scripts/backup_database.py --dry-run

  # Custom destination:
  python scripts/backup_database.py --output-dir /path/to/dir

Restore via scripts/restore_database.py (companion).
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import tarfile
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# Tables to back up. Order matters for restore (referenced before
# referencing). The dashboard schema is small and mostly flat, so order
# below is a safe topological-ish ordering: lookup/static first, then
# core trade/portfolio tables, then time-series.
TABLES = [
    "allowed_users",
    "jobs",
    "rebalances",
    "trades",
    "trade_matches",
    "open_positions",
    "holdings",
    "signals",
    "equity_curve",
    "metrics",
]

# Tables whose loss would mean unrecoverable live-execution state. If
# any of these are empty in a backup, surface a loud warning.
IRREPLACEABLE = {"trades", "trade_matches", "open_positions", "rebalances"}


# Output directory resolution order:
#   1. --output-dir CLI flag (operator explicit override)
#   2. KITE_BACKUP_OUTPUT_DIR env var (Railway: set to /data/db_backups)
#   3. ~/Documents/stock_data/db_backups/  (Mac-local default)
DEFAULT_OUTPUT_DIR = Path(
    os.environ.get(
        "KITE_BACKUP_OUTPUT_DIR",
        str(Path.home() / "Documents" / "stock_data" / "db_backups"),
    )
)


@dataclass
class BackupReport:
    out_path: Optional[Path] = None
    row_counts: dict = None
    elapsed_s: float = 0.0
    smoke_ok: bool = False
    warnings: list = None

    def __post_init__(self):
        if self.row_counts is None:
            self.row_counts = {}
        if self.warnings is None:
            self.warnings = []


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _redact(url: str) -> str:
    """Mask credentials in a postgresql URL for safe logging."""
    if "@" not in url or "://" not in url:
        return "<unparseable url>"
    scheme, rest = url.split("://", 1)
    creds, host = rest.split("@", 1)
    return f"{scheme}://***:***@{host}"


def _engine_from_env() -> Engine:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit(
            "DATABASE_URL not set. From Railway → Postgres service → "
            "Variables, copy DATABASE_PUBLIC_URL (NOT DATABASE_URL — that "
            "uses the postgres.railway.internal hostname which only "
            "resolves inside Railway's private network)."
        )
    # Some Railway URLs use postgres:// which SQLAlchemy 2.x rejects.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    print(f"[backup] connecting to {_redact(url)}")

    engine = create_engine(url, pool_pre_ping=True, future=True)

    # Fail fast on unreachable host — without this, every per-table query
    # below would emit the same DNS / connection error and the output
    # becomes noise. One clear message is better.
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        msg = str(exc)
        if "postgres.railway.internal" in msg:
            raise SystemExit(
                "Connection failed: the postgres.railway.internal hostname "
                "only resolves inside Railway's private network. From your "
                "Mac you need DATABASE_PUBLIC_URL (Railway → Postgres → "
                "Variables, or enable Public Networking under Settings)."
            ) from None
        raise SystemExit(f"Database connection failed: {exc!s}") from None
    return engine


# ---------------------------------------------------------------------------
# Dump
# ---------------------------------------------------------------------------

def _table_to_csv_gz_bytes(engine: Engine, table: str) -> tuple[bytes, int]:
    """SELECT * FROM <table>, return gzip-compressed CSV bytes + row count.

    Datetime / timestamp columns are written in pandas ISO 8601 format,
    which round-trips cleanly through ``pd.read_csv(..., parse_dates=...)``
    on restore.
    """
    if table not in TABLES:
        raise ValueError(f"unknown table: {table!r} (not in TABLES whitelist)")
    df = pd.read_sql_query(text(f"SELECT * FROM {table}"), engine)  # noqa: S608  # nosemgrep: tools.security.sql-string-interpolation,python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text  # table validated against TABLES whitelist above
    buf = io.BytesIO()
    df.to_csv(buf, index=False, compression="gzip")
    return buf.getvalue(), len(df)


def dump_to_tarball(engine: Engine, out_path: Path,
                    captured_at: str) -> tuple[dict, list[str]]:
    """Write parquet-per-table inside a single timestamped tar.gz.

    Returns (row_counts, warnings).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    row_counts: dict = {}
    warnings: list = []

    # Build the tarball in memory first, then atomically rename into
    # place, so an interrupted dump never leaves a half-written file
    # that confuses rotation.
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    with tarfile.open(tmp_path, "w:gz") as tar:
        # Write a manifest entry so the tarball is self-describing.
        manifest = {
            "captured_at": captured_at,
            "tables": TABLES,
            "schema_version": 1,
            "source_url_redacted": _redact(os.environ.get("DATABASE_URL", "")),
        }
        import json
        man_bytes = json.dumps(manifest, indent=2).encode()
        info = tarfile.TarInfo(name="manifest.json")
        info.size = len(man_bytes)
        info.mtime = int(datetime.utcnow().timestamp())
        tar.addfile(info, io.BytesIO(man_bytes))

        for tbl in TABLES:
            try:
                data, n = _table_to_csv_gz_bytes(engine, tbl)
            except Exception as exc:
                warnings.append(f"{tbl}: dump failed ({exc!s})")
                row_counts[tbl] = -1
                continue
            row_counts[tbl] = n
            info = tarfile.TarInfo(name=f"{tbl}.csv.gz")
            info.size = len(data)
            info.mtime = int(datetime.utcnow().timestamp())
            tar.addfile(info, io.BytesIO(data))
            print(f"  {tbl:<20s}  rows={n}")

    tmp_path.replace(out_path)
    return row_counts, warnings


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

def smoke_test_tarball(path: Path, expected_row_counts: dict) -> list[str]:
    """Re-open the tarball, confirm every expected file is present and
    CSV-readable, and that row counts match what we just wrote.

    Returns a list of error strings. Empty list ⇒ OK.
    """
    errors: list = []
    try:
        with tarfile.open(path, "r:gz") as tar:
            names = set(tar.getnames())
            if "manifest.json" not in names:
                errors.append("manifest.json missing from tarball")
            for tbl in TABLES:
                fname = f"{tbl}.csv.gz"
                if fname not in names:
                    errors.append(f"{fname} missing from tarball")
                    continue
                if expected_row_counts.get(tbl, -1) < 0:
                    continue  # already warned during dump
                member = tar.extractfile(fname)
                if member is None:
                    errors.append(f"{fname} extractable failed")
                    continue
                df = pd.read_csv(io.BytesIO(member.read()), compression="gzip")
                if len(df) != expected_row_counts[tbl]:
                    errors.append(
                        f"{fname} row count mismatch: tarball={len(df)} "
                        f"vs dump={expected_row_counts[tbl]}"
                    )
    except Exception as exc:
        errors.append(f"tarball unreadable: {exc!s}")
    return errors


def check_irreplaceable_nonempty(row_counts: dict) -> list[str]:
    """Warn if any irreplaceable table is empty in this backup."""
    warnings: list = []
    for tbl in IRREPLACEABLE:
        n = row_counts.get(tbl, 0)
        if n == 0:
            warnings.append(
                f"{tbl}: 0 rows — suspicious for an irreplaceable table. "
                f"Confirm you're pointed at the production DB."
            )
        elif n < 0:
            warnings.append(f"{tbl}: dump failed earlier (already logged)")
    return warnings


# ---------------------------------------------------------------------------
# Rotation
# ---------------------------------------------------------------------------

def _parse_ts(name: str) -> Optional[datetime]:
    """Extract datetime from 'kitelab_db_YYYYMMDD_HHMMSS.tar.gz'."""
    prefix = "kitelab_db_"
    if not name.startswith(prefix) or not name.endswith(".tar.gz"):
        return None
    core = name[len(prefix):-len(".tar.gz")]
    try:
        return datetime.strptime(core, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def apply_rotation(out_dir: Path, keep_daily: int = 14,
                   keep_weekly: int = 12, keep_monthly: int = 12,
                   dry_run: bool = False) -> list[Path]:
    """Apply a 14d + 12w + 12m retention to existing backups in out_dir.

    Daily: keep the N most recent backups regardless of weekday.
    Weekly: for each of the last N ISO weeks, keep the most recent backup
            in that week (if not already kept by daily).
    Monthly: for each of the last N calendar months, keep the most recent
             backup in that month (if not already kept).

    Anything not kept is deleted. Returns the list of removed paths.
    """
    files = []
    for p in out_dir.iterdir():
        if p.is_file():
            ts = _parse_ts(p.name)
            if ts is not None:
                files.append((ts, p))
    files.sort(key=lambda t: t[0])  # oldest first

    keep: set = set()
    # Daily — most recent N
    for _, p in files[-keep_daily:]:
        keep.add(p)
    # Weekly — most recent per ISO week, oldest-first scan, keep last per
    # week up to N weeks
    by_week: dict = {}
    for ts, p in files:
        wk = (ts.isocalendar().year, ts.isocalendar().week)
        by_week[wk] = p  # later in list ⇒ more recent ⇒ overwrites earlier
    weeks_sorted = sorted(by_week.keys())
    for wk in weeks_sorted[-keep_weekly:]:
        keep.add(by_week[wk])
    # Monthly
    by_month: dict = {}
    for ts, p in files:
        m = (ts.year, ts.month)
        by_month[m] = p
    months_sorted = sorted(by_month.keys())
    for m in months_sorted[-keep_monthly:]:
        keep.add(by_month[m])

    removed = []
    for _, p in files:
        if p not in keep:
            removed.append(p)
            if not dry_run:
                p.unlink()
    return removed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run(output_dir: Path, dry_run: bool = False) -> BackupReport:
    rep = BackupReport()
    start = datetime.utcnow()
    captured_at = start.isoformat(timespec="seconds") + "Z"

    engine = _engine_from_env()
    if dry_run:
        print("[backup] --dry-run: counting rows, no files written")
        for tbl in TABLES:
            try:
                with engine.connect() as conn:
                    # tbl is iterated directly from the TABLES whitelist constant —
                    # not user input. Safe to interpolate.
                    n = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()  # noqa: S608  # nosemgrep: tools.security.sql-string-interpolation,python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
            except Exception as exc:
                rep.warnings.append(f"{tbl}: count failed ({exc!s})")
                rep.row_counts[tbl] = -1
                continue
            rep.row_counts[tbl] = int(n)
            print(f"  {tbl:<20s}  rows={n}")
        rep.warnings.extend(check_irreplaceable_nonempty(rep.row_counts))
        rep.elapsed_s = (datetime.utcnow() - start).total_seconds()
        return rep

    ts_tag = start.strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"kitelab_db_{ts_tag}.tar.gz"
    print(f"[backup] writing {out_path}")

    rep.row_counts, dump_warnings = dump_to_tarball(engine, out_path, captured_at)
    rep.warnings.extend(dump_warnings)
    rep.out_path = out_path

    errors = smoke_test_tarball(out_path, rep.row_counts)
    if errors:
        rep.smoke_ok = False
        rep.warnings.append("smoke test FAILED — backup will NOT be trusted "
                            "for rotation purposes:")
        rep.warnings.extend(f"  - {e}" for e in errors)
        # Don't apply rotation if smoke test failed — we don't want to
        # delete older known-good backups based on a bad new one.
        print("[backup] SMOKE TEST FAILED — leaving rotation untouched.")
    else:
        rep.smoke_ok = True
        print("[backup] smoke test OK")

    rep.warnings.extend(check_irreplaceable_nonempty(rep.row_counts))

    if rep.smoke_ok:
        removed = apply_rotation(output_dir, dry_run=False)
        if removed:
            print(f"[backup] rotation removed {len(removed)} old backup(s):")
            for p in removed:
                print(f"  - {p.name}")

    rep.elapsed_s = (datetime.utcnow() - start).total_seconds()
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                    help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    ap.add_argument("--dry-run", action="store_true",
                    help="Count rows + check connection but write nothing")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rep = run(args.output_dir, dry_run=args.dry_run)

    print()
    print("=" * 60)
    if rep.out_path:
        size_mb = rep.out_path.stat().st_size / (1024 * 1024) if rep.out_path.exists() else 0
        print(f"Backup written: {rep.out_path}  ({size_mb:.2f} MB)")
    print(f"Elapsed: {rep.elapsed_s:.1f}s")
    print(f"Smoke test: {'OK' if rep.smoke_ok else 'FAIL' if not args.dry_run else 'n/a (--dry-run)'}")
    if rep.row_counts:
        total = sum(n for n in rep.row_counts.values() if n > 0)
        print(f"Total rows: {total}")
    if rep.warnings:
        print()
        print("Warnings:")
        for w in rep.warnings:
            print(f"  - {w}")
    print("=" * 60)

    # Exit non-zero on smoke-test failure so a cron caller can detect it.
    if not args.dry_run and not rep.smoke_ok:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
