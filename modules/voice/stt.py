"""
JARVIS Speech-to-Text (STT) Engine
Transcribes spoken user audio from microphone streams and audio files.
Supports English and Tamil language recognition.
"""

import io
import wave
import logging
from typing import Optional, Union
import speech_recognition as sr

logger = logging.getLogger("jarvis.voice.stt")


class STTEngine:
    def __init__(self, default_language: str = "en-US"):
        self.default_language = default_language
        self.recognizer = sr.Recognizer()
        # Calibrate energy thresholds
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    def transcribe_audio_file(
        self,
        audio_file_path: str,
        language: Optional[str] = None
    ) -> Optional[str]:
        """Transcribes an audio file on disk to text."""
        lang = language or self.default_language
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language=lang)
                logger.info(f"STT recognized: '{text}' (lang={lang})")
                return text
        except sr.UnknownValueError:
            logger.debug("STT could not understand audio (silence or unintelligible).")
            return None
        except sr.RequestError as e:
            logger.error(f"STT service error: {e}")
            return None
        except Exception as e:
            logger.error(f"STT file processing error: {e}")
            return None

    def transcribe_pcm_bytes(
        self,
        pcm_bytes: bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
        channels: int = 1,
        language: Optional[str] = None
    ) -> Optional[str]:
        """Transcribes raw PCM audio bytes received from WebSocket or microphone."""
        lang = language or self.default_language
        try:
            # Wrap PCM in standard WAV container in-memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_bytes)
            wav_buffer.seek(0)

            with sr.AudioFile(wav_buffer) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language=lang)
                logger.info(f"STT recognized from stream: '{text}'")
                return text
        except sr.UnknownValueError:
            return None
        except Exception as e:
            logger.warning(f"PCM transcription error: {e}")
            return None


# Global singleton instance
stt_engine = STTEngine()
