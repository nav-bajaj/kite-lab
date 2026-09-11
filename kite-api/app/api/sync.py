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
    # recursively and merged into MASTER_STORE_DIR (/data/master on the volume). Same member
    # validation; nothing outside the store directory is written; existing files are overwritten
    # by the archive's copies, files absent from the archive are left alone (a merge, not a replace).
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
    else:
        target_dir = settings.data_dir / target

    try:
        # Save upload to temp file
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

        # Extract tar.gz
        with tarfile.open(tmp_path, "r:gz") as tar:
            # Security: check for path traversal
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    raise HTTPException(status_code=400, detail=f"Unsafe path in archive: {member.name}")

            # Extract to a temp dir first, then move files into target.
            # Member names were validated against path-traversal above (lines
            # 100-102); the temp dir bounds the blast radius further. R-014.
            with tempfile.TemporaryDirectory() as extract_dir:
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
                    for f in source.rglob("*"):
                        if f.is_file():
                            rel = f.relative_to(source)
                            dest = (target_dir / rel).resolve()
                            if not str(dest).startswith(str(target_dir.resolve()) + os.sep):
                                raise HTTPException(status_code=400, detail=f"Unsafe path in archive: {rel}")
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, dest)
                            count += 1
                else:
                    for f in source.glob("*.csv"):
                        shutil.copy2(f, target_dir / f.name)
                        count += 1

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

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
