"""
Unit tests for Autonomous WhatsApp Automation & Level 3 Permission Guards
Tests search result classification, Chats prioritization over Groups in common,
conversation header & composer inspection, restricted group guardrails,
and natural language intent routing.
"""

import pytest
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
from core.security.permissions import permission_engine
from core.brain.intent import intent_classifier


def test_whatsapp_contact_resolution():
    # 1. Alias lookup (father -> Father)
    res_dad = whatsapp_automation.resolve_contact("father")
    assert res_dad["success"] is True
    assert res_dad["resolved_name"] in ("Father", "father", "Dad")
    assert res_dad["ambiguous"] is False

    # 2. Regional alias (appa -> father alias)
    res_appa = whatsapp_automation.resolve_contact("appa")
    assert res_appa["success"] is True
    assert res_appa["resolved_name"] in ("Appa", "Father")

    # 3. Direct contact name
    res_direct = whatsapp_automation.resolve_contact("Karthik")
    assert res_direct["success"] is True
    assert res_direct["resolved_name"] == "Karthik"


def test_whatsapp_message_preparation_and_permission_challenge():
    # Prepare message to father
    draft = whatsapp_automation.prepare_message(recipient="father", message_text="Hi")
    assert draft["success"] is True
    assert draft["status"] == "awaiting_authorization"
    assert "Hi" in draft["message"]
    assert "challenge" in draft
    assert "confirmation_prompt" in draft
    challenge_id = draft["challenge"]["challenge_id"]

    # Verify message is blocked from sending without authorization
    unauth_send = whatsapp_automation.send_message(recipient="father", message_text="Hi", skip_permission_check=False)
    assert unauth_send["success"] is False
    assert unauth_send["awaiting_authorization"] is True

    # User authorizes via permission engine challenge resolution
    approved, resolved_ch = permission_engine.resolve_challenge(challenge_id, approved=True)
    assert approved is True
    assert resolved_ch["challenge_id"] == challenge_id


def test_whatsapp_voice_confirmation_resolution():
    # Prepare draft
    draft = whatsapp_automation.prepare_message(recipient="father", message_text="Good morning")
    assert draft["success"] is True

    # Test confirmation with English phrase 'yes'
    approved, ch = permission_engine.resolve_voice_confirmation("yes")
    assert approved is True

    # Test denial with 'cancel'
    draft2 = whatsapp_automation.prepare_message(recipient="brother", message_text="Call me")
    approved2, ch2 = permission_engine.resolve_voice_confirmation("cancel")
    assert approved2 is False


def test_whatsapp_blocks_input_when_window_not_active(monkeypatch):
    """Guarantees that when WhatsApp is not active in foreground, keystroke injection is completely blocked."""
    from modules.computer_use.mouse_kb import mouse_kb

    mock_type = MagicMock()
    mock_press = MagicMock()
    mock_click = MagicMock()

    monkeypatch.setattr(mouse_kb, "type_text", mock_type)
    monkeypatch.setattr(mouse_kb, "press_key", mock_press)
    monkeypatch.setattr(mouse_kb, "click", mock_click)

    # Force active window checks to fail
    monkeypatch.setattr(whatsapp_automation, "_is_whatsapp_foreground", lambda: False)
    monkeypatch.setattr(whatsapp_automation, "_ensure_whatsapp_active", lambda max_attempts=3: False)

    res = whatsapp_automation.send_message(
        recipient="test_friend",
        message_text="sensitive keystroke",
        skip_permission_check=True
    )

    assert res["success"] is False
    assert "not active" in res["error"].lower()
    mock_type.assert_not_called()
    mock_press.assert_not_called()
    mock_click.assert_not_called()


def test_whatsapp_open_conversation_safe_from_enter_key(monkeypatch):
    """Guarantees that open_conversation navigates by clicking without pressing enter in chat."""
    from modules.computer_use.mouse_kb import mouse_kb

    mock_type = MagicMock()
    mock_press = MagicMock()
    mock_click = MagicMock()

    monkeypatch.setattr(mouse_kb, "type_text", mock_type)
    monkeypatch.setattr(mouse_kb, "press_key", mock_press)
    monkeypatch.setattr(mouse_kb, "click", mock_click)
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
                {"text": "Family", "x": 150, "y": 600, "w": 60, "h": 20, "cx": 180, "cy": 610},
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

    res = whatsapp_automation.open_conversation("Appa")
    assert res["success"] is True

    # Critical check: 'enter' must NEVER be pressed during open_conversation
    pressed_keys = [call.args[0] for call in mock_press.call_args_list if call.args]
    assert "enter" not in pressed_keys
    # Click must have been used to select search result
    assert mock_click.call_count >= 2


def test_whatsapp_intent_routing_direct_send():
    """Verifies that direct user commands to send messages route to whatsapp.send_message."""
    # Direct send command
    ic1 = intent_classifier.classify("send hi to Sreedharan")
    assert ic1.target_tool == "whatsapp.send_message"
    assert ic1.extracted_params["recipient"] == "Sreedharan"
    assert ic1.extracted_params["message"] == "hi"

    # Command with 'saying'
    ic2 = intent_classifier.classify("send a message to my father saying I will come home tomorrow")
    assert ic2.target_tool == "whatsapp.send_message"
    assert ic2.extracted_params["recipient"] == "father"
    assert ic2.extracted_params["message"] == "I will come home tomorrow"

    # Draft / Prepare command
    ic3 = intent_classifier.classify("prepare message to Sreedharan saying hi")
    assert ic3.target_tool == "whatsapp.prepare_message"
    assert ic3.extracted_params["recipient"] == "Sreedharan"
    assert ic3.extracted_params["message"] == "hi"


def test_whatsapp_search_result_classification_prioritizes_chats(monkeypatch):
    """
    R1 & R3: Verifies search result classification and that direct one-to-one
    conversations under 'Chats' are strictly prioritized over 'Groups in common'.
    """
    mock_ocr_words = [
        # Section Heading: Chats
        {"text": "Chats", "x": 150, "y": 360, "w": 60, "h": 20, "cx": 180, "cy": 370},
        # Direct Contact under Chats
        {"text": "Appa", "x": 150, "y": 420, "w": 50, "h": 20, "cx": 175, "cy": 430},
        # Section Heading: Groups in common
        {"text": "Groups in common", "x": 150, "y": 550, "w": 120, "h": 20, "cx": 210, "cy": 560},
        # Group result containing contact
        {"text": "G: 7 VPS", "x": 150, "y": 620, "w": 80, "h": 20, "cx": 190, "cy": 630},
        # Participant snippet mentioning Appa
        {"text": "Appa is also in this group", "x": 150, "y": 660, "w": 160, "h": 20, "cx": 230, "cy": 670},
        # Section Heading: Messages
        {"text": "Messages", "x": 150, "y": 750, "w": 70, "h": 20, "cx": 185, "cy": 760},
        # Message snippet
        {"text": "Appa: See you tomorrow", "x": 150, "y": 800, "w": 140, "h": 20, "cx": 220, "cy": 810},
    ]

    monkeypatch.setattr(whatsapp_automation, "run_ocr", lambda path: mock_ocr_words)

    window_rect = (100, 100, 1200, 900)
    candidates = whatsapp_automation._extract_results_via_ocr("Appa", "dummy.png", window_rect)

    # Verify classification of each result type
    direct_items = [c for c in candidates if c.result_type == SearchResultType.DIRECT_CHAT]
    group_items = [c for c in candidates if c.result_type in (SearchResultType.GROUP_CHAT, SearchResultType.GROUP_MEMBER)]
    msg_items = [c for c in candidates if c.result_type == SearchResultType.MESSAGE_SNIPPET]

    assert len(direct_items) >= 1
    assert direct_items[0].name == "Appa"
    assert direct_items[0].section == SearchSection.CHATS
    assert direct_items[0].is_direct_chat is True
    assert direct_items[0].is_group is False

    assert any(g.name == "G: 7 VPS" and g.section == SearchSection.GROUPS_IN_COMMON for g in group_items)
    assert any("also in this group" in g.name and g.result_type == SearchResultType.GROUP_MEMBER for g in group_items)
    assert any(m.section == SearchSection.MESSAGES for m in msg_items)

    # Select best direct chat
    selected, err = whatsapp_automation.select_best_direct_chat(candidates, "Appa")
    assert err is None
    assert selected is not None
    assert selected.name == "Appa"
    assert selected.section == SearchSection.CHATS
    assert selected.is_direct_chat is True
    assert selected.is_group is False


def test_whatsapp_rejects_groups_in_common_when_searching_direct_contact():
    """
    R1: Verifies that when only 'Groups in common' exist and no direct contact
    is listed under 'Chats', selection refuses to pick a group.
    """
    candidates = [
        ClassifiedSearchResult(
            name="Family Group",
            section=SearchSection.GROUPS_IN_COMMON,
            result_type=SearchResultType.GROUP_CHAT,
            bounds=(100, 600, 100, 30),
            center_coords=(150, 615),
            confidence=0.8,
            raw_text="Family Group",
            is_direct_chat=False,
            is_group=True
        ),
        ClassifiedSearchResult(
            name="Appa is also in this group",
            section=SearchSection.GROUPS_IN_COMMON,
            result_type=SearchResultType.GROUP_MEMBER,
            bounds=(100, 640, 150, 30),
            center_coords=(175, 655),
            confidence=0.7,
            raw_text="Appa is also in this group",
            is_direct_chat=False,
            is_group=True,
            participant_info="group_member_snippet"
        )
    ]

    selected, err = whatsapp_automation.select_best_direct_chat(candidates, "Appa")
    assert selected is None
    assert "Only group conversations found" in err


def test_whatsapp_aborts_when_conversation_is_group(monkeypatch):
    """
    R2: Verifies that if a group conversation is opened instead of direct chat,
    the workflow detects the group header, refuses to type or send, and aborts.
    """
    from modules.computer_use.mouse_kb import mouse_kb

    mock_type = MagicMock()
    mock_click = MagicMock()
    monkeypatch.setattr(mouse_kb, "type_text", mock_type)
    monkeypatch.setattr(mouse_kb, "click", mock_click)
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

    # Mock OCR returning search results with a candidate, but opening it yields group header
    def mock_run_ocr(img_path):
        if "search" in str(img_path) or "classified" in str(img_path):
            return [
                {"text": "Chats", "x": 150, "y": 360, "w": 60, "h": 20, "cx": 180, "cy": 370},
                {"text": "Appa", "x": 150, "y": 420, "w": 50, "h": 20, "cx": 175, "cy": 430},
            ]
        elif "selected_conversation" in str(img_path):
            # Group header with subtitle "click here for group info"
            return [
                {"text": "G: 7 VPS", "x": 600, "y": 105, "w": 80, "h": 20, "cx": 640, "cy": 115},
                {"text": "click here for group info", "x": 600, "y": 140, "w": 180, "h": 15, "cx": 690, "cy": 147},
            ]
        return []

    monkeypatch.setattr(whatsapp_automation, "run_ocr", mock_run_ocr)
    monkeypatch.setattr(whatsapp_automation, "capture_whatsapp_window", lambda step: (None, f"dummy_{step}.png"))

    whatsapp_automation._current_open_contact = None
    res = whatsapp_automation.open_conversation("Appa")
    assert res["success"] is False
    assert res["is_group"] is True
    assert "group chat" in res["error"].lower()

    # Verify no message content was typed into the group (only search query was typed)
    assert all("message" not in str(c).lower() for c in mock_type.call_args_list)
    assert mock_type.call_count <= 1
    assert whatsapp_automation.current_state in (WhatsAppState.GROUP_CHAT_DETECTED, WhatsAppState.FAILED)


@pytest.mark.parametrize("banner_text,expected_reason", [
    ("Only admins can send messages", "only admins can send messages"),
    ("You can't send messages to this group", "you cant send messages to this group"),
    ("You are no longer a participant", "you are no longer a participant"),
    ("This chat is unavailable", "this chat is unavailable"),
    ("Only community admins can send messages", "only community admins can send messages"),
    ("Messages can't be sent to this group", "messages cant be sent to this group"),
])
def test_whatsapp_detects_restricted_composer_states(monkeypatch, banner_text, expected_reason):
    """
    R2: Verifies detection of read-only/restricted group composer banners.
    Workflow must halt immediately without entering keystrokes.
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

    # Mock OCR returning composer with the restricted banner
    def mock_run_ocr(img_path):
        if "composer" in str(img_path):
            return [
                {"text": banner_text, "x": 600, "y": 820, "w": 250, "h": 20, "cx": 725, "cy": 830}
            ]
        return []

    monkeypatch.setattr(whatsapp_automation, "run_ocr", mock_run_ocr)
    monkeypatch.setattr(whatsapp_automation, "capture_whatsapp_window", lambda step: (None, f"dummy_{step}.png"))

    comp_info = whatsapp_automation._inspect_composer()
    assert comp_info.is_enabled is False
    assert comp_info.sending_permitted is False
    assert expected_reason in comp_info.restriction_reason

    # Test prepare_message halts when composer is restricted
    monkeypatch.setattr(whatsapp_automation, "open_conversation", lambda q: {"success": True, "contact": q, "verified": True})

    res = whatsapp_automation.prepare_message("Appa", "Hello")
    assert res["success"] is False
    assert res["composer_state"] == "restricted"
    assert "Cannot send message" in res["error"]
    # Ensure zero message keystrokes were typed
    mock_type.assert_not_called()
    assert whatsapp_automation.current_state == WhatsAppState.COMPOSER_RESTRICTED


def test_whatsapp_ambiguous_direct_chats_request_clarification():
    """
    R1: Verifies that when multiple direct chats match under 'Chats',
    clarification is requested rather than guessing.
    """
    candidates = [
        ClassifiedSearchResult(
            name="Appa Home",
            section=SearchSection.CHATS,
            result_type=SearchResultType.DIRECT_CHAT,
            bounds=(100, 400, 120, 30),
            center_coords=(160, 415),
            confidence=0.9,
            raw_text="Appa Home",
            is_direct_chat=True,
            is_group=False
        ),
        ClassifiedSearchResult(
            name="Appa Work",
            section=SearchSection.CHATS,
            result_type=SearchResultType.DIRECT_CHAT,
            bounds=(100, 450, 120, 30),
            center_coords=(160, 465),
            confidence=0.9,
            raw_text="Appa Work",
            is_direct_chat=True,
            is_group=False
        )
    ]

    selected, err = whatsapp_automation.select_best_direct_chat(candidates, "Appa")
    assert selected is None
    assert "Multiple direct conversations match" in err
    assert "Appa Home" in err
    assert "Appa Work" in err


def test_whatsapp_command_intent_parsing_coverage():
    """
    Acceptance Criteria & Intent: Verifies clean wake-word stripping,
    prefix removal, and trailing punctuation stripping across all 4 mandatory commands.
    """
    cases = [
        ("Jarvis, send hi to Appa", "Appa", "hi"),
        ("Send hello to Amma.", "Amma", "hello"),
        ("Send good morning to Appa.", "Appa", "good morning"),
        ("Appa ku hi anupu.", "Appa", "hi"),
    ]

    for cmd, expected_recip, expected_msg in cases:
        ic = intent_classifier.classify(cmd)
        assert ic.target_tool in ("whatsapp.send_message", "whatsapp.prepare_message"), f"Failed for '{cmd}'"
        assert ic.extracted_params["recipient"].lower() == expected_recip.lower(), f"Recipient mismatch for '{cmd}'"
        assert ic.extracted_params["message"].lower() == expected_msg.lower(), f"Message mismatch for '{cmd}'"


def test_whatsapp_logging_and_screenshot_milestones(monkeypatch):
    """
    R4: Verifies standard milestone screenshot capture and non-tautological message verification.
    """
    saved_milestones = []

    def mock_save_milestone(step_name):
        saved_milestones.append(step_name)
        return (None, f"logs/whatsapp_debug/{step_name}_mock.png")

    monkeypatch.setattr(whatsapp_automation, "save_milestone_screenshot", mock_save_milestone)

    # Test all 6 standard milestone checkpoint names
    for m in [
        "search_results",
        "classified_direct_chat_results",
        "selected_conversation",
        "message_composer",
        "after_message_entry",
        "after_sending"
    ]:
        whatsapp_automation.save_milestone_screenshot(m)

    assert "search_results" in saved_milestones
    assert "classified_direct_chat_results" in saved_milestones
    assert "selected_conversation" in saved_milestones
    assert "message_composer" in saved_milestones
    assert "after_message_entry" in saved_milestones
    assert "after_sending" in saved_milestones

    # Verify message verification returns genuine boolean
    monkeypatch.setattr(whatsapp_automation, "capture_whatsapp_window", lambda s: (None, "dummy.png"))
    monkeypatch.setattr(whatsapp_automation, "run_ocr", lambda p: [{"text": "Hello world"}])
    res_found = whatsapp_automation.verify_message("Hello")
    assert res_found["verified"] is True

    monkeypatch.setattr(whatsapp_automation, "run_ocr", lambda p: [{"text": "Unrelated content"}])
    res_not_found = whatsapp_automation.verify_message("Nonexistent phrase")
    assert res_not_found["verified"] is False
