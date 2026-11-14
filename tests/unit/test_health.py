"""
Unit tests for Core Health, Telemetry, and Session Endpoints
"""

import pytest
from starlette.testclient import TestClient
from api.main import app
from storage.db.connection import init_db


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_health_check_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/system/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["service"] == "JARVIS Personal AI OS Core"
        assert data["database"] == "healthy"


def test_system_metrics_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/system/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "percent" in data["cpu"]
        assert "ram" in data
        assert data["ram"]["total_gb"] > 0
        assert "disk" in data


def test_session_lifecycle():
    with TestClient(app) as client:
        # 1. Create a new conversation session
        create_res = client.post("/api/sessions", json={"title": "Test Exam Prep"})
        assert create_res.status_code == 200
        session_data = create_res.json()
        session_id = session_data["id"]
        assert session_data["title"] == "Test Exam Prep"

        # 2. Send a message to the session
        msg_res = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": "Prepare study notes for Computer Networks", "input_modality": "text"}
        )
        assert msg_res.status_code == 200
        msg_data = msg_res.json()
        assert msg_data["content"] == "Prepare study notes for Computer Networks"
        assert msg_data["sender"] == "user"

        # 3. List messages in session
        list_res = client.get(f"/api/sessions/{session_id}/messages")
        assert list_res.status_code == 200
        messages = list_res.json()
        assert len(messages) >= 1
        assert messages[0]["content"] == "Prepare study notes for Computer Networks"
