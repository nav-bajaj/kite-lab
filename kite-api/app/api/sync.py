"""
Sync API endpoints - Import data from CSVs to database

All endpoints require authentication.
"""
from fastapi import APIRouter, Query, HTTPException, Depends

from app.config import is_valid_universe, UniverseId
from app.auth import get_current_user

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
