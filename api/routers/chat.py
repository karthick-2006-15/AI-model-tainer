"""
Chat & Neural Orchestration REST Endpoints
Routes user instructions through the Central AI Brain.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from storage.db.connection import get_db
from storage.db.models import Session, Message
from core.brain.orchestrator import brain_orchestrator
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    input_modality: Optional[str] = "text"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_executed: Optional[str] = None
    intent: Optional[str] = None
    verified: bool = True


@router.post("", response_model=ChatResponse)
async def process_chat_message(request: ChatRequest, db: DbSession = Depends(get_db)):
    """Processes a message through the Central AI Brain and returns the response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # 1. Resolve or create session
    session = None
    if request.session_id:
        session = db.query(Session).filter(Session.id == request.session_id).first()
    if not session:
        session = Session(title=request.message[:40])
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. Record User Message
    user_msg = Message(
        session_id=session.id,
        sender="user",
        content=request.message,
        input_modality=request.input_modality or "text"
    )
    db.add(user_msg)
    db.commit()

    # 3. Retrieve recent session context
    past_msgs = db.query(Message).filter(Message.session_id == session.id).order_by(Message.created_at.desc()).limit(6).all()
    history = [{"role": m.sender, "content": m.content} for m in reversed(past_msgs)]

    # 4. Invoke Central AI Brain
    result = await brain_orchestrator.process_user_request(request.message, session_history=history)

    # 5. Record JARVIS Response
    ai_msg = Message(
        session_id=session.id,
        sender="jarvis",
        content=result["response"],
        input_modality="text"
    )
    db.add(ai_msg)
    db.commit()

    return ChatResponse(
        response=result["response"],
        session_id=session.id,
        tool_executed=result.get("tool_executed"),
        intent=result.get("intent"),
        verified=result.get("verified", True)
    )
