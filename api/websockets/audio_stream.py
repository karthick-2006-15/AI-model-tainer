"""
Binary Audio Duplex Streaming WebSocket
Enables low-latency streaming audio input and output between JARVIS Core and Clients.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import asyncio
from modules.voice.vad import VADDetector
from modules.voice.stt import stt_engine
from modules.voice.wakeword import wakeword_detector
from modules.voice.duplex import duplex_controller

router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger("jarvis.websocket.audio")


@router.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Audio duplex stream connected.")

    vad = VADDetector()
    audio_buffer = bytearray()
    is_recording_speech = False

    try:
        while True:
            # Receive either binary audio frame or control JSON text
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                chunk = message["bytes"]

                # 1. Check for barge-in: If JARVIS is speaking and user speaks, halt speech immediately
                if duplex_controller.process_incoming_audio_frame(chunk):
                    await websocket.send_json({
                        "type": "barge_in",
                        "message": "Speech interrupted by user."
                    })

                # 2. VAD State Machine
                is_speech, just_started = vad.process_frame(chunk)

                if is_speech:
                    if just_started:
                        is_recording_speech = True
                        audio_buffer.clear()
                        await websocket.send_json({
                            "type": "vad_event",
                            "state": "speech_started"
                        })
                    audio_buffer.extend(chunk)

                elif is_recording_speech:
                    # Speech ended (silence reached)
                    is_recording_speech = False
                    await websocket.send_json({
                        "type": "vad_event",
                        "state": "speech_ended"
                    })

                    # Transcribe captured audio buffer
                    if len(audio_buffer) > 3200:  # Minimum ~100ms of audio
                        transcript = stt_engine.transcribe_pcm_bytes(bytes(audio_buffer))
                        if transcript:
                            wake_detected, command = wakeword_detector.check_text(transcript)
                            await websocket.send_json({
                                "type": "transcript",
                                "raw_text": transcript,
                                "wake_word_detected": wake_detected,
                                "command": command or transcript
                            })
                    audio_buffer.clear()

            elif "text" in message and message["text"]:
                # Control signal received
                pass

    except WebSocketDisconnect:
        logger.info("Audio duplex stream disconnected.")
    except Exception as e:
        logger.error(f"Audio stream error: {e}")
