"""
Unit tests for Multilingual Communication, Code-Switching Normalizer & Continuous Conversation Mode
"""

import pytest
from modules.voice.multilingual import multilingual_engine
from modules.voice.conversation import conversation_manager
from core.brain.intent import intent_classifier


def test_language_detection():
    assert multilingual_engine.detect_language("Open Chrome browser") == "en"
    assert multilingual_engine.detect_language("WhatsApp open pannu") == "tanglish"
    assert multilingual_engine.detect_language("en father ku Hi message send pannu") == "tanglish"
    assert multilingual_engine.detect_language("Chrome kholo") == "hinglish"
    assert multilingual_engine.detect_language("mere father ko Hi message bhejo") == "hinglish"


def test_code_switching_normalization():
    # Tanglish open app
    cmd1, lang1 = multilingual_engine.normalize_code_switching("WhatsApp open pannu")
    assert cmd1.lower() == "open whatsapp"
    assert lang1 == "tanglish"

    # Hinglish open app
    cmd2, lang2 = multilingual_engine.normalize_code_switching("Chrome kholo")
    assert cmd2.lower() == "open chrome"
    assert lang2 == "hinglish"

    # Tanglish messaging
    cmd3, lang3 = multilingual_engine.normalize_code_switching("en father ku Hi message send pannu")
    assert "send hi to father" in cmd3.lower()
    assert lang3 == "tanglish"

    # Hinglish messaging
    cmd4, lang4 = multilingual_engine.normalize_code_switching("mere father ko Hi message bhejo")
    assert "send hi to father" in cmd4.lower()
    assert lang4 == "hinglish"


def test_localized_responses():
    # Tanglish localized response
    resp_t = multilingual_engine.localize_response("Chrome is open.", "tanglish")
    assert "open aaiduchu" in resp_t

    # Hinglish localized response
    resp_h = multilingual_engine.localize_response("Chrome is open.", "hinglish")
    assert "khul gaya hai" in resp_h


def test_continuous_conversation_turns_without_wakeword():
    conversation_manager.session.reset()

    # 1. Turn 1: User says wake word ("Hey Jarvis")
    turn1 = conversation_manager.process_incoming_speech("Hey Jarvis")
    assert turn1["handled"] is True
    assert turn1["is_greeting_only"] is True
    assert conversation_manager.session.is_active() is True

    # 2. Turn 2: User gives follow-up command WITHOUT wake-word
    turn2 = conversation_manager.process_incoming_speech("Open WhatsApp")
    assert turn2["handled"] is True
    assert turn2["in_active_session"] is True
    assert "open whatsapp" in turn2["canonical_instruction"].lower()

    # 3. Turn 3: User says "send Hi to father" without wake-word
    turn3 = conversation_manager.process_incoming_speech("Send Hi to my father")
    assert turn3["handled"] is True
    assert "send hi to my father" in turn3["canonical_instruction"].lower()

    # Clean up
    conversation_manager.session.reset()
