"""
Voice Activity Detection (VAD) Engine
Analyzes streaming audio frames to detect human speech boundaries and background noise.
Powers the Duplex Barge-in interruption mechanism.
"""

import math
import struct
from typing import Tuple


class VADDetector:
    def __init__(
        self,
        energy_threshold: float = 0.02,
        speech_pad_frames: int = 5,
        silence_pad_frames: int = 15
    ):
        self.energy_threshold = energy_threshold
        self.speech_pad_frames = speech_pad_frames
        self.silence_pad_frames = silence_pad_frames
        
        self.consecutive_speech_frames = 0
        self.consecutive_silence_frames = 0
        self.is_speech_active = False

    @staticmethod
    def calculate_rms(pcm_bytes: bytes) -> float:
        """Calculates Root-Mean-Square (RMS) amplitude of 16-bit PCM audio."""
        if not pcm_bytes:
            return 0.0
        
        count = len(pcm_bytes) // 2
        if count == 0:
            return 0.0
            
        format_str = f"<{count}h"
        try:
            shorts = struct.unpack(format_str, pcm_bytes)
            sum_squares = sum(s * s for s in shorts)
            mean_squares = sum_squares / count
            return math.sqrt(mean_squares) / 32768.0  # Normalize to 0.0 - 1.0
        except Exception:
            return 0.0

    def process_frame(self, pcm_bytes: bytes) -> Tuple[bool, bool]:
        """
        Processes an audio frame.
        Returns:
            (is_currently_speech: bool, transition_to_speech: bool)
            transition_to_speech is True on the exact frame the user begins speaking.
        """
        rms = self.calculate_rms(pcm_bytes)
        frame_is_loud = rms > self.energy_threshold
        just_started_speaking = False

        if frame_is_loud:
            self.consecutive_speech_frames += 1
            self.consecutive_silence_frames = 0
            if not self.is_speech_active and self.consecutive_speech_frames >= self.speech_pad_frames:
                self.is_speech_active = True
                just_started_speaking = True
        else:
            self.consecutive_silence_frames += 1
            if self.is_speech_active and self.consecutive_silence_frames >= self.silence_pad_frames:
                self.is_speech_active = False
                self.consecutive_speech_frames = 0

        return self.is_speech_active, just_started_speaking

    def reset(self):
        """Resets the detector state."""
        self.consecutive_speech_frames = 0
        self.consecutive_silence_frames = 0
        self.is_speech_active = False
