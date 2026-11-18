"""
Unit tests for Windows Automation, File Operations, Shell Sandboxing & Permissions
"""

import pytest
import os
import shutil
import tempfile
from fastapi.testclient import TestClient
from api.main import app
from modules.automation.apps import ApplicationManager
from modules.automation.shell import shell_sandbox
from modules.automation.file_ops import FileOperationsManager
from core.security.permissions import permission_engine


def test_permission_engine_hierarchy():
    # 1. Level 1: Read operation auto-approved
    allowed, reason, challenge = permission_engine.evaluate_request(
        tool_name="get_telemetry",
        permission_level=1,
        target_resource="system.metrics",
        arguments={}
    )
    assert allowed is True
    assert challenge is None

    # 2. Level 3: Execute requires challenge
    allowed_l3, reason_l3, challenge_l3 = permission_engine.evaluate_request(
        tool_name="shell.execute_command",
        permission_level=3,
        target_resource="Restart-Computer",
        arguments={"command": "Restart-Computer"}
    )
    assert allowed_l3 is False
    assert challenge_l3 is not None
    challenge_id = challenge_l3["challenge_id"]

    # 3. Resolve challenge (user approved)
    approved, resolved_ch = permission_engine.resolve_challenge(challenge_id, approved=True)
    assert approved is True
    assert resolved_ch["challenge_id"] == challenge_id


def test_shell_sandbox_safety_and_execution():
    # 1. Block destructive syntax
    dangerous_cmd = "Format-Volume -DriveLetter C"
    assert not shell_sandbox.is_command_safe(dangerous_cmd)
    res_block = shell_sandbox.execute_command(dangerous_cmd, skip_permission_check=True)
    assert res_block["success"] is False
    assert "Destructive syntax" in res_block["error"]

    # 2. Safe execution (echo)
    safe_res = shell_sandbox.execute_command("Write-Output 'JARVIS ONLINE'", skip_permission_check=True)
    assert safe_res["success"] is True
    assert "JARVIS ONLINE" in safe_res["stdout"]

    # 3. Guardrail interceptor without skip
    intercepted = shell_sandbox.execute_command("Get-Process", skip_permission_check=False)
    assert intercepted["awaiting_approval"] is True
    assert "challenge" in intercepted


def test_file_operations_and_organization():
    temp_dir = tempfile.mkdtemp(prefix="jarvis_test_org_")
    try:
        # 1. Path safety check
        assert not FileOperationsManager._is_path_safe("C:/Windows/System32")

        # 2. Create subfolder
        sub_dir = os.path.join(temp_dir, "test_sub")
        res_create = FileOperationsManager.create_directory(sub_dir)
        assert res_create["success"] is True
        assert os.path.exists(sub_dir)

        # 3. Create dummy files of different types
        doc_file = os.path.join(temp_dir, "syllabus.pdf")
        img_file = os.path.join(temp_dir, "diagram.png")
        code_file = os.path.join(temp_dir, "script.py")

        with open(doc_file, "w") as f: f.write("Dummy PDF")
        with open(img_file, "w") as f: f.write("Dummy Image")
        with open(code_file, "w") as f: f.write("print('hello')")

        # 4. Organize folder
        org_res = FileOperationsManager.organize_directory(temp_dir)
        assert org_res["success"] is True
        assert org_res["moved_count"] >= 3

        # Verify sorted destinations
        assert os.path.exists(os.path.join(temp_dir, "Documents", "syllabus.pdf"))
        assert os.path.exists(os.path.join(temp_dir, "Images", "diagram.png"))
        assert os.path.exists(os.path.join(temp_dir, "Code", "script.py"))

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_automation_rest_endpoints():
    with TestClient(app) as client:
        # 1. List Windows
        win_res = client.get("/api/automation/windows")
        assert win_res.status_code == 200
        assert isinstance(win_res.json(), list)

        # 2. Shell execution endpoint (intercepted by Level 3 guardrail)
        shell_res = client.post("/api/automation/shell", json={
            "command": "Get-Date"
        })
        assert shell_res.status_code == 200
        data = shell_res.json()
        assert data.get("awaiting_approval") is True
        challenge_id = data["challenge"]["challenge_id"]

        # Verify that attempting to pass skip_permission_check does not bypass Level 3 enforcement
        bypass_attempt = client.post("/api/automation/shell", json={
            "command": "Get-Date",
            "skip_permission_check": True
        })
        assert bypass_attempt.status_code == 200
        assert bypass_attempt.json().get("awaiting_approval") is True

        # 3. Resolve challenge via API
        resolve_res = client.post("/api/automation/challenges/resolve", json={
            "challenge_id": challenge_id,
            "approved": True
        })
        assert resolve_res.status_code == 200
        assert resolve_res.json()["approved"] is True


def test_system_controller():
    from modules.automation.system import system_controller
    # Volume adjustment
    vol_res = system_controller.adjust_volume(action="up", steps=2)
    assert vol_res["success"] is True
    assert "up" in vol_res["action"]

    mute_res = system_controller.adjust_volume(action="mute")
    assert mute_res["success"] is True

    # Shutdown safety verification (unconfirmed must be rejected)
    unconf_restart = system_controller.restart_system(confirm=False)
    assert unconf_restart["success"] is False
    assert unconf_restart["requires_confirmation"] is True

    unconf_shutdown = system_controller.shutdown_system(confirm=False)
    assert unconf_shutdown["success"] is False
    assert unconf_shutdown["requires_confirmation"] is True
