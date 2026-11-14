"""
Duplex Audio Pipeline & Barge-In Controller
Coordinates concurrent microphone listening and audio playback.
Ensures JARVIS can be interrupted naturally mid-speech.
"""

import asyncio
import logging
from typing import Optional, Callable
from modules.voice.vad import VADDetector

logger = logging.getLogger("jarvis.voice.duplex")


class DuplexController:
    def __init__(self):
        self.vad = VADDetector()
        self.is_speaking = False
        self.is_listening = False
        self._interrupt_event = asyncio.Event()
        self.on_interrupted_callbacks = []

    def register_interruption_handler(self, callback: Callable):
        """Registers a callback function to execute whenever speech is interrupted."""
        self.on_interrupted_callbacks.append(callback)

    def trigger_interruption(self, reason: str = "User speech detected"):
        """Instantly cuts off current TTS audio playback."""
        if self.is_speaking:
            logger.info(f"BARGE-IN TRIGGERED: {reason}. Aborting active speech.")
            self.is_speaking = False
            self._interrupt_event.set()
            for cb in self.on_interrupted_callbacks:
                try:
                    cb()
                except Exception as e:
                    logger.warning(f"Error in interruption callback: {e}")

    def notify_speech_started(self):
        """Called when TTS playback begins."""
        self.is_speaking = True
        self._interrupt_event.clear()

    def notify_speech_finished(self):
        """Called when TTS playback finishes naturally."""
        self.is_speaking = False
        self._interrupt_event.clear()

    def process_incoming_audio_frame(self, pcm_bytes: bytes) -> bool:
        """
        Processes an incoming microphone frame.
        If user starts speaking while JARVIS is talking, triggers immediate barge-in.
        Returns:
            True if speech was interrupted, False otherwise.
        """
        is_speech, just_started = self.vad.process_frame(pcm_bytes)
        
        if just_started and self.is_speaking:
            self.trigger_interruption(reason="Acoustic barge-in detected from microphone")
            return True
        
        return False

    @property
    def was_interrupted(self) -> bool:
        return self._interrupt_event.is_set()


# Global singleton instance
duplex_controller = DuplexController()
