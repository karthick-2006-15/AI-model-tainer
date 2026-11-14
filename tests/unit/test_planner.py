"""
Unit Tests for Phase 9: Autonomous Planning & Execution Engine (DAG)
Tests DAG dependency waves, cycle detection, result verification, heuristic and dynamic planning, and executor cascades.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from core.planning.task import PlanDAG, SubTask, TaskStatus
from core.planning.verifier import result_verifier
from core.planning.planner import goal_planner
from core.planning.executor import dag_executor
from core.brain.tools import tool_registry

client = TestClient(app)


def test_dag_topological_waves_and_dependencies():
    dag = PlanDAG(goal="Test Multi-Step Wave Graph")
    
    # Wave 0 (no dependencies)
    dag.add_subtask(SubTask(id="task_1", description="Fetch telemetry", tool_name="get_system_telemetry"))
    dag.add_subtask(SubTask(id="task_2", description="Find files", tool_name="find_duplicate_files"))
    
    # Wave 1 (depends on task_1)
    dag.add_subtask(SubTask(id="task_3", description="Process stats", tool_name="web_search", dependencies=["task_1"]))
    
    # Wave 2 (depends on task_2 and task_3)
    dag.add_subtask(SubTask(id="task_4", description="Final synthesis", tool_name="web_search", dependencies=["task_2", "task_3"]))

    assert not dag.has_cycles()
    waves = dag.get_execution_waves()

    assert len(waves) == 3
    assert set(waves[0]) == {"task_1", "task_2"}
    assert waves[1] == ["task_3"]
    assert waves[2] == ["task_4"]


def test_dag_detects_cycles():
    dag = PlanDAG(goal="Cyclic Deadlock Test")
    dag.add_subtask(SubTask(id="a", description="Step A", dependencies=["b"]))
    dag.add_subtask(SubTask(id="b", description="Step B", dependencies=["a"]))

    assert dag.has_cycles() is True
    with pytest.raises(ValueError, match="Dependency cycle detected"):
        dag.get_execution_waves()


def test_result_verifier_evaluates_outcomes():
    subtask = SubTask(id="task_verify", description="Test verification")

    # Success case
    is_valid, _ = result_verifier.verify_subtask_outcome(subtask, {"success": True, "data": 123})
    assert is_valid is True

    # Explicit failure case
    is_valid, reason = result_verifier.verify_subtask_outcome(subtask, {"success": False, "error": "Access denied"})
    assert is_valid is False
    assert "Access denied" in reason

    # Null case
    is_valid, reason = result_verifier.verify_subtask_outcome(subtask, None)
    assert is_valid is False


def test_result_verifier_retry_and_abort():
    subtask = SubTask(id="task_retry", description="Retry test", max_retries=2)
    
    # First failure -> retry allowed
    retry1 = result_verifier.evaluate_retry_or_abort(subtask, "Temporary network timeout")
    assert retry1 is True
    assert subtask.retry_count == 1
    assert subtask.status == TaskStatus.PENDING

    # Second failure -> abort/failed
    retry2 = result_verifier.evaluate_retry_or_abort(subtask, "Temporary network timeout")
    assert retry2 is False
    assert subtask.retry_count == 2
    assert subtask.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_goal_planner_heuristic_generation():
    exam_dag = await goal_planner.create_plan("Prepare my Computer Networks examination")
    assert len(exam_dag.subtasks) >= 3
    assert not exam_dag.has_cycles()
    assert "task_1" in exam_dag.subtasks

    org_dag = await goal_planner.create_plan("Organize downloads and clean up duplicates")
    assert len(org_dag.subtasks) >= 2
    assert not org_dag.has_cycles()


@pytest.mark.asyncio
async def test_dag_executor_cascading_failure():
    dag = PlanDAG(goal="Failure Cascade Test")
    
    # Step 1: Deliberately failing tool
    dag.add_subtask(SubTask(
        id="step_fail",
        description="Failing step",
        tool_name="read_file_content",
        arguments={"file_path": "non_existent_ghost_file_12345.xyz"},
        max_retries=1
    ))
    
    # Step 2: Depends on step_fail (should be BLOCKED)
    dag.add_subtask(SubTask(
        id="step_downstream",
        description="Downstream step",
        tool_name="get_system_telemetry",
        dependencies=["step_fail"]
    ))

    completed_dag = await dag_executor.execute_plan(dag)
    assert completed_dag.status == TaskStatus.FAILED
    assert completed_dag.get_subtask("step_fail").status == TaskStatus.FAILED
    assert completed_dag.get_subtask("step_downstream").status == TaskStatus.BLOCKED


@pytest.mark.asyncio
async def test_dag_executor_successful_pipeline():
    dag = PlanDAG(goal="Successful Telemetry & Search Pipeline")
    dag.add_subtask(SubTask(
        id="t1",
        description="Collect hardware metrics",
        tool_name="get_system_telemetry"
    ))
    dag.add_subtask(SubTask(
        id="t2",
        description="Search documentation",
        tool_name="web_search",
        arguments={"query": "FastAPI WebSockets", "max_results": 2},
        dependencies=["t1"]
    ))

    completed_dag = await dag_executor.execute_plan(dag)
    assert completed_dag.status == TaskStatus.SUCCESS
    assert completed_dag.get_subtask("t1").status == TaskStatus.SUCCESS
    assert completed_dag.get_subtask("t2").status == TaskStatus.SUCCESS
    assert completed_dag.get_subtask("t1").result is not None


def test_tasks_api_endpoints():
    # 1. Plan endpoint
    plan_res = client.post("/api/tasks/plan", json={"goal": "Prepare my Operating Systems examination"})
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert "plan_id" in plan_data
    assert len(plan_data["subtasks"]) >= 3
    plan_id = plan_data["plan_id"]

    # 2. Plan and execute endpoint
    exec_res = client.post("/api/tasks/plan-and-execute", json={"goal": "Check system storage and find duplicates"})
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] in ("success", "failed")

    # 3. List plans endpoint
    list_res = client.get("/api/tasks")
    assert list_res.status_code == 200
    assert "plans" in list_res.json()


def test_planning_tools_registered_in_brain():
    plan_tool = tool_registry.get_tool("create_goal_plan")
    exec_tool = tool_registry.get_tool("execute_goal_plan")
    assert plan_tool is not None
    assert exec_tool is not None
    assert exec_tool.permission_level == 2
