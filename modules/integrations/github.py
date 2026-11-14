"""
GitHub & Local Git Integration Plugin
Inspects repository state, branch tracking, commit logs, and working tree status.
"""

import os
import shutil
import subprocess
import logging
from typing import Dict, Any, List
from modules.integrations.base import BaseIntegration

logger = logging.getLogger("jarvis.integrations.github")


class GitHubIntegration(BaseIntegration):
    def __init__(self):
        super().__init__(
            name="GitHub / Git",
            description="Version control and repository state intelligence.",
            capabilities=["status", "branch", "recent_commits", "repo_summary"],
            permission_level=1
        )

    def is_available(self) -> bool:
        return shutil.which("git") is not None

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        repo_dir = params.get("path", os.getcwd())
        try:
            if action == "status":
                proc = subprocess.run(
                    ["git", "status", "-s"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output = proc.stdout.strip()
                files_changed = [line.strip() for line in output.split("\n") if line.strip()] if output else []
                res = {
                    "success": proc.returncode == 0,
                    "clean_working_tree": len(files_changed) == 0,
                    "changed_files_count": len(files_changed),
                    "changed_files": files_changed
                }
                self.log_execution(action, params, res["success"], res)
                return res

            elif action == "branch":
                proc = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                branch_name = proc.stdout.strip() or "main"
                res = {"success": proc.returncode == 0, "current_branch": branch_name}
                self.log_execution(action, params, res["success"], res)
                return res

            elif action == "recent_commits":
                limit = params.get("limit", 5)
                proc = subprocess.run(
                    ["git", "log", f"-n {limit}", "--oneline"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                commits = [c.strip() for c in proc.stdout.strip().split("\n") if c.strip()]
                res = {"success": proc.returncode == 0, "commits": commits, "count": len(commits)}
                self.log_execution(action, params, res["success"], res)
                return res

            elif action == "repo_summary":
                # Aggregate status, branch, and commits
                st = await self.execute("status", params)
                br = await self.execute("branch", params)
                cm = await self.execute("recent_commits", params)
                res = {
                    "success": True,
                    "branch": br.get("current_branch", "unknown"),
                    "clean": st.get("clean_working_tree", True),
                    "changed_count": st.get("changed_files_count", 0),
                    "recent_commits": cm.get("commits", [])
                }
                self.log_execution(action, params, True, res)
                return res

            else:
                err = f"Unknown Git action '{action}'"
                self.log_execution(action, params, False, None, err)
                return {"success": False, "error": err}

        except Exception as e:
            self.log_execution(action, params, False, None, str(e))
            return {"success": False, "error": str(e)}


# Global instance
github_integration = GitHubIntegration()
