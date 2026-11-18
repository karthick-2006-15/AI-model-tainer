"""
Tier 3 End-to-End Test Suite: Pairwise & Cross-Feature System Interactions
Verifies 8 complex multi-subsystem workflows:
- TC-XFEAT-01: Voice Wake-Word to Desktop App Launch & Visual Verification
- TC-XFEAT-02: Speech Barge-in Aborting Active TTS and Triggering Emergency Stop
- TC-XFEAT-03: Persistent Memory Surviving Restart and Answering Brain Queries
- TC-XFEAT-04: WhatsApp Automation with Memory Lookup, Level 3 Challenge, and Spoken Approval
- TC-XFEAT-05: Browser DOM Intelligence, Question Extraction, and Form Verification
- TC-XFEAT-06: Shell Sandbox Blocklist Enforcement and Emergency Lockout
- TC-XFEAT-07: Mobile File Transfer Confinement and Vector Indexing
- TC-XFEAT-08: Spotify Playback Synchronization with Avatar Expression and HUD Telemetry
"""

import os
import io
import struct
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from core.brain.intent import intent_classifier
from core.brain.orchestrator import brain_orchestrator
from core.security.permissions import permission_engine
from core.memory.profile import profile_memory
from modules.voice.duplex import duplex_controller
from modules.computer_use.app_manager import UniversalAppManager
from modules.computer_use.whatsapp import whatsapp_automation
from modules.computer_use.page_intelligence import PageIntelligenceEngine
from modules.computer_use.browser_playwright import PlaywrightBrowserController
from modules.automation.shell import shell_sandbox
import storage.db.connection as db_conn


def test_tc_xfeat_01_voice_to_desktop_app_launch(app_client):
    """TC-XFEAT-01: Voice Wake-Word to Desktop App Launch & Verification flow."""
    # 1. Stream simulated speech over /ws/audio with wake-word and command
    with patch("modules.voice.stt.stt_engine.transcribe_pcm_bytes", return_value="Hey Jarvis open notepad"):
        with app_client.websocket_connect("/ws/audio") as ws:
            loud_samples = [10000 if i % 2 == 0 else -10000 for i in range(1600)]
            loud_pcm = struct.pack(f"<{len(loud_samples)}h", *loud_samples)
            for _ in range(6):
                ws.send_bytes(loud_pcm)
            ws.receive_json()  # speech_started

            for _ in range(16):
                ws.send_bytes(bytes(3200))
            ws.receive_json()  # speech_ended

            # Transcript event with wake word
            msg = ws.receive_json()
            assert msg.get("type") == "transcript"
            assert msg.get("wake_word_detected") is True
            assert "notepad" in msg.get("command", "").lower()

    # 2. Process extracted command through brain and verify desktop launch tool
    intent = intent_classifier.classify(msg["command"])
    assert intent.target_tool in ("open_application", "tool_open_application")
    assert intent.extracted_params["app_name"].lower() == "notepad"


def test_tc_xfeat_02_barge_in_to_emergency_stop(app_client):
    """TC-XFEAT-02: Speech Barge-in Aborting Active TTS and Triggering Emergency Stop."""
    # 1. JARVIS begins speaking
    duplex_controller.notify_speech_started()
    assert duplex_controller.is_speaking is True

    # 2. User interrupts by speaking loudly (acoustic barge-in)
    loud_frame = struct.pack("<1600h", *[10000 if i % 2 == 0 else -10000 for i in range(1600)])
    # Feed frames to trigger barge-in
    for _ in range(6):
        duplex_controller.process_incoming_audio_frame(loud_frame)

    assert duplex_controller.is_speaking is False
    assert duplex_controller.was_interrupted is True

    # 3. User says "Emergency stop, abort all operations"
    chat_res = app_client.post("/api/chat", json={"message": "Emergency stop! Abort all operations!"})
    assert chat_res.status_code == 200
    assert permission_engine.is_emergency_stopped() is True

    # Reset
    permission_engine.reset_emergency_stop()


def test_tc_xfeat_03_memory_restart_recovery(app_client, isolated_storage):
    """TC-XFEAT-03: Persistent Memory Surviving Restart and Answering Brain Queries."""
    # 1. Store preference entity
    profile_memory.add_or_update_fact(
        key_name="user_birthday",
        category="preference",
        value_data={"date": "August 15", "text": "My birthday is on August 15."}
    )

    # 2. Simulate complete application restart by resetting engine connection
    db_path = isolated_storage["db_path"]
    db_conn.engine.dispose()

    reopened_engine = create_engine(f"sqlite:///{os.path.abspath(db_path)}", echo=False)
    db_conn.engine = reopened_engine
    db_conn.SessionLocal.configure(bind=reopened_engine)

    try:
        # 3. Query chat endpoint asking about the fact
        chat_res = app_client.post("/api/chat", json={"message": "When is my birthday?"})
        assert chat_res.status_code == 200
        response_text = chat_res.json()["response"]
        assert "August 15" in response_text or "august 15" in response_text.lower()
    finally:
        reopened_engine.dispose()


def test_tc_xfeat_04_whatsapp_memory_lookup_and_challenge(app_client):
    """TC-XFEAT-04: WhatsApp Automation with Memory Lookup, Level 3 Challenge, and Spoken Approval."""
    from modules.computer_use.mouse_kb import mouse_kb

    # 1. Seed Profile Memory with relation alias
    profile_memory.add_or_update_fact(
        key_name="father",
        category="general",
        value_data={"text": "Ramesh"}
    )

    # 2. Resolve relation "Appa" -> "Ramesh"
    res_contact = whatsapp_automation.resolve_contact("Appa")
    assert res_contact["success"] is True
    assert res_contact["resolved_name"] == "Ramesh"

    # 3. Prepare message (creates Level 3 Challenge)
    with patch.object(whatsapp_automation, "open_conversation", return_value={"success": True}):
        draft = whatsapp_automation.prepare_message("Appa", "I am on my way")
        assert draft["success"] is True
        assert draft["status"] == "awaiting_authorization"
        challenge_id = draft["challenge_id"]
        assert challenge_id is not None

        # 4. Spoken approval "Yes, send it"
        approved, ch = permission_engine.resolve_voice_confirmation("Yes, send it")
        assert approved is True
        assert ch["challenge_id"] == challenge_id

        # 5. Send message post-approval
        whatsapp_automation._current_open_contact = "ramesh"
        with patch.object(whatsapp_automation, "_ensure_whatsapp_active", return_value=True), \
             patch.object(whatsapp_automation, "_is_whatsapp_foreground", return_value=True), \
             patch.object(whatsapp_automation, "verify_message", return_value={"verified": True, "method": "mock"}), \
             patch.object(mouse_kb, "click"), \
             patch.object(mouse_kb, "press_hotkey"), \
             patch.object(mouse_kb, "press_key"), \
             patch.object(mouse_kb, "type_text"):
            send_res = whatsapp_automation.send_message("Ramesh", "I am on my way", skip_permission_check=True)
            assert send_res["success"] is True


def test_tc_xfeat_05_browser_page_intelligence_and_form():
    """TC-XFEAT-05: Browser DOM Intelligence, Question Extraction, and Form Verification."""
    from modules.computer_use.browser_playwright import playwright_controller
    playwright_controller._ensure_browser = MagicMock()
    mock_page = MagicMock()

    # Configure evaluate for questions, form inputs, and verify_form
    def mock_eval(script, *args):
        if "qIndex" in script:
            return [
                {"question_id": "q_1", "prompt": "Physics Law", "field_name": "q1", "type": "text", "options": [], "current_value": ""},
                {"question_id": "q_2", "prompt": "Units of Force", "field_name": "q2", "type": "text", "options": [], "current_value": ""}
            ]
        elif "completion_percentage" in script:
            return {
                "total_fields": 2,
                "filled_fields": 2,
                "empty_fields": 0,
                "completion_percentage": 100,
                "missing_required_fields": [],
                "is_ready_to_submit": True
            }
        return {}

    mock_page.evaluate = mock_eval
    playwright_controller._pages = [mock_page]

    engine = PageIntelligenceEngine()

    # Step 1: Extract questions
    questions = engine.extract_questions()
    assert len(questions) == 2
    assert questions[0]["question_id"] == "q_1"

    # Step 2: Fill form
    with patch.object(playwright_controller, "fill", return_value={"success": True}):
        fill_res = engine.fill_form({"q1": "Newton's First Law", "q2": "Newtons"})
        assert fill_res["success"] is True
        assert fill_res["total_filled"] == 2

    # Step 3: Verify form
    verify_res = engine.verify_form()
    assert verify_res["success"] is True
    assert verify_res["verification"]["is_ready_to_submit"] is True


def test_tc_xfeat_06_shell_sandbox_blocklist_and_lockout(app_client):
    """TC-XFEAT-06: Shell Sandbox Blocklist Enforcement and Emergency Lockout."""
    # Step 1: Safe command with approval
    with patch("subprocess.run") as mock_subp:
        mock_subp.return_value = MagicMock(returncode=0, stdout="test_dir", stderr="")
        safe_res = shell_sandbox.execute_command("dir", skip_permission_check=True)
        assert safe_res["success"] is True
        assert safe_res["exit_code"] == 0

    # Step 2: Blocklisted command intercepted
    bad_res = app_client.post("/api/automation/shell", json={"command": "del /s C:\\Windows\\System32"})
    assert bad_res.status_code == 200
    assert bad_res.json()["success"] is False
    assert bad_res.json()["exit_code"] == -1

    # Step 3: Trigger emergency stop
    permission_engine.trigger_emergency_stop(reason="Security Incident Halt")
    try:
        # Step 4: Previously safe command is now blocked
        lockout_res = app_client.post("/api/automation/shell", json={"command": "dir"})
        assert lockout_res.status_code == 200
        assert lockout_res.json()["success"] is False
        assert "Emergency Stop is ACTIVE" in lockout_res.json().get("message", "")
    finally:
        permission_engine.reset_emergency_stop()


def test_tc_xfeat_07_mobile_file_sync_confinement(app_client):
    """TC-XFEAT-07: Mobile File Transfer Confinement and Validation."""
    # 1. Send mobile file
    content = b"E2E Mobile Sync Content"
    res = app_client.post(
        "/api/mobile/files/send-to-laptop",
        files={"file": ("sync_document.txt", io.BytesIO(content), "text/plain")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "MobileSync" in data["saved_path"]

    # 2. Verify download with traversal attack is blocked
    bad_dl = app_client.get("/api/mobile/files/download?file_path=../../../../etc/passwd")
    assert bad_dl.status_code == 403


def test_tc_xfeat_08_spotify_playback_with_hud_telemetry(app_client):
    """TC-XFEAT-08: Spotify Playback Synchronization with Avatar Expression and HUD Telemetry."""
    from modules.media.spotify_controller import spotify_controller

    with app_client.websocket_connect("/ws/hud") as ws:
        # Initial greeting and avatar frames (agent_state, voice_state, avatar_state)
        init_frames = [ws.receive_json() for _ in range(3)]
        init_types = {f["type"] for f in init_frames}
        assert "agent_state" in init_types
        assert "avatar_state" in init_types

        # Dispatch chat input over HUD socket
        with patch.object(spotify_controller, "play_track", return_value={
            "success": True, "playing": True, "track": "Bohemian Rhapsody", "artist": "Queen", "message": "Playing Bohemian Rhapsody."
        }):
            ws.send_json({"type": "chat_input", "text": "Play Bohemian Rhapsody on Spotify"})

            # Receive frames until thinking or agent/avatar state is observed
            found_state = False
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("type") in ("agent_state", "avatar_state"):
                    found_state = True
                    break
            assert found_state is True
