"""Phase 6 — tick-archive offload: push day archives to Drive, then prune.

``archive.py`` turns raw tick day-dirs into ``<date>.tar.gz`` on the volume
but nothing ever removed them, so the 5GB worker volume filled at roughly
140MB/session. This module is the missing second half: each EOD, archives
older than ``keep_archive_days`` are uploaded to Google Drive and deleted
locally only once Drive's md5 matches the local file.

Credentials come from ``GDRIVE_REFRESH_TOKEN_JSON`` (the same authorized-user
JSON the kite-lab service already uses for nightly backups). With no creds
present the offload is a no-op — capture is never put at risk by it.

Safety properties, deliberately mirroring ``archive.py``:
- Never touches the last ``keep_archive_days`` archives.
- Local delete only after Drive's md5Checksum equals the local md5.
- Idempotent: an archive already in Drive with a matching md5 is not
  re-uploaded, only pruned — that covers a prior run that died between
  upload and delete.
- Any mismatch or error leaves BOTH copies in place and counts as failed.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("options_worker.offload")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Matches only completed archives — never the .tar.gz.partial a failed
# archive run can leave behind.
_ARCHIVE_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.tar\.gz$")

ROOT_FOLDER = "kite-lab-backups"


def _load_credentials():
    """Authorized-user creds from the env, refreshed if stale.

    Returns None when no token is configured, which the caller treats as
    "offload not wired up yet" rather than an error.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    env_token = os.environ.get("GDRIVE_REFRESH_TOKEN_JSON", "").strip()
    if not env_token:
        return None

    creds = Credentials.from_authorized_user_info(json.loads(env_token), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _build_service(creds):
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_or_create_folder(svc, name: str, parent_id: Optional[str] = None) -> str:
    q = [
        "mimeType = 'application/vnd.google-apps.folder'",
        f"name = '{name}'",
        "trashed = false",
        f"'{parent_id}' in parents" if parent_id else "'root' in parents",
    ]
    resp = svc.files().list(
        q=" and ".join(q), fields="files(id, name)", pageSize=10,
    ).execute()
    for f in resp.get("files", []):
        return f["id"]

    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    return svc.files().create(body=body, fields="id").execute()["id"]


def _list_folder(svc, folder_id: str) -> Dict[str, dict]:
    """name -> file metadata for everything already in the Drive folder."""
    out: Dict[str, dict] = {}
    page_token = None
    while True:
        resp = svc.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, size, md5Checksum)",
            pageSize=200, pageToken=page_token,
        ).execute()
        for f in resp.get("files", []):
            out[f["name"]] = f
        page_token = resp.get("nextPageToken")
        if not page_token:
            return out


def _md5_local(path: Path) -> str:
    # md5 only to match Drive's md5Checksum for integrity/dedup, never for
    # security; usedforsecurity=False marks that intent for SAST scanners.
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _upload(svc, path: Path, folder_id: str) -> dict:
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(path), mimetype="application/gzip", resumable=True)
    return svc.files().create(
        body={"name": path.name, "parents": [folder_id]},
        media_body=media,
        fields="id, name, size, md5Checksum",
    ).execute()


def _archive_files(archive_dir: Path) -> List[Tuple[date, Path]]:
    out = []
    if not archive_dir.exists():
        return out
    for p in sorted(archive_dir.iterdir()):
        m = _ARCHIVE_FILE.match(p.name)
        if m and p.is_file():
            out.append((date.fromisoformat(m.group(1)), p))
    return out


def offload_archives(
    archive_dir: Path,
    keep_archive_days: int,
    today: date,
    service=None,
    folder_name: str = "options_ticks",
    max_files: Optional[int] = None,
) -> dict:
    """Upload aged archives to Drive and prune the local copies.

    ``service`` is injectable so tests can drive a fake Drive. ``max_files``
    bounds the work one run will do, so a backlog drains over several nights
    instead of blocking a single EOD for minutes.

    Returns counters for the health snapshot / logs.
    """
    stats = {"uploaded": 0, "pruned": 0, "skipped": 0, "failed": 0, "freed_mb": 0.0}

    candidates = [
        (d, p) for d, p in _archive_files(archive_dir)
        if d < today - timedelta(days=keep_archive_days)
    ]
    if not candidates:
        return stats

    if service is None:
        creds = _load_credentials()
        if creds is None:
            log.warning(
                "offload skipped: GDRIVE_REFRESH_TOKEN_JSON not set (%d archives waiting)",
                len(candidates),
            )
            stats["skipped"] = len(candidates)
            return stats
        service = _build_service(creds)

    root_id = _find_or_create_folder(service, ROOT_FOLDER)
    folder_id = _find_or_create_folder(service, folder_name, root_id)
    remote = _list_folder(service, folder_id)

    if max_files is not None:
        candidates = candidates[:max_files]

    for d, path in candidates:
        size_mb = path.stat().st_size / 1e6
        try:
            local_md5 = _md5_local(path)
            existing = remote.get(path.name)

            if existing is not None and existing.get("md5Checksum") == local_md5:
                # A prior run uploaded this and died before pruning.
                path.unlink()
                stats["pruned"] += 1
                stats["freed_mb"] += size_mb
                log.info("offload: %s already in Drive (md5 match), local pruned", path.name)
                continue

            if existing is not None:
                # Same name, different content: never overwrite, never delete.
                stats["failed"] += 1
                log.error(
                    "offload: %s exists in Drive with a different md5 — both copies kept",
                    path.name,
                )
                continue

            meta = _upload(service, path, folder_id)
            stats["uploaded"] += 1

            if meta.get("md5Checksum") != local_md5:
                stats["failed"] += 1
                log.error(
                    "offload: %s uploaded but md5 mismatch (drive=%s local=%s) — local kept",
                    path.name, meta.get("md5Checksum"), local_md5,
                )
                continue

            path.unlink()
            stats["pruned"] += 1
            stats["freed_mb"] += size_mb
            log.info("offload: %s -> Drive (%.0f MB, md5 verified), local pruned",
                     path.name, size_mb)

        except Exception as exc:
            stats["failed"] += 1
            log.error("offload of %s failed (local kept): %s", path.name, exc)

    stats["freed_mb"] = round(stats["freed_mb"], 1)
    return stats


def _main() -> int:
    """One-off CLI: python -u -m app.workers.options.offload [--keep N] [--dry-run]

    Used for the initial backlog drain; the EOD hook handles steady state.
    """
    import argparse
    import shutil

    from app.workers.options.config import get_worker_settings
    from app.workers.options.scheduler import now_ist

    settings = get_worker_settings()
    ap = argparse.ArgumentParser(description="Offload tick archives to Google Drive")
    ap.add_argument("--keep", type=int, default=settings.keep_archive_days,
                    help="days of archives to leave on the volume")
    ap.add_argument("--max-files", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    archive_dir = settings.ticks_archive_dir
    today = now_ist().date()

    pending = [
        (d, p) for d, p in _archive_files(archive_dir)
        if d < today - timedelta(days=args.keep)
    ]
    total_mb = sum(p.stat().st_size for _, p in pending) / 1e6
    log.info("offload: %d archives pending (%.0f MB), keep=%d days",
             len(pending), total_mb, args.keep)
    if args.dry_run:
        for d, p in pending:
            log.info("  would offload %s (%.0f MB)", p.name, p.stat().st_size / 1e6)
        return 0

    before = shutil.disk_usage(archive_dir).free / 1e6
    stats = offload_archives(archive_dir, args.keep, today, max_files=args.max_files)
    after = shutil.disk_usage(archive_dir).free / 1e6
    log.info("offload done: %s | volume free %.0f MB -> %.0f MB", stats, before, after)
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(_main())
