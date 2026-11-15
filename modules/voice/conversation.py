"""
Continuous Voice Conversation Manager
Maintains conversational context across consecutive voice turns without requiring the wake word every time.
Handles authorization confirmations ('Yes', 'Aama', 'Haan', 'No', 'Cancel') and session timeouts.
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple, List
from modules.voice.multilingual import multilingual_engine
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.voice.conversation")


class ConversationSession:
    """Tracks state and memory for a single multi-turn voice interaction."""

    def __init__(self, timeout_seconds: float = 15.0):
        self.timeout_seconds = timeout_seconds
        self.state = "idle"  # 'idle', 'active', 'awaiting_confirmation'
        self.last_active_time = 0.0
        self.active_language = "en"
        self.context_history: List[Dict[str, str]] = []
        self.pending_action: Optional[Dict[str, Any]] = None

    def is_active(self) -> bool:
        """Returns True if the session is currently within the active follow-up conversational window."""
        if self.state in ("active", "awaiting_confirmation"):
            if (time.time() - self.last_active_time) <= self.timeout_seconds:
                return True
            else:
                logger.info("Continuous conversation session timed out. Returning to idle mode.")
                self.reset()
                return False
        return False

    def touch(self):
        """Refreshes the active conversation timer."""
        self.last_active_time = time.time()

    def activate(self, language: str = "en"):
        """Activates continuous conversation mode."""
        self.state = "active"
        self.active_language = language
        self.touch()
        logger.info(f"Continuous conversation ACTIVATED (lang={language}, window={self.timeout_seconds}s)")

    def set_awaiting_confirmation(self, action_details: Dict[str, Any]):
        """Sets session state to wait for authorization confirmation."""
        self.state = "awaiting_confirmation"
        self.pending_action = action_details
        self.touch()
        logger.info(f"Conversation state set to AWAITING_CONFIRMATION for action: {action_details.get('action')}")

    def add_turn(self, role: str, content: str):
        """Appends a turn to the conversational context."""
        self.context_history.append({"role": role, "content": content})
        if len(self.context_history) > 10:
            self.context_history = self.context_history[-10:]
        self.touch()

    def reset(self):
        """Resets session back to idle."""
        self.state = "idle"
        self.pending_action = None
        self.context_history.clear()


class ContinuousConversationManager:
    """Manages voice conversational turns and auto-resolves follow-ups."""

    def __init__(self):
        self.session = ConversationSession(timeout_seconds=15.0)

    def process_incoming_speech(self, raw_transcript: str) -> Dict[str, Any]:
        """
        Processes incoming transcribed speech:
        1. Checks if we are waiting for a Level 3 Voice Confirmation ('Yes', 'Aama', 'Haan', 'No').
        2. Detects language (English, Tanglish, Hinglish).
        3. Checks if wake-word is present or if we are in continuous active conversation mode.
        """
        cleaned = raw_transcript.strip()
        detected_lang = multilingual_engine.detect_language(cleaned)

        # 1. Check if we are awaiting a confirmation
        if self.session.state == "awaiting_confirmation":
            self.session.touch()
            approved, resolved_ch = permission_engine.resolve_voice_confirmation(cleaned)
            if approved is not None:
                self.session.state = "active"  # return to active
                return {
                    "is_confirmation_response": True,
                    "approved": approved,
                    "challenge": resolved_ch,
                    "pending_action": self.session.pending_action,
                    "language": self.session.active_language,
                    "user_text": cleaned
                }

        # 2. Check if continuous session is active (wake-word NOT required!)
        in_active_session = self.session.is_active()

        # 3. Check for Wake Word ("Hey Jarvis")
        from modules.voice.wakeword import wakeword_detector
        wake_detected, command = wakeword_detector.check_text(cleaned)

        if not wake_detected and not in_active_session:
            # Unrelated background speech while idle
            return {
                "handled": False,
                "reason": "Idle and wake word not detected."
            }

        # User is speaking to JARVIS (either via wake-word or continuous follow-up)
        self.session.activate(language=detected_lang)

        # Determine effective instruction
        instruction = command if (wake_detected and command) else cleaned
        # Normalize any Tanglish / Hinglish code-switching
        canonical_instruction, lang = multilingual_engine.normalize_code_switching(instruction)

        self.session.add_turn(role="user", content=canonical_instruction)

        return {
            "handled": True,
            "wake_detected": wake_detected,
            "in_active_session": in_active_session,
            "raw_text": cleaned,
            "canonical_instruction": canonical_instruction,
            "language": lang,
            "is_greeting_only": (wake_detected and not command and not in_active_session)
        }

    def record_assistant_response(self, response_text: str, requires_confirmation: bool = False, action_details: Optional[Dict[str, Any]] = None):
        """Records assistant turn and updates conversation state."""
        self.session.add_turn(role="assistant", content=response_text)
        if requires_confirmation and action_details:
            self.session.set_awaiting_confirmation(action_details)
        else:
            self.session.touch()


# Global singleton instance
conversation_manager = ContinuousConversationManager()
