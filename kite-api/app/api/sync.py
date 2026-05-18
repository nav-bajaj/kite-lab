"""
Sync API endpoints - Import data from CSVs to database

All endpoints require authentication.
"""
import tarfile
import tempfile
import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, Query, HTTPException, Depends, UploadFile, File

from app.config import is_valid_universe, UniverseId, settings
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("")
async def sync_universe(
    universe: UniverseId = Query(default="nse500", description="Universe to sync"),
    user: dict = Depends(get_current_user)
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
async def sync_all_universes(user: dict = Depends(get_current_user)):
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
    "nse500_data_full",       # GDF backfill stitched with Kite live (comprehensive)
    "indices_data",
}


@router.post("/upload-data")
async def upload_price_data(
    file: UploadFile = File(...),
    target: str = Query(..., description="Target directory (nse500_data, indices_data, etc.)"),
    user: dict = Depends(get_current_user)
):
    """
    Upload a tar.gz archive of price data and extract to the target directory.

    Used for one-time sync of local historical data to the production volume.
    """
    if target not in ALLOWED_UPLOAD_DIRS:
        raise HTTPException(status_code=400, detail=f"Invalid target: {target}. Allowed: {ALLOWED_UPLOAD_DIRS}")

    if not file.filename.endswith((".tar.gz", ".tgz")):
        raise HTTPException(status_code=400, detail="File must be a .tar.gz archive")

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

            # Extract to a temp dir first, then move files into target
            with tempfile.TemporaryDirectory() as extract_dir:
                tar.extractall(extract_dir)

                # Find the extracted content (might be in a subdirectory matching target name)
                extracted = Path(extract_dir)
                source = extracted / target
                if not source.is_dir():
                    source = extracted

                # Ensure target dir exists
                target_dir.mkdir(parents=True, exist_ok=True)

                # Copy files into target
                count = 0
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
