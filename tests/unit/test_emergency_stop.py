"""
Unit tests for Global Emergency Stop (Kill Switch) & Permission Model
"""

import pytest
from core.security.permissions import permission_engine


def test_emergency_stop_lifecycle():
    assert permission_engine.is_emergency_stopped() is False

    # Trigger emergency stop
    res = permission_engine.trigger_emergency_stop(reason="User commanded abort")
    assert res["emergency_stopped"] is True
    assert permission_engine.is_emergency_stopped() is True

    # Attempting any action while emergency stopped is rejected
    allowed, reason, challenge = permission_engine.evaluate_request(
        tool_name="computer.click_element",
        permission_level=2,
        target_resource="Screen Button",
        arguments={}
    )
    assert allowed is False
    assert "Global Emergency Stop is ACTIVE" in reason

    # Reset emergency stop
    reset_res = permission_engine.reset_emergency_stop()
    assert reset_res["emergency_stopped"] is False
    assert permission_engine.is_emergency_stopped() is False

    # Subsequent request is now allowed according to standard policy
    allowed_post, reason_post, _ = permission_engine.evaluate_request(
        tool_name="get_system_telemetry",
        permission_level=1,
        target_resource="telemetry",
        arguments={}
    )
    assert allowed_post is True
