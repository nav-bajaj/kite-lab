"""Phase 5 — raw-tick retention: compress old day dirs, prune the raw.

Raw ticks cost ~230MB/day; the worker volume is 5GB (~3 weeks). Each
EOD, day dirs older than keep_raw_days are tar.gz'd in place
(data/options/ticks_archive/<date>.tar.gz) and the raw dir removed only
after the archive is written AND re-listed. Bars in Postgres stay the
queryable layer; the archive is the replay/reproducibility source.

Safety properties:
- Never touches today's or the last keep_raw_days' dirs.
- Archive verified (tar member count == file count) before any delete.
- Idempotent: an existing archive for a date is never overwritten; if
  the raw dir also still exists, the prior run died between write and
  delete — verify and delete only.
"""
from __future__ import annotations

import logging
import re
import tarfile
from pathlib import Path
from datetime import date, timedelta
from typing import List, Tuple

log = logging.getLogger("options_worker.archive")

_DATE_DIR = re.compile(r"^date=(\d{4}-\d{2}-\d{2})$")


def _day_dirs(ticks_dir: Path) -> List[Tuple[date, Path]]:
    out = []
    if not ticks_dir.exists():
        return out
    for p in ticks_dir.iterdir():
        m = _DATE_DIR.match(p.name)
        if m and p.is_dir():
            out.append((date.fromisoformat(m.group(1)), p))
    return sorted(out)


def _verify(archive_path: Path, expected_files: int) -> bool:
    try:
        with tarfile.open(archive_path, "r:gz") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
        return len(members) == expected_files
    except Exception as exc:
        log.error("archive verify failed for %s: %s", archive_path, exc)
        return False


def archive_old_days(ticks_dir: Path, archive_dir: Path, keep_raw_days: int, today: date) -> dict:
    """Returns counters for the health snapshot / logs."""
    cutoff = today - timedelta(days=keep_raw_days)
    archived = pruned = skipped = failed = 0
    archive_dir.mkdir(parents=True, exist_ok=True)

    for d, raw_dir in _day_dirs(ticks_dir):
        if d >= cutoff:
            continue
        files = sorted(f for f in raw_dir.iterdir() if f.is_file())
        if not files:
            raw_dir.rmdir()
            continue
        dest = archive_dir / f"{d.isoformat()}.tar.gz"

        if not dest.exists():
            tmp = dest.with_suffix(".tar.gz.partial")
            try:
                with tarfile.open(tmp, "w:gz") as tf:
                    for f in files:
                        tf.add(f, arcname=f"{raw_dir.name}/{f.name}")
                tmp.rename(dest)
                archived += 1
            except Exception as exc:
                failed += 1
                log.error("archiving %s failed (raw kept): %s", d, exc)
                tmp.unlink(missing_ok=True)
                continue

        if _verify(dest, len(files)):
            for f in files:
                f.unlink()
            raw_dir.rmdir()
            pruned += 1
            log.info("archived %s -> %s (%.0f MB), raw pruned",
                     d, dest.name, dest.stat().st_size / 1e6)
        else:
            failed += 1
            log.error("archive for %s failed verification — raw dir kept", d)

    return {"archived": archived, "pruned": pruned, "skipped": skipped, "failed": failed}
