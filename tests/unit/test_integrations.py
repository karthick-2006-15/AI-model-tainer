"""
Unit Tests for Application Integrations & Extensible Plugins
Tests VS Code, GitHub/Git, Spotify Media Controls, and Daily Productivity Analytics.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from modules.integrations.vscode import vscode_integration
from modules.integrations.github import github_integration
from modules.integrations.spotify import spotify_integration
from modules.integrations.productivity import productivity_analyzer
from core.brain.tools import tool_registry

client = TestClient(app)


@pytest.mark.asyncio
async def test_vscode_integration_inspect():
    res = await vscode_integration.execute("inspect_project", {"path": "."})
    assert res["success"] is True
    assert "tech_stack" in res
    assert "Python / FastAPI" in res["tech_stack"] or "Node.js / TypeScript / React" in res["tech_stack"]
    assert len(vscode_integration.execution_logs) > 0


@pytest.mark.asyncio
async def test_github_integration_summary():
    res = await github_integration.execute("repo_summary", {"path": "."})
    assert res["success"] is True
    assert "branch" in res
    assert "clean" in res
    assert "recent_commits" in res
    assert len(res["recent_commits"]) > 0


@pytest.mark.asyncio
async def test_spotify_integration_playback():
    res = await spotify_integration.execute("volume_up", {})
    assert res["success"] is True
    assert res["action"] == "volume_up"


def test_productivity_analyzer_report():
    report = productivity_analyzer.analyze_daily_productivity()
    assert report["success"] is True
    assert 0 <= report["score"] <= 100
    assert "rating" in report
    assert len(report["speech_text"]) > 20
    assert "Productivity Score" in report["report_markdown"]


def test_integrations_rest_endpoints():
    # 1. List integrations
    list_res = client.get("/api/integrations")
    assert list_res.status_code == 200
    data = list_res.json()
    assert "integrations" in data
    assert len(data["integrations"]) >= 3

    # 2. GitHub action endpoint
    git_res = client.post("/api/integrations/github/action", json={"action": "branch", "params": {"path": "."}})
    assert git_res.status_code == 200
    assert "current_branch" in git_res.json()

    # 3. Spotify control endpoint
    spot_res = client.post("/api/integrations/spotify/control", json={"action": "mute"})
    assert spot_res.status_code == 200
    assert spot_res.json()["success"] is True

    # 4. Productivity endpoint
    prod_res = client.get("/api/integrations/productivity")
    assert prod_res.status_code == 200
    assert "score" in prod_res.json()


def test_integration_tools_registered_in_brain():
    vscode_tool = tool_registry.get_tool("open_vscode_project")
    git_tool = tool_registry.get_tool("inspect_git_status")
    spotify_tool = tool_registry.get_tool("control_spotify_media")
    prod_tool = tool_registry.get_tool("analyze_daily_productivity")

    assert vscode_tool is not None
    assert git_tool is not None
    assert spotify_tool is not None
    assert prod_tool is not None
    assert vscode_tool.permission_level == 2
    assert git_tool.permission_level == 1
    assert spotify_tool.permission_level == 1
    assert prod_tool.permission_level == 1
