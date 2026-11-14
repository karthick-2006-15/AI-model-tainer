"""
Visual Studio Code Integration Plugin
Manages workspace launching, project environment inspection, and development tasks.
"""

import os
import shutil
import subprocess
import logging
from typing import Dict, Any
from modules.integrations.base import BaseIntegration

logger = logging.getLogger("jarvis.integrations.vscode")


class VSCodeIntegration(BaseIntegration):
    def __init__(self):
        super().__init__(
            name="VS Code",
            description="Visual Studio Code development environment integration.",
            capabilities=["open_workspace", "inspect_project", "start_dev_environment"],
            permission_level=2
        )

    def is_available(self) -> bool:
        return shutil.which("code") is not None or shutil.which("code.cmd") is not None

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        target_path = params.get("path", os.getcwd())
        norm_path = os.path.abspath(target_path)

        try:
            if action == "open_workspace":
                cmd = f'code "{norm_path}"'
                proc = subprocess.Popen(cmd, shell=True)
                res = {
                    "success": True,
                    "action": "open_workspace",
                    "path": norm_path,
                    "pid": proc.pid,
                    "message": f"Opened '{norm_path}' in VS Code."
                }
                self.log_execution(action, params, True, res)
                return res

            elif action == "inspect_project":
                has_package_json = os.path.exists(os.path.join(norm_path, "package.json"))
                has_requirements = os.path.exists(os.path.join(norm_path, "requirements.txt"))
                has_vscode_dir = os.path.exists(os.path.join(norm_path, ".vscode"))
                has_git = os.path.exists(os.path.join(norm_path, ".git"))

                tech_stack = []
                if has_package_json:
                    tech_stack.append("Node.js / TypeScript / React")
                if has_requirements:
                    tech_stack.append("Python / FastAPI")
                if not tech_stack:
                    tech_stack.append("General Codebase")

                res = {
                    "success": True,
                    "path": norm_path,
                    "tech_stack": tech_stack,
                    "has_vscode_config": has_vscode_dir,
                    "is_git_repository": has_git
                }
                self.log_execution(action, params, True, res)
                return res

            elif action == "start_dev_environment":
                # Launch VS Code in the project directory
                subprocess.Popen(f'code "{norm_path}"', shell=True)
                res = {
                    "success": True,
                    "action": "start_dev_environment",
                    "path": norm_path,
                    "message": f"Development environment primed for {norm_path}."
                }
                self.log_execution(action, params, True, res)
                return res

            else:
                err = f"Unknown VS Code action '{action}'"
                self.log_execution(action, params, False, None, err)
                return {"success": False, "error": err}

        except Exception as e:
            self.log_execution(action, params, False, None, str(e))
            return {"success": False, "error": str(e)}


# Global instance
vscode_integration = VSCodeIntegration()
