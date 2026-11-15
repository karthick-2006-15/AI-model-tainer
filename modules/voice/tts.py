"""
JARVIS Text-to-Speech (TTS) Engine
Dual-tier architecture:
- Tier A: Edge-TTS (High-fidelity neural streaming voices in English & Tamil, zero API cost)
- Tier B: Local SAPI5 pyttsx3 (100% offline, zero latency fallback)
"""

import os
import asyncio
import logging
import queue
import threading
import re
from typing import Optional, List, Dict
import edge_tts
import pyttsx3

logger = logging.getLogger("jarvis.voice.tts")


class TTSEngine:
    SUPPORTED_VOICES = {
        "en": [
            {"id": "en-US-ChristopherNeural", "name": "Christopher (US Male - JARVIS style)", "gender": "Male"},
            {"id": "en-US-GuyNeural", "name": "Guy (US Male)", "gender": "Male"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (UK Male)", "gender": "Male"},
            {"id": "en-US-JennyNeural", "name": "Jenny (US Female)", "gender": "Female"},
        ],
        "ta": [
            {"id": "ta-IN-ValluvarNeural", "name": "Valluvar (Tamil Male)", "gender": "Male"},
            {"id": "ta-IN-PallaviNeural", "name": "Pallavi (Tamil Female)", "gender": "Female"},
        ]
    }

    def __init__(self, default_voice: str = "en-US-ChristopherNeural"):
        self.default_voice = default_voice
        self._offline_engine: Optional[pyttsx3.Engine] = None
        self._speech_queue: queue.Queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def _speech_worker(self):
        """Dedicated background thread for audio output via Windows SAPI5."""
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 185)
            # Find natural voice (Microsoft David or first English voice)
            voices = engine.getProperty("voices")
            for v in voices:
                if "david" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
        except Exception as e:
            logger.error(f"Failed to initialize SAPI5 speech worker: {e}")
            return

        while True:
            text = self._speech_queue.get()
            if text is None:
                break
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.warning(f"Error during speech vocalization: {e}")
            finally:
                self._speech_queue.task_done()

    @staticmethod
    def clean_for_speech(text: str) -> str:
        """Strips markdown syntax, links, and symbols for natural vocalization."""
        if not text:
            return ""
        # Remove markdown bold, italic, code backticks, headers, tildes
        t = re.sub(r"[*_#`~]", "", text)
        # Convert markdown links [text](url) -> text
        t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
        t = re.sub(r"https?://\S+", "", t)
        # Remove bullet points and lists
        t = re.sub(r"^[ \t]*[•\-\*][ \t]+", "", t, flags=re.MULTILINE)
        t = re.sub(r"[•\t]+", " ", t)
        # Normalize whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def speak(self, text: str):
        """Immediately queues speech to be spoken aloud through laptop speakers."""
        cleaned = self.clean_for_speech(text)
        if cleaned:
            self._speech_queue.put(cleaned)
            logger.info(f"Queued vocal response ({len(cleaned)} chars)")

    def get_supported_voices(self) -> Dict[str, List[Dict[str, str]]]:
        """Returns catalogue of supported voices categorized by language."""
        return self.SUPPORTED_VOICES

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> bool:
        """
        Synthesizes text to an MP3 file using Edge-TTS with fallback to offline SAPI5.
        """
        selected_voice = voice or self.default_voice
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        try:
            # 1. Attempt High-Fidelity Edge-TTS synthesis
            communicate = edge_tts.Communicate(text, selected_voice, rate=rate, pitch=pitch)
            await communicate.save(output_path)
            logger.info(f"Edge-TTS synthesized {len(text)} chars to {output_path}")
            return True
        except Exception as e:
            logger.warning(f"Edge-TTS synthesis failed ({e}). Falling back to offline SAPI5.")
            return self._synthesize_offline(text, output_path)

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None
    ):
        """
        Streams audio bytes asynchronously in chunks for ultra-low latency playback.
        """
        selected_voice = voice or self.default_voice
        communicate = edge_tts.Communicate(text, selected_voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    def _synthesize_offline(self, text: str, output_path: str) -> bool:
        """Fallback local TTS using Windows SAPI5."""
        try:
            if not self._offline_engine:
                self._offline_engine = pyttsx3.init()
            
            # SAPI5 supports saving to wav
            wav_path = output_path.replace(".mp3", ".wav")
            self._offline_engine.save_to_file(text, wav_path)
            self._offline_engine.runAndWait()
            logger.info(f"Offline SAPI5 synthesized {len(text)} chars to {wav_path}")
            return True
        except Exception as e:
            logger.error(f"Offline SAPI5 synthesis failed: {e}")
            return False


# Global singleton instance
tts_engine = TTSEngine()
