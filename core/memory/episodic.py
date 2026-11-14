"""
Tier 2: Episodic Memory Engine
Relational persistence and retrieval of historical conversation sessions, commands, and tool executions.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as DbSession
from storage.db.connection import SessionLocal
from storage.db.models import Session, Message, AuditLog
from datetime import datetime, timedelta, timezone


class EpisodicMemory:
    def get_past_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent conversation sessions with metadata."""
        with SessionLocal() as db:
            sessions = db.query(Session).order_by(Session.updated_at.desc()).limit(limit).all()
            return [
                {
                    "session_id": s.id,
                    "title": s.title,
                    "is_active": s.is_active,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat()
                }
                for s in sessions
            ]

    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves messages from a specific historical session."""
        with SessionLocal() as db:
            messages = (
                db.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.created_at.asc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "content": m.content,
                    "modality": m.input_modality,
                    "timestamp": m.created_at.isoformat()
                }
                for m in messages
            ]

    def search_past_conversations(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across all historical messages."""
        with SessionLocal() as db:
            messages = (
                db.query(Message)
                .filter(Message.content.ilike(f"%{keyword}%"))
                .order_by(Message.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "session_id": m.session_id,
                    "sender": m.sender,
                    "content": m.content,
                    "timestamp": m.created_at.isoformat()
                }
                for m in messages
            ]

    def get_recent_tool_executions(self, hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves past tool executions from audit logs for historical context."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        with SessionLocal() as db:
            logs = (
                db.query(AuditLog)
                .filter(AuditLog.timestamp >= since)
                .order_by(AuditLog.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "action_type": log.action_type,
                    "target_resource": log.target_resource,
                    "decision": log.decision,
                    "success": log.execution_success,
                    "timestamp": log.timestamp.isoformat()
                }
                for log in logs
            ]


# Global singleton instance
episodic_memory = EpisodicMemory()
