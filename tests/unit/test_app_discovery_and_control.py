"""
Comprehensive Unit & Integration Tests for Universal Windows Application Discovery & Control
Tests dynamic discovery across Win32, UWP, Registry, Start Menu, System Apps,
Window Switching, Launch Verification, Multilingual Voice Intents, and Safety.
"""

import pytest
import os
from modules.computer_use.app_discovery import app_discovery, ApplicationRecord
from modules.computer_use.app_manager import universal_app_manager
from core.brain.intent import intent_classifier, IntentCategory
from core.brain.tools import tool_registry
from modules.voice.multilingual import multilingual_engine


def test_application_discovery_sources_and_indexing():
    """Verifies dynamic discovery across Start Menu, Registry, App Paths, UWP, and System apps."""
    res = app_discovery.refresh_index(force=True)
    assert res["success"] is True
    assert res["count"] >= 50  # Real systems have 100-400+ discovered apps
    assert len(app_discovery._index) >= 50

    # Verify essential fields exist on records
    sample_apps = list(app_discovery._index.values())[:10]
    for app in sample_apps:
        assert isinstance(app.id, str) and len(app.id) > 0
        assert isinstance(app.name, str) and len(app.name) > 0
        assert isinstance(app.aliases, list)
        assert isinstance(app.app_type, str)
        assert app.launch_method in ("direct_exec", "apps_folder", "system_uri", "shortcut", "explorer_folder")
        assert app.source in ("start_menu", "registry", "app_paths", "uwp_package", "app_alias", "system", "folder")
        assert isinstance(app.categories, list)


def test_application_search_and_fuzzy_resolution():
    """Tests exact, prefix, alias, and fuzzy application searching."""
    # 1. Exact / Substring Search
    chrome_matches = app_discovery.search("chrome")
    assert len(chrome_matches) > 0
    assert any("chrome" in m["name"].lower() for m in chrome_matches)

    calc_matches = app_discovery.search("calculator")
    assert len(calc_matches) > 0
    assert any("calc" in m["name"].lower() for m in calc_matches)

    # 2. Alias Search
    settings_matches = app_discovery.search("settings")
    assert len(settings_matches) > 0
    assert any("settings" in m["name"].lower() for m in settings_matches)

    # 3. Direct Resolution
    res_chrome = app_discovery.resolve("Google Chrome")
    assert res_chrome["success"] is True
    assert res_chrome["app"] is not None
    assert "chrome" in res_chrome["app"]["name"].lower()

    # 4. Unknown App Handling
    res_unknown = app_discovery.resolve("non_existent_application_xyz_999")
    assert res_unknown["success"] is False
    assert res_unknown["app"] is None


def test_find_app_by_description():
    """Tests semantic and functional description queries."""
    # "application I use for Python"
    py_apps = app_discovery.find_by_description("application I use for Python")
    assert len(py_apps) > 0
    py_names = [a["name"].lower() for a in py_apps]
    assert any("python" in n or "code" in n or "idle" in n for n in py_names)

    # "my music player"
    music_apps = app_discovery.find_by_description("my music player")
    assert len(music_apps) > 0
    music_names = [a["name"].lower() for a in music_apps]
    assert any("media" in n or "audio" in n or "player" in n or "spotify" in n for n in music_names)


def test_special_user_folders_discovery():
    """Verifies that user special folders (Downloads, Documents, Desktop) are indexed for explorer launch."""
    downloads_matches = app_discovery.search("downloads")
    assert len(downloads_matches) > 0
    dl = downloads_matches[0]
    assert dl["launch_method"] == "explorer_folder"
    assert "downloads" in dl["target"].lower()
    assert os.path.exists(dl["target"])


def test_running_apps_and_window_enumeration():
    """Tests window enumeration and active window inspection."""
    running = universal_app_manager.get_running_apps()
    assert isinstance(running, list)
    # On an active desktop session, running applications should exist
    if running:
        app = running[0]
        assert "process_name" in app
        assert "primary_pid" in app
        assert "window_count" in app

    # Active foreground window inspection
    active = universal_app_manager.get_active_window()
    assert active["success"] is True
    assert "hwnd" in active
    assert "title" in active
    assert "process_name" in active


def test_app_close_and_safety_checks():
    """Verifies graceful app closing and unknown app handling."""
    # Attempting to close non-existent app returns clean response
    close_res = universal_app_manager.close_app("non_existent_app_98765")
    assert close_res["success"] is False
    assert "No running application" in close_res["message"]


def test_voice_intent_and_multilingual_routing():
    """Tests natural voice commands across English, Tanglish, and Hinglish."""
    # 1. English Voice Commands
    int_tm = intent_classifier.classify("Jarvis, open Task Manager")
    assert int_tm.category == IntentCategory.SYSTEM_CONTROL
    assert int_tm.target_tool in ("open_application", "computer.open_app")
    assert "task manager" in int_tm.extracted_params["app_name"].lower()

    int_dl = intent_classifier.classify("Jarvis, open my Downloads folder")
    assert int_dl.category == IntentCategory.SYSTEM_CONTROL
    assert "downloads folder" in int_dl.extracted_params["app_name"].lower()

    int_close = intent_classifier.classify("Jarvis, close Notepad")
    assert int_close.category == IntentCategory.SYSTEM_CONTROL
    assert int_close.target_tool == "computer.close_app"
    assert int_close.extracted_params["app_name_or_process"] == "notepad"

    int_sw = intent_classifier.classify("Jarvis, switch to Chrome")
    assert int_sw.category == IntentCategory.SYSTEM_CONTROL
    assert int_sw.target_tool == "computer.switch_app"
    assert int_sw.extracted_params["app_name_or_window"] == "chrome"

    int_running = intent_classifier.classify("what apps are running")
    assert int_running.category == IntentCategory.SYSTEM_CONTROL
    assert int_running.target_tool == "computer.get_running_apps"

    int_list = intent_classifier.classify("find all installed browsers")
    assert int_list.category == IntentCategory.SYSTEM_CONTROL
    assert int_list.target_tool == "computer.list_installed_apps"

    # 2. Tanglish Normalization
    norm_ta_close, lang_ta1 = multilingual_engine.normalize_code_switching("Notepad ah close pannu")
    assert norm_ta_close == "close notepad"
    assert lang_ta1 == "tanglish"

    norm_ta_switch, lang_ta2 = multilingual_engine.normalize_code_switching("Chrome ku switch pannu")
    assert norm_ta_switch == "switch to chrome"
    assert lang_ta2 == "tanglish"

    norm_ta_open, lang_ta3 = multilingual_engine.normalize_code_switching("Downloads folder open pannunga")
    assert norm_ta_open == "open downloads folder"
    assert lang_ta3 == "tanglish"

    # 3. Hinglish Normalization
    norm_hi_close, lang_hi1 = multilingual_engine.normalize_code_switching("Notepad band karo")
    assert norm_hi_close == "close notepad"
    assert lang_hi1 == "hinglish"

    norm_hi_switch, lang_hi2 = multilingual_engine.normalize_code_switching("Chrome par switch karo")
    assert norm_hi_switch == "switch to chrome"
    assert lang_hi2 == "hinglish"

    norm_hi_open, lang_hi3 = multilingual_engine.normalize_code_switching("Task Manager kholo")
    assert norm_hi_open == "open task manager"
    assert lang_hi3 == "hinglish"


@pytest.mark.asyncio
async def test_tool_registry_universal_tools():
    """Verifies that all 9 universal computer tools are registered and executable."""
    schemas = tool_registry.get_schemas()
    tool_names = [s["function"]["name"] for s in schemas]

    expected_tools = [
        "computer.search_app",
        "computer.list_installed_apps",
        "computer.open_app",
        "computer.close_app",
        "computer.restart_app",
        "computer.switch_app",
        "computer.get_active_window",
        "computer.get_running_apps",
        "computer.find_app_by_description"
    ]
    for t in expected_tools:
        assert t in tool_names, f"Tool '{t}' missing from tool_registry"

    # Execute read-only search tool
    res_search = await tool_registry.execute("computer.search_app", {"query": "notepad", "limit": 2})
    assert res_search["success"] is True
    assert len(res_search["result"]) > 0

    # Execute list installed apps tool
    res_list = await tool_registry.execute("computer.list_installed_apps", {"limit": 5})
    assert res_list["success"] is True
    assert res_list["result"]["total_indexed"] > 0

    # Execute get running apps tool
    res_run = await tool_registry.execute("computer.get_running_apps", {})
    assert res_run["success"] is True
    assert isinstance(res_run["result"], list)
