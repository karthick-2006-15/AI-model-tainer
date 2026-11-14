"""
Unit tests for Central AI Brain, Intent Classifier, Tools, and Model Router
"""

import pytest
from starlette.testclient import TestClient
from api.main import app
from core.brain.intent import intent_classifier, IntentCategory
from core.brain.tools import tool_registry
from core.brain.orchestrator import brain_orchestrator
from core.providers.router import model_router, MockProvider


def test_intent_classification():
    # 1. System Telemetry
    res_storage = intent_classifier.classify("Jarvis, check my laptop storage")
    assert res_storage.category == IntentCategory.SYSTEM_CONTROL
    assert res_storage.target_tool == "get_system_telemetry"

    # 2. Application Launch
    res_app = intent_classifier.classify("Hey Jarvis, open VS Code")
    assert res_app.category == IntentCategory.SYSTEM_CONTROL
    assert res_app.target_tool == "open_application"
    assert res_app.extracted_params["app_name"] == "vs code"

    # 3. File Operations
    res_files = intent_classifier.classify("Find all pdfs in my project")
    assert res_files.category == IntentCategory.FILE_OPERATION

    # 4. General Conversational
    res_conv = intent_classifier.classify("Hello Jarvis, good morning!")
    assert res_conv.category == IntentCategory.CONVERSATIONAL


@pytest.mark.asyncio
async def test_tool_registry_and_execution():
    # Verify tool discovery & schemas
    schemas = tool_registry.get_schemas()
    assert len(schemas) >= 4
    tool_names = [s["function"]["name"] for s in schemas]
    assert "get_system_telemetry" in tool_names
    assert "open_application" in tool_names
    assert "search_workspace_files" in tool_names

    # Test direct execution
    result = await tool_registry.execute("get_system_telemetry", {})
    assert result["success"] is True
    assert "cpu" in result["result"]
    assert "ram" in result["result"]


@pytest.mark.asyncio
async def test_brain_orchestrator_fast_path():
    # Instruct brain to check system telemetry
    result = await brain_orchestrator.process_user_request("Check my laptop storage")
    assert result["verified"] is True
    assert result["tool_executed"] == "get_system_telemetry"
    assert "System telemetry check complete" in result["response"]


@pytest.mark.asyncio
async def test_brain_orchestrator_with_mock_provider():
    # Set mock provider for conversational queries
    mock = MockProvider(response_text="I am ready to assist you, Sir.")
    model_router.set_override_provider(mock)
    try:
        result = await brain_orchestrator.process_user_request("Who are you?")
        assert result["verified"] is True
        assert result["response"] == "I am ready to assist you, Sir."
    finally:
        model_router.clear_override()


def test_chat_rest_endpoint():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={
            "message": "Check laptop storage"
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["verified"] is True
        assert data["tool_executed"] == "get_system_telemetry"
        assert "session_id" in data
