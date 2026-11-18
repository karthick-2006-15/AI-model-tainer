"""
JARVIS Voice State Machine
Manages central voice lifecycle states:
IDLE, LISTENING, PROCESSING, THINKING, SPEAKING, INTERRUPTED, ERROR.
Coordinates avatar state synchronization, duplex barge-in interruption, and WebSocket telemetry.
"""

from enum import Enum
import logging
from typing import Optional, Callable, List, Union
import asyncio

logger = logging.getLogger("jarvis.voice.state_machine")


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"


class VoiceStateMachine:
    """Central state machine coordinating all voice states and event subscribers."""

    def __init__(self, initial_state: VoiceState = VoiceState.IDLE):
        self._state: VoiceState = initial_state
        self._listeners: List[Callable[[VoiceState, Optional[str]], None]] = []
        self._async_listeners: List[Callable[[VoiceState, Optional[str]], asyncio.Future]] = []

    @property
    def current_state(self) -> VoiceState:
        return self._state

    def register_listener(self, callback: Callable[[VoiceState, Optional[str]], None]):
        """Registers a synchronous listener callback."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def register_async_listener(self, callback: Callable):
        """Registers an asynchronous broadcast listener."""
        if callback not in self._async_listeners:
            self._async_listeners.append(callback)

    def transition_to(self, new_state: Union[VoiceState, str], reason: Optional[str] = None) -> VoiceState:
        """
        Transitions the voice subsystem to a new state and notifies all subscribers.
        """
        if isinstance(new_state, str):
            try:
                new_state = VoiceState(new_state.lower())
            except ValueError:
                logger.warning(f"Unknown voice state string '{new_state}'. Defaulting to ERROR.")
                new_state = VoiceState.ERROR

        old_state = self._state
        self._state = new_state
        logger.info(f"VoiceState transition: [{old_state.value.upper()}] -> [{new_state.value.upper()}] (reason={reason})")

        # 1. Coordinate instant barge-in if transitioning to INTERRUPTED
        if new_state == VoiceState.INTERRUPTED:
            try:
                from modules.voice.tts import tts_engine
                tts_engine.stop()
            except Exception as e:
                logger.debug(f"Interruption TTS stop note: {e}")

        # 2. Synchronize Avatar engine expression & state
        try:
            from modules.avatar.avatar_engine import avatar_engine
            avatar_map = {
                VoiceState.IDLE: ("idle", reason or "Standing by."),
                VoiceState.LISTENING: ("listening", reason or "Listening..."),
                VoiceState.PROCESSING: ("thinking", reason or "Transcribing audio..."),
                VoiceState.THINKING: ("thinking", reason or "Reasoning..."),
                VoiceState.SPEAKING: ("speaking", reason or "Vocalizing..."),
                VoiceState.INTERRUPTED: ("confused", reason or "Interrupted."),
                VoiceState.ERROR: ("error", reason or "Voice system error.")
            }
            av_state, av_msg = avatar_map.get(new_state, ("idle", "Standing by."))
            avatar_engine.set_state(av_state, av_msg)
        except Exception as e:
            logger.debug(f"Avatar state sync note: {e}")

        # 3. Notify synchronous listeners
        for listener in self._listeners:
            try:
                listener(new_state, reason)
            except Exception as e:
                logger.warning(f"Error in voice state listener: {e}")

        # 4. Schedule async broadcast if an event loop is running
        if self._async_listeners:
            try:
                loop = asyncio.get_running_loop()
                for al in self._async_listeners:
                    loop.create_task(al(new_state, reason))
            except RuntimeError:
                pass  # No running event loop in thread

        return self._state

    def reset(self):
        """Resets the state machine back to IDLE."""
        self.transition_to(VoiceState.IDLE, reason="State machine reset")


# Global singleton instance
voice_state_machine = VoiceStateMachine()
