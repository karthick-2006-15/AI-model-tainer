"""
Proactive Monitoring & Background Job Scheduler Engine
Manages interval and recurring tasks, telemetry health checks, and scheduled autonomous workflows.
"""

import asyncio
import datetime
import uuid
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from modules.scheduler.briefing import daily_briefing_generator
from modules.automation.system import SystemMonitor
from core.brain.tools import tool_registry

logger = logging.getLogger("jarvis.scheduler.engine")


class ScheduledJob(BaseModel):
    job_id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    name: str
    trigger_type: str = "interval"  # "interval", "once"
    interval_seconds: int = 3600
    action_type: str = "briefing"  # "briefing", "system_health", "file_cleanup", "custom_tool"
    action_params: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    last_result: Optional[Any] = None


class SchedulerEngine:
    """Coordinates periodic background monitoring and proactive action execution."""

    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._is_running = False

    def add_job(
        self,
        name: str,
        interval_seconds: int = 3600,
        action_type: str = "briefing",
        action_params: Optional[Dict[str, Any]] = None,
        trigger_type: str = "interval"
    ) -> ScheduledJob:
        """Registers and starts a new scheduled job."""
        job = ScheduledJob(
            name=name,
            interval_seconds=max(interval_seconds, 1),
            action_type=action_type,
            action_params=action_params or {},
            trigger_type=trigger_type,
            next_run=(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=interval_seconds)).isoformat()
        )
        self._jobs[job.job_id] = job
        logger.info(f"Registered scheduled job '{job.name}' [{job.job_id}] with interval {job.interval_seconds}s")

        # Launch background loop if scheduler is active
        if self._is_running:
            self._start_job_loop(job)

        return job

    def cancel_job(self, job_id: str) -> bool:
        """Stops and removes a scheduled job."""
        if job_id not in self._jobs:
            return False

        if job_id in self._running_tasks:
            self._running_tasks[job_id].cancel()
            del self._running_tasks[job_id]

        del self._jobs[job_id]
        logger.info(f"Cancelled scheduled job [{job_id}]")
        return True

    async def trigger_job_now(self, job_id: str) -> Dict[str, Any]:
        """Manually executes a scheduled job immediately."""
        job = self._jobs.get(job_id)
        if not job:
            return {"success": False, "error": f"Job [{job_id}] not found"}
        return await self._execute_job_action(job)

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [j.model_dump() for j in self._jobs.values()]

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        return self._jobs.get(job_id)

    def start(self):
        """Starts all active jobs in the event loop."""
        if self._is_running:
            return
        self._is_running = True
        logger.info("Scheduler engine started. Activating registered background jobs.")
        for job in self._jobs.values():
            if job.is_active:
                self._start_job_loop(job)

    def stop(self):
        """Stops all running background loops."""
        self._is_running = False
        for t_id, task in list(self._running_tasks.items()):
            task.cancel()
        self._running_tasks.clear()
        logger.info("Scheduler engine stopped.")

    def _start_job_loop(self, job: ScheduledJob):
        """Spawns an asyncio background worker task for a job."""
        async def _loop():
            while job.is_active:
                try:
                    await asyncio.sleep(job.interval_seconds)
                    await self._execute_job_action(job)
                    if job.trigger_type == "once":
                        job.is_active = False
                        break
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in scheduled job loop [{job.job_id}]: {e}")

        task = asyncio.create_task(_loop())
        self._running_tasks[job.job_id] = task

    async def _execute_job_action(self, job: ScheduledJob) -> Dict[str, Any]:
        """Dispatches action execution based on action_type."""
        logger.info(f"Executing scheduled action for job '{job.name}' ({job.action_type})")
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        job.last_run = now_iso
        job.run_count += 1
        job.next_run = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=job.interval_seconds)).isoformat()

        result: Dict[str, Any] = {}
        try:
            if job.action_type == "briefing":
                result = daily_briefing_generator.generate_briefing()
            elif job.action_type == "system_health":
                metrics = SystemMonitor.get_hardware_metrics()
                warnings = []
                if metrics.get("cpu_percent", 0) > 90:
                    warnings.append("High CPU utilization (>90%)")
                if metrics.get("memory", {}).get("percent", 0) > 90:
                    warnings.append("Critical RAM consumption (>90%)")
                result = {
                    "success": True,
                    "metrics": metrics,
                    "warnings": warnings,
                    "healthy": len(warnings) == 0
                }
            elif job.action_type == "file_cleanup":
                from modules.files.indexer import file_indexer
                dupes = file_indexer.find_duplicate_files()
                result = {"success": True, "duplicates_found": len(dupes), "duplicates": dupes}
            elif job.action_type == "custom_tool":
                tool_name = job.action_params.get("tool_name", "")
                args = job.action_params.get("arguments", {})
                result = await tool_registry.execute(tool_name, args)
            else:
                result = {"success": True, "message": f"Action '{job.action_type}' acknowledged."}

            job.last_result = result
            return result

        except Exception as e:
            logger.error(f"Scheduled job execution failure [{job.job_id}]: {e}")
            err_res = {"success": False, "error": str(e)}
            job.last_result = err_res
            return err_res


# Global scheduler engine singleton
scheduler_engine = SchedulerEngine()
