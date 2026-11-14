"""
SQLAlchemy Declarative Models for JARVIS
Defines relational schemas for devices, sessions, messages, memory, tasks, and audit logs.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from storage.db.connection import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    device_name = Column(String(100), nullable=False)
    device_type = Column(String(20), nullable=False)  # 'windows_host', 'android_mobile', 'web_client'
    public_key = Column(String(128), nullable=False)
    is_authorized = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    sessions = relationship("Session", back_populates="device")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, default="New Conversation")
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    device = relationship("Device", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(20), nullable=False)  # 'user', 'jarvis', 'system'
    content = Column(Text, nullable=False)
    input_modality = Column(String(20), default="text")  # 'text', 'voice', 'automation'
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    session = relationship("Session", back_populates="messages")


class MemoryEntity(Base):
    __tablename__ = "memory_entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    category = Column(String(50), nullable=False)  # 'preference', 'project', 'academic', 'app', 'fact'
    key_name = Column(String(100), nullable=False, index=True)
    value_data = Column(JSON, nullable=False)
    confidence_score = Column(Float, default=1.0)
    provenance = Column(String(50), nullable=False)  # 'user_explicit', 'system_inferred', 'file_extracted'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=True)
    goal = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # 'pending', 'planning', 'in_progress', 'completed', 'failed', 'aborted'
    plan_dag = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("Session", back_populates="tasks")
    subtasks = relationship("Subtask", back_populates="task", cascade="all, delete-orphan")


class Subtask(Base):
    __tablename__ = "subtasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    tool_name = Column(String(100), nullable=False)
    arguments = Column(JSON, nullable=False, default=dict)
    permission_level = Column(Integer, nullable=False, default=1)  # 1, 2, or 3
    status = Column(String(20), default="pending")  # 'pending', 'awaiting_approval', 'executing', 'success', 'failed'
    execution_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("Task", back_populates="subtasks")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), default=utc_now)
    device_id = Column(String(36), nullable=True)
    permission_level = Column(Integer, nullable=False)
    action_type = Column(String(50), nullable=False)
    target_resource = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)
    decision = Column(String(20), nullable=False)  # 'auto_allowed', 'user_confirmed', 'user_denied', 'system_blocked'
    execution_success = Column(Boolean, nullable=True)
    hash_checksum = Column(String(64), nullable=False)


class IndexedFile(Base):
    __tablename__ = "indexed_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    file_path = Column(Text, unique=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_extension = Column(String(20), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False)
    last_modified = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text, nullable=True)
    extracted_tags = Column(JSON, nullable=True, default=list)
    is_indexed_in_vector = Column(Boolean, default=False)
    indexed_at = Column(DateTime(timezone=True), default=utc_now)
