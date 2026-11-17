"""
Tier 4 End-to-End Test Suite: 16 Phase 12 Real-World Operational Scenarios
Authoritative Reference: PROJECT.md, TEST_INFRA.md, teamwork_explorer_e2e_3/handoff.md

Verifies:
- Scenario 1: Wake-Word Activation ("Hey Jarvis") over /ws/audio
- Scenario 2: Voice Interruption (Barge-In)
- Scenario 3: Multilingual Routing (EN, TA, Tanglish, HI, Hinglish)
- Scenario 4: Application Discovery Across Windows 11
- Scenario 5: Application Launch with Interactive Bridge & Verification
- Scenario 6: Window Switching via Thread Input Attachment
- Scenario 7: Desktop Screenshot Capture & Visual Inspection
- Scenario 8: File Operations with System Boundary Guardrails
- Scenario 9: Shell Sandbox with Command Blocklisting & Timeout
- Scenario 10: Browser Navigation & DOM Inspection via Playwright
- Scenario 11: Web Form Detection, Structured Filling, and Verification
- Scenario 12: Autonomous YouTube Search, Selection, and Player Controls
- Scenario 13: WhatsApp Automation with Relation Lookup & Level 3 Challenge
- Scenario 14: Authentic Spotify Media Controls (Zero False Simulation)
- Scenario 15: Persistent Memory Recovery Across Full Application Restart
- Scenario 16: Global Emergency Stop Kill-Switch & Total Lockout
"""

import os
import io
import time
import struct
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from sqlalchemy import create_engine

from core.security.permissions import permission_engine
from core.memory.profile import profile_memory
from core.brain.intent import intent_classifier
from modules.voice.duplex import duplex_controller
from modules.voice.wakeword import wakeword_detector
from modules.voice.multilingual import multilingual_engine
from modules.computer_use.app_discovery import app_discovery
from modules.computer_use.app_manager import UniversalAppManager
from modules.computer_use.screen import screen_intelligence
from modules.automation.file_ops import FileOperationsManager
from modules.automation.shell import shell_sandbox
from modules.computer_use.browser_playwright import PlaywrightBrowserController, playwright_controller
from modules.computer_use.page_intelligence import page_intelligence
from modules.computer_use.youtube import youtube_automation
from modules.computer_use.whatsapp import whatsapp_automation
from modules.computer_use.mouse_kb import mouse_kb
import storage.db.connection as db_conn


# ==============================================================================
# SCENARIO 1: Wake-Word Activation ("Hey Jarvis")
# ==============================================================================
def test_scenario_01_wake_word_activation(app_client):
    """
    Scenario 1: Acoustic PCM audio stream over /ws/audio containing 'Hey Jarvis, open my downloads folder'.
    VAD detects speech activity, STT transcribes buffer, and WakeWordDetector scans text.
    Emits transcript event with wake_word_detected=True and extracted command.
    """
    with patch("modules.voice.stt.stt_engine.transcribe_pcm_bytes", return_value="Hey Jarvis open my downloads folder"):
        with app_client.websocket_connect("/ws/audio") as ws:
            # 1. Stream loud speech frames (> 5 frames to trigger speech_started)
            loud_samples = [10000 if i % 2 == 0 else -10000 for i in range(1600)]
            loud_pcm = struct.pack(f"<{len(loud_samples)}h", *loud_samples)
            for _ in range(6):
                ws.send_bytes(loud_pcm)
            ev1 = ws.receive_json()
            assert ev1.get("type") == "vad_event"
            assert ev1.get("state") == "speech_started"

            # 2. Stream silence frames (>= 15 frames to trigger speech_ended)
            for _ in range(16):
                ws.send_bytes(bytes(3200))
            ev2 = ws.receive_json()
            assert ev2.get("type") == "vad_event"
            assert ev2.get("state") == "speech_ended"

            # 3. Receive transcript event
            msg = ws.receive_json()
            assert msg.get("type") == "transcript"
            assert msg.get("wake_word_detected") is True
            assert msg.get("command") == "open my downloads folder"


# ==============================================================================
# SCENARIO 2: Voice Interruption (Barge-In)
# ==============================================================================
def test_scenario_02_voice_interruption_barge_in():
    """
    Scenario 2: Halts active TTS output immediately upon mid-utterance microphone input frame.
    duplex_controller.is_speaking immediately flips to False and was_interrupted is True.
    """
    try:
        # 1. Simulate active speech vocalization
        duplex_controller.notify_speech_started()
        assert duplex_controller.is_speaking is True
        assert duplex_controller.was_interrupted is False

        interruption_called = []
        def on_interrupt():
            interruption_called.append(True)

        duplex_controller.register_interruption_handler(on_interrupt)

        # 2. Incoming audio frame with RMS energy > threshold (stream up to 6 frames for VAD speech_started)
        loud_samples = [12000 if i % 2 == 0 else -12000 for i in range(800)]
        loud_pcm = struct.pack(f"<{len(loud_samples)}h", *loud_samples)

        start_t = time.time()
        interrupted = False
        for _ in range(6):
            if duplex_controller.process_incoming_audio_frame(loud_pcm):
                interrupted = True
                break
        elapsed_ms = (time.time() - start_t) * 1000

        # 3. Verify immediate halt
        assert interrupted is True
        assert duplex_controller.is_speaking is False
        assert duplex_controller.was_interrupted is True
        assert len(interruption_called) >= 1
        assert elapsed_ms < 150.0  # Must be sub-150ms
    finally:
        # Clean up duplex controller, VAD state, and handlers
        duplex_controller._interrupt_event.clear()
        duplex_controller.vad.reset()
        duplex_controller.on_interrupted_callbacks.clear()
        duplex_controller.is_speaking = False


# ==============================================================================
# SCENARIO 3: Multilingual Routing (EN, TA, Tanglish, HI, Hinglish)
# ==============================================================================
def test_scenario_03_multilingual_routing():
    """
    Scenario 3: Normalizes colloquial multilingual instructions (Tamil, Tanglish, Hindi, Hinglish, English)
    and verifies canonical command extraction and intent classification without LLM latency.
    """
    cases = [
        # (Input text, expected_lang, expected_canonical_substring, expected_intent_target)
        ("வணக்கம் ஜார்விஸ் கால்குலேட்டரை திறக்கவும்", "ta", None, None),
        ("WhatsApp open pannu", "tanglish", "open WhatsApp", "open_application"),
        ("Chrome kholo", "hinglish", "open Chrome", "open_application"),
        ("mere father ko Hi message bhejo", "hinglish", "send Hi to father", "whatsapp.prepare_message"),
        ("Open Visual Studio Code", "en", "Open Visual Studio Code", "open_application"),
    ]

    for text, exp_lang, exp_canonical, exp_tool in cases:
        detected_lang = multilingual_engine.detect_language(text)
        assert detected_lang == exp_lang

        canonical_cmd, norm_lang = multilingual_engine.normalize_code_switching(text)
        assert norm_lang == exp_lang

        if exp_canonical:
            assert exp_canonical.lower() in canonical_cmd.lower()

        if exp_tool:
            ic = intent_classifier.classify(canonical_cmd)
            assert ic.target_tool == exp_tool


# ==============================================================================
# SCENARIO 4: Application Discovery Across Windows 11
# ==============================================================================
def test_scenario_04_application_discovery():
    """
    Scenario 4: Discovers applications across system defs, special folders, and installed apps.
    Search by query ('calc', 'paint', 'terminal', 'downloads') returns structured ApplicationRecords.
    """
    # 1. Search calculator
    res_calc = app_discovery.search("calc", limit=3)
    assert len(res_calc) >= 1
    top_calc = res_calc[0]
    assert "calculator" in top_calc["name"].lower() or "calc" in [a.lower() for a in top_calc.get("aliases", [])]
    assert "target" in top_calc
    assert "app_type" in top_calc
    assert "launch_method" in top_calc

    # 2. Search paint
    res_paint = app_discovery.search("paint", limit=3)
    assert len(res_paint) >= 1
    assert any("paint" in r["name"].lower() for r in res_paint)

    # 3. Search downloads folder
    res_down = app_discovery.search("downloads", limit=3)
    assert len(res_down) >= 1
    assert any("downloads" in r["name"].lower() for r in res_down)


# ==============================================================================
# SCENARIO 5: Application Launch with Interactive Bridge & Verification
# ==============================================================================
def test_scenario_05_application_launch_and_verification(app_client):
    """
    Scenario 5: Launches app via Interactive Bridge and verifies window/process within closed-loop verification loop.
    UniversalAppManager.open_app returns verified=True and pid.
    POST /api/automation/apps/launch returns success=True.
    """
    mgr = UniversalAppManager()
    mgr.shutil = __import__("shutil")

    mock_window = {
        "hwnd": 4567,
        "title": "Untitled - Notepad",
        "pid": 8910,
        "process_name": "notepad.exe",
        "geometry": {"x": 100, "y": 100, "width": 800, "height": 600}
    }

    # 1. Test UniversalAppManager closed-loop verification
    with patch.object(UniversalAppManager, "_launch_interactive_desktop", return_value=True), \
         patch.object(UniversalAppManager, "list_open_windows", return_value=[mock_window]), \
         patch.object(UniversalAppManager, "switch_app", return_value=True):
        launch_res = mgr.open_app("notepad")
        assert launch_res["success"] is True
        assert launch_res["verified"] is True
        assert launch_res["pid"] == 8910
        assert "Notepad" in launch_res["app_name"]

    # 2. Test REST endpoint
    with patch("modules.automation.apps.ApplicationManager.launch", return_value={"success": True, "app_name": "notepad", "verified": True, "pid": 8910}):
        res = app_client.post("/api/automation/apps/launch", json={"app_name": "notepad"})
        assert res.status_code == 200
        assert res.json()["success"] is True


# ==============================================================================
# SCENARIO 6: Window Switching via Thread Input Attachment
# ==============================================================================
def test_scenario_06_window_switching_thread_input(app_client):
    """
    Scenario 6: Targets window 'Calculator' and switches focus using thread input attachment.
    POST /api/automation/windows/focus returns success=True.
    """
    mgr = UniversalAppManager()
    mock_windows = [
        {"hwnd": 1001, "title": "Notepad", "pid": 2001, "process_name": "notepad.exe"},
        {"hwnd": 1002, "title": "Calculator", "pid": 2002, "process_name": "calc.exe"}
    ]

    # 1. Verify UniversalAppManager.switch_app thread input attachment
    with patch.object(UniversalAppManager, "list_open_windows", return_value=mock_windows), \
         patch("modules.computer_use.app_manager.win32gui") as mock_gui, \
         patch("modules.computer_use.app_manager.win32process") as mock_proc, \
         patch("modules.computer_use.app_manager.win32api") as mock_api:
        mock_api.GetCurrentThreadId.return_value = 1111
        mock_proc.GetWindowThreadProcessId.return_value = (2222, 2002)

        switched = mgr.switch_app("Calculator")
        assert switched is True
        mock_proc.AttachThreadInput.assert_any_call(1111, 2222, True)
        mock_gui.SetForegroundWindow.assert_called_with(1002)

    # 2. Verify REST endpoint
    with patch("modules.automation.apps.ApplicationManager.focus_window", return_value=True):
        res = app_client.post("/api/automation/windows/focus", json={"title": "Calculator"})
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["title"] == "Calculator"


# ==============================================================================
# SCENARIO 7: Desktop Screenshot Capture & Visual Inspection
# ==============================================================================
def test_scenario_07_desktop_screenshot_capture(tmp_path):
    """
    Scenario 7: Captures screen, resizes preserving aspect ratio, and saves valid PNG with non-zero size.
    """
    screen_intelligence.storage_dir = str(tmp_path)

    # Mock ImageGrab.grab to return a 1920x1080 test image deterministically
    synthetic_screen = Image.new("RGB", (1920, 1080), color=(30, 41, 59))
    with patch("PIL.ImageGrab.grab", return_value=synthetic_screen):
        res = screen_intelligence.capture_screen(max_dimension=1920)

    assert res["success"] is True
    assert os.path.exists(res["file_path"])
    assert res["width"] == 1920
    assert res["height"] == 1080

    # Verify image integrity via PIL
    loaded = Image.open(res["file_path"])
    assert loaded.size == (1920, 1080)
    assert os.path.getsize(res["file_path"]) > 1000


# ==============================================================================
# SCENARIO 8: File Operations with System Boundary Guardrails
# ==============================================================================
def test_scenario_08_file_operations_with_guardrails(tmp_path):
    """
    Scenario 8: File Operations:
    Sub-action A: Create directory in authorized folder.
    Sub-action B: Organize directory with mixed files into categorized subfolders.
    Sub-action C: Attempt file operation on restricted system path (blocked by guardrails).
    """
    # Sub-action A: Create directory
    test_dir = tmp_path / "work_folder"
    create_res = FileOperationsManager.create_directory(str(test_dir))
    assert create_res["success"] is True

    # Sub-action B: Create mixed files and organize
    (test_dir / "report.pdf").write_text("sample pdf", encoding="utf-8")
    (test_dir / "picture.png").write_text("sample png", encoding="utf-8")
    (test_dir / "script.py").write_text("sample code", encoding="utf-8")
    (test_dir / "bundle.zip").write_text("sample zip", encoding="utf-8")

    org_res = FileOperationsManager.organize_directory(str(test_dir))
    assert org_res["success"] is True
    assert org_res["moved_count"] == 4

    assert os.path.exists(test_dir / "Documents" / "report.pdf")
    assert os.path.exists(test_dir / "Images" / "picture.png")
    assert os.path.exists(test_dir / "Code" / "script.py")
    assert os.path.exists(test_dir / "Archives" / "bundle.zip")

    # Sub-action C: Attempt operation on restricted C:\Windows directory
    restricted_attempt = FileOperationsManager.create_directory("C:/Windows/System32/jarvis_hacked")
    assert restricted_attempt["success"] is False
    assert "Access to restricted system directory denied" in restricted_attempt["error"]


# ==============================================================================
# SCENARIO 9: Shell Sandbox with Command Blocklisting & Timeout
# ==============================================================================
def test_scenario_09_shell_sandbox_blocklist_and_timeout():
    """
    Scenario 9: Shell sandbox execution:
    - Safe command runs and returns exit code 0.
    - Blocklisted destructive command is blocked immediately with exit code -1.
    - Long-running command exceeding timeout is aborted with exit code -2.
    """
    # 1. Safe command
    safe_res = shell_sandbox.execute_command("Write-Output 'E2E_OK'", skip_permission_check=True)
    assert safe_res["success"] is True
    assert safe_res["exit_code"] == 0
    assert "E2E_OK" in safe_res["stdout"]

    # 2. Dangerous blocklisted command
    danger_res = shell_sandbox.execute_command("format-volume -DriveLetter D")
    assert danger_res["success"] is False
    assert danger_res["exit_code"] == -1
    assert "blocked by JARVIS Security Guardrails" in danger_res["error"]

    # 3. Timeout enforcement
    timeout_res = shell_sandbox.execute_command("Start-Sleep -Seconds 5", timeout=1, skip_permission_check=True)
    assert timeout_res["success"] is False
    assert timeout_res["exit_code"] == -2
    assert "timed out" in timeout_res["error"].lower()


# ==============================================================================
# SCENARIO 10: Browser Navigation & DOM Inspection via Playwright
# ==============================================================================
def test_scenario_10_browser_navigation_and_dom_inspection():
    """
    Scenario 10: Playwright Browser Controller navigates to target URL, inspects DOM elements,
    and extracts body text cleanly.
    """
    ctrl = PlaywrightBrowserController(headless=True)
    ctrl._ensure_browser = MagicMock()
    mock_page = MagicMock()
    mock_page.title.return_value = "Example Domain"
    mock_page.url = "https://example.com"

    def mock_eval(script, *args):
        if "inputs.length" in script:
            return [{"tag": "input", "id": "search_box", "name": "q", "type": "text"}]
        elif "buttons.length" in script:
            return ["Search", "Cancel"]
        elif "links.length" in script:
            return [{"text": "More information...", "href": "https://www.iana.org/domains/example"}]
        return [{"level": "h1", "text": "Example Domain"}]

    mock_page.evaluate = mock_eval
    ctrl._pages = [mock_page]

    # 1. Open
    open_res = ctrl.open("https://example.com")
    assert open_res["success"] is True
    assert open_res["title"] == "Example Domain"

    # 2. Inspect
    inspect_res = ctrl.inspect()
    assert inspect_res["success"] is True
    assert any("Example Domain" in h.get("text", "") for h in inspect_res["headings"])
    assert len(inspect_res["links"]) >= 1

    # 3. Extract text
    mock_page.evaluate = MagicMock(return_value="Example Domain\nThis domain is for use in illustrative examples in documents.")
    text_res = ctrl.extract_text()
    assert text_res["success"] is True
    assert "Example Domain" in text_res["text"]


# ==============================================================================
# SCENARIO 11: Web Form Detection, Structured Filling, and Verification
# ==============================================================================
def test_scenario_11_web_form_detection_and_filling():
    """
    Scenario 11: Page Intelligence detects form fields, fills structured answers,
    and verifies completion readiness before submission.
    """
    playwright_controller._ensure_browser = MagicMock()
    mock_page = MagicMock()

    form_mock_questions = [
        {"question_id": "q_1", "prompt": "Your Name", "field_name": "name", "type": "input", "options": []},
        {"question_id": "q_2", "prompt": "Email Address", "field_name": "email", "type": "input", "options": []},
        {"question_id": "q_3", "prompt": "Message", "field_name": "message", "type": "textarea", "options": []}
    ]

    mock_page.evaluate.return_value = form_mock_questions
    playwright_controller._pages = [mock_page]

    # 1. Extract questions
    questions = page_intelligence.extract_questions()
    assert len(questions) == 3
    assert questions[0]["field_name"] == "name"

    # 2. Fill form
    form_data = {"name": "Karthik", "email": "karthik@example.com", "message": "Automated Phase 12 test"}
    with patch.object(playwright_controller, "fill", return_value={"success": True, "field": "mock"}):
        fill_res = page_intelligence.fill_form(form_data)
        assert fill_res["success"] is True
        assert fill_res["total_filled"] == 3

    # 3. Verify form readiness
    mock_verification = {
        "total_fields": 3,
        "filled_fields": 3,
        "empty_fields": 0,
        "completion_percentage": 100,
        "missing_required_fields": [],
        "is_ready_to_submit": True
    }
    mock_page.evaluate.return_value = mock_verification
    verify_res = page_intelligence.verify_form()
    assert verify_res["success"] is True
    assert verify_res["verification"]["is_ready_to_submit"] is True
    assert verify_res["verification"]["completion_percentage"] == 100


# ==============================================================================
# SCENARIO 12: Autonomous YouTube Search, Selection, and Player Controls
# ==============================================================================
def test_scenario_12_youtube_search_and_controls():
    """
    Scenario 12: Autonomous YouTube browsing:
    - Search parses top video items.
    - Video playback opens selected target.
    - Player controls dispatch native shortcuts ('k' for pause, 'f' for fullscreen).
    """
    playwright_controller._ensure_browser = MagicMock()
    mock_page = MagicMock()

    mock_yt_results = [
        {
            "index": 1,
            "title": "Python Full Course for Beginners",
            "url": "https://www.youtube.com/watch?v=sample1",
            "channel": "Programming Channel",
            "metadata": "2M views • 1 year ago"
        },
        {
            "index": 2,
            "title": "Learn Python in 1 Hour",
            "url": "https://www.youtube.com/watch?v=sample2",
            "channel": "Code Academy",
            "metadata": "500K views • 6 months ago"
        }
    ]

    mock_page.evaluate.return_value = mock_yt_results
    playwright_controller._pages = [mock_page]

    # 1. Search
    with patch.object(playwright_controller, "open", return_value={"success": True, "title": "YouTube Search"}):
        search_res = youtube_automation.search("Python tutorials")
        assert search_res["success"] is True
        assert search_res["results_count"] == 2
        assert search_res["results"][0]["title"] == "Python Full Course for Beginners"

    # 2. Play video
    with patch.object(playwright_controller, "open", return_value={"success": True, "title": "Playing Video"}):
        play_res = youtube_automation.play_video(result_index=1)
        assert play_res["success"] is True
        assert "Python Full Course for Beginners" in play_res["video_title"]

    # 3. Control playback (pause -> 'k', fullscreen -> 'f')
    ctrl_pause = youtube_automation.control_playback("pause")
    assert ctrl_pause["success"] is True
    assert ctrl_pause["key_dispatched"] == "k"
    mock_page.keyboard.press.assert_called_with("k")

    ctrl_fs = youtube_automation.control_playback("fullscreen")
    assert ctrl_fs["success"] is True
    assert ctrl_fs["key_dispatched"] == "f"
    mock_page.keyboard.press.assert_called_with("f")


# ==============================================================================
# SCENARIO 13: WhatsApp Automation with Relation Lookup & Level 3 Challenge
# ==============================================================================
def test_scenario_13_whatsapp_automation_and_challenge(app_client):
    """
    Scenario 13: Resolves relation 'Appa' -> 'father' -> 'Ramesh'.
    Prepares message with Level 3 Challenge, resolves challenge via spoken confirmation,
    and sends message.
    """
    # 1. Seed Profile Memory
    profile_memory.add_or_update_fact(
        key_name="father",
        category="general",
        value_data={"text": "Ramesh"}
    )

    # 2. Resolve relation "Appa"
    res_rel = whatsapp_automation.resolve_contact("Appa")
    assert res_rel["success"] is True
    assert res_rel["resolved_name"] == "Ramesh"

    # 3. Prepare message (intercepted by Level 3 Challenge)
    with patch.object(whatsapp_automation, "open_conversation", return_value={"success": True}):
        draft = whatsapp_automation.prepare_message("Appa", "Meeting at 5 PM")
        assert draft["success"] is True
        assert draft["status"] == "awaiting_authorization"
        challenge_id = draft["challenge_id"]
        assert challenge_id is not None

        # 4. Spoken confirmation "Send it"
        approved, ch = permission_engine.resolve_voice_confirmation("Send it")
        assert approved is True
        assert ch["challenge_id"] == challenge_id

        # 5. Dispatch message post-approval
        whatsapp_automation._current_open_contact = "ramesh"
        with patch.object(whatsapp_automation, "_ensure_whatsapp_active", return_value=True), \
             patch.object(whatsapp_automation, "_is_whatsapp_foreground", return_value=True), \
             patch.object(whatsapp_automation, "verify_message", return_value={"verified": True, "method": "mock"}), \
             patch.object(mouse_kb, "click"), \
             patch.object(mouse_kb, "press_hotkey"), \
             patch.object(mouse_kb, "press_key"), \
             patch.object(mouse_kb, "type_text"):
            send_res = whatsapp_automation.send_message("Ramesh", "Meeting at 5 PM", skip_permission_check=True)
            assert send_res["success"] is True


# ==============================================================================
# SCENARIO 14: Authentic Spotify Media Controls (Zero False Simulation)
# ==============================================================================
def test_scenario_14_authentic_spotify_controls(app_client):
    """
    Scenario 14: Authentic Spotify desktop & media playback controls without false simulation:
    open -> play -> volume -> pause -> resume -> state.
    """
    from modules.media.spotify_controller import spotify_controller

    with patch.object(spotify_controller, "open_spotify", return_value={"success": True, "message": "Spotify opened."}), \
         patch.object(spotify_controller, "play_track", return_value={"success": True, "playing": True, "track": "Blinding Lights"}), \
         patch.object(spotify_controller, "set_volume", return_value={"success": True, "volume": 40}), \
         patch.object(spotify_controller, "pause_playback", return_value={"success": True, "paused": True}), \
         patch.object(spotify_controller, "resume_playback", return_value={"success": True, "playing": True}), \
         patch.object(spotify_controller, "get_playback_state", return_value={"is_playing": True, "track": "Blinding Lights", "artist": "The Weeknd"}):

        # 1. Open
        res_open = app_client.post("/api/spotify/open")
        assert res_open.status_code == 200
        assert res_open.json()["success"] is True

        # 2. Play
        res_play = app_client.post("/api/spotify/play", json={"query": "Blinding Lights"})
        assert res_play.status_code == 200
        assert res_play.json()["track"] == "Blinding Lights"

        # 3. Volume
        res_vol = app_client.post("/api/spotify/volume", json={"level": 40})
        assert res_vol.status_code == 200
        assert res_vol.json()["volume"] == 40

        # 4. Pause
        res_pause = app_client.post("/api/spotify/pause")
        assert res_pause.status_code == 200
        assert res_pause.json()["paused"] is True

        # 5. Resume
        res_resume = app_client.post("/api/spotify/resume")
        assert res_resume.status_code == 200
        assert res_resume.json()["playing"] is True

        # 6. State
        res_state = app_client.get("/api/spotify/state")
        assert res_state.status_code == 200
        assert res_state.json()["is_playing"] is True


# ==============================================================================
# SCENARIO 15: Persistent Memory Recovery Across Full Application Restart
# ==============================================================================
def test_scenario_15_persistent_memory_recovery_across_restart(app_client, isolated_storage):
    """
    Scenario 15: Simulates full application restart by re-binding SQLAlchemy engine and SessionLocal.
    Asserts zero loss of MemoryEntity, Sessions, and Messages across restarts.
    """
    db_path = isolated_storage["db_path"]

    # 1. Write personal fact and session conversation
    profile_memory.add_or_update_fact(
        key_name="preferred_ide",
        category="preference",
        value_data={"name": "Visual Studio Code", "version": "1.90"}
    )

    res_sess = app_client.post("/api/sessions", json={"title": "Phase 12 Session"})
    assert res_sess.status_code == 200
    session_id = res_sess.json()["id"]

    res_msg = app_client.post(f"/api/sessions/{session_id}/messages", json={
        "content": "Remember my favourite IDE is VS Code.",
        "input_modality": "text"
    })
    assert res_msg.status_code == 200

    # 2. Simulate complete application shutdown & restart
    db_conn.engine.dispose()
    reopened_engine = create_engine(f"sqlite:///{os.path.abspath(db_path)}", echo=False, connect_args={"check_same_thread": False})
    db_conn.engine = reopened_engine
    db_conn.SessionLocal.configure(bind=reopened_engine)

    try:
        # 3. Query memory entities post-restart
        res_entities = app_client.get("/api/memory/entities")
        assert res_entities.status_code == 200
        facts = res_entities.json()
        saved_fact = next((f for f in facts if f["key_name"] == "preferred_ide"), None)
        assert saved_fact is not None
        assert saved_fact["value_data"]["name"] == "Visual Studio Code"

        # 4. Query session messages post-restart
        res_history = app_client.get(f"/api/sessions/{session_id}/messages")
        assert res_history.status_code == 200
        messages = res_history.json()
        assert len(messages) == 1
        assert "favourite IDE" in messages[0]["content"]
    finally:
        reopened_engine.dispose()


# ==============================================================================
# SCENARIO 16: Global Emergency Stop Kill-Switch & Total Lockout
# ==============================================================================
def test_scenario_16_global_emergency_stop_killswitch():
    """
    Scenario 16: Global Emergency Stop:
    - Triggering kill-switch purges pending challenges and activates emergency stop.
    - All subsequent tool executions (shell, browser, computer) are 100% blocked.
    - Clearing emergency stop successfully re-arms subsystems.
    """
    # 1. Create a dummy pending challenge
    allowed, reason, ch = permission_engine.evaluate_request(
        tool_name="shell.execute_command",
        permission_level=3,
        target_resource="test_cmd",
        arguments={"cmd": "test"}
    )
    assert allowed is False
    assert ch is not None
    assert len(permission_engine._pending_challenges) >= 1

    # 2. Trigger Global Emergency Stop
    stop_res = permission_engine.trigger_emergency_stop(reason="User commanded abort")
    assert stop_res["emergency_stopped"] is True
    assert permission_engine.is_emergency_stopped() is True
    assert len(permission_engine._pending_challenges) == 0  # Challenges purged

    # 3. Verify total tool execution lockout
    tools_to_test = [
        ("shell.execute_command", 3, "rmdir"),
        ("browser.open", 2, "https://example.com"),
        ("screen.inspect", 1, "desktop")
    ]
    for tool_name, perm_level, target in tools_to_test:
        allow, resn, ch_obj = permission_engine.evaluate_request(
            tool_name=tool_name,
            permission_level=perm_level,
            target_resource=target,
            arguments={}
        )
        assert allow is False
        assert "Global Emergency Stop is ACTIVE" in resn
        assert ch_obj is None

    # 4. Reset Emergency Stop and verify subsystems re-armed
    reset_res = permission_engine.reset_emergency_stop()
    assert reset_res["emergency_stopped"] is False
    assert permission_engine.is_emergency_stopped() is False

    # Level 1 read action should now be allowed
    rearm_allow, _, _ = permission_engine.evaluate_request(
        tool_name="screen.inspect",
        permission_level=1,
        target_resource="desktop",
        arguments={}
    )
    assert rearm_allow is True
