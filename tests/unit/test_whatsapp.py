"""
Unit tests for Autonomous WhatsApp Automation & Level 3 Permission Guards
"""

import pytest
from modules.computer_use.whatsapp import whatsapp_automation
from core.security.permissions import permission_engine


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
    from unittest.mock import MagicMock
    from modules.computer_use.mouse_kb import mouse_kb

    mock_type = MagicMock()
    mock_press = MagicMock()
    mock_click = MagicMock()

    monkeypatch.setattr(mouse_kb, "type_text", mock_type)
    monkeypatch.setattr(mouse_kb, "press_key", mock_press)
    monkeypatch.setattr(mouse_kb, "click", mock_click)

    # Force active window checks to fail (simulating Antigravity or other app being active)
    monkeypatch.setattr(whatsapp_automation, "_is_whatsapp_foreground", lambda: False)
    monkeypatch.setattr(whatsapp_automation, "_ensure_whatsapp_active", lambda max_attempts=3: False)

    res = whatsapp_automation.send_message(
        recipient="test_friend",
        message_text="sensitive keystroke",
        skip_permission_check=True
    )

    assert res["success"] is False
    assert "not active" in res["error"].lower()
    # Ensure zero keystrokes were injected
    mock_type.assert_not_called()
    mock_press.assert_not_called()
    mock_click.assert_not_called()


def test_whatsapp_open_conversation_safe_from_enter_key(monkeypatch):
    """Guarantees that open_conversation navigates by clicking without pressing enter in chat."""
    from unittest.mock import MagicMock
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

    res = whatsapp_automation.open_conversation("Appa")
    assert res["success"] is True

    # Critical check: 'enter' must NEVER be pressed during open_conversation
    pressed_keys = [call.args[0] for call in mock_press.call_args_list if call.args]
    assert "enter" not in pressed_keys
    # Click must have been used to select search result
    assert mock_click.call_count >= 2  # search box click + first result click


def test_whatsapp_intent_routing_direct_send():
    """Verifies that direct user commands to send messages route to whatsapp.send_message."""
    from core.brain.intent import intent_classifier

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
