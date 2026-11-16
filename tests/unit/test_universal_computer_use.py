"""
JARVIS-10: Universal Computer Use & Autonomous Interaction Test Suite
Verifies Playwright browser control, YouTube automation, Page intelligence,
Universal computer control tools, WhatsApp workflows, and multilingual voice routing.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from modules.computer_use.browser_playwright import PlaywrightBrowserController
from modules.computer_use.youtube import YouTubeAutomation
from modules.computer_use.page_intelligence import PageIntelligenceEngine
from modules.computer_use.mouse_kb import mouse_kb
from modules.computer_use.screen import screen_intelligence
from modules.computer_use.native_uia import native_uia
from modules.computer_use.loop import observation_loop
from modules.computer_use.whatsapp import whatsapp_automation
from modules.voice.multilingual import multilingual_engine
from core.brain.intent import intent_classifier
from core.brain.tools import tool_registry
from core.security.permissions import permission_engine


@pytest.fixture
def mock_playwright_page():
    """Provides a mocked Playwright Page object for headless unit verification."""
    mock_page = MagicMock()
    mock_page.title.return_value = "Test Document - Universal Web"
    mock_page.url = "https://example.com/test-worksheet"
    mock_page.goto.return_value = MagicMock(status=200)

    # Mock evaluate to return realistic DOM data
    def mock_eval(script, *args):
        if "wordCount" in script or "word_count" in script:
            return {
                "headings": [{"level": "h1", "text": "Science Test"}],
                "forms_count": 1,
                "inputs_count": 3,
                "buttons_count": 2,
                "tables_count": 1,
                "links_count": 4,
                "word_count": 450,
                "text_preview": "This is a comprehensive science exam covering kinematics..."
            }
        elif "completion_percentage" in script:
            return {
                "total_fields": 4,
                "filled_fields": 4,
                "empty_fields": 0,
                "completion_percentage": 100,
                "missing_required_fields": [],
                "is_ready_to_submit": True
            }
        elif "table_index" in script or "total_tables_on_page" in script:
            return {
                "table_index": 0,
                "total_tables_on_page": 1,
                "headers": ["Robot Model", "Payload (kg)", "Battery Life (hrs)"],
                "row_count": 2,
                "rows": [["Kuka KMR", "200", "8"], ["Fetch Freight", "100", "9"]]
            }
        elif "qIndex" in script or "containers" in script:
            return [
                {"question_id": "q_1", "prompt": "What is Newton's Second Law?", "field_name": "q1_answer", "type": "text", "options": [], "current_value": ""},
                {"question_id": "q_2", "prompt": "Select primary force:", "field_name": "q2_force", "type": "single_choice", "options": ["Gravity", "Friction", "Electromagnetism"], "current_value": ""}
            ]
        elif "ytd-video-renderer" in script:
            return [
                {"index": 1, "title": "Java DSA Complete Course 2026", "url": "https://www.youtube.com/watch?v=123", "channel": "Tech Academy", "metadata": "1.2M views • 2 weeks ago"},
                {"index": 2, "title": "Data Structures in Java in 10 Hours", "url": "https://www.youtube.com/watch?v=456", "channel": "Code Pro", "metadata": "500K views • 1 month ago"},
                {"index": 3, "title": "Advanced Binary Trees & Graphs", "url": "https://www.youtube.com/watch?v=789", "channel": "Algo Daily", "metadata": "250K views • 3 days ago"}
            ]
        elif "inputs" in script and "select" in script:
            return [{"tag": "input", "id": "username", "name": "username", "type": "text", "placeholder": "Enter Name", "value": ""}]
        elif "buttons" in script:
            return ["Submit Answers", "Next Page"]
        elif "links" in script:
            return [{"text": "Home", "href": "https://example.com"}]
        elif "headers" in script or "headings" in script:
            return [{"level": "h1", "text": "Physics Worksheet 1"}]
        return []

    mock_page.evaluate.side_effect = mock_eval
    return mock_page


def test_playwright_browser_controller_lifecycle(mock_playwright_page):
    """Verifies Playwright browser controller navigation, DOM inspection, and tab tracking."""
    controller = PlaywrightBrowserController(headless=True)
    controller._pages = [mock_playwright_page]
    controller._active_page_index = 0
    controller._ensure_browser = MagicMock()

    # 1. Navigation
    res_open = controller.open("https://example.com/test-worksheet")
    assert res_open["success"] is True
    assert res_open["title"] == "Test Document - Universal Web"

    # 2. Inspect
    inspect_res = controller.inspect()
    assert inspect_res["success"] is True
    assert len(inspect_res["inputs"]) >= 1
    assert "Submit Answers" in inspect_res["buttons"]

    # 3. Tabs
    tabs = controller.get_tabs()
    assert len(tabs) == 1
    assert tabs[0]["is_active"] is True


def test_youtube_automation_search_and_playback(mock_playwright_page):
    """Verifies YouTube search extraction, video picking, and player shortcut controls."""
    from modules.computer_use.browser_playwright import playwright_controller
    playwright_controller._pages = [mock_playwright_page]
    playwright_controller._active_page_index = 0
    playwright_controller._ensure_browser = MagicMock()

    yt = YouTubeAutomation()
    with patch.object(playwright_controller, "open", return_value={"success": True}):
        # 1. Search
        search_res = yt.search("Java DSA tutorials")
        assert search_res["success"] is True
        assert search_res["results_count"] == 3
        assert "Java DSA Complete Course" in search_res["results"][0]["title"]
        assert search_res["results"][2]["index"] == 3

        # 2. Play 3rd result
        play_res = yt.play_video(result_index=3)
        assert play_res["success"] is True
        assert "Advanced Binary Trees" in play_res["video_title"]

        # 3. Playback Controls
        ctrl_res = yt.control_playback("pause")
        assert ctrl_res["success"] is True
        assert ctrl_res["action"] == "pause"

        vol_res = yt.control_playback("volume_up")
        assert vol_res["success"] is True
        assert vol_res["key_dispatched"] == "ArrowUp"


def test_page_intelligence_analysis_and_forms(mock_playwright_page):
    """Verifies deep page analysis, table parsing, question extraction, and form verification."""
    from modules.computer_use.browser_playwright import playwright_controller
    playwright_controller._pages = [mock_playwright_page]
    playwright_controller._active_page_index = 0
    playwright_controller._ensure_browser = MagicMock()

    engine = PageIntelligenceEngine()
    with patch.object(playwright_controller, "fill", return_value={"success": True}):
        # 1. Analyze Page
        analysis = engine.analyze_page()
        assert analysis["success"] is True
        assert analysis["structure"]["word_count"] == 450
        assert analysis["structure"]["forms_count"] == 1

        # 2. Extract Questions
        questions = engine.extract_questions()
        assert len(questions) == 2
        assert questions[0]["prompt"] == "What is Newton's Second Law?"
        assert questions[1]["type"] == "single_choice"

        # 3. Extract Tables
        tbl_res = engine.extract_tables(0)
        assert tbl_res["success"] is True
        assert tbl_res["table"]["headers"] == ["Robot Model", "Payload (kg)", "Battery Life (hrs)"]
        assert len(tbl_res["table"]["rows"]) == 2

        # 4. Fill Form
        fill_res = engine.fill_form({"q1_answer": "F = m * a", "q2_force": "Gravity"})
        assert fill_res["success"] is True
        assert fill_res["total_filled"] == 2

        # 5. Verify Form
        verify_res = engine.verify_form()
        assert verify_res["success"] is True
        assert verify_res["verification"]["completion_percentage"] == 100
        assert verify_res["verification"]["is_ready_to_submit"] is True


def test_universal_computer_control_primitives():
    """Verifies mouse, keyboard, and screen coordinates safety clamping and execution."""
    # 1. Mouse bounds clamping
    safe_x, safe_y = mouse_kb._validate_coords(99999, -500)
    assert 0 <= safe_x < mouse_kb.screen_width
    assert safe_y == 0

    # 2. Key press
    with patch("pyautogui.press") as mock_press:
        res = mouse_kb.press_key("enter")
        assert res["success"] is True
        mock_press.assert_called_once_with("enter")

    # 3. Screen capture
    cap = screen_intelligence.capture_screen()
    assert cap["success"] is True
    assert os.path.exists(cap["file_path"])
    assert cap["width"] > 0 and cap["height"] > 0

    # Clean up test file
    try:
        os.remove(cap["file_path"])
    except OSError:
        pass


def test_whatsapp_11_step_pipeline():
    """Verifies contact resolution, ambiguous disambiguation, and Level 3 authorization guard."""
    # 1. Resolve contact
    contact = whatsapp_automation.resolve_contact("father")
    assert contact["success"] is True
    assert contact["ambiguous"] is False

    # 2. Draft message with Level 3 challenge
    draft = whatsapp_automation.prepare_message("father", "Hi Appa, reach home safe.")
    assert draft["success"] is True
    assert draft["requires_confirmation"] is True
    assert draft["permission_level"] == 3
    assert draft["challenge_id"].startswith("ch_")

    # 3. Unauthorized send is blocked
    block_res = whatsapp_automation.send_message("father", "Hi Appa", skip_permission_check=False)
    assert block_res["success"] is False
    assert block_res.get("awaiting_authorization") is True or "authorization" in block_res.get("error", "").lower()


def test_multilingual_voice_intent_routing():
    """Verifies natural English, Tamil, Tanglish, and Hindi code-switching routing."""
    # 1. Tanglish YouTube search
    t1, l1 = multilingual_engine.normalize_code_switching("youtube la Java tutorial search pannu")
    assert "youtube" in t1.lower() and "java tutorial" in t1.lower()
    intent1 = intent_classifier.classify("open youtube and search for Java tutorial")
    assert intent1.target_tool == "youtube.search"
    assert "java tutorial" in intent1.extracted_params["query"].lower()

    # 2. English video selection
    intent2 = intent_classifier.classify("play the first video")
    assert intent2.target_tool == "youtube.play_video"
    assert intent2.extracted_params["result_index"] == 1

    # 3. YouTube control
    intent3 = intent_classifier.classify("pause the video")
    assert intent3.target_tool == "youtube.control_playback"
    assert intent3.extracted_params["action"] == "pause"

    # 4. Universal Page Analysis
    intent4 = intent_classifier.classify("analyze this page and follow my instructions")
    assert intent4.target_tool == "page.analyze"

    # 5. Tanglish WhatsApp message
    t5, l5 = multilingual_engine.normalize_code_switching("en father ku Hi message send pannu")
    assert "send hi to father" in t5.lower()
    intent5 = intent_classifier.classify("send Hi to father")
    assert intent5.target_tool == "whatsapp.prepare_message"


def test_tool_registry_universal_coverage():
    """Verifies that all 10 computer.*, 8 browser.*, 6 page.*, and youtube.* tools are registered."""
    expected_tools = [
        # computer.*
        "computer.capture_screen",
        "computer.inspect_active_window",
        "computer.inspect_ui",
        "computer.find_element",
        "computer.click",
        "computer.type",
        "computer.press_key",
        "computer.scroll",
        "computer.switch_window",
        "computer.verify_action",
        # browser.*
        "browser.open",
        "browser.inspect",
        "browser.search",
        "browser.click",
        "browser.fill",
        "browser.extract_text",
        "browser.get_tabs",
        "browser.screenshot",
        # page.*
        "page.analyze",
        "page.find_element",
        "page.extract_questions",
        "page.extract_tables",
        "page.fill_form",
        "page.verify_form",
        # youtube.*
        "youtube.search",
        "youtube.play_video",
        "youtube.control_playback"
    ]

    for tool_name in expected_tools:
        meta = tool_registry.get_tool(tool_name)
        assert meta is not None, f"Required JARVIS-10 tool '{tool_name}' must be registered in ToolRegistry."
        assert meta.permission_level in (1, 2, 3)
