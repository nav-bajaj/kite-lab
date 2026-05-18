"""Mirror ``~/Documents/stock_data/`` to Google Drive for offsite redundancy.

Phase 2.5.4 of the pipeline-improvements work. Closes the
single-Mac-risk loop identified in CRITICAL_DATA.md.

What gets uploaded
------------------

* ``db_backups/`` (tarballs produced by ``scripts/backup_database.py``) —
  mirrored file-by-file. Each daily/weekly/monthly tarball preserved
  individually so the local rotation policy is faithfully reflected
  in Drive.

* ``nse500_data/``, ``nse500_data_historical/``, ``nse500_data_hourly/``,
  ``indices_data/`` — tarred-and-gzipped on the fly, uploaded as a
  single timestamped file per directory per run
  (``<dirname>_<YYYYMMDD>.tar.gz``). Rotation keeps the last 7 daily
  tarballs in Drive; older ones are deleted to avoid Drive bloat.

The Drive layout, under ``My Drive/kite-lab-backups/``:

    db_backups/                          file-per-tarball mirror
    nse500_data_snapshots/               7 daily tarballs
    nse500_data_historical_snapshots/    7 daily tarballs
    nse500_data_hourly_snapshots/        7 daily tarballs
    indices_data_snapshots/              7 daily tarballs

One-time setup
--------------

1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the Google Drive API on that project
3. APIs & Services → Credentials → Create credentials → OAuth client ID
   - Application type: Desktop app
   - Download the JSON; save it to
     ``~/.config/kite-lab/gdrive_client_secret.json``
4. First run:  ``python scripts/upload_to_gdrive.py auth``
   This opens a browser, you grant Drive scope, the refresh token is
   saved to ``~/.config/kite-lab/gdrive_token.json``. Subsequent runs
   reuse the refresh token (no browser).

Daily use
---------

    python scripts/upload_to_gdrive.py upload

Best invoked after ``scripts/backup_database.py`` finishes so the
freshly-written DB tarball is the first thing uploaded.

Exit codes:
  0 = all uploads OK
  1 = setup or auth problem
  2 = one or more uploads failed (other uploads may still have succeeded)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import tarfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".config" / "kite-lab"
CLIENT_SECRET_PATH = CONFIG_DIR / "gdrive_client_secret.json"
TOKEN_PATH = CONFIG_DIR / "gdrive_token.json"

# Source-root resolution order:
#   1. KITE_BACKUP_SOURCE_ROOT env var (Railway: set to /data)
#   2. ~/Documents/stock_data/  (Mac-local default)
SOURCE_ROOT = Path(os.environ.get(
    "KITE_BACKUP_SOURCE_ROOT",
    str(Path.home() / "Documents" / "stock_data"),
))
DRIVE_ROOT_FOLDER = "kite-lab-backups"

# Top-level dirs that get the "file-by-file mirror" treatment.
MIRROR_FILE_BY_FILE = {"db_backups"}

# Top-level dirs that get the "daily tarball with rotation" treatment.
SNAPSHOT_DIRS = (
    "nse500_data",
    "nse500_data_historical",
    "nse500_data_hourly",
    "indices_data",
)
SNAPSHOT_RETENTION = 7  # Keep last N daily tarballs in Drive per dir

# Drive API scope.
# drive.file restricts the app to files it creates or that the user
# explicitly opens via a Drive picker. Sufficient for our use because
# we create both the kite-lab-backups folder and all files within it,
# and rotation only deletes files this app created. This minimises
# blast radius if the OAuth refresh token leaks (notably: when stored
# on Railway as an env var).
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _load_credentials():
    """Load cached OAuth credentials, refreshing if expired.

    Credential resolution order:
      1. GDRIVE_REFRESH_TOKEN_JSON env var (Railway-style: full
         authorized-user JSON pasted in as a single env-var value)
      2. ~/.config/kite-lab/gdrive_token.json (Mac-local default)

    Returns the Credentials object, or None if first-time auth is needed.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    env_token = os.environ.get("GDRIVE_REFRESH_TOKEN_JSON", "").strip()
    if env_token:
        creds = Credentials.from_authorized_user_info(
            json.loads(env_token), SCOPES,
        )
    elif TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    else:
        return None

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Only persist refreshed token back to disk in local-file mode;
        # on Railway the env var is the source of truth and we don't
        # touch the container filesystem (it's ephemeral anyway).
        if not env_token and TOKEN_PATH.exists():
            TOKEN_PATH.write_text(creds.to_json())
    return creds


def _run_oauth_flow():
    """Interactive OAuth: open browser, grant scope, cache refresh token.

    Always runs from the operator's Mac (Railway containers have no
    browser). After this completes, the resulting JSON can either be
    left at ~/.config/kite-lab/gdrive_token.json (local use) or copied
    into the GDRIVE_REFRESH_TOKEN_JSON env var on Railway (production
    use). See RAILWAY_BACKUP_SETUP.md for the copy-to-Railway step.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    # Allow env-var override of the client-secret file path so the
    # operator can keep multiple OAuth clients (e.g. one with old
    # drive scope, one with drive.file).
    secret_path = Path(os.environ.get(
        "GDRIVE_CLIENT_SECRET_PATH", str(CLIENT_SECRET_PATH),
    ))
    if not secret_path.exists():
        raise SystemExit(
            f"Missing {secret_path}.\n"
            f"Download the OAuth client-secret JSON from Google Cloud Console "
            f"(APIs & Services → Credentials → Create credentials → OAuth client "
            f"ID, Desktop app) and save it there. See the top-of-file docstring "
            f"for the full setup steps."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
    creds = flow.run_local_server(port=0)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    os.chmod(TOKEN_PATH, 0o600)
    print(f"[upload] saved refresh token to {TOKEN_PATH}")
    print(f"[upload] scope granted: {SCOPES[0]}")
    print()
    print("To use this token on Railway, copy the JSON below into a new")
    print("env var named GDRIVE_REFRESH_TOKEN_JSON (single-line value):")
    print()
    print(f"  cat {TOKEN_PATH} | tr -d '\\n'")
    print()
    return creds


def _build_service(creds):
    """Build a googleapiclient Drive v3 service from creds."""
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def _drive_find_or_create_folder(svc, name: str, parent_id: Optional[str] = None) -> str:
    """Return the Drive folder ID for ``name`` under ``parent_id`` (or root).

    Creates the folder if it doesn't exist.
    """
    q_parts = [
        "mimeType = 'application/vnd.google-apps.folder'",
        f"name = '{name}'",
        "trashed = false",
    ]
    if parent_id:
        q_parts.append(f"'{parent_id}' in parents")
    else:
        q_parts.append("'root' in parents")
    q = " and ".join(q_parts)
    resp = svc.files().list(q=q, fields="files(id, name)", pageSize=10).execute()
    for f in resp.get("files", []):
        return f["id"]
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]
    folder = svc.files().create(body=body, fields="id").execute()
    return folder["id"]


def _drive_list_files(svc, folder_id: str) -> list[dict]:
    """List all files in ``folder_id`` with size + md5 + modifiedTime."""
    files: list[dict] = []
    page_token: Optional[str] = None
    while True:
        resp = svc.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, size, md5Checksum, modifiedTime)",
            pageSize=200, pageToken=page_token,
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def _md5_local(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _upload_file(svc, local_path: Path, folder_id: str,
                 drive_name: Optional[str] = None) -> dict:
    """Upload ``local_path`` to ``folder_id``. Returns the new file metadata."""
    from googleapiclient.http import MediaFileUpload

    name = drive_name or local_path.name
    body = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(str(local_path), resumable=True)
    return svc.files().create(
        body=body, media_body=media, fields="id, name, size",
    ).execute()


# ---------------------------------------------------------------------------
# Mirror + snapshot strategies
# ---------------------------------------------------------------------------

@dataclass
class UploadStats:
    uploaded: int = 0
    skipped: int = 0
    deleted: int = 0
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def mirror_db_backups(svc, root_folder_id: str, source_dir: Path) -> UploadStats:
    """File-by-file mirror of ``source_dir`` → Drive ``db_backups`` folder.

    A local file is uploaded only if a Drive file with the same name and
    same md5 doesn't already exist. Deletions on disk are NOT propagated
    to Drive (rotation in Drive is the operator's responsibility — Drive
    is the deeper archive).
    """
    stats = UploadStats()
    if not source_dir.is_dir():
        return stats
    drive_folder_id = _drive_find_or_create_folder(svc, source_dir.name, root_folder_id)
    existing = {f["name"]: f for f in _drive_list_files(svc, drive_folder_id)}

    for local in sorted(source_dir.iterdir()):
        if not local.is_file():
            continue
        d = existing.get(local.name)
        if d is not None:
            # Already there; check md5 to detect a partial / corrupted prior upload.
            if d.get("md5Checksum") == _md5_local(local):
                stats.skipped += 1
                continue
            print(f"  {local.name}: md5 mismatch with Drive copy, re-uploading")
        try:
            _upload_file(svc, local, drive_folder_id)
            stats.uploaded += 1
            print(f"  [up] {local.name}")
        except Exception as exc:
            stats.errors.append(f"{local.name}: {exc!s}")
    return stats


def snapshot_dir_to_drive(svc, root_folder_id: str, source_dir: Path,
                          retention: int = SNAPSHOT_RETENTION) -> UploadStats:
    """Tarball ``source_dir``, upload as ``<dirname>_<YYYYMMDD>.tar.gz``.

    If a snapshot for today already exists in Drive, skip. Otherwise
    create the tarball in-memory, upload, then trim older snapshots to
    ``retention`` newest.
    """
    stats = UploadStats()
    if not source_dir.is_dir():
        return stats

    drive_dirname = f"{source_dir.name}_snapshots"
    drive_folder_id = _drive_find_or_create_folder(svc, drive_dirname, root_folder_id)
    today = datetime.now().strftime("%Y%m%d")
    drive_name = f"{source_dir.name}_{today}.tar.gz"

    existing = _drive_list_files(svc, drive_folder_id)
    if any(f["name"] == drive_name for f in existing):
        print(f"  {drive_name}: today's snapshot already in Drive, skipping")
        stats.skipped += 1
    else:
        # Build the tarball to a temp file (in-memory could OOM on big dirs).
        tmp_path = Path(f"/tmp/{drive_name}")
        try:
            print(f"  {drive_name}: building tarball from {source_dir} ...")
            with tarfile.open(tmp_path, "w:gz") as tar:
                tar.add(source_dir, arcname=source_dir.name)
            size_mb = tmp_path.stat().st_size / (1024 * 1024)
            print(f"  {drive_name}: tarball {size_mb:.1f} MB, uploading ...")
            _upload_file(svc, tmp_path, drive_folder_id, drive_name=drive_name)
            stats.uploaded += 1
            print(f"  [up] {drive_name}")
        except Exception as exc:
            stats.errors.append(f"{drive_name}: {exc!s}")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    # Rotation in Drive: keep `retention` newest tarballs of this dir.
    existing = _drive_list_files(svc, drive_folder_id)  # refresh after upload
    matching = [f for f in existing if f["name"].startswith(f"{source_dir.name}_")
                and f["name"].endswith(".tar.gz")]
    # Newest first (filenames sort lexicographically by date)
    matching.sort(key=lambda f: f["name"], reverse=True)
    for old in matching[retention:]:
        try:
            svc.files().delete(fileId=old["id"]).execute()
            stats.deleted += 1
            print(f"  [rotate] removed {old['name']} from Drive")
        except Exception as exc:
            stats.errors.append(f"rotate {old['name']}: {exc!s}")
    return stats


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_auth(args) -> int:
    creds = _load_credentials()
    if creds and not creds.expired:
        print(f"[upload] already authed; token at {TOKEN_PATH}")
        return 0
    _run_oauth_flow()
    print("[upload] auth complete")
    return 0


def cmd_upload(args) -> int:
    creds = _load_credentials()
    if creds is None or (creds.expired and not creds.refresh_token):
        print("[upload] no valid credentials; run "
              "`python scripts/upload_to_gdrive.py auth` first", file=sys.stderr)
        return 1

    svc = _build_service(creds)
    print(f"[upload] source: {SOURCE_ROOT}")
    root_id = _drive_find_or_create_folder(svc, DRIVE_ROOT_FOLDER)
    print(f"[upload] drive folder: My Drive/{DRIVE_ROOT_FOLDER}/  (id={root_id})")

    overall = UploadStats()

    for name in sorted(MIRROR_FILE_BY_FILE):
        src = SOURCE_ROOT / name
        print(f"\n[mirror] {src}")
        s = mirror_db_backups(svc, root_id, src)
        overall.uploaded += s.uploaded
        overall.skipped += s.skipped
        overall.errors.extend(s.errors)

    for name in SNAPSHOT_DIRS:
        src = SOURCE_ROOT / name
        print(f"\n[snapshot] {src}")
        s = snapshot_dir_to_drive(svc, root_id, src)
        overall.uploaded += s.uploaded
        overall.skipped += s.skipped
        overall.deleted += s.deleted
        overall.errors.extend(s.errors)

    print()
    print("=" * 60)
    print(f"Upload summary: {overall.uploaded} uploaded, "
          f"{overall.skipped} skipped, {overall.deleted} old removed")
    if overall.errors:
        print(f"Errors: {len(overall.errors)}")
        for e in overall.errors:
            print(f"  - {e}")
    print("=" * 60)
    return 2 if overall.errors else 0


def cmd_status(args) -> int:
    """Print what's currently in the Drive backup folder."""
    creds = _load_credentials()
    if creds is None:
        print("[upload] not authed yet — run `auth` first")
        return 1
    svc = _build_service(creds)
    root_id = _drive_find_or_create_folder(svc, DRIVE_ROOT_FOLDER)
    print(f"My Drive/{DRIVE_ROOT_FOLDER}/  (id={root_id})")
    for sub_name in sorted(MIRROR_FILE_BY_FILE) + [f"{n}_snapshots" for n in SNAPSHOT_DIRS]:
        sub_id = _drive_find_or_create_folder(svc, sub_name, root_id)
        files = _drive_list_files(svc, sub_id)
        total_bytes = sum(int(f.get("size", 0)) for f in files if f.get("size"))
        print(f"  {sub_name}/  {len(files)} files, {total_bytes/(1024*1024):.1f} MB")
        for f in sorted(files, key=lambda x: x["name"]):
            sz = int(f.get("size", 0)) / (1024 * 1024) if f.get("size") else 0
            mt = f.get("modifiedTime", "?")
            print(f"    {f['name']:<50s}  {sz:6.1f} MB  {mt}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("auth", help="Run the one-time OAuth flow")
    sub.add_parser("upload", help="Mirror source dir to Drive (default action)")
    sub.add_parser("status", help="Print the current Drive backup state")

    args = ap.parse_args()
    # No subcommand → default to upload. Lets schedulers (kite-api
    # APScheduler, Mac cron) invoke the script without an explicit
    # action. Auth and status remain CLI-only.
    if args.cmd is None or args.cmd == "upload":
        return cmd_upload(args)
    if args.cmd == "auth":
        return cmd_auth(args)
    if args.cmd == "status":
        return cmd_status(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
