"""
Unit Tests for JARVIS Animated Avatar Face System
Verifies AvatarEngine state machine, emotional expressions, real-time lip-sync, settings, and REST endpoints.
"""

import pytest
import time
from fastapi.testclient import TestClient
from api.main import app
from modules.avatar.avatar_engine import AvatarEngine, avatar_engine


def test_avatar_engine_state_transitions():
    engine = AvatarEngine()
    assert engine.get_state()["state"] == "idle"

    states_to_test = [
        ("listening", 1.05, 0.1),
        ("thinking", 0.95, -0.15),
        ("speaking", 1.0, 0.05),
        ("happy", 0.85, 0.25),
        ("confused", 1.0, -0.3),
        ("error", 0.9, -0.4),
        ("warning", 1.05, -0.2),
        ("sleeping", 0.1, 0.0),
        ("idle", 1.0, 0.0)
    ]

    for state, expected_eyelid, expected_eyebrow in states_to_test:
        success = engine.set_state(state, f"State: {state}")
        assert success is True
        st = engine.get_state()
        assert st["state"] == state
        assert st["eye_metrics"]["eyelid_open"] == pytest.approx(expected_eyelid, abs=0.01)
        assert st["eye_metrics"]["eyebrow_tilt"] == pytest.approx(expected_eyebrow, abs=0.01)

    # Test invalid state falls back to idle
    engine.set_state("non_existent_state")
    assert engine.get_state()["state"] == "idle"


def test_avatar_engine_transient_expression():
    engine = AvatarEngine()
    engine.set_state("idle")

    # Trigger a 0.2s expression
    engine.trigger_expression("happy", duration=0.2)
    st = engine.get_state()
    assert st["expression"] == "happy"

    # Wait for expiry
    time.sleep(0.3)
    st_expired = engine.get_state()
    assert st_expired["expression"] == "neutral"


def test_avatar_engine_lip_sync():
    engine = AvatarEngine()
    
    # Test valid amplitude
    res = engine.update_lip_sync(0.65, phoneme="OH")
    assert res["amplitude"] == pytest.approx(0.65, abs=0.001)
    assert res["mouth_open"] == pytest.approx(0.65, abs=0.001)
    assert res["phoneme"] == "OH"

    # Test clamping
    res_high = engine.update_lip_sync(1.5, phoneme="AH")
    assert res_high["amplitude"] == 1.0
    assert res_high["mouth_open"] == 1.0

    res_low = engine.update_lip_sync(-0.5)
    assert res_low["amplitude"] == 0.0
    assert res_low["mouth_open"] == 0.0


def test_avatar_engine_settings_persistence():
    engine = AvatarEngine()
    initial_settings = engine.get_settings()
    assert initial_settings["theme"] == "classic_cyan"

    # Valid update
    updated = engine.update_settings({
        "theme": "quantum_violet",
        "size": "large",
        "glow_intensity": 0.95,
        "scanlines_enabled": False
    })
    assert updated["theme"] == "quantum_violet"
    assert updated["size"] == "large"
    assert updated["glow_intensity"] == 0.95
    assert updated["scanlines_enabled"] is False

    # Invalid values should be ignored
    engine.update_settings({
        "theme": "invalid_theme",
        "size": "extra_gigantic"
    })
    curr = engine.get_settings()
    assert curr["theme"] == "quantum_violet"
    assert curr["size"] == "large"


def test_avatar_rest_endpoints():
    client = TestClient(app)

    # GET /api/avatar/state
    resp = client.get("/api/avatar/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "state" in data
    assert "eye_metrics" in data
    assert "lip_sync" in data

    # POST /api/avatar/state
    resp_set = client.post("/api/avatar/state", json={"state": "listening", "message": "Listening now..."})
    assert resp_set.status_code == 200
    assert resp_set.json()["state"] == "listening"

    # Verify updated
    resp_check = client.get("/api/avatar/state")
    assert resp_check.json()["state"] == "listening"

    # POST /api/avatar/expression
    resp_expr = client.post("/api/avatar/expression", json={"expression": "confused", "duration": 2.0})
    assert resp_expr.status_code == 200
    assert resp_expr.json()["expression"] == "confused"

    # POST /api/avatar/lip_sync
    resp_lip = client.post("/api/avatar/lip_sync", json={"amplitude": 0.8, "phoneme": "EE"})
    assert resp_lip.status_code == 200
    assert resp_lip.json()["lip_sync"]["mouth_open"] == 0.8

    # GET and POST /api/avatar/settings
    resp_settings = client.get("/api/avatar/settings")
    assert resp_settings.status_code == 200
    assert "theme" in resp_settings.json()

    resp_up_settings = client.post("/api/avatar/settings", json={"theme": "arc_gold", "glow_intensity": 0.9})
    assert resp_up_settings.status_code == 200
    assert resp_up_settings.json()["settings"]["theme"] == "arc_gold"

    # Reset back to idle for subsequent test isolation
    avatar_engine.reset_to_idle()


@pytest.mark.asyncio
async def test_avatar_tools_registered_in_brain():
    from core.brain.tools import tool_registry
    
    assert "avatar.set_state" in tool_registry._tools
    assert "avatar.set_expression" in tool_registry._tools
    assert "avatar.set_theme" in tool_registry._tools
    assert "avatar.get_status" in tool_registry._tools

    # Test tool invocation via registry
    res = await tool_registry.execute("avatar.set_state", {"state": "happy", "message": "Joyful test"})
    assert res["success"] is True
    assert res["result"]["state"] == "happy"
    assert res["result"]["status_message"] == "Joyful test"

    status = await tool_registry.execute("avatar.get_status", {})
    assert status["success"] is True
    assert status["result"]["state"] == "happy"

    avatar_engine.reset_to_idle()

