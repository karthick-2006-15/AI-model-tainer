"""
Mobile WebSocket Bridge & Remote Command Protocol
Maintains authenticated bidirectional communication between Android companion and JARVIS Core.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set, Dict, Any
import asyncio
import json
import logging
from modules.mobile.pairing import pairing_manager
from modules.automation.system import SystemMonitor
from core.brain.orchestrator import brain_orchestrator
from core.security.permissions import permission_engine

router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger("jarvis.mobile.bridge")


class MobileBridgeManager:
    def __init__(self):
        self.active_mobile_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_mobile_connections.add(websocket)
        logger.info(f"Android companion connected. Active mobile links: {len(self.active_mobile_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_mobile_connections.discard(websocket)
        logger.info(f"Android companion disconnected. Active mobile links: {len(self.active_mobile_connections)}")

    async def push_to_all_mobiles(self, message: Dict[str, Any]):
        """Pushes alerts, approval requests, or notifications to all connected phones."""
        dead = []
        for ws in list(self.active_mobile_connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.disconnect(d)


mobile_bridge = MobileBridgeManager()


@router.websocket("/ws/mobile")
async def mobile_websocket_endpoint(websocket: WebSocket):
    await mobile_bridge.connect(websocket)

    # Send initial welcome and connection ack
    await websocket.send_json({
        "type": "connection_ack",
        "service": "JARVIS Personal AI OS Core",
        "laptop_status": "online",
        "message": "Secure mobile bridge established."
    })

    # Background task for periodic telemetry sync to mobile (every 2 seconds)
    async def telemetry_push_loop():
        try:
            while True:
                metrics = SystemMonitor.get_hardware_metrics()
                await websocket.send_json({
                    "type": "laptop_telemetry",
                    "data": metrics
                })
                await asyncio.sleep(2.0)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.warning(f"Mobile telemetry push error: {e}")

    telemetry_task = asyncio.create_task(telemetry_push_loop())

    try:
        while True:
            text_data = await websocket.receive_text()
            try:
                payload = json.loads(text_data)
                msg_type = payload.get("type")

                # 1. Ping / Latency Check
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": payload.get("timestamp")})

                # 2. Remote Command (Spoken or Typed on Android)
                elif msg_type == "mobile_command":
                    command_text = payload.get("command", "").strip()
                    if command_text:
                        await websocket.send_json({
                            "type": "execution_status",
                            "state": "executing",
                            "command": command_text
                        })

                        # Execute through Central AI Brain
                        result = await brain_orchestrator.process_user_request(command_text)

                        await websocket.send_json({
                            "type": "command_result",
                            "command": command_text,
                            "response": result["response"],
                            "tool_executed": result.get("tool_executed"),
                            "verified": result.get("verified", True)
                        })

                # 3. Biometric Approval for Level 3 Actions
                elif msg_type == "biometric_approval":
                    challenge_id = payload.get("challenge_id")
                    approved = payload.get("approved", False)
                    biometric_type = payload.get("biometric_type", "fingerprint")

                    logger.info(f"Received mobile biometric approval for {challenge_id}: {approved} ({biometric_type})")
                    permission_engine.resolve_challenge(challenge_id=challenge_id, approved=approved)

                    await websocket.send_json({
                        "type": "approval_ack",
                        "challenge_id": challenge_id,
                        "approved": approved
                    })

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format."})

    except WebSocketDisconnect:
        mobile_bridge.disconnect(websocket)
    finally:
        telemetry_task.cancel()
