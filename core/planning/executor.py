"""
Autonomous DAG Execution Engine
Coordinates topological wave execution, parallel subtask dispatch, live status tracking, and dependency cascades.
"""

import asyncio
import datetime
import logging
from typing import Dict, Any, List, Optional
from core.planning.task import PlanDAG, SubTask, TaskStatus
from core.planning.verifier import result_verifier
from core.brain.tools import tool_registry

logger = logging.getLogger("jarvis.planning.executor")


class DAGExecutor:
    """Orchestrates asynchronous DAG plan execution with safety limits and verification."""

    def __init__(self):
        self._active_plans: Dict[str, PlanDAG] = {}

    def get_plan(self, plan_id: str) -> Optional[PlanDAG]:
        return self._active_plans.get(plan_id)

    def list_plans(self) -> List[Dict[str, Any]]:
        return [
            {
                "plan_id": p.plan_id,
                "goal": p.goal,
                "status": p.status,
                "subtasks_count": len(p.subtasks),
                "created_at": p.created_at,
                "completed_at": p.completed_at
            }
            for p in self._active_plans.values()
        ]

    async def execute_plan(self, dag: PlanDAG) -> PlanDAG:
        """
        Executes an entire PlanDAG in topological waves.
        Returns the updated PlanDAG with all results and status states.
        """
        logger.info(f"Starting execution of Plan DAG [{dag.plan_id}] for goal: '{dag.goal}'")
        self._active_plans[dag.plan_id] = dag
        dag.status = TaskStatus.RUNNING

        try:
            waves = dag.get_execution_waves()
        except ValueError as e:
            logger.error(f"Plan validation error: {e}")
            dag.status = TaskStatus.FAILED
            dag.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return dag

        failed_tasks: set = set()

        for wave_idx, wave_task_ids in enumerate(waves):
            logger.info(f"Executing Wave {wave_idx + 1}/{len(waves)} with tasks: {wave_task_ids}")

            # Check if any tasks in this wave have failed dependencies
            runnable_in_wave = []
            for t_id in wave_task_ids:
                subtask = dag.get_subtask(t_id)
                if any(dep in failed_tasks for dep in subtask.dependencies):
                    logger.warning(f"Blocking Subtask '{t_id}' due to upstream dependency failure.")
                    subtask.status = TaskStatus.BLOCKED
                    subtask.error = "Unmet upstream dependency."
                    failed_tasks.add(t_id)
                else:
                    runnable_in_wave.append(subtask)

            # Execute runnable subtasks concurrently
            if runnable_in_wave:
                results = await asyncio.gather(
                    *(self._execute_single_subtask(subtask) for subtask in runnable_in_wave),
                    return_exceptions=True
                )

                for subtask, res in zip(runnable_in_wave, results):
                    if isinstance(res, Exception):
                        subtask.status = TaskStatus.FAILED
                        subtask.error = str(res)
                        failed_tasks.add(subtask.id)
                    elif subtask.status != TaskStatus.SUCCESS:
                        failed_tasks.add(subtask.id)

        # Finalize DAG Status
        has_failures = any(t.status in (TaskStatus.FAILED, TaskStatus.BLOCKED) for t in dag.subtasks.values())
        dag.status = TaskStatus.FAILED if has_failures else TaskStatus.SUCCESS
        dag.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        logger.info(f"Plan DAG [{dag.plan_id}] execution completed with status: {dag.status.value}")
        return dag

    async def _execute_single_subtask(self, subtask: SubTask) -> SubTask:
        """Executes a single subtask with retry evaluation and result verification."""
        subtask.status = TaskStatus.RUNNING
        subtask.started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        while subtask.retry_count <= subtask.max_retries:
            try:
                if not subtask.tool_name:
                    subtask.status = TaskStatus.SUCCESS
                    subtask.result = {"info": "Informational step completed."}
                    break

                # Execute registered tool
                exec_output = await tool_registry.execute(subtask.tool_name, subtask.arguments)
                is_valid, reason = result_verifier.verify_subtask_outcome(subtask, exec_output)

                if is_valid:
                    subtask.status = TaskStatus.SUCCESS
                    subtask.result = exec_output.get("result") if isinstance(exec_output, dict) else exec_output
                    subtask.error = None
                    break
                else:
                    should_retry = result_verifier.evaluate_retry_or_abort(subtask, reason)
                    if not should_retry:
                        break
                    await asyncio.sleep(0.5)  # brief backoff before retry

            except Exception as e:
                should_retry = result_verifier.evaluate_retry_or_abort(subtask, str(e))
                if not should_retry:
                    break
                await asyncio.sleep(0.5)

        subtask.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return subtask


# Global executor singleton
dag_executor = DAGExecutor()
