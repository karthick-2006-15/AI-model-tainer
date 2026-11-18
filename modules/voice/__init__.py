"""
JARVIS Voice Subsystem Package
"""

from modules.voice.state_machine import VoiceState, VoiceStateMachine, voice_state_machine
from modules.voice.stt import STTEngine, stt_engine
from modules.voice.tts import TTSEngine, tts_engine
from modules.voice.duplex import DuplexController, duplex_controller
from modules.voice.vad import VADDetector
from modules.voice.wakeword import WakeWordDetector, wakeword_detector
from modules.voice.conversation import ContinuousConversationManager, conversation_manager
from modules.voice.multilingual import MultilingualEngine, multilingual_engine

__all__ = [
    "VoiceState",
    "VoiceStateMachine",
    "voice_state_machine",
    "STTEngine",
    "stt_engine",
    "TTSEngine",
    "tts_engine",
    "DuplexController",
    "duplex_controller",
    "VADDetector",
    "WakeWordDetector",
    "wakeword_detector",
    "ContinuousConversationManager",
    "conversation_manager",
    "MultilingualEngine",
    "multilingual_engine",
]
