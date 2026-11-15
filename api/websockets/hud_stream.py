"""
HUD Real-time Streaming WebSocket Handler
Maintains live bidirectional channel between the React HUD and JARVIS backend core.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import asyncio
import json
import logging
from modules.automation.system import SystemMonitor
from core.brain.orchestrator import brain_orchestrator
from modules.voice.tts import tts_engine

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


@router.websocket("/ws/hud")
async def hud_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send initial welcome state
    await websocket.send_json({
        "type": "agent_state",
        "state": "idle",
        "message": "JARVIS Core Online. All subsystems operational."
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
                        # 1. Update agent status to thinking
                        await websocket.send_json({
                            "type": "agent_state",
                            "state": "thinking",
                            "message": f"Analyzing: {text}"
                        })

                        # 2. Invoke Central AI Brain
                        result = await brain_orchestrator.process_user_request(text)

                        # If tool was executed, briefly show executing state
                        if result.get("tool_executed"):
                            await websocket.send_json({
                                "type": "agent_state",
                                "state": "executing",
                                "message": f"Executed tool: {result['tool_executed']}"
                            })
                            await asyncio.sleep(0.4)

                        # 3. Stream back final response chunk and vocalize
                        tts_engine.speak(result["response"])
                        await websocket.send_json({
                            "type": "token_chunk",
                            "chunk": result["response"],
                            "tool_executed": result.get("tool_executed"),
                            "verified": result.get("verified", True)
                        })

                        # 4. Return to idle state
                        await websocket.send_json({
                            "type": "agent_state",
                            "state": "idle",
                            "message": "Standing by."
                        })

                elif msg_type == "permission_response":
                    request_id = payload.get("request_id")
                    granted = payload.get("granted", False)
                    logger.info(f"Permission challenge {request_id} response: {granted}")

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format."})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        telemetry_task.cancel()
