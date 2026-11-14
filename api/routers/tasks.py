"""
Autonomous Planning & DAG Task Management REST Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from core.planning.planner import goal_planner
from core.planning.executor import dag_executor
from core.planning.task import PlanDAG

router = APIRouter(prefix="/api/tasks", tags=["Planning & Tasks"])


class PlanRequest(BaseModel):
    goal: str


@router.post("/plan")
async def create_goal_plan(request: PlanRequest):
    """Decomposes a user goal into an acyclic directed graph (DAG) of subtasks."""
    if not request.goal.strip():
        raise HTTPException(status_code=400, detail="Goal description cannot be empty.")
    dag = await goal_planner.create_plan(request.goal)
    return dag.model_dump()


@router.post("/{plan_id}/execute")
async def execute_existing_plan(plan_id: str):
    """Executes a previously prepared PlanDAG by ID."""
    dag = dag_executor.get_plan(plan_id)
    if not dag:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")
    completed_dag = await dag_executor.execute_plan(dag)
    return completed_dag.model_dump()


@router.post("/plan-and-execute")
async def plan_and_execute_goal(request: PlanRequest):
    """One-shot pipeline: Decomposes goal into DAG and immediately executes it."""
    if not request.goal.strip():
        raise HTTPException(status_code=400, detail="Goal description cannot be empty.")
    dag = await goal_planner.create_plan(request.goal)
    completed_dag = await dag_executor.execute_plan(dag)
    return completed_dag.model_dump()


@router.get("/{plan_id}")
async def get_plan_status(plan_id: str):
    """Returns the current state and execution output of a PlanDAG."""
    dag = dag_executor.get_plan(plan_id)
    if not dag:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")
    return dag.model_dump()


@router.get("")
async def list_active_plans():
    """Lists all active and recent execution plans."""
    return {"plans": dag_executor.list_plans()}
