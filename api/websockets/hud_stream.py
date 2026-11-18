"""
HUD Real-time Streaming WebSocket Handler
Maintains live bidirectional channel between the React HUD and JARVIS backend core.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set, Optional, List, Dict, Any
import asyncio
import json
import logging
from modules.automation.system import SystemMonitor
from core.brain.orchestrator import brain_orchestrator
from modules.voice.tts import tts_engine
from modules.voice.state_machine import voice_state_machine, VoiceState
from modules.avatar.avatar_engine import avatar_engine
from storage.db.connection import SessionLocal
from storage.db.models import Session, Message
from core.security.permissions import permission_engine

router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger("jarvis.websocket")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"HUD client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"HUD client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)


manager = ConnectionManager()


async def _broadcast_voice_state(state, reason):
    await manager.broadcast({
        "type": "voice_state",
        "state": state.value if hasattr(state, "value") else str(state),
        "reason": reason
    })

voice_state_machine.register_async_listener(_broadcast_voice_state)


@router.websocket("/ws/hud")
async def hud_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send initial welcome state, voice state, and avatar state
    await websocket.send_json({
        "type": "agent_state",
        "state": "idle",
        "message": "JARVIS Core Online. All subsystems operational."
    })
    await websocket.send_json({
        "type": "voice_state",
        "state": voice_state_machine.current_state.value,
        "reason": "HUD initial connection"
    })
    await websocket.send_json({
        "type": "avatar_state",
        "avatar": avatar_engine.get_state()
    })

    # Background task for periodic telemetry broadcast to this socket
    async def telemetry_loop():
        try:
            while True:
                metrics = SystemMonitor.get_hardware_metrics()
                await websocket.send_json({
                    "type": "telemetry",
                    "data": metrics
                })
                await asyncio.sleep(1.0)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.warning(f"Telemetry stream error: {e}")

    telemetry_task = asyncio.create_task(telemetry_loop())
    active_session_id: Optional[str] = None

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                msg_type = payload.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": payload.get("timestamp")})

                elif msg_type == "chat_input":
                    text = payload.get("text", "").strip()
                    if text:
                        # 1. Update agent status & avatar to thinking
                        voice_state_machine.transition_to(VoiceState.THINKING, f"Analyzing: {text}")
                        avatar_engine.set_state("thinking", f"Analyzing: {text}")
                        await manager.broadcast({
                            "type": "agent_state",
                            "state": "thinking",
                            "message": f"Analyzing: {text}"
                        })
                        await manager.broadcast({
                            "type": "avatar_state",
                            "avatar": avatar_engine.get_state()
                        })

                        # Retrieve recent conversation session history from database
                        history: List[Dict[str, str]] = []
                        session_id_to_use = payload.get("session_id") or active_session_id
                        try:
                            with SessionLocal() as db:
                                db_session = None
                                if session_id_to_use:
                                    db_session = db.query(Session).filter(Session.id == session_id_to_use).first()
                                if not db_session:
                                    db_session = db.query(Session).filter(Session.is_active == True).order_by(Session.updated_at.desc()).first()
                                if not db_session:
                                    db_session = Session(title=text[:40])
                                    db.add(db_session)
                                    db.commit()
                                    db.refresh(db_session)

                                active_session_id = db_session.id

                                # Retrieve past messages in chronological order
                                past_msgs = (
                                    db.query(Message)
                                    .filter(Message.session_id == db_session.id)
                                    .order_by(Message.created_at.desc())
                                    .limit(10)
                                    .all()
                                )
                                history = [
                                    {
                                        "role": "user" if m.sender == "user" else "assistant",
                                        "content": m.content
                                    }
                                    for m in reversed(past_msgs)
                                ]

                                # Record incoming user message
                                user_msg = Message(
                                    session_id=db_session.id,
                                    sender="user",
                                    content=text,
                                    input_modality="text"
                                )
                                db.add(user_msg)
                                db.commit()
                        except Exception as e:
                            logger.warning(f"Error querying/updating session history in database: {e}")

                        # 2. Invoke Central AI Brain with session history
                        result = await brain_orchestrator.process_user_request(text, session_history=history)

                        # Record assistant response in database
                        if active_session_id:
                            try:
                                with SessionLocal() as db:
                                    ai_msg = Message(
                                        session_id=active_session_id,
                                        sender="assistant",
                                        content=result.get("response", ""),
                                        input_modality="text"
                                    )
                                    db.add(ai_msg)
                                    db.commit()
                            except Exception as e:
                                logger.warning(f"Error recording assistant response in database: {e}")

                        # If tool was executed, briefly show executing state
                        if result.get("tool_executed"):
                            avatar_engine.set_state("executing", f"Executed tool: {result['tool_executed']}")
                            await manager.broadcast({
                                "type": "agent_state",
                                "state": "executing",
                                "message": f"Executed tool: {result['tool_executed']}"
                            })
                            await manager.broadcast({
                                "type": "avatar_state",
                                "avatar": avatar_engine.get_state()
                            })
                            await asyncio.sleep(0.4)

                        # 3. Stream back final response chunk and vocalize (speaking state)
                        voice_state_machine.transition_to(VoiceState.SPEAKING, "Vocalizing response")
                        avatar_engine.set_state("speaking", "Vocalizing response.")
                        await manager.broadcast({
                            "type": "agent_state",
                            "state": "speaking",
                            "message": "Speaking..."
                        })
                        await manager.broadcast({
                            "type": "avatar_state",
                            "avatar": avatar_engine.get_state()
                        })

                        tts_engine.speak(result["response"])
                        await websocket.send_json({
                            "type": "token_chunk",
                            "chunk": result["response"],
                            "tool_executed": result.get("tool_executed"),
                            "verified": result.get("verified", True),
                            "session_id": active_session_id
                        })

                        # Short delay before resetting to idle, or client will notify when speech synthesis finishes
                        await asyncio.sleep(1.0)
                        voice_state_machine.transition_to(VoiceState.IDLE, "Standing by")
                        avatar_engine.set_state("idle", "Standing by.")
                        await manager.broadcast({
                            "type": "agent_state",
                            "state": "idle",
                            "message": "Standing by."
                        })
                        await manager.broadcast({
                            "type": "avatar_state",
                            "avatar": avatar_engine.get_state()
                        })

                elif msg_type == "set_avatar_state":
                    state = payload.get("state", "idle")
                    msg = payload.get("message")
                    avatar_engine.set_state(state, msg)
                    await manager.broadcast({
                        "type": "avatar_state",
                        "avatar": avatar_engine.get_state()
                    })

                elif msg_type == "avatar_expression":
                    expr = payload.get("expression", "neutral")
                    dur = payload.get("duration", 3.0)
                    avatar_engine.trigger_expression(expr, dur)
                    await manager.broadcast({
                        "type": "avatar_expression",
                        "expression": expr,
                        "duration": dur
                    })

                elif msg_type == "avatar_lip_sync":
                    amp = payload.get("amplitude", 0.0)
                    phoneme = payload.get("phoneme", "")
                    res = avatar_engine.update_lip_sync(amp, phoneme)
                    await manager.broadcast({
                        "type": "avatar_lip_sync",
                        "lip_sync": res
                    })

                elif msg_type == "abort_task":
                    tts_engine.stop()
                    voice_state_machine.transition_to(VoiceState.INTERRUPTED, "Emergency abort triggered")
                    avatar_engine.set_state("error", "Emergency abort triggered.")
                    await manager.broadcast({
                        "type": "agent_state",
                        "state": "error",
                        "message": payload.get("reason", "Emergency abort active.")
                    })
                    await manager.broadcast({
                        "type": "avatar_state",
                        "avatar": avatar_engine.get_state()
                    })

                elif msg_type == "permission_response":
                    request_id = payload.get("request_id")
                    granted = payload.get("granted", False)
                    logger.info(f"Permission challenge {request_id} response: {granted}")
                    if request_id:
                        approved, resolved_ch = permission_engine.resolve_challenge(request_id, granted)
                        await manager.broadcast({
                            "type": "permission_resolved",
                            "request_id": request_id,
                            "granted": approved,
                            "challenge": resolved_ch
                        })

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format."})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        telemetry_task.cancel()
