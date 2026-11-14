"""
PowerShell Execution Sandbox with Security Guardrails
Provides sandboxed execution with timeout, command blocklisting, and Level 3 permission checks.
"""

import subprocess
import re
import logging
from typing import Dict, Any, Optional
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.automation.shell")


class ShellSandbox:
    BLOCKLIST_PATTERNS = [
        r"\bformat[\s\-]volume\b",
        r"\bdiskpart\b",
        r"\bdel\s+(?:\/[a-zA-Z]+\s+)*[cC]:\\windows\b",
        r"\bremove\-item\s+.*[cC]:\\windows\b",
        r"\breg\s+delete\b",
        r"\bshutdown\b",
        r"\brmdir\s+\/s\s+\/q\s+[cC]:\\",
    ]

    def __init__(self, default_timeout_seconds: int = 30):
        self.default_timeout = default_timeout_seconds
        self._compiled_blocklist = [re.compile(p, re.IGNORECASE) for p in self.BLOCKLIST_PATTERNS]

    def is_command_safe(self, command: str) -> bool:
        """Checks if a command contains blocklisted destructive syntax."""
        for pattern in self._compiled_blocklist:
            if pattern.search(command):
                logger.warning(f"BLOCKED DANGEROUS COMMAND: {command}")
                return False
        return True

    def execute_command(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout: Optional[int] = None,
        skip_permission_check: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a PowerShell terminal command.
        Enforces Level 3 permission authorization unless explicitly overridden.
        """
        if not self.is_command_safe(command):
            return {
                "success": False,
                "error": "Command blocked by JARVIS Security Guardrails (Destructive syntax detected).",
                "exit_code": -1
            }

        # 1. Permission Evaluation (Level 3: EXECUTE)
        if not skip_permission_check:
            allowed, reason, challenge = permission_engine.evaluate_request(
                tool_name="shell.execute_command",
                permission_level=3,
                target_resource=command,
                arguments={"command": command, "cwd": working_directory}
            )
            if not allowed:
                return {
                    "success": False,
                    "awaiting_approval": True,
                    "challenge": challenge,
                    "message": reason
                }

        # 2. Command Execution via PowerShell
        timeout_sec = timeout or self.default_timeout
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            success = result.returncode == 0

            return {
                "success": success,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "command": command
            }
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout_sec}s: {command}")
            return {
                "success": False,
                "error": f"Execution timed out after {timeout_sec} seconds.",
                "exit_code": -2
            }
        except Exception as e:
            logger.error(f"Command execution failure: {e}")
            return {
                "success": False,
                "error": str(e),
                "exit_code": -3
            }


# Global singleton instance
shell_sandbox = ShellSandbox()
