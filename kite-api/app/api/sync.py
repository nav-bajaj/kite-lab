"""
Sync API endpoints - Import data from CSVs to database
"""
from fastapi import APIRouter, Query, HTTPException

from app.config import is_valid_universe, UniverseId

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("")
async def sync_universe(
    universe: UniverseId = Query(default="nse500", description="Universe to sync")
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
async def sync_all_universes():
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
