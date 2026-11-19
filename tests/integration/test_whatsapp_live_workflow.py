"""
Integration Tests for JARVIS Autonomous WhatsApp Desktop Automation Workflow
Tests the full state-driven pipeline, voice command parsing, contact resolution,
DPI awareness, Level 3 permission challenges, safe draft preparation,
R1-R3 search result classification & Chats prioritization, and R2 safety guardrails.
"""

import pytest
import os
import json
from unittest.mock import MagicMock
from modules.computer_use.whatsapp import (
    whatsapp_automation,
    WhatsAppState,
    SearchResultType,
    SearchSection,
    ClassifiedSearchResult,
    ConversationHeaderInfo,
    ComposerStateInfo
)
from core.brain.intent import intent_classifier
from core.security.permissions import permission_engine
from core.brain.orchestrator import BrainOrchestrator


def test_whatsapp_state_machine_enum_completeness():
    """Verifies that all 18 required states and auxiliary guardrail states exist in WhatsAppState enum."""
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
        # Auxiliary states for R1/R2/R4 guardrails
        "SEARCH_RESULTS_CLASSIFIED",
        "GROUP_CHAT_DETECTED",
        "COMPOSER_RESTRICTED",
        "SEARCH_RESULTS_RETRYING",
        "CONVERSATION_HEADER_VERIFIED",
        "COMPOSER_VERIFIED",
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
    draft = whatsapp_automation.prepare_message(recipient="Appa", message_text="I will come home tomorrow")
    assert draft["success"] is True
    assert draft["requires_confirmation"] is True
    assert "Shall I send it?" in draft["confirmation_prompt"]
    assert draft["challenge_id"] is not None

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


def test_live_workflow_state_machine_with_classification_and_verification(monkeypatch):
    """
    R1 & R3: Verifies that the live state machine transitions through the full verified sequence:
    WHATSAPP_FOREGROUND_VERIFIED -> CONTACT_SEARCHING -> CONTACT_RESULTS_DETECTED ->
    SEARCH_RESULTS_CLASSIFIED -> CONTACT_IDENTIFIED -> CONVERSATION_OPENING ->
    CONVERSATION_HEADER_VERIFIED -> CONVERSATION_VERIFIED.
    """
    from modules.computer_use.mouse_kb import mouse_kb

    monkeypatch.setattr(mouse_kb, "type_text", MagicMock())
    monkeypatch.setattr(mouse_kb, "click", MagicMock())
    monkeypatch.setattr(mouse_kb, "press_key", MagicMock())
    monkeypatch.setattr(mouse_kb, "press_hotkey", MagicMock())

    monkeypatch.setattr(whatsapp_automation, "_is_whatsapp_foreground", lambda: True)
    monkeypatch.setattr(whatsapp_automation, "_ensure_whatsapp_active", lambda max_attempts=3: True)

    from modules.automation.apps import ApplicationManager
    monkeypatch.setattr(ApplicationManager, "list_open_windows", lambda: [
        {"hwnd": 1115440, "title": "WhatsApp", "process_name": "WhatsApp.Root.exe"}
    ])
    import win32gui
    monkeypatch.setattr(win32gui, "GetWindowRect", lambda hwnd: (100, 100, 1200, 900))

    def mock_run_ocr(img_path):
        if "search" in str(img_path) or "classified" in str(img_path):
            return [
                {"text": "Chats", "x": 150, "y": 360, "w": 60, "h": 20, "cx": 180, "cy": 370},
                {"text": "Appa", "x": 150, "y": 420, "w": 50, "h": 20, "cx": 175, "cy": 430},
                {"text": "Groups in common", "x": 150, "y": 550, "w": 120, "h": 20, "cx": 210, "cy": 560},
                {"text": "Family Group", "x": 150, "y": 600, "w": 90, "h": 20, "cx": 195, "cy": 610},
                {"text": "Appa is also in this group", "x": 150, "y": 630, "w": 150, "h": 20, "cx": 225, "cy": 640},
            ]
        elif "selected_conversation" in str(img_path):
            return [
                {"text": "Appa", "x": 600, "y": 105, "w": 50, "h": 20, "cx": 625, "cy": 115},
                {"text": "online", "x": 600, "y": 140, "w": 40, "h": 15, "cx": 620, "cy": 147},
            ]
        return []

    monkeypatch.setattr(whatsapp_automation, "run_ocr", mock_run_ocr)
    monkeypatch.setattr(whatsapp_automation, "capture_whatsapp_window", lambda step: (None, f"dummy_{step}.png"))

    wa = whatsapp_automation
    wa.state_history.clear()
    wa._current_open_contact = None

    res = wa.open_conversation("Appa")
    assert res["success"] is True
    assert res["verified"] is True
    assert res["is_group"] is False

    # Check state history sequence
    recorded_states = [entry["to_state"] for entry in wa.state_history]
    assert WhatsAppState.CONTACT_SEARCHING.value in recorded_states
    assert WhatsAppState.CONTACT_RESULTS_DETECTED.value in recorded_states
    assert WhatsAppState.SEARCH_RESULTS_CLASSIFIED.value in recorded_states
    assert WhatsAppState.CONTACT_IDENTIFIED.value in recorded_states
    assert WhatsAppState.CONVERSATION_OPENING.value in recorded_states
    assert WhatsAppState.CONVERSATION_HEADER_VERIFIED.value in recorded_states
    assert WhatsAppState.CONVERSATION_VERIFIED.value in recorded_states


def test_live_workflow_restricted_group_safety_abort(monkeypatch):
    """
    R2: Verifies safety abort when composer banner displays 'Only admins can send messages'.
    Ensures state transitions to COMPOSER_RESTRICTED and message entry is completely prevented.
    """
    from modules.computer_use.mouse_kb import mouse_kb

    mock_type = MagicMock()
    monkeypatch.setattr(mouse_kb, "type_text", mock_type)
    monkeypatch.setattr(mouse_kb, "click", MagicMock())
    monkeypatch.setattr(mouse_kb, "press_key", MagicMock())
    monkeypatch.setattr(mouse_kb, "press_hotkey", MagicMock())

    monkeypatch.setattr(whatsapp_automation, "_is_whatsapp_foreground", lambda: True)
    monkeypatch.setattr(whatsapp_automation, "_ensure_whatsapp_active", lambda max_attempts=3: True)

    from modules.automation.apps import ApplicationManager
    monkeypatch.setattr(ApplicationManager, "list_open_windows", lambda: [
        {"hwnd": 1115440, "title": "WhatsApp", "process_name": "WhatsApp.Root.exe"}
    ])
    import win32gui
    monkeypatch.setattr(win32gui, "GetWindowRect", lambda hwnd: (100, 100, 1200, 900))

    # Mock open_conversation succeeding, but composer inspection detects restriction banner
    monkeypatch.setattr(whatsapp_automation, "open_conversation", lambda q: {"success": True, "contact": q, "verified": True})

    def mock_run_ocr(img_path):
        if "composer" in str(img_path):
            return [
                {"text": "Only admins can send messages", "x": 600, "y": 820, "w": 250, "h": 20, "cx": 725, "cy": 830}
            ]
        return []

    monkeypatch.setattr(whatsapp_automation, "run_ocr", mock_run_ocr)
    monkeypatch.setattr(whatsapp_automation, "capture_whatsapp_window", lambda step: (None, f"dummy_{step}.png"))

    draft = whatsapp_automation.prepare_message("Appa", "Hello everyone")
    assert draft["success"] is False
    assert draft["composer_state"] == "restricted"
    assert "only admins can send messages" in draft["restriction"].lower()

    # Verify zero typing took place
    mock_type.assert_not_called()
    assert whatsapp_automation.current_state == WhatsAppState.COMPOSER_RESTRICTED


@pytest.mark.asyncio
async def test_end_to_end_command_to_whatsapp_orchestration(monkeypatch):
    """
    Acceptance Criteria End-to-End: Verifies orchestrator execution for all 4 required command variations:
    1. "Jarvis, send hi to Appa"
    2. "Send hello to Amma."
    3. "Send good morning to Appa."
    4. "Appa ku hi anupu."
    """
    orchestrator = BrainOrchestrator()

    test_commands = [
        ("Jarvis, send hi to Appa", "Appa", "hi"),
        ("Send hello to Amma.", "Amma", "hello"),
        ("Send good morning to Appa.", "Appa", "good morning"),
        ("Appa ku hi anupu.", "Appa", "hi"),
    ]

    for user_cmd, expected_recip, expected_msg in test_commands:
        res = await orchestrator.process_user_request(user_cmd)
        assert res["tool_executed"] == "whatsapp.send_message", f"Wrong tool for: {user_cmd}"
        assert "Shall I send it?" in res["response"], f"Missing prompt for: {user_cmd}"
        assert expected_recip.lower() in res["response"].lower(), f"Missing recipient for: {user_cmd}"
        assert expected_msg.lower() in res["response"].lower(), f"Missing message for: {user_cmd}"

        # Cleanly cancel the prepared draft
        cancel_res = await orchestrator.process_user_request("No, cancel it")
        assert "cancelled" in cancel_res["response"].lower()
        assert whatsapp_automation._last_prepared_draft is None
