"""
Session & Message REST Endpoints
Handles creation, listing, and message history for conversation sessions.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from storage.db.connection import get_db
from storage.db.models import Session, Message
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    input_modality: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    id: str
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    content: str
    input_modality: Optional[str] = "text"


@router.get("", response_model=List[SessionResponse])
def list_sessions(db: DbSession = Depends(get_db)):
    """Lists all active and archived conversation sessions."""
    return db.query(Session).order_by(Session.updated_at.desc()).all()


@router.post("", response_model=SessionResponse)
def create_session(request: CreateSessionRequest, db: DbSession = Depends(get_db)):
    """Creates a new conversation session."""
    session = Session(title=request.title or "New Conversation")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
def get_messages(session_id: str, db: DbSession = Depends(get_db)):
    """Retrieves all messages for a specific session."""
    return db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()


@router.post("/{session_id}/messages", response_model=MessageResponse)
def send_message(session_id: str, request: SendMessageRequest, db: DbSession = Depends(get_db)):
    """Adds a message to a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = Message(
        session_id=session_id,
        sender="user",
        content=request.content,
        input_modality=request.input_modality or "text"
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    return user_msg
