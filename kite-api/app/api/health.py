"""
Health check endpoint.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.models.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint - no authentication required.

    Used by Railway for health checks and monitoring.
    Returns database connectivity status.
    """
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    status = "ok" if db_status == "connected" else "degraded"

    return {
        "status": status,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "kite-lab-api",
    }
