"""
Permission & Security Interceptor Engine
Enforces 3-Level Permission Hierarchy (Read, Modify, Execute) and generates challenges for Level 3 actions.
Maintains a tamper-evident SHA-256 audit log chain.
"""

import hashlib
import json
import uuid
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from storage.db.connection import SessionLocal
from storage.db.models import AuditLog
from core.config.settings import settings

logger = logging.getLogger("jarvis.security.permissions")


class PermissionEngine:
    LEVEL_1_READ = 1      # Read files, inspect system telemetry, web search
    LEVEL_2_MODIFY = 2    # Create files, edit documents, organize folders
    LEVEL_3_EXECUTE = 3   # Run terminal commands, delete files, change system config

    def __init__(self):
        self._pending_challenges: Dict[str, Dict[str, Any]] = {}
        self._last_log_hash: str = "0" * 64

    def evaluate_request(
        self,
        tool_name: str,
        permission_level: int,
        target_resource: str,
        arguments: Dict[str, Any],
        device_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Evaluates an action against permission policy.
        Returns:
            (allowed: bool, reason: str, challenge: Optional[Dict])
        """
        # Level 1: Read operations are autonomously allowed
        if permission_level <= self.LEVEL_1_READ:
            self.log_action(
                permission_level=1,
                action_type=f"tool_exec:{tool_name}",
                target_resource=target_resource,
                parameters=arguments,
                decision="auto_allowed",
                success=True,
                device_id=device_id
            )
            return True, "Level 1 Read action automatically approved.", None

        # Level 2: State-changing operations
        if permission_level == self.LEVEL_2_MODIFY:
            # Check if auto-approve is enabled in settings
            if settings.AUTO_APPROVE_LEVEL_2:
                self.log_action(
                    permission_level=2,
                    action_type=f"tool_exec:{tool_name}",
                    target_resource=target_resource,
                    parameters=arguments,
                    decision="auto_allowed",
                    success=True,
                    device_id=device_id
                )
                return True, "Level 2 Modify action approved with notification.", None

        # Level 3: Destructive / Terminal execution requires explicit user authorization
        challenge_id = f"ch_{uuid.uuid4().hex[:8]}"
        challenge = {
            "challenge_id": challenge_id,
            "tool_name": tool_name,
            "permission_level": permission_level,
            "target_resource": target_resource,
            "arguments": arguments,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_in_seconds": settings.LEVEL_3_TIMEOUT_SECONDS
        }
        self._pending_challenges[challenge_id] = challenge
        logger.warning(f"LEVEL 3 ACTION INTERCEPTED: {tool_name} on {target_resource}. Challenge created: {challenge_id}")

        self.log_action(
            permission_level=permission_level,
            action_type=f"challenge_created:{tool_name}",
            target_resource=target_resource,
            parameters=arguments,
            decision="awaiting_user_approval",
            success=None,
            device_id=device_id
        )

        return False, "Action requires explicit user authorization (Level 3 Confirmation Required).", challenge

    def resolve_challenge(self, challenge_id: str, approved: bool) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Resolves an out-of-band user approval challenge."""
        challenge = self._pending_challenges.pop(challenge_id, None)
        if not challenge:
            return False, None

        decision = "user_confirmed" if approved else "user_denied"
        self.log_action(
            permission_level=challenge["permission_level"],
            action_type=f"challenge_resolved:{challenge['tool_name']}",
            target_resource=challenge["target_resource"],
            parameters=challenge["arguments"],
            decision=decision,
            success=approved
        )
        return approved, challenge

    def log_action(
        self,
        permission_level: int,
        action_type: str,
        target_resource: str,
        parameters: Dict[str, Any],
        decision: str,
        success: Optional[bool] = None,
        device_id: Optional[str] = None
    ) -> str:
        """Appends a tamper-evident SHA-256 hashed audit log record."""
        ts = datetime.now(timezone.utc)
        record_content = f"{self._last_log_hash}:{ts.isoformat()}:{action_type}:{target_resource}:{decision}"
        checksum = hashlib.sha256(record_content.encode("utf-8")).hexdigest()
        self._last_log_hash = checksum

        try:
            with SessionLocal() as db:
                log_entry = AuditLog(
                    timestamp=ts,
                    device_id=device_id,
                    permission_level=permission_level,
                    action_type=action_type,
                    target_resource=target_resource,
                    parameters=parameters,
                    decision=decision,
                    execution_success=success,
                    hash_checksum=checksum
                )
                db.add(log_entry)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to record audit log: {e}")

        return checksum


# Global singleton instance
permission_engine = PermissionEngine()
