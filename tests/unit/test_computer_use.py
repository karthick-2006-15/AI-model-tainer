"""
Unit tests for Computer Use Engine, Screen Intelligence, UI Automation & Observation Loop
"""

import os
import pytest
from modules.computer_use.screen import screen_intelligence
from modules.computer_use.mouse_kb import mouse_kb
from modules.computer_use.native_uia import native_uia
from modules.computer_use.loop import observation_loop
from core.security.permissions import permission_engine


def test_screen_intelligence_capture_and_window():
    # 1. Screen capture
    cap = screen_intelligence.capture_screen()
    assert cap["success"] is True
    assert os.path.exists(cap["file_path"])
    assert cap["width"] > 0
    assert cap["height"] > 0

    # 2. Active window detection
    win = screen_intelligence.get_active_window()
    assert win["success"] is True
    assert "title" in win
    assert "bounds" in win
    assert win["bounds"]["width"] >= 0


def test_visual_state_comparison():
    # Test identical images have 0 change ratio
    cap = screen_intelligence.capture_screen()
    path = cap["file_path"]

    diff_same = screen_intelligence.compare_visual_states(path, path)
    assert diff_same["success"] is True
    assert diff_same["changed"] is False
    assert diff_same["change_ratio"] == 0.0


def test_mouse_kb_safety_and_clamping():
    # Coords outside screen are safely clamped
    w, h = mouse_kb.screen_width, mouse_kb.screen_height
    safe_x, safe_y = mouse_kb._validate_coords(-100, h + 500)
    assert safe_x == 0
    assert safe_y == h - 1

    # Emergency stop blocks actions
    permission_engine.trigger_emergency_stop(reason="Test stop")
    try:
        res = mouse_kb.click(100, 100)
        assert res["success"] is False
        assert "Emergency Stop" in res["error"]
    finally:
        permission_engine.reset_emergency_stop()


def test_native_uia_inspection():
    # Inspect foreground window
    uia_res = native_uia.inspect_active_window()
    assert uia_res["success"] is True
    assert "elements" in uia_res
    assert isinstance(uia_res["elements"], list)


def test_observation_loop_verified_execution():
    call_count = 0

    def mock_action():
        nonlocal call_count
        call_count += 1
        return {"success": True, "action": "test_step"}

    res = observation_loop.execute_verified_action(
        action_name="unit_test_action",
        target_description="Mock Component",
        act_func=mock_action
    )
    assert res["success"] is True
    assert res["verified"] is True
    assert call_count >= 1
