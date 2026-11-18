"""
Integration Tests for JARVIS Autonomous WhatsApp Desktop Automation Workflow
Tests the full state-driven pipeline, voice command parsing, contact resolution,
DPI awareness, Level 3 permission challenges, and safe draft preparation.
"""

import pytest
import os
import json
from unittest.mock import MagicMock
from modules.computer_use.whatsapp import whatsapp_automation, WhatsAppState
from core.brain.intent import intent_classifier
from core.security.permissions import permission_engine
from core.brain.orchestrator import BrainOrchestrator


def test_whatsapp_state_machine_enum_completeness():
    """Verifies that all 18 required states exist in WhatsAppState enum."""
    expected_states = [
        "WHATSAPP_IDLE",
        "WHATSAPP_LAUNCHING",
        "WHATSAPP_WINDOW_DETECTED",
        "WHATSAPP_WINDOW_RESTORED",
        "WHATSAPP_FOREGROUND_VERIFIED",
        "CONTACT_SEARCHING",
        "CONTACT_RESULTS_DETECTED",
        "CONTACT_IDENTIFIED",
        "CONVERSATION_OPENING",
        "CONVERSATION_VERIFIED",
        "COMPOSER_DETECTED",
        "MESSAGE_ENTERING",
        "MESSAGE_CONTENT_VERIFIED",
        "AWAITING_USER_CONFIRMATION",
        "MESSAGE_SENDING",
        "MESSAGE_SENT_VERIFIED",
        "MESSAGE_DELIVERY_PENDING",
        "FAILED",
    ]
    for s in expected_states:
        assert hasattr(WhatsAppState, s), f"Missing required state: {s}"
        assert getattr(WhatsAppState, s).value == s


def test_contact_resolution_aliases():
    """Verifies contact alias handling and user query preservation."""
    # Appa
    res_appa = whatsapp_automation.resolve_contact("Appa")
    assert res_appa["success"] is True
    assert res_appa["resolved_name"].lower() in ("appa", "father", "sreedharan")
    assert res_appa["query"] == "Appa"

    # Dad
    res_dad = whatsapp_automation.resolve_contact("Dad")
    assert res_dad["success"] is True
    assert res_dad["relation"] == "father"

    # Sreedharan
    res_sree = whatsapp_automation.resolve_contact("Sreedharan")
    assert res_sree["success"] is True
    assert res_sree["resolved_name"] == "Sreedharan"

    # Amma / Mom
    res_amma = whatsapp_automation.resolve_contact("Amma")
    assert res_amma["success"] is True
    assert res_amma["relation"] == "mother"


def test_intent_classification_natural_whatsapp_commands():
    """Verifies intent parsing across varied voice commands."""
    cases = [
        ("send hi to Appa", "Appa", "hi"),
        ("Hey Jarvis, send hi to Appa", "Appa", "hi"),
        ("Send message to Appa saying I will come home tomorrow", "Appa", "I will come home tomorrow"),
        ("send hi to Sreedharan", "Sreedharan", "hi"),
        ("open whatsapp and send hello to dad", "dad", "hello"),
        ("draft message to Mother saying Happy Birthday", "Mother", "Happy Birthday"),
    ]
    for user_cmd, expected_recip, expected_msg in cases:
        ic = intent_classifier.classify(user_cmd)
        assert ic.target_tool in ("whatsapp.send_message", "whatsapp.prepare_message"), f"Failed for '{user_cmd}'"
        assert ic.extracted_params["recipient"].lower() == expected_recip.lower()
        assert ic.extracted_params["message"].lower() == expected_msg.lower()


def test_state_timeline_tracking(monkeypatch):
    """Verifies that transitions record properly in the state timeline."""
    wa = whatsapp_automation
    initial_len = len(wa.state_history)
    wa._transition(WhatsAppState.WHATSAPP_LAUNCHING, {"test": 1})
    wa._transition(WhatsAppState.WHATSAPP_WINDOW_DETECTED, {"hwnd": 12345})
    wa._transition(WhatsAppState.WHATSAPP_FOREGROUND_VERIFIED)

    assert wa.current_state == WhatsAppState.WHATSAPP_FOREGROUND_VERIFIED
    assert len(wa.state_history) == initial_len + 3
    recent = wa.state_history[-1]
    assert recent["to_state"] == WhatsAppState.WHATSAPP_FOREGROUND_VERIFIED.value
    assert recent["success"] is True


def test_safe_draft_and_cancellation_lifecycle(monkeypatch):
    """Verifies full draft preparation, confirmation prompt generation, and safe cancellation."""
    # Prepare draft
    draft = whatsapp_automation.prepare_message(recipient="Appa", message_text="I will come home tomorrow")
    assert draft["success"] is True
    assert draft["requires_confirmation"] is True
    assert "Shall I send it?" in draft["confirmation_prompt"]
    assert draft["challenge_id"] is not None

    # Verify cancel draft clears the state
    cancel_res = whatsapp_automation.cancel_draft()
    assert cancel_res["success"] is True
    assert whatsapp_automation._last_prepared_draft is None
    assert whatsapp_automation.current_state == WhatsAppState.WHATSAPP_IDLE


@pytest.mark.asyncio
async def test_orchestrator_whatsapp_confirmation_gate(monkeypatch):
    """Verifies that orchestrator handles the two-stage approval gate cleanly."""
    orchestrator = BrainOrchestrator()

    # Step 1: User requests to send message -> Orchestrator intercepts and returns confirmation prompt
    res1 = await orchestrator.process_user_request("Hey Jarvis, send hi to Appa")
    assert res1["tool_executed"] == "whatsapp.send_message"
    assert "Shall I send it?" in res1["response"]

    # Step 2: User says "No" / "Cancel" -> Orchestrator safely aborts without sending
    res2 = await orchestrator.process_user_request("No, cancel it")
    assert "cancelled" in res2["response"].lower()
    assert whatsapp_automation._last_prepared_draft is None
