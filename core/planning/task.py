"""
Autonomous Planning Engine: Subtask & Directed Acyclic Graph (DAG) Models
Provides topological dependency resolution, cyclic graph validation, and execution state management.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import datetime
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class SubTask(BaseModel):
    id: str
    description: str
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class PlanDAG(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    goal: str
    subtasks: Dict[str, SubTask] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def add_subtask(self, subtask: SubTask):
        self.subtasks[subtask.id] = subtask

    def get_subtask(self, task_id: str) -> Optional[SubTask]:
        return self.subtasks.get(task_id)

    def has_cycles(self) -> bool:
        """Kahn's algorithm to detect cycles in the dependency graph."""
        in_degree = {t_id: 0 for t_id in self.subtasks}
        for task in self.subtasks.values():
            for dep in task.dependencies:
                if dep in in_degree:
                    in_degree[task.id] += 1

        queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
        visited_count = 0

        adj: Dict[str, List[str]] = {t_id: [] for t_id in self.subtasks}
        for task in self.subtasks.values():
            for dep in task.dependencies:
                if dep in adj:
                    adj[dep].append(task.id)

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited_count != len(self.subtasks)

    def get_execution_waves(self) -> List[List[str]]:
        """
        Calculates execution waves (tiers) of subtask IDs that can be safely
        executed in parallel without unmet dependencies.
        """
        if self.has_cycles():
            raise ValueError("Dependency cycle detected in execution plan DAG.")

        resolved: set = set()
        waves: List[List[str]] = []
        remaining = set(self.subtasks.keys())

        while remaining:
            # Find all tasks whose dependencies are entirely in `resolved`
            current_wave = [
                t_id for t_id in remaining
                if set(self.subtasks[t_id].dependencies).issubset(resolved)
            ]
            if not current_wave:
                # Deadlock / unresolvable dependency
                break

            waves.append(current_wave)
            resolved.update(current_wave)
            remaining.difference_update(current_wave)

        return waves
