"""
Sync API endpoints - Import data from CSVs to database

All endpoints require authentication.
"""
import os
import tarfile
import tempfile
import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, Query, HTTPException, Depends, UploadFile, File

from app.config import is_valid_universe, UniverseId, settings
from app.auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("")
async def sync_universe(
    universe: UniverseId = Query(default="nse500", description="Universe to sync"),
    user: dict = Depends(require_admin)
):
    """
    Sync data from CSVs to database for a universe.

    This imports holdings, equity curve, and metrics from the latest
    experiment directory into PostgreSQL.
    """
    try:
        from app.services.sync_service import sync_all
        result = sync_all(universe)
        return result
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Sync service not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


@router.post("/all")
async def sync_all_universes(user: dict = Depends(require_admin)):
    """
    Sync data for all universes.
    """
    try:
        from app.services.sync_service import sync_all_universes
        result = sync_all_universes()
        return result
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Sync service not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


# Allowed directories for upload (whitelist).
# nse500_data_historical holds the 2009-2019 GDF backfill that can't
# be re-fetched from Zerodha — see tasks/pipeline_improvements/CRITICAL_DATA.md.
MAX_ARCHIVE_BYTES = 4 * 1024 ** 3        # R-023: the master store is ~2.4 GB extracted; nothing legitimate is larger
MAX_ARCHIVE_MEMBERS = 200_000
MIN_FREE_BYTES_AFTER = 1 * 1024 ** 3     # R-023: keep 1 GB on the volume for tokens, backups and the nightly

ALLOWED_UPLOAD_DIRS = {
    "nse500_data",
    "nse500_data_hourly",
    "nse500_data_historical",
    "nse500_data_gdf_full",   # 2009-2023 deep GDF backfill (raw)
    "nse500_data_full",       # stocks: GDF + Kite stitched (comprehensive)
    "indices_data",
    "indices_data_full",      # indices: historical + Kite stitched (comprehensive)
    # Insight-engine long-history panels (insights_v2 Phase A). breadth.py reads
    # settings.data_dir/nse500_data_merged; macro.py/watchlists.py read
    # settings.data_dir/indices_data_historical via app.insights._paths. Both
    # extract to settings.data_dir/<target> here and are volume-symlinked in
    # scripts/init_persistent_storage.sh so uploads survive a redeploy.
    "nse500_data_merged",     # 16y split-adjusted stock panel (breadth engine)
    "indices_data_historical",  # 16y indices + VIX panel (macro engine)
    # production_port_2026 P1 (2026-09-11): the honest master store. Unlike the flat panels above it
    # is a directory tree (prices/*/, raw/, membership/, benchmarks/, qa/ ...), so it is extracted
    # recursively and merged into MASTER_STORE_DIR (/data/master on the volume). Guarantees (security
    # review 2026-09-11, R-014/R-023): only regular files and directories are accepted (link and special
    # members are rejected before extraction, and extraction uses tarfile's "data" filter where the
    # interpreter has it); the archive's declared size and the volume's free space are checked first;
    # the resolved store path must be an absolute directory named "master" that is not a parent of the
    # token directory; every destination is validated before any file is copied (all-or-nothing);
    # existing files are overwritten by the archive's copies, files absent from the archive are kept.
    "master",
}


@router.post("/upload-data")
async def upload_price_data(
    file: UploadFile = File(...),
    target: str = Query(..., description="Target directory (nse500_data, indices_data, etc.)"),
    user: dict = Depends(require_admin)
):
    """
    Upload a tar.gz archive of price data and extract to the target directory.

    Used for one-time sync of local historical data to the production volume.
    """
    if target not in ALLOWED_UPLOAD_DIRS:
        raise HTTPException(status_code=400, detail=f"Invalid target: {target}. Allowed: {ALLOWED_UPLOAD_DIRS}")

    if not file.filename.endswith((".tar.gz", ".tgz")):
        raise HTTPException(status_code=400, detail="File must be a .tar.gz archive")

    if target == "master":
        # the same resolution the nightly runner uses: MASTER_STORE_DIR (set to /data/master on Railway), else <root>/data/master
        target_dir = Path(os.environ.get("MASTER_STORE_DIR", str(settings.data_dir / "data" / "master")))
        resolved = target_dir.resolve()
        forbidden = {Path("/"), Path("/data"), Path("/app"), Path.home()}
        tokens_dir = Path("/data/tokens").resolve()
        if (not target_dir.is_absolute() or resolved.name != "master" or resolved in forbidden
                or str(tokens_dir).startswith(str(resolved) + os.sep)):
            raise HTTPException(status_code=500, detail="MASTER_STORE_DIR is not a valid store path (must be an absolute directory named 'master')")
    else:
        target_dir = settings.data_dir / target

    tmp_path = None
    try:
        # Save upload to temp file
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

        # Extract tar.gz
        with tarfile.open(tmp_path, "r:gz") as tar:
            members = tar.getmembers()
            # Security: path traversal, link and special members, size and count (R-014, R-023)
            for member in members:
                if member.name.startswith("/") or ".." in member.name:
                    raise HTTPException(status_code=400, detail=f"Unsafe path in archive: {member.name}")
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise HTTPException(status_code=400, detail=f"Link or special member in archive: {member.name}")
            declared = sum(m.size for m in members if m.isfile())
            if declared > MAX_ARCHIVE_BYTES or len(members) > MAX_ARCHIVE_MEMBERS:
                raise HTTPException(status_code=413, detail=f"Archive too large: {declared} bytes, {len(members)} members")
            probe = target_dir if target_dir.exists() else next(p for p in target_dir.parents if p.exists())
            if shutil.disk_usage(probe).free - declared < MIN_FREE_BYTES_AFTER:
                raise HTTPException(status_code=507, detail="Insufficient free space on the data volume for this archive")

            # Extract to a temp dir first, then move files into target.
            # Member names were validated above; the temp dir bounds the blast radius further. R-014.
            with tempfile.TemporaryDirectory() as extract_dir:
                try:
                    tar.extractall(extract_dir, filter="data")  # noqa: S202  # nosec B202  # PEP 706 filter: rejects links, absolute paths and traversal
                except TypeError:   # interpreter without the filter argument (< 3.11.4): members were validated above
                    tar.extractall(extract_dir)  # noqa: S202  # nosec B202  # validated members, sandboxed temp dir; R-014

                # Find the extracted content (might be in a subdirectory matching target name)
                extracted = Path(extract_dir)
                source = extracted / target
                if not source.is_dir():
                    source = extracted

                # Ensure target dir exists
                target_dir.mkdir(parents=True, exist_ok=True)

                # Copy files into target
                count = 0
                if target == "master":
                    root = target_dir.resolve()
                    plan = []
                    for f in source.rglob("*"):          # validate every destination first: all-or-nothing
                        if f.is_symlink():
                            raise HTTPException(status_code=400, detail=f"Symlink in archive: {f.relative_to(source)}")
                        if not f.is_file():
                            continue
                        if f.name.startswith("._") or f.name == ".DS_Store":   # macOS metadata sidecars from a BSD-tar archive; not data
                            continue
                        rel = f.relative_to(source)
                        dest = (target_dir / rel).resolve()
                        if not str(dest).startswith(str(root) + os.sep):
                            raise HTTPException(status_code=400, detail=f"Unsafe path in archive: {rel}")
                        plan.append((f, dest))
                    for f, dest in plan:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dest, follow_symlinks=False)
                        count += 1
                else:
                    for f in source.glob("*.csv"):
                        shutil.copy2(f, target_dir / f.name)
                        count += 1

        logger.info(f"Uploaded {count} files to {target_dir} by {user.get('email')}")
        return {
            "status": "success",
            "target": target,
            "files_written": count,
            "target_dir": str(target_dir),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)   # on success and on every rejection (R-014 review 2026-09-11)
