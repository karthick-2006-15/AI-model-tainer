"""
Application Integrations & Extensible Plugins REST Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from modules.integrations.vscode import vscode_integration
from modules.integrations.github import github_integration
from modules.integrations.spotify import spotify_integration
from modules.integrations.productivity import productivity_analyzer

router = APIRouter(prefix="/api/integrations", tags=["Integrations & Plugins"])


class IntegrationActionRequest(BaseModel):
    action: str
    params: Optional[Dict[str, Any]] = None


class VSCodeOpenRequest(BaseModel):
    path: Optional[str] = "."


class SpotifyControlRequest(BaseModel):
    action: str  # "play_pause", "next", "previous", "volume_up", "volume_down", "mute", "search_play"
    query: Optional[str] = "Lo-Fi Beats"


@router.get("")
async def list_registered_integrations():
    """Lists all available application integrations and their operational capabilities."""
    return {
        "integrations": [
            vscode_integration.get_info(),
            github_integration.get_info(),
            spotify_integration.get_info(),
            {
                "name": "Productivity Analyzer",
                "description": "Daily developer productivity and focus analytics.",
                "capabilities": ["analyze_daily_productivity"],
                "available": True
            }
        ]
    }


@router.post("/vscode/open")
async def open_in_vscode(request: VSCodeOpenRequest):
    """Launches an authorized project directory or workspace in VS Code."""
    res = await vscode_integration.execute("open_workspace", {"path": request.path or "."})
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res


@router.post("/github/action")
async def execute_github_action(request: IntegrationActionRequest):
    """Executes a Git/GitHub action (status, branch, recent_commits, repo_summary)."""
    res = await github_integration.execute(request.action, request.params or {})
    if not res.get("success", False):
        raise HTTPException(status_code=400, detail=res.get("error", "Git action failed."))
    return res


@router.post("/spotify/control")
async def control_spotify_media(request: SpotifyControlRequest):
    """Controls Spotify or system media playback (play/pause, next, volume, search)."""
    res = await spotify_integration.execute(request.action, {"query": request.query or ""})
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.get("/productivity")
async def get_daily_productivity():
    """Generates an executive personal productivity and workspace focus analysis."""
    return productivity_analyzer.analyze_daily_productivity()
