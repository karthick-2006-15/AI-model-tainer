"""
JARVIS Wake-Word Detection Engine
Detects the activation phrase "Hey Jarvis" and extracts subsequent instructions.
"""

import re
from typing import Tuple, Optional


class WakeWordDetector:
    DEFAULT_WAKE_PATTERNS = [
        r"\b(?:hey|hi|hello|ok|okay)?\s*jarvis\b",
        r"\bjarvis\b",
    ]

    def __init__(self, wake_word: str = "hey jarvis", sensitivity: float = 0.5):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self._compiled_regexes = [re.compile(p, re.IGNORECASE) for p in self.DEFAULT_WAKE_PATTERNS]

    def check_text(self, transcript: str) -> Tuple[bool, Optional[str]]:
        """
        Scans a transcribed text string for the wake word.
        Returns:
            (wake_detected: bool, extracted_command: Optional[str])
        Example:
            "Hey Jarvis open my project" -> (True, "open my project")
        """
        if not transcript:
            return False, None

        cleaned = transcript.strip()
        for pattern in self._compiled_regexes:
            match = pattern.search(cleaned)
            if match:
                # Extract the trailing command after the wake-word
                command_part = cleaned[match.end():].strip()
                # Remove leading commas or punctuation
                command_part = re.sub(r"^[,.:;!\-\s]+", "", command_part)
                return True, command_part if command_part else None

        return False, None


# Global singleton instance
wakeword_detector = WakeWordDetector()
