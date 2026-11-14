"""
Extensible Application Integration Plugin Architecture
Base class defining capabilities, permission scopes, authentication, and execution auditing.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import datetime
import logging

logger = logging.getLogger("jarvis.integrations.base")


class BaseIntegration(ABC):
    """Abstract base class for third-party application integrations."""

    def __init__(
        self,
        name: str,
        description: str,
        capabilities: List[str],
        permission_level: int = 1
    ):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.permission_level = permission_level
        self.execution_logs: List[Dict[str, Any]] = []

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the underlying service, CLI, or application is installed/accessible."""
        pass

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a defined capability action."""
        pass

    def log_execution(self, action: str, params: Dict[str, Any], success: bool, output: Any, error: Optional[str] = None):
        """Maintains an execution audit trail for the integration."""
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "action": action,
            "params": params,
            "success": success,
            "output": output,
            "error": error
        }
        self.execution_logs.append(entry)
        if len(self.execution_logs) > 50:
            self.execution_logs.pop(0)

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "permission_level": self.permission_level,
            "available": self.is_available(),
            "execution_count": len(self.execution_logs)
        }
