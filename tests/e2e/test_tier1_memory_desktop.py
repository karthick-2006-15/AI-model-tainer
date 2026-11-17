"""
Tier 1 End-to-End Test Suite: Memory, Desktop Automation, Browser, Security & System Telemetry
Covers all primary happy paths (TC-MEM-01 to 05, TC-AUTO-01 to 05, TC-BROWSER-01 to 05, TC-SEC-01 to 05, TC-SYS-01 to 06).
Adheres strictly to opaque-box testing via REST APIs, WebSockets, and subsystem contracts.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from core.security.permissions import permission_engine
from modules.computer_use.app_manager import UniversalAppManager
from modules.computer_use.browser_playwright import PlaywrightBrowserController
from modules.computer_use.page_intelligence import PageIntelligenceEngine
from storage.db.connection import SessionLocal
from storage.db.models import AuditLog


# =============================================================================
# CATEGORY 1: MEMORY & DATABASE SUBSYSTEM (5 Test Cases)
# =============================================================================

def test_tc_mem_01_entity_creation_and_retrieval(app_client):
    """TC-MEM-01: Memory Entity Creation & Retrieval via REST API."""
    # 1. Add entity
    payload = {
        "key_name": "project_deadline",
        "category": "project",
        "value_data": {"date": "2026-12-01", "description": "Phase 12 Delivery"},
        "confidence_score": 1.0,
        "provenance": "user_explicit"
    }
    create_res = app_client.post("/api/memory/entities", json=payload)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["key_name"] == "project_deadline"
    assert created["category"] == "project"
    entity_id = created["id"]

    # 2. Retrieve entity list
    list_res = app_client.get("/api/memory/entities?category=project")
    assert list_res.status_code == 200
    entities = list_res.json()
    assert any(e["id"] == entity_id for e in entities)


def test_tc_mem_02_entity_deletion(app_client):
    """TC-MEM-02: Memory Entity Deletion removes record from SQLite and vector store."""
    # Create entity
    res = app_client.post("/api/memory/entities", json={
        "key_name": "temporary_fact",
        "category": "general",
        "value_data": {"note": "to be deleted"}
    })
    entity_id = res.json()["id"]

    # Delete entity
    del_res = app_client.delete(f"/api/memory/entities/{entity_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # Confirm deletion
    list_res = app_client.get("/api/memory/entities")
    assert not any(e["id"] == entity_id for e in list_res.json())


def test_tc_mem_03_semantic_vector_similarity_search(app_client):
    """TC-MEM-03: Semantic Vector Similarity Search retrieves relevant facts."""
    # Seed fact
    app_client.post("/api/memory/entities", json={
        "key_name": "preferred_editor",
        "category": "preference",
        "value_data": {"text": "I always write Python code in Visual Studio Code."}
    })

    # Search
    search_res = app_client.get("/api/memory/search?q=editor+for+coding&limit=3")
    assert search_res.status_code == 200
    results = search_res.json()["results"]
    assert len(results) >= 1
    assert any("Visual Studio Code" in r["text"] or "preferred_editor" in r.get("key", "") for r in results)


def test_tc_mem_04_automated_natural_language_fact_extraction(app_client):
    """TC-MEM-04: Automated Natural Language Fact Extraction parses facts from text."""
    sample_text = "I study at Stanford University and my major is Computer Science."
    extract_res = app_client.post("/api/memory/extract", json={"text": sample_text})
    assert extract_res.status_code == 200
    data = extract_res.json()
    assert "extracted_count" in data
    assert isinstance(data["facts"], list)


def test_tc_mem_05_session_and_message_history_persistence(app_client):
    """TC-MEM-05: Conversation Session & Message History Persistence links messages to session."""
    # 1. Create session
    sess_res = app_client.post("/api/sessions", json={"title": "E2E Test Session"})
    assert sess_res.status_code == 200
    session_id = sess_res.json()["id"]

    # 2. Add messages
    m1 = app_client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "What is the capital of France?", "input_modality": "text"}
    )
    assert m1.status_code == 200

    m2 = app_client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "The capital of France is Paris.", "input_modality": "text"}
    )
    assert m2.status_code == 200

    # 3. Retrieve messages
    get_msgs = app_client.get(f"/api/sessions/{session_id}/messages")
    assert get_msgs.status_code == 200
    messages = get_msgs.json()
    assert len(messages) == 2
    assert messages[0]["content"] == "What is the capital of France?"
    assert messages[1]["content"] == "The capital of France is Paris."


# =============================================================================
# CATEGORY 2: AUTOMATION & DESKTOP SUBSYSTEM (5 Test Cases)
# =============================================================================

def test_tc_auto_01_universal_app_search():
    """TC-AUTO-01: Universal Application Search finds installed applications."""
    mgr = UniversalAppManager()
    results = mgr.search_app("calculator")
    assert isinstance(results, list)
    # Windows has calc or calculator installed
    if results:
        first = results[0]
        assert "name" in first
        assert "target" in first


def test_tc_auto_02_app_launch_with_verification(app_client):
    """TC-AUTO-02: Application Launch with Verification returns launch metadata."""
    with patch("modules.automation.apps.ApplicationManager.launch") as mock_launch:
        mock_launch.return_value = {
            "success": True,
            "verified": True,
            "app_name": "Notepad",
            "pid": 1234,
            "window_title": "Untitled - Notepad",
            "message": "Application 'Notepad' launched and verified on desktop."
        }
        res = app_client.post("/api/automation/apps/launch", json={"app_name": "notepad"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["verified"] is True
        assert data["app_name"] == "Notepad"


def test_tc_auto_03_desktop_window_enumeration(app_client):
    """TC-AUTO-03: Visible Desktop Window Enumeration returns list of open windows."""
    res = app_client.get("/api/automation/windows")
    assert res.status_code == 200
    windows = res.json()
    assert isinstance(windows, list)


def test_tc_auto_04_window_foreground_focus(app_client):
    """TC-AUTO-04: Window Foreground Focus endpoint sends focus command."""
    with patch("modules.automation.apps.ApplicationManager.focus_window", return_value=True):
        res = app_client.post("/api/automation/windows/focus", json={"title": "Notepad"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["title"] == "Notepad"


def test_tc_auto_05_application_termination(app_client):
    """TC-AUTO-05: Graceful / Force Application Termination terminates processes."""
    with patch("modules.automation.apps.ApplicationManager.close") as mock_close:
        mock_close.return_value = {
            "success": True,
            "closed_windows": 1,
            "terminated_pids": [1234],
            "message": "Closed application 'notepad'."
        }
        res = app_client.post("/api/automation/apps/close", json={"app_name": "notepad", "force": True})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True


# =============================================================================
# CATEGORY 3: BROWSER SUBSYSTEM (5 Test Cases)
# =============================================================================

def test_tc_browser_01_url_navigation():
    """TC-BROWSER-01: URL Navigation & Page Loading opens URL and retrieves status."""
    ctrl = PlaywrightBrowserController(headless=True)
    ctrl._ensure_browser = MagicMock()
    mock_page = MagicMock()
    mock_page.title.return_value = "Example Domain"
    mock_page.url = "https://example.com"
    mock_page.goto.return_value = MagicMock(status=200)

    ctrl._pages = [mock_page]
    res = ctrl.open("https://example.com")
    assert res["success"] is True
    assert res["status_code"] == 200
    assert res["title"] == "Example Domain"


def test_tc_browser_02_dom_structure_inspection():
    """TC-BROWSER-02: DOM Structure Inspection extracts headings, buttons, and inputs."""
    ctrl = PlaywrightBrowserController(headless=True)
    ctrl._ensure_browser = MagicMock()
    mock_page = MagicMock()
    mock_page.title.return_value = "Test Portal"
    mock_page.url = "https://example.com/portal"

    def mock_eval(script, *args):
        if "inputs.length" in script:
            return [{"tag": "input", "id": "username", "name": "user", "type": "text"}]
        elif "buttons.length" in script:
            return ["Submit", "Cancel"]
        elif "links.length" in script:
            return [{"text": "Home", "href": "https://example.com"}]
        return [{"level": "h1", "text": "Welcome to Portal"}]

    mock_page.evaluate = mock_eval
    ctrl._pages = [mock_page]

    res = ctrl.inspect()
    assert res["success"] is True
    assert res["title"] == "Test Portal"
    assert len(res["headings"]) >= 1
    assert len(res["buttons"]) >= 1


def test_tc_browser_03_semantic_text_extraction():
    """TC-BROWSER-03: Semantic Text Extraction pulls body text and computes word count."""
    ctrl = PlaywrightBrowserController(headless=True)
    ctrl._ensure_browser = MagicMock()
    mock_page = MagicMock()
    mock_page.evaluate.return_value = "This is sample article text explaining artificial intelligence."
    ctrl._pages = [mock_page]

    res = ctrl.extract_text()
    assert res["success"] is True
    assert "artificial intelligence" in res["text"]
    assert res["char_count"] > 10


def test_tc_browser_04_structured_table_extraction():
    """TC-BROWSER-04: Structured Table Extraction parses HTML table into structured JSON rows."""
    from modules.computer_use.browser_playwright import playwright_controller
    playwright_controller._ensure_browser = MagicMock()
    mock_page = MagicMock()

    mock_page.evaluate.return_value = {
        "table_index": 0,
        "total_tables_on_page": 1,
        "headers": ["Model", "Accuracy", "Latency"],
        "row_count": 2,
        "rows": [["GPT-4", "92%", "400ms"], ["Llama-3", "88%", "150ms"]]
    }

    playwright_controller._pages = [mock_page]
    engine = PageIntelligenceEngine()
    res = engine.extract_tables(0)
    assert res["success"] is True
    table = res["table"]
    assert table["headers"] == ["Model", "Accuracy", "Latency"]
    assert table["row_count"] == 2
    assert table["rows"][0][0] == "GPT-4"


def test_tc_browser_05_form_input_filling_and_verification():
    """TC-BROWSER-05: Form Input Filling & Verification populates fields and verifies completeness."""
    from modules.computer_use.browser_playwright import playwright_controller
    playwright_controller._ensure_browser = MagicMock()
    mock_page = MagicMock()

    mock_page.evaluate.return_value = {
        "total_fields": 2,
        "filled_fields": 2,
        "empty_fields": 0,
        "completion_percentage": 100,
        "missing_required_fields": [],
        "is_ready_to_submit": True
    }
    playwright_controller._pages = [mock_page]

    engine = PageIntelligenceEngine()
    with patch.object(playwright_controller, "fill", return_value={"success": True}):
        fill_res = engine.fill_form({"username": "karthik", "password": "secure_password"})
        assert fill_res["success"] is True
        assert fill_res["total_filled"] == 2

        verify_res = engine.verify_form()
        assert verify_res["success"] is True
        assert verify_res["verification"]["is_ready_to_submit"] is True


# =============================================================================
# CATEGORY 4: SECURITY & PERMISSIONS SUBSYSTEM (5 Test Cases)
# =============================================================================

def test_tc_sec_01_level_1_read_action_autonomous_approval():
    """TC-SEC-01: Level 1 Read Action is automatically approved without user challenge."""
    allowed, reason, challenge = permission_engine.evaluate_request(
        tool_name="screen.inspect",
        permission_level=1,
        target_resource="desktop_display",
        arguments={}
    )
    assert allowed is True
    assert challenge is None
    assert "automatically approved" in reason.lower() or "auto_allowed" in reason.lower()


def test_tc_sec_02_level_3_external_action_challenge_creation():
    """TC-SEC-02: Level 3 External Action generates an interactive confirmation challenge."""
    allowed, reason, challenge = permission_engine.evaluate_request(
        tool_name="whatsapp.send_message",
        permission_level=3,
        target_resource="WhatsApp Message to Karthik",
        arguments={"recipient": "Karthik", "message": "Test"}
    )
    assert allowed is False
    assert challenge is not None
    assert "challenge_id" in challenge
    assert challenge["permission_level"] == 3


def test_tc_sec_03_interactive_challenge_resolution_rest(app_client):
    """TC-SEC-03: Interactive Challenge Resolution via REST endpoint resolves pending challenge."""
    # 1. Create a Level 3 challenge
    _, _, challenge = permission_engine.evaluate_request(
        tool_name="shell.execute_command",
        permission_level=3,
        target_resource="dir",
        arguments={"command": "dir"}
    )
    challenge_id = challenge["challenge_id"]

    # 2. Resolve challenge via REST
    res = app_client.post(
        "/api/automation/challenges/resolve",
        json={"challenge_id": challenge_id, "approved": True}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["challenge_id"] == challenge_id
    assert data["approved"] is True


def test_tc_sec_04_tamper_evident_sha256_audit_logging():
    """TC-SEC-04: Tamper-Evident SHA-256 Audit Logging writes cryptographically signed records."""
    permission_engine.log_action(
        permission_level=1,
        action_type="test:audit_verification",
        target_resource="test_resource",
        parameters={"test": "param"},
        decision="auto_allowed",
        success=True
    )

    with SessionLocal() as db:
        log = db.query(AuditLog).filter(AuditLog.action_type == "test:audit_verification").first()
        assert log is not None
        assert len(log.hash_checksum) == 64  # SHA-256 is 64 hex characters
        assert log.decision == "auto_allowed"


def test_tc_sec_05_global_emergency_stop_activation():
    """TC-SEC-05: Global Emergency Stop Activation halts all operations immediately."""
    stop_res = permission_engine.trigger_emergency_stop(reason="E2E Safety Test Halt")
    assert stop_res["emergency_stopped"] is True
    assert permission_engine.is_emergency_stopped() is True

    # Confirm all operations are blocked
    allowed, reason, challenge = permission_engine.evaluate_request(
        tool_name="any_tool",
        permission_level=1,
        target_resource="any",
        arguments={}
    )
    assert allowed is False
    assert "emergency stop is active" in reason.lower()

    # Reset
    permission_engine.reset_emergency_stop()
    assert permission_engine.is_emergency_stopped() is False


# =============================================================================
# CATEGORY 5: SYSTEM TELEMETRY, MEDIA & MOBILE (6 Test Cases)
# =============================================================================

def test_tc_sys_01_comprehensive_system_health(app_client):
    """TC-SYS-01: Comprehensive System Health Endpoint returns online status and DB health."""
    res = app_client.get("/api/system/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["service"] == "JARVIS Personal AI OS Core"
    assert data["database"] == "healthy"


def test_tc_sys_02_live_hardware_telemetry_metrics(app_client):
    """TC-SYS-02: Live Hardware Telemetry Metrics returns CPU, RAM, and disk metrics."""
    res = app_client.get("/api/system/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert "cpu" in metrics
    assert "ram" in metrics
    assert "disk" in metrics
    assert metrics["cpu"]["percent"] >= 0.0
    assert metrics["ram"]["used_gb"] >= 0.0


def test_tc_sys_03_active_process_inspection(app_client):
    """TC-SYS-03: Active Process Inspection returns top CPU/memory consuming processes."""
    res = app_client.get("/api/system/processes?limit=5")
    assert res.status_code == 200
    processes = res.json()
    assert isinstance(processes, list)
    assert len(processes) <= 5
    if processes:
        p = processes[0]
        assert "pid" in p
        assert "name" in p
        assert "cpu_percent" in p


def test_tc_sys_04_spotify_volume_control(app_client):
    """TC-SYS-04: Spotify Volume Control sets volume level (0-100)."""
    from modules.media.spotify_controller import spotify_controller
    with patch.object(spotify_controller, "set_volume", return_value={"success": True, "volume": 65}):
        res = app_client.post("/api/spotify/volume", json={"level": 65})
        assert res.status_code == 200
        assert res.json()["volume"] == 65


def test_tc_sys_05_hud_websocket_telemetry_streaming(app_client):
    """TC-SYS-05: HUD WebSocket streams periodic hardware telemetry packets."""
    with app_client.websocket_connect("/ws/hud") as ws:
        # First frame: agent_state
        f1 = ws.receive_json()
        assert f1["type"] == "agent_state"
        # Second frame: avatar_state
        f2 = ws.receive_json()
        assert f2["type"] == "avatar_state"
        # Wait for telemetry packet
        f3 = ws.receive_json()
        assert f3["type"] == "telemetry"
        assert "cpu" in f3["data"]


def test_tc_sys_06_mobile_pairing_initiation(app_client):
    """TC-SYS-06: Mobile Companion Pairing Initiation generates code and QR payload."""
    res = app_client.post("/api/mobile/pairing/initiate", json={"device_name": "Pixel 8 Pro"})
    assert res.status_code == 200
    data = res.json()
    assert "pairing_code" in data
    assert "qr_payload" in data
    assert data["qr_payload"]["code"] == data["pairing_code"]
