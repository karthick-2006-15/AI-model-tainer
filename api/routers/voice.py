"""
Voice Intelligence REST Endpoints
Handles speech synthesis, audio transcription, voice catalogue, and duplex state.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import os
import shutil
from modules.voice.tts import tts_engine
from modules.voice.stt import stt_engine
from modules.voice.duplex import duplex_controller
from core.config.settings import settings

router = APIRouter(prefix="/api/voice", tags=["Voice"])


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"


class InterruptionRequest(BaseModel):
    reason: Optional[str] = "Manual user interrupt"


@router.get("/status")
def get_voice_status():
    """Returns current audio and voice engine status."""
    return {
        "status": "ready",
        "default_voice_en": settings.DEFAULT_VOICE_EN,
        "default_voice_ta": settings.DEFAULT_VOICE_TA,
        "wake_word": settings.WAKE_WORD,
        "is_speaking": duplex_controller.is_speaking,
        "supported_languages": ["en-US", "ta-IN"]
    }


@router.get("/voices")
def get_voices():
    """Returns catalogue of available neural voices categorized by language."""
    return tts_engine.get_supported_voices()


@router.post("/tts")
async def synthesize_speech(request: TTSRequest):
    """Synthesizes text to neural audio and streams MP3 back to caller."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    duplex_controller.notify_speech_started()
    try:
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"jarvis_tts_{os.getpid()}_{id(request)}.mp3")
        
        success = await tts_engine.synthesize_to_file(
            text=request.text,
            output_path=temp_file,
            voice=request.voice or settings.DEFAULT_VOICE_EN,
            rate=request.rate or "+0%",
            pitch=request.pitch or "+0Hz"
        )
        
        if not success or not os.path.exists(temp_file):
            raise HTTPException(status_code=500, detail="TTS synthesis failed.")

        return FileResponse(
            temp_file,
            media_type="audio/mpeg",
            filename="jarvis_speech.mp3"
        )
    finally:
        duplex_controller.notify_speech_finished()


@router.post("/stt")
async def transcribe_speech(
    file: UploadFile = File(...),
    language: Optional[str] = Form("en-US")
):
    """Uploads an audio file and transcribes speech to text."""
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, f"jarvis_upload_{file.filename}")
    
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = stt_engine.transcribe_audio_file(temp_file, language=language)
        return {
            "success": text is not None,
            "transcription": text or "",
            "language": language
        }
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


@router.post("/interrupt")
def trigger_interrupt(request: InterruptionRequest):
    """Triggers immediate speech barge-in cancellation."""
    duplex_controller.trigger_interruption(reason=request.reason or "Manual user interrupt")
    return {"interrupted": True}
