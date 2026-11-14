"""
Proactive Monitoring & Background Job Scheduler REST Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from modules.scheduler.engine import scheduler_engine
from modules.scheduler.briefing import daily_briefing_generator

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler & Monitoring"])


class CreateJobRequest(BaseModel):
    name: str
    interval_seconds: Optional[int] = 3600
    action_type: Optional[str] = "briefing"  # "briefing", "system_health", "file_cleanup", "custom_tool"
    action_params: Optional[Dict[str, Any]] = None
    trigger_type: Optional[str] = "interval"


@router.get("/jobs")
async def list_jobs_endpoint():
    """Returns all active, scheduled, and completed background monitoring jobs."""
    return {"jobs": scheduler_engine.list_jobs()}


@router.post("/jobs")
async def create_job_endpoint(request: CreateJobRequest):
    """Registers and schedules a new periodic background monitoring job."""
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Job name cannot be empty.")
    job = scheduler_engine.add_job(
        name=request.name,
        interval_seconds=request.interval_seconds or 3600,
        action_type=request.action_type or "briefing",
        action_params=request.action_params or {},
        trigger_type=request.trigger_type or "interval"
    )
    return job.model_dump()


@router.delete("/jobs/{job_id}")
async def cancel_job_endpoint(job_id: str):
    """Cancels and unregisters an active background scheduled job."""
    success = scheduler_engine.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return {"success": True, "message": f"Job '{job_id}' cancelled successfully."}


@router.post("/jobs/{job_id}/trigger")
async def trigger_job_endpoint(job_id: str):
    """Manually fires a scheduled job immediately and returns its execution result."""
    result = await scheduler_engine.trigger_job_now(job_id)
    if not result.get("success", True):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/briefing")
async def get_proactive_briefing_endpoint():
    """Generates an executive daily briefing with live hardware telemetry, tasks, and speech script."""
    return daily_briefing_generator.generate_briefing()
