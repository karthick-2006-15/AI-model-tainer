"""
Avatar Intelligence REST Endpoints
Controls avatar state, facial expressions, real-time lip-sync, and visual customization.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from modules.avatar.avatar_engine import avatar_engine

router = APIRouter(prefix="/api/avatar", tags=["Avatar"])


class StateChangeRequest(BaseModel):
    state: str = Field(..., description="Target avatar state: idle, listening, thinking, speaking, happy, confused, error, warning, sleeping, success")
    message: Optional[str] = Field(None, description="Optional status message accompanying the state change")


class ExpressionRequest(BaseModel):
    expression: str = Field(..., description="Emotional expression: happy, confused, alert, wink, focus")
    duration: Optional[float] = Field(3.0, ge=0.5, le=30.0, description="Duration in seconds for transient expression")


class LipSyncRequest(BaseModel):
    amplitude: float = Field(..., ge=0.0, le=1.0, description="Audio volume amplitude 0.0 to 1.0")
    phoneme: Optional[str] = Field("", description="Active speech viseme / phoneme symbol")


class SettingsUpdateRequest(BaseModel):
    theme: Optional[str] = None
    size: Optional[str] = None
    glow_intensity: Optional[float] = Field(None, ge=0.1, le=1.0)
    scanlines_enabled: Optional[bool] = None
    click_through: Optional[bool] = None
    always_on_top: Optional[bool] = None
    speech_sync_enabled: Optional[bool] = None
    gaze_tracking_enabled: Optional[bool] = None


@router.get("/state")
def get_avatar_state():
    """Returns the current visual, animation, and emotional state of the avatar."""
    return avatar_engine.get_state()


@router.post("/state")
def set_avatar_state(request: StateChangeRequest):
    """Updates the avatar animation state."""
    success = avatar_engine.set_state(request.state, request.message)
    return {"status": "ok", "state": request.state, "success": success}


@router.post("/expression")
def trigger_expression(request: ExpressionRequest):
    """Triggers a transient facial expression for the specified duration."""
    success = avatar_engine.trigger_expression(request.expression, request.duration or 3.0)
    return {"status": "ok", "expression": request.expression, "duration": request.duration, "success": success}


@router.post("/lip_sync")
def update_lip_sync(request: LipSyncRequest):
    """Synchronizes mouth aperture with real-time speech audio amplitude."""
    result = avatar_engine.update_lip_sync(request.amplitude, request.phoneme)
    return {"status": "ok", "lip_sync": result}


@router.get("/settings")
def get_avatar_settings():
    """Returns current avatar configuration settings."""
    return avatar_engine.get_settings()


@router.post("/settings")
def update_avatar_settings(request: SettingsUpdateRequest):
    """Updates avatar visualization preferences."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    updated = avatar_engine.update_settings(updates)
    return {"status": "ok", "settings": updated}
