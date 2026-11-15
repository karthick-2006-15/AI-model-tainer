"""
Productivity & Natural Voice Task Management Engine
Manages user tasks, priorities, deadlines, reminders, completion tracking,
and natural language voice scheduling.
"""

import os
import re
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field

from modules.scheduler.engine import scheduler_engine

logger = logging.getLogger("jarvis.scheduler.productivity")


class UserTask(BaseModel):
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    title: str
    priority: str = "medium"  # "high", "medium", "low"
    deadline: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    is_completed: bool = False
    reminder_job_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ProductivityManager:
    """Manages tasks, deadlines, natural voice scheduling, and progress tracking."""

    def __init__(self):
        self._tasks: Dict[str, UserTask] = {}

    def create_task(
        self,
        title: str,
        priority: str = "medium",
        deadline_str: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> UserTask:
        """Creates a prioritized task with optional deadline."""
        norm_priority = priority.lower() if priority.lower() in ("high", "medium", "low") else "medium"
        task = UserTask(
            title=title.strip(),
            priority=norm_priority,
            deadline=deadline_str,
            tags=tags or []
        )
        self._tasks[task.id] = task
        logger.info(f"Created task [{task.id}]: '{task.title}' (Priority: {task.priority})")
        return task

    def complete_task(self, task_id: str) -> bool:
        """Marks a task as completed."""
        task = self._tasks.get(task_id)
        if not task:
            # Try matching by title
            for t in self._tasks.values():
                if task_id.lower() in t.title.lower():
                    task = t
                    break
        if not task:
            return False

        task.is_completed = True
        task.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Task [{task.id}] marked completed: '{task.title}'")
        return True

    def list_tasks(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        """Lists active and completed tasks."""
        tasks = list(self._tasks.values())
        if not include_completed:
            tasks = [t for t in tasks if not t.is_completed]
        return [t.model_dump() for t in tasks]

    def schedule_voice_reminder(self, voice_command: str) -> Dict[str, Any]:
        """
        Parses natural language voice reminder commands:
        e.g., "Jarvis, remind me to submit my assignment tomorrow at 9 AM"
              "Remind me in 30 minutes to take a break"
        """
        cmd = voice_command.lower().strip()
        # Clean prefix
        cmd = re.sub(r"^(?:jarvis\s+|hey\s+jarvis\s+|please\s+)?(?:remind\s+me\s+to\s+|remind\s+me\s+)", "", cmd).strip()

        # Check relative time (e.g. "in 30 minutes", "in 2 hours")
        m_rel = re.search(r"in\s+(\d+)\s+(minute|min|minutes|hour|hours|second|seconds)", cmd)
        delay_seconds = 3600  # Default 1 hour
        reminder_text = cmd

        if m_rel:
            val = int(m_rel.group(1))
            unit = m_rel.group(2)
            if "min" in unit:
                delay_seconds = val * 60
            elif "hour" in unit:
                delay_seconds = val * 3600
            elif "sec" in unit:
                delay_seconds = val
            reminder_text = re.sub(r"in\s+\d+\s+(?:minute|min|minutes|hour|hours|second|seconds)", "", cmd).strip()

        # Check "tomorrow"
        elif "tomorrow" in cmd:
            delay_seconds = 86400
            reminder_text = cmd.replace("tomorrow", "").strip()

        target_time = (datetime.now() + timedelta(seconds=delay_seconds)).strftime("%I:%M %p")

        # Register task
        task = self.create_task(
            title=reminder_text.title(),
            priority="high",
            deadline_str=f"Scheduled at {target_time}"
        )

        # Register scheduled job in engine
        job = scheduler_engine.add_job(
            name=f"Reminder: {reminder_text}",
            interval_seconds=delay_seconds,
            trigger_type="once",
            action_type="briefing"
        )
        task.reminder_job_id = job.job_id

        return {
            "success": True,
            "task_id": task.id,
            "reminder": reminder_text,
            "target_time": target_time,
            "message": f"Reminder set for '{reminder_text}' at {target_time}."
        }

    def get_progress_report(self) -> Dict[str, Any]:
        """Generates summary of active, completed, and overdue tasks."""
        active = [t for t in self._tasks.values() if not t.is_completed]
        completed = [t for t in self._tasks.values() if t.is_completed]
        return {
            "active_tasks_count": len(active),
            "completed_tasks_count": len(completed),
            "total_tasks": len(self._tasks),
            "high_priority_active": sum(1 for t in active if t.priority == "high"),
            "active_tasks": [t.model_dump() for t in active],
            "completed_tasks": [t.model_dump() for t in completed]
        }


# Global singleton instance
productivity_manager = ProductivityManager()
