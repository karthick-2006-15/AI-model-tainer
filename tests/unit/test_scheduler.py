"""
Unit Tests for Phase 11: Proactive Monitoring & Scheduling Engine
Tests daily executive briefing, background job registration, manual triggers, health checks, and API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from modules.scheduler.briefing import daily_briefing_generator
from modules.scheduler.engine import scheduler_engine
from core.brain.tools import tool_registry

client = TestClient(app)


def test_daily_briefing_generation():
    briefing = daily_briefing_generator.generate_briefing()
    assert briefing["success"] is True
    assert "greeting" in briefing
    assert len(briefing["speech_text"]) > 20
    assert "System Health Status" in briefing["briefing_markdown"]
    assert "cpu_percent" in briefing["telemetry"]
    assert "ram_percent" in briefing["telemetry"]


@pytest.mark.asyncio
async def test_scheduler_engine_job_lifecycle():
    # 1. Add job
    job = scheduler_engine.add_job(
        name="Hourly Health Diagnostic",
        interval_seconds=3600,
        action_type="system_health"
    )
    assert job.job_id in [j["job_id"] for j in scheduler_engine.list_jobs()]
    assert job.run_count == 0

    # 2. Trigger job now
    res = await scheduler_engine.trigger_job_now(job.job_id)
    assert res["success"] is True
    assert "metrics" in res
    assert job.run_count == 1
    assert job.last_run is not None

    # 3. Cancel job
    cancelled = scheduler_engine.cancel_job(job.job_id)
    assert cancelled is True
    assert job.job_id not in [j["job_id"] for j in scheduler_engine.list_jobs()]


@pytest.mark.asyncio
async def test_scheduler_custom_tool_action():
    # Schedule a job executing a registered tool (get_system_telemetry)
    job = scheduler_engine.add_job(
        name="Telemetry Watcher",
        interval_seconds=1800,
        action_type="custom_tool",
        action_params={"tool_name": "get_system_telemetry", "arguments": {}}
    )
    res = await scheduler_engine.trigger_job_now(job.job_id)
    assert res["success"] is True
    scheduler_engine.cancel_job(job.job_id)


def test_scheduler_rest_endpoints():
    # 1. Get briefing
    b_res = client.get("/api/scheduler/briefing")
    assert b_res.status_code == 200
    b_data = b_res.json()
    assert b_data["success"] is True
    assert "speech_text" in b_data

    # 2. Create job
    create_res = client.post("/api/scheduler/jobs", json={
        "name": "Evening Maintenance",
        "interval_seconds": 7200,
        "action_type": "briefing"
    })
    assert create_res.status_code == 200
    job_data = create_res.json()
    job_id = job_data["job_id"]
    assert job_data["name"] == "Evening Maintenance"

    # 3. Trigger job
    trig_res = client.post(f"/api/scheduler/jobs/{job_id}/trigger")
    assert trig_res.status_code == 200

    # 4. List jobs
    list_res = client.get("/api/scheduler/jobs")
    assert list_res.status_code == 200
    assert any(j["job_id"] == job_id for j in list_res.json()["jobs"])

    # 5. Delete job
    del_res = client.delete(f"/api/scheduler/jobs/{job_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_scheduler_tools_registered_in_brain():
    briefing_tool = tool_registry.get_tool("get_daily_briefing")
    schedule_tool = tool_registry.get_tool("schedule_periodic_task")

    assert briefing_tool is not None
    assert schedule_tool is not None
    assert briefing_tool.permission_level == 1
    assert schedule_tool.permission_level == 2
