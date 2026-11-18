"""
Permission & Security Interceptor Engine
Enforces 3-Level Permission Hierarchy (Read, Modify, Execute) and generates challenges for Level 3 actions.
Maintains a tamper-evident SHA-256 audit log chain.
"""

import hashlib
import json
import uuid
import re
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from storage.db.connection import SessionLocal
from storage.db.models import AuditLog
from core.config.settings import settings

logger = logging.getLogger("jarvis.security.permissions")


class PermissionEngine:
    LEVEL_1_READ = 1             # Read files, inspect screens, web search, read documents
    LEVEL_2_MODIFY = 2           # Edit documents, fill forms, modify code, move files
    LEVEL_3_EXTERNAL_ACTION = 3  # Send messages, submit forms/worksheets, purchases, sensitive commands

    # Backward compatibility alias
    LEVEL_3_EXECUTE = LEVEL_3_EXTERNAL_ACTION

    CONFIRMATION_PHRASES = {
        "yes", "yeah", "yep", "sure", "confirm", "send", "send it", "do it", "proceed", "okay", "ok",
        "aama", "sari", "send pannu", "pannu", "bhej do", "haan", "theek hai", "kardo"
    }
    CANCELLATION_PHRASES = {
        "no", "nope", "cancel", "stop", "don't", "abort", "nevermind",
        "vendaam", "koodaadhu", "mat bhejo", "nahin", "rok do"
    }

    def __init__(self):
        self._pending_challenges: Dict[str, Dict[str, Any]] = {}
        self._last_log_hash: str = "0" * 64
        self._emergency_stopped: bool = False
        self._emergency_stop_reason: Optional[str] = None

    def trigger_emergency_stop(self, reason: str = "User initiated emergency abort") -> Dict[str, Any]:
        """Instantly halts all automated computer actions, tool executions, and pending challenges."""
        self._emergency_stopped = True
        self._emergency_stop_reason = reason
        self._pending_challenges.clear()
        logger.critical(f"GLOBAL EMERGENCY STOP TRIGGERED: {reason}")
        self.log_action(
            permission_level=3,
            action_type="system:emergency_stop",
            target_resource="global_kill_switch",
            parameters={"reason": reason},
            decision="halted_all_operations",
            success=True
        )
        return {
            "emergency_stopped": True,
            "reason": reason,
            "message": "Global emergency stop activated. All operations halted immediately."
        }

    def reset_emergency_stop(self) -> Dict[str, Any]:
        """Clears the emergency stop state to resume normal operations."""
        self._emergency_stopped = False
        self._emergency_stop_reason = None
        logger.info("Global emergency stop reset. Normal operations resumed.")
        return {
            "emergency_stopped": False,
            "message": "Emergency stop cleared. JARVIS subsystems re-armed."
        }

    def is_emergency_stopped(self) -> bool:
        """Checks if global emergency stop is currently active."""
        return self._emergency_stopped

    def get_latest_challenge(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent pending Level 3 challenge."""
        if not self._pending_challenges:
            return None
        # Return the most recently added challenge
        return list(self._pending_challenges.values())[-1]

    def resolve_voice_confirmation(self, user_phrase: str) -> Tuple[Optional[bool], Optional[Dict[str, Any]]]:
        """
        Evaluates a spoken response ('yes', 'send it', 'aama', 'haan', 'no', 'cancel')
        against the latest pending Level 3 authorization challenge.
        Returns:
            (approved: Optional[bool], challenge: Optional[Dict])
            approved is True for confirmation, False for cancellation, None if phrase was ambiguous.
        """
        latest = self.get_latest_challenge()
        if not latest:
            return None, None

        cleaned = user_phrase.lower().strip().strip(" .,!?:;'\"")

        # Guard: If the utterance is a new directed command (e.g. "send hi to Appa", "send message to Dad"),
        # it is a new instruction, not a confirmation of an existing challenge.
        if re.search(r"\b(?:send|text|whatsapp)\b.+\bto\s+[a-zA-Z0-9]", cleaned) or re.search(r"\bto\s+[a-zA-Z0-9_]+\s+(?:saying|that)\b", cleaned):
            return None, None

        # Check for confirmation
        if any(term in cleaned.split() or term == cleaned for term in self.CONFIRMATION_PHRASES):
            approved, resolved_ch = self.resolve_challenge(latest["challenge_id"], approved=True)
            return True, resolved_ch

        # Check for cancellation
        if any(term in cleaned.split() or term == cleaned for term in self.CANCELLATION_PHRASES):
            approved, resolved_ch = self.resolve_challenge(latest["challenge_id"], approved=False)
            return False, resolved_ch

        return None, latest

    def evaluate_request(
        self,
        tool_name: str,
        permission_level: int,
        target_resource: str,
        arguments: Dict[str, Any],
        device_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Evaluates an action against permission policy and emergency stop status.
        Returns:
            (allowed: bool, reason: str, challenge: Optional[Dict])
        """
        # Global Kill Switch Check
        if self._emergency_stopped:
            msg = f"Operation blocked: Global Emergency Stop is ACTIVE ({self._emergency_stop_reason})."
            logger.warning(msg)
            return False, msg, None

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

        # Level 3: External Action (Send messages, submit worksheets, sensitive commands)
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
        logger.warning(f"LEVEL 3 EXTERNAL ACTION INTERCEPTED: {tool_name} on {target_resource}. Challenge created: {challenge_id}")

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
