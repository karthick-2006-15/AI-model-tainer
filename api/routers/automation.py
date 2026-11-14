"""
Windows Laptop Automation & OS Control REST Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from modules.automation.apps import ApplicationManager
from modules.automation.shell import shell_sandbox
from modules.automation.file_ops import FileOperationsManager
from core.security.permissions import permission_engine

router = APIRouter(prefix="/api/automation", tags=["Automation"])


class LaunchAppRequest(BaseModel):
    app_name: str
    args: Optional[str] = None


class CloseAppRequest(BaseModel):
    app_name: str
    force: Optional[bool] = False


class ShellCommandRequest(BaseModel):
    command: str
    cwd: Optional[str] = None
    timeout: Optional[int] = 30
    skip_permission_check: Optional[bool] = False


class OrganizeFolderRequest(BaseModel):
    folder_path: str


class FocusWindowRequest(BaseModel):
    title: str


class ResolveChallengeRequest(BaseModel):
    challenge_id: str
    approved: bool


@router.post("/apps/launch")
def launch_application(request: LaunchAppRequest):
    """Launches an application or program by name."""
    res = ApplicationManager.launch(request.app_name, args=request.args)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to launch application."))
    return res


@router.post("/apps/close")
def close_application(request: CloseAppRequest):
    """Terminates active processes matching application name."""
    return ApplicationManager.close(request.app_name, force=request.force or False)


@router.get("/windows")
def list_open_windows():
    """Lists visible application windows on the desktop."""
    return ApplicationManager.list_open_windows()


@router.post("/windows/focus")
def focus_window(request: FocusWindowRequest):
    """Brings a window to the front."""
    success = ApplicationManager.focus_window(request.title)
    return {"success": success, "title": request.title}


@router.post("/shell")
def execute_shell(request: ShellCommandRequest):
    """Executes a PowerShell command with sandboxing and Level 3 guardrails."""
    return shell_sandbox.execute_command(
        command=request.command,
        working_directory=request.cwd,
        timeout=request.timeout,
        skip_permission_check=request.skip_permission_check or False
    )


@router.post("/organize")
def organize_folder(request: OrganizeFolderRequest):
    """Organizes files in a target directory into categorized subfolders."""
    res = FileOperationsManager.organize_directory(request.folder_path)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.post("/challenges/resolve")
def resolve_challenge(request: ResolveChallengeRequest):
    """Resolves an interactive Level 3 permission challenge."""
    approved, challenge = permission_engine.resolve_challenge(
        challenge_id=request.challenge_id,
        approved=request.approved
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge ID not found or already expired.")
    return {
        "challenge_id": request.challenge_id,
        "approved": approved,
        "tool_name": challenge["tool_name"],
        "target_resource": challenge["target_resource"]
    }
