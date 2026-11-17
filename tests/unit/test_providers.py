"""
Unit Tests for LLM Providers (OpenAI, Gemini, Anthropic, Ollama), Model Router,
Tool Registry Security Interceptor, Tool Deduplication, and WebSocket Multi-Turn Chat.
"""

import pytest
import json
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from core.providers.base import BaseLLMProvider, LLMProvider, LLMResponse, ToolCallRequest, ToolCall
from core.providers.gemini_provider import GeminiProvider
from core.providers.anthropic_provider import AnthropicProvider
from core.providers.openai_provider import OpenAIProvider
from core.providers.ollama_provider import OllamaProvider
from core.providers.router import ModelRouter, MockProvider
from core.config.settings import settings
from core.brain.tools import tool_registry
from core.security.permissions import permission_engine
from starlette.testclient import TestClient
from api.main import app
from storage.db.connection import SessionLocal
from storage.db.models import Session as DbSession, Message as DbMessage


# =====================================================================
# 1. Google Gemini Provider Tests
# =====================================================================

def test_gemini_payload_system_instruction_and_tools():
    provider = GeminiProvider(api_key="test_gemini_key", model="gemini-1.5-flash")
    messages = [
        {"role": "system", "content": "You are JARVIS AI assistant."},
        {"role": "user", "content": "Find my documents and summarize them."}
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_workspace_files",
                "description": "Search workspace files",
                "parameters": {
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                    "required": ["keyword"]
                }
            }
        }
    ]

    payload = provider._build_payload(messages, tools=tools, temperature=0.3, max_tokens=2000)

    # 1. Verify system instruction is extracted natively
    assert "system_instruction" in payload
    assert payload["system_instruction"]["parts"][0]["text"] == "You are JARVIS AI assistant."

    # 2. Verify non-system messages in contents
    assert len(payload["contents"]) == 1
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][0]["parts"][0]["text"] == "Find my documents and summarize them."

    # 3. Verify tool function declarations schema
    assert "tools" in payload
    assert len(payload["tools"]) == 1
    assert "function_declarations" in payload["tools"][0]
    decl = payload["tools"][0]["function_declarations"][0]
    assert decl["name"] == "search_workspace_files"
    assert decl["description"] == "Search workspace files"
    assert decl["parameters"]["properties"]["keyword"]["type"] == "string"


@pytest.mark.asyncio
async def test_gemini_generate_with_tool_call():
    provider = GeminiProvider(api_key="test_gemini_key")

    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [
                        {"text": "Executing file search..."},
                        {
                            "functionCall": {
                                "name": "search_workspace_files",
                                "args": {"keyword": "report"}
                            }
                        }
                    ]
                },
                "finishReason": "STOP",
                "index": 0
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 25,
            "candidatesTokenCount": 35,
            "totalTokenCount": 60
        }
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = mock_gemini_response
        mock_post.return_value = mock_resp

        messages = [{"role": "user", "content": "Search for report files"}]
        result = await provider.generate(messages)

        assert isinstance(result, LLMResponse)
        assert result.content == "Executing file search..."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "search_workspace_files"
        assert result.tool_calls[0].arguments == {"keyword": "report"}
        assert result.prompt_tokens == 25
        assert result.completion_tokens == 35


@pytest.mark.asyncio
async def test_gemini_streaming_and_generate_stream():
    provider = GeminiProvider(api_key="test_gemini_key")

    sse_lines = [
        b'data: {"candidates": [{"content": {"parts": [{"text": "Hello "}]}}]}\n\n',
        b'data: {"candidates": [{"content": {"parts": [{"text": "Sir, JARVIS online."}]}}]}\n\n'
    ]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line.decode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.aiter_lines = mock_aiter_lines
    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_resp

    with patch("httpx.AsyncClient.stream", return_value=mock_stream_ctx):
        chunks = []
        async for chunk in provider.generate_stream([{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello Sir, JARVIS online."


# =====================================================================
# 2. Anthropic LLM Provider Tests
# =====================================================================

def test_anthropic_payload_system_and_tools():
    provider = AnthropicProvider(api_key="test_anthropic_key", model="claude-3-5-sonnet-20241022")
    messages = [
        {"role": "system", "content": "You are JARVIS Anthropic Assistant."},
        {"role": "user", "content": "Turn up the volume"},
        {"role": "user", "content": "Make it 80 percent"}  # Consecutive user messages should be merged
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "spotify.set_volume",
                "description": "Set Spotify audio volume level",
                "parameters": {
                    "type": "object",
                    "properties": {"level": {"type": "integer"}},
                    "required": ["level"]
                }
            }
        }
    ]

    payload = provider._build_messages_payload(messages, tools=tools, temperature=0.1, max_tokens=1000)

    # 1. System extracted to top-level
    assert payload["system"] == "You are JARVIS Anthropic Assistant."

    # 2. Alternation & merge of consecutive user messages
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert "Turn up the volume" in payload["messages"][0]["content"]
    assert "Make it 80 percent" in payload["messages"][0]["content"]

    # 3. Anthropic tool schema format
    assert "tools" in payload
    tool_entry = payload["tools"][0]
    assert tool_entry["name"] == "spotify.set_volume"
    assert tool_entry["description"] == "Set Spotify audio volume level"
    assert "input_schema" in tool_entry
    assert tool_entry["input_schema"]["properties"]["level"]["type"] == "integer"


@pytest.mark.asyncio
async def test_anthropic_generate_with_tool_use():
    provider = AnthropicProvider(api_key="test_anthropic_key")

    mock_anthropic_response = {
        "id": "msg_12345",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Adjusting volume now."},
            {
                "type": "tool_use",
                "id": "toolu_abc123",
                "name": "spotify.set_volume",
                "input": {"level": 80}
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "tool_use",
        "usage": {
            "input_tokens": 15,
            "output_tokens": 30
        }
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = mock_anthropic_response
        mock_post.return_value = mock_resp

        result = await provider.generate([{"role": "user", "content": "Set volume to 80"}])

        assert isinstance(result, LLMResponse)
        assert result.content == "Adjusting volume now."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "spotify.set_volume"
        assert result.tool_calls[0].arguments == {"level": 80}
        assert result.tool_calls[0].id == "toolu_abc123"
        assert result.prompt_tokens == 15
        assert result.completion_tokens == 30
        assert result.finish_reason == "tool_use"


@pytest.mark.asyncio
async def test_anthropic_streaming():
    provider = AnthropicProvider(api_key="test_anthropic_key")

    sse_lines = [
        'event: content_block_delta',
        'data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Understood, "}}',
        'event: content_block_delta',
        'data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Sir."}}',
        'event: message_stop',
        'data: {"type": "message_stop"}'
    ]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.aiter_lines = mock_aiter_lines
    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__.return_value = mock_resp

    with patch("httpx.AsyncClient.stream", return_value=mock_stream_ctx):
        chunks = []
        async for chunk in provider.stream([{"role": "user", "content": "Status report"}]):
            chunks.append(chunk)

        assert "".join(chunks) == "Understood, Sir."


# =====================================================================
# 3. Model Router Wiring Tests
# =====================================================================

def test_model_router_anthropic_priority():
    router = ModelRouter()

    # When OPENAI_API_KEY is unset and ANTHROPIC_API_KEY is set
    with patch.object(settings, "OPENAI_API_KEY", None):
        with patch.object(settings, "ANTHROPIC_API_KEY", "sk-ant-test-key"):
            with patch.object(settings, "GEMINI_API_KEY", "test-gemini-key"):
                provider = router.get_provider(fast_tier=False)
                assert isinstance(provider, AnthropicProvider)
                assert provider.model == "claude-3-5-sonnet-20241022"
                assert provider.api_key == "sk-ant-test-key"

                fast_provider = router.get_provider(fast_tier=True)
                assert isinstance(fast_provider, AnthropicProvider)
                assert fast_provider.model == "claude-3-5-haiku-20241022"


def test_model_router_fallback_order():
    router = ModelRouter()

    # 1. OpenAI takes first precedence if present
    with patch.object(settings, "OPENAI_API_KEY", "sk-openai-key"):
        with patch.object(settings, "ANTHROPIC_API_KEY", "sk-ant-key"):
            p1 = router.get_provider()
            assert isinstance(p1, OpenAIProvider)

    # 2. Anthropic takes second precedence
    with patch.object(settings, "OPENAI_API_KEY", None):
        with patch.object(settings, "ANTHROPIC_API_KEY", "sk-ant-key"):
            p2 = router.get_provider()
            assert isinstance(p2, AnthropicProvider)

    # 3. Gemini takes third precedence
    with patch.object(settings, "OPENAI_API_KEY", None):
        with patch.object(settings, "ANTHROPIC_API_KEY", None):
            with patch.object(settings, "GEMINI_API_KEY", "gemini-key"):
                p3 = router.get_provider()
                assert isinstance(p3, GeminiProvider)

    # 4. Ollama default fallback
    with patch.object(settings, "OPENAI_API_KEY", None):
        with patch.object(settings, "ANTHROPIC_API_KEY", None):
            with patch.object(settings, "GEMINI_API_KEY", None):
                p4 = router.get_provider()
                assert isinstance(p4, OllamaProvider)


# =====================================================================
# 4. Tool Registry Security Interceptor & Deduplication Tests
# =====================================================================

@pytest.mark.asyncio
async def test_tool_registry_emergency_stop_interceptor():
    # Verify emergency stop halts execution
    permission_engine.trigger_emergency_stop("Safety verification abort")
    try:
        res = await tool_registry.execute("get_system_telemetry", {})
        assert res["success"] is False
        assert res["emergency_stopped"] is True
        assert "Global Emergency Stop is active" in res["error"]

        with pytest.raises(PermissionError):
            await tool_registry.execute("get_system_telemetry", {}, raise_on_denied=True)
    finally:
        permission_engine.reset_emergency_stop()


@pytest.mark.asyncio
async def test_tool_registry_level3_challenge_interceptor():
    # Level 3 tool execution without prior confirmation must be intercepted
    res = await tool_registry.execute("execute_shell_command", {"command": "echo test"})
    assert res["success"] is False
    assert res["permission_denied"] is True
    assert "challenge" in res
    assert res["challenge"]["tool_name"] == "execute_shell_command"
    assert res["challenge"]["permission_level"] == 3


def test_tool_open_application_deduplicated():
    schemas = tool_registry.get_schemas()
    open_app_tools = [s for s in schemas if s["function"]["name"] == "open_application"]
    # Must only appear once in schemas
    assert len(open_app_tools) == 1

    metadata = tool_registry.get_tool("open_application")
    assert metadata is not None
    # Must point to universal_app_manager wrapper
    assert "universal_app_manager" in metadata.func.__code__.co_names


# =====================================================================
# 5. WebSocket HUD Multi-Turn Context Tests
# =====================================================================

def test_websocket_hud_multi_turn_context_and_resolution():
    mock_llm = MockProvider(response_text="Your favorite language is Python.")
    from core.providers.router import model_router
    model_router.set_override_provider(mock_llm)

    try:
        with patch("modules.voice.tts.tts_engine.speak"):
            with TestClient(app) as client:
                # Create a test session in database
                with SessionLocal() as db:
                    test_session = DbSession(title="WS Context Test Session", is_active=True)
                    db.add(test_session)
                    db.commit()
                    db.refresh(test_session)
                    session_id = test_session.id

                    # Pre-populate prior messages
                    msg1 = DbMessage(session_id=session_id, sender="user", content="Remember my favorite language is Python.")
                    msg2 = DbMessage(session_id=session_id, sender="assistant", content="Acknowledged, I will remember that Python is your favorite language.")
                    db.add_all([msg1, msg2])
                    db.commit()

                # Connect over WebSocket HUD
                with client.websocket_connect("/ws/hud") as ws:
                    # Receive initial states
                    msg_agent = ws.receive_json()
                    assert msg_agent["type"] == "agent_state"
                    msg_avatar = ws.receive_json()
                    assert msg_avatar["type"] == "avatar_state"

                    # Send chat input referencing the session
                    ws.send_json({
                        "type": "chat_input",
                        "text": "What is my favorite language?",
                        "session_id": session_id
                    })

                    # Receive thinking/executing broadcasts and final token_chunk
                    received_chunk = False
                    for _ in range(30):
                        resp = ws.receive_json()
                        if resp.get("type") == "token_chunk":
                            received_chunk = True
                            assert resp.get("session_id") == session_id
                            assert resp.get("chunk") == "Your favorite language is Python."
                            break

                    assert received_chunk is True

                    # Verify that database recorded the new user message and assistant reply
                    with SessionLocal() as db:
                        messages = db.query(DbMessage).filter(DbMessage.session_id == session_id).order_by(DbMessage.created_at.asc()).all()
                        assert len(messages) >= 4
                        assert messages[2].sender == "user"
                        assert messages[2].content == "What is my favorite language?"
                        assert messages[3].sender == "assistant"
                        assert messages[3].content == "Your favorite language is Python."

                    # Test permission response resolution over WS
                    # Create a pending challenge
                    _, _, challenge = permission_engine.evaluate_request(
                        tool_name="worksheet.submit",
                        permission_level=3,
                        target_resource="worksheet_exam",
                        arguments={}
                    )
                    ch_id = challenge["challenge_id"]

                    ws.send_json({
                        "type": "permission_response",
                        "request_id": ch_id,
                        "granted": True
                    })

                    # Broadcast message should confirm resolution
                    resolved_event = False
                    for _ in range(15):
                        evt = ws.receive_json()
                        if evt.get("type") == "permission_resolved" and evt.get("request_id") == ch_id:
                            resolved_event = True
                            assert evt.get("granted") is True
                            break

                    assert resolved_event is True
    finally:
        model_router.clear_override()
