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
    """Orchestrates asynchronous DAG plan execution with safety limits, verification, and SQLite persistence."""

    def __init__(self):
        self._active_plans: Dict[str, PlanDAG] = {}

    def _persist_plan_to_db(self, dag: PlanDAG, session_id: Optional[str] = None):
        """Persists or updates a PlanDAG and its subtasks in the SQLite database."""
        try:
            from storage.db.connection import SessionLocal
            from storage.db.models import Task, Subtask
            with SessionLocal() as db:
                task = db.query(Task).filter(Task.id == dag.plan_id).first()
                created_dt = (
                    datetime.datetime.fromisoformat(dag.created_at)
                    if isinstance(dag.created_at, str)
                    else datetime.datetime.now(datetime.timezone.utc)
                )
                completed_dt = (
                    datetime.datetime.fromisoformat(dag.completed_at)
                    if isinstance(dag.completed_at, str)
                    else None
                )

                if not task:
                    task = Task(
                        id=dag.plan_id,
                        session_id=session_id,
                        goal=dag.goal,
                        status=dag.status.value if hasattr(dag.status, "value") else str(dag.status),
                        plan_dag=dag.model_dump(),
                        created_at=created_dt,
                        completed_at=completed_dt
                    )
                    db.add(task)
                    db.flush()
                else:
                    task.status = dag.status.value if hasattr(dag.status, "value") else str(dag.status)
                    task.plan_dag = dag.model_dump()
                    task.completed_at = completed_dt

                # Sync individual subtasks
                for idx, (t_id, subtask) in enumerate(dag.subtasks.items(), start=1):
                    sub_record = db.query(Subtask).filter(Subtask.task_id == dag.plan_id, Subtask.step_number == idx).first()
                    sub_status = subtask.status.value if hasattr(subtask.status, "value") else str(subtask.status)
                    sub_res = {"result": subtask.result} if subtask.result is not None else None

                    if not sub_record:
                        sub_record = Subtask(
                            task_id=dag.plan_id,
                            step_number=idx,
                            tool_name=subtask.tool_name or "informational",
                            arguments=subtask.arguments or {},
                            status=sub_status,
                            execution_result=sub_res,
                            error_message=subtask.error
                        )
                        db.add(sub_record)
                    else:
                        sub_record.status = sub_status
                        sub_record.execution_result = sub_res
                        sub_record.error_message = subtask.error

                db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist DAG plan '{dag.plan_id}' to SQLite: {e}")

    def get_plan(self, plan_id: str) -> Optional[PlanDAG]:
        """Retrieves a plan from active memory or falls back to SQLite database."""
        if plan_id in self._active_plans:
            return self._active_plans[plan_id]

        try:
            from storage.db.connection import SessionLocal
            from storage.db.models import Task
            with SessionLocal() as db:
                task = db.query(Task).filter(Task.id == plan_id).first()
                if task and task.plan_dag:
                    dag = PlanDAG(**task.plan_dag)
                    self._active_plans[dag.plan_id] = dag
                    return dag
        except Exception as e:
            logger.warning(f"Failed to load plan '{plan_id}' from DB: {e}")
        return None

    def list_plans(self) -> List[Dict[str, Any]]:
        """Lists all active and historically persisted execution plans from database and memory."""
        plans_dict = {}
        # 1. Load from SQLite
        try:
            from storage.db.connection import SessionLocal
            from storage.db.models import Task
            with SessionLocal() as db:
                db_tasks = db.query(Task).order_by(Task.created_at.desc()).all()
                for t in db_tasks:
                    sub_count = len(t.plan_dag.get("subtasks", {})) if isinstance(t.plan_dag, dict) else 0
                    plans_dict[t.id] = {
                        "plan_id": t.id,
                        "goal": t.goal,
                        "status": t.status,
                        "subtasks_count": sub_count,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "completed_at": t.completed_at.isoformat() if t.completed_at else None
                    }
        except Exception as e:
            logger.warning(f"Error querying tasks from DB: {e}")

        # 2. Overlay with active in-memory plans
        for p in self._active_plans.values():
            plans_dict[p.plan_id] = {
                "plan_id": p.plan_id,
                "goal": p.goal,
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                "subtasks_count": len(p.subtasks),
                "created_at": p.created_at,
                "completed_at": p.completed_at
            }

        return list(plans_dict.values())

    def delete_plan(self, plan_id: str) -> bool:
        """Deletes a plan from in-memory cache and SQLite database."""
        deleted = False
        if plan_id in self._active_plans:
            del self._active_plans[plan_id]
            deleted = True

        try:
            from storage.db.connection import SessionLocal
            from storage.db.models import Task
            with SessionLocal() as db:
                task = db.query(Task).filter(Task.id == plan_id).first()
                if task:
                    db.delete(task)
                    db.commit()
                    deleted = True
        except Exception as e:
            logger.warning(f"Failed to delete plan '{plan_id}' from DB: {e}")

        return deleted

    async def execute_plan(self, dag: PlanDAG, session_id: Optional[str] = None) -> PlanDAG:
        """
        Executes an entire PlanDAG in topological waves with persistent progress saving.
        Returns the updated PlanDAG with all results and status states.
        """
        logger.info(f"Starting execution of Plan DAG [{dag.plan_id}] for goal: '{dag.goal}'")
        self._active_plans[dag.plan_id] = dag
        dag.status = TaskStatus.RUNNING
        self._persist_plan_to_db(dag, session_id=session_id)

        try:
            waves = dag.get_execution_waves()
        except ValueError as e:
            logger.error(f"Plan validation error: {e}")
            dag.status = TaskStatus.FAILED
            dag.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self._persist_plan_to_db(dag, session_id=session_id)
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

            # Persist checkpoint after each wave
            self._persist_plan_to_db(dag, session_id=session_id)

        # Finalize DAG Status
        has_failures = any(t.status in (TaskStatus.FAILED, TaskStatus.BLOCKED) for t in dag.subtasks.values())
        dag.status = TaskStatus.FAILED if has_failures else TaskStatus.SUCCESS
        dag.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._persist_plan_to_db(dag, session_id=session_id)

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
