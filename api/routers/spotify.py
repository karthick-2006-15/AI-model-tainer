"""
Spotify Music Controller REST Endpoints
Provides real-time music control, track metadata, and volume synchronization.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from modules.media.spotify_controller import spotify_controller

router = APIRouter(prefix="/api/spotify", tags=["Spotify Music System"])


class PlayRequest(BaseModel):
    query: Optional[str] = Field("", description="Song title, artist, playlist, or Spotify URI")


class VolumeRequest(BaseModel):
    level: int = Field(..., ge=0, le=100, description="Volume level from 0 to 100")


@router.get("/state")
def get_playback_state():
    """Returns complete Spotify desktop playback state and telemetry."""
    return spotify_controller.get_playback_state()


@router.get("/current")
def get_current_track():
    """Returns currently playing track details."""
    return spotify_controller.get_current_track()


@router.post("/play")
def play_track(request: PlayRequest):
    """Searches for a track or starts playback on the Windows Spotify client."""
    return spotify_controller.play_track(request.query or "")


@router.post("/pause")
def pause_playback():
    """Pauses playback."""
    return spotify_controller.pause_playback()


@router.post("/resume")
def resume_playback():
    """Resumes playback."""
    return spotify_controller.resume_playback()


@router.post("/next")
def next_track():
    """Skips to next track."""
    return spotify_controller.next_track()


@router.post("/previous")
def previous_track():
    """Returns to previous track."""
    return spotify_controller.previous_track()


@router.post("/volume")
def set_volume(request: VolumeRequest):
    """Sets volume level 0-100."""
    return spotify_controller.set_volume(request.level)


@router.get("/devices")
def get_available_devices():
    """Lists available Spotify playback devices."""
    return spotify_controller.get_available_devices()


@router.post("/open")
def open_spotify():
    """Launches or focuses the Windows Spotify desktop client."""
    return spotify_controller.open_spotify()
