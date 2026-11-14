"""
System & Telemetry REST Endpoints
Provides system health status and hardware metrics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from storage.db.connection import get_db
from modules.automation.system import SystemMonitor
from core.config.settings import settings
from datetime import datetime, timezone

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check for DB, hardware, and runtime."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online",
        "service": "JARVIS Personal AI OS Core",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "debug_mode": settings.JARVIS_DEBUG
    }


@router.get("/metrics")
def get_metrics():
    """Returns current hardware performance metrics."""
    return SystemMonitor.get_hardware_metrics()


@router.get("/processes")
def get_processes(limit: int = 5):
    """Returns top active processes by CPU consumption."""
    return SystemMonitor.get_top_processes(limit=limit)
