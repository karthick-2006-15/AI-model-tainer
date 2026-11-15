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
    assert res_appa["resolved_name"] == "Father"

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
