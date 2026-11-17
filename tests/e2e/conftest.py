"""
E2E Test Suite Conftest Harness
Provides hermetic, isolated fixtures for:
- Temporary isolated SQLite database and Qdrant storage (zero workspace pollution)
- Mocked voice hardware preventing microphone acquisition and 2.5s thread delay
- Mocked LLM provider preventing 120s Ollama timeouts and returning deterministic responses
- Mocked GSMTC preventing Windows COM apartment deadlocks
- Reusable synchronous and asynchronous FastAPI clients
- Reusable WebSocket HUD test helper
"""

import os
import sys
import json
import tempfile
import asyncio
from typing import Generator, Dict, Any, List, Optional
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.main import app
from core.config.settings import settings
import storage.db.connection as db_conn
from storage.db.connection import Base
from core.providers.router import model_router
from core.providers.base import BaseLLMProvider, LLMResponse
from modules.voice.listener import voice_listener
from modules.voice.duplex import duplex_controller
from modules.media.spotify_controller import spotify_controller
from qdrant_client import QdrantClient
from core.memory.semantic import semantic_memory


class E2EDeterministicLLMProvider(BaseLLMProvider):
    """
    Intelligent deterministic mock LLM provider for E2E tests.
    Responds with valid structured JSON for PlanDAG decomposition,
    and context-aware answers for multi-turn conversational queries.
    """
    def __init__(self, default_response: str = "JARVIS Subsystems Operational."):
        self.default_response = default_response
        self.call_history: List[List[Dict[str, Any]]] = []

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> LLMResponse:
        self.call_history.append(messages)
        full_text = " ".join(m.get("content", "") for m in messages).lower()

        # 1. PlanDAG Goal Decomposition requests
        if "plan" in full_text or "subtasks" in full_text or "tools_schema" in full_text:
            plan_json = {
                "subtasks": [
                    {
                        "id": "task_1",
                        "description": "Conduct initial data gathering",
                        "tool_name": "web_search",
                        "arguments": {"query": "quantum computing trends", "max_results": 3},
                        "dependencies": []
                    },
                    {
                        "id": "task_2",
                        "description": "Fetch system performance metrics",
                        "tool_name": "get_system_telemetry",
                        "arguments": {},
                        "dependencies": []
                    },
                    {
                        "id": "task_3",
                        "description": "Synthesize final research report",
                        "tool_name": "conduct_research_report",
                        "arguments": {"topic": "quantum computing", "max_sources": 3},
                        "dependencies": ["task_1"]
                    }
                ]
            }
            return LLMResponse(content=json.dumps(plan_json), model="mock-e2e-planner")

        # 2. Multi-turn conversational questions
        if "rust" in full_text or "favourite programming language" in full_text or "favorite programming language" in full_text:
            return LLMResponse(content="Your favourite programming language is Rust.", model="mock-e2e-model")

        if "birthday" in full_text:
            return LLMResponse(content="Your birthday is on August 15.", model="mock-e2e-model")

        # 3. Default response
        return LLMResponse(content=self.default_response, model="mock-e2e-model")

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1500
    ):
        res = await self.generate(messages, temperature=temperature, max_tokens=max_tokens)
        for token in res.content.split():
            yield token + " "


@pytest.fixture(autouse=True)
def isolated_storage():
    """
    Hermetic test isolation fixture:
    Creates a temporary SQLite database and temporary Qdrant directory for each test run.
    Ensures ZERO writes or locks on the user's `jarvis.db` and `./storage/vector_data`.
    """
    original_db_url = settings.DATABASE_URL
    original_qdrant_path = settings.QDRANT_STORAGE_PATH
    original_engine = db_conn.engine

    with tempfile.TemporaryDirectory(prefix="jarvis_e2e_") as temp_dir:
        test_db_path = os.path.join(temp_dir, "e2e_isolated.db")
        test_db_url = f"sqlite:///{os.path.abspath(test_db_path)}"
        test_qdrant_path = os.path.join(temp_dir, "vector_data")

        settings.DATABASE_URL = test_db_url
        settings.QDRANT_STORAGE_PATH = test_qdrant_path

        # Re-create engine and rebind sessionmaker
        new_engine = create_engine(
            test_db_url,
            echo=False,
            connect_args={"check_same_thread": False}
        )
        db_conn.engine = new_engine
        db_conn.SessionLocal.configure(bind=new_engine)

        # Create all schemas
        Base.metadata.create_all(bind=new_engine)

        # Re-initialize semantic memory in in-memory mode or isolated temp dir
        try:
            semantic_memory.client = QdrantClient(":memory:")
            semantic_memory._ensure_collection()
        except Exception:
            pass

        yield {
            "temp_dir": temp_dir,
            "db_path": test_db_path,
            "db_url": test_db_url,
            "engine": new_engine
        }

        # Teardown
        new_engine.dispose()
        db_conn.engine = original_engine
        db_conn.SessionLocal.configure(bind=original_engine)
        settings.DATABASE_URL = original_db_url
        settings.QDRANT_STORAGE_PATH = original_qdrant_path


@pytest.fixture(autouse=True)
def mock_voice_hardware():
    """
    Prevents physical microphone hardware acquisition, calibration delay (0.8s),
    and thread join delay (2.0s) on every FastAPI startup/shutdown.
    """
    duplex_controller.is_speaking = False
    duplex_controller._interrupt_event.clear()

    with patch.object(voice_listener, "start", return_value=None), \
         patch.object(voice_listener, "stop", return_value=None), \
         patch("speech_recognition.Microphone", MagicMock()):
        yield


@pytest.fixture(autouse=True)
def mock_llm_provider():
    """
    Injects deterministic mock provider into model_router to eliminate 120s Ollama timeouts.
    """
    provider = E2EDeterministicLLMProvider()
    model_router.set_override_provider(provider)
    yield provider
    model_router.clear_override()


@pytest.fixture(autouse=True)
def mock_gsmtc():
    """
    Stubs GSMTC to prevent COM apartment deadlocks during media tests.
    """
    def _mock_run_gsmtc(coro_fn):
        return {
            "title": "Blinding Lights",
            "artist": "The Weeknd",
            "status": "Playing",
            "is_playing": True
        }

    with patch.object(spotify_controller, "_run_gsmtc", side_effect=_mock_run_gsmtc):
        yield


@pytest.fixture
def app_client():
    """FastAPI TestClient with lifespan management."""
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client():
    """Async HTTPX client for testing ASGI application."""
    import httpx
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


class HUDWebSocketHelper:
    """Helper for interacting with /ws/hud and filtering messages."""
    def __init__(self, ws):
        self.ws = ws

    def send_json(self, payload: dict):
        self.ws.send_json(payload)

    def receive_json(self) -> dict:
        return self.ws.receive_json()

    def wait_for_type(self, target_type: str, max_messages: int = 25) -> Optional[dict]:
        """Reads frames until a frame matching target_type is found, skipping telemetry."""
        for _ in range(max_messages):
            msg = self.ws.receive_json()
            if msg.get("type") == target_type:
                return msg
        return None


@pytest.fixture
def ws_hud_client(app_client):
    """Context manager fixture providing a connected HUD WebSocket client."""
    def _connect():
        cm = app_client.websocket_connect("/ws/hud")
        ws = cm.__enter__()
        # Read initial welcome frames
        helper = HUDWebSocketHelper(ws)
        # First frame is agent_state: idle
        # Second frame is avatar_state
        return cm, helper
    return _connect
