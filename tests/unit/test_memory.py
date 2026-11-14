"""
Unit tests for 4-Tier Personal Memory Engine
"""

import pytest
from starlette.testclient import TestClient
from api.main import app
from core.memory.working import working_memory
from core.memory.episodic import episodic_memory
from core.memory.semantic import semantic_memory
from core.memory.profile import profile_memory


def test_working_memory_lifecycle():
    working_memory.clear()

    # 1. Add conversation turns
    working_memory.add_turn(role="user", content="Hello Jarvis")
    working_memory.add_turn(role="jarvis", content="Greetings. How can I help?")
    turns = working_memory.get_recent_turns()
    assert len(turns) == 2
    assert turns[0]["content"] == "Hello Jarvis"

    # 2. Context slots
    working_memory.set_slot("current_project", "Autonomous Warehouse AI")
    assert working_memory.get_slot("current_project") == "Autonomous Warehouse AI"
    assert "current_project" in working_memory.get_all_slots()

    # 3. Scratchpad
    working_memory.write_scratchpad("pending_file", "report.pdf")
    assert working_memory.read_scratchpad("pending_file") == "report.pdf"


def test_profile_memory_crud_and_extraction():
    # 1. Add/update a verified fact
    fact = profile_memory.add_or_update_fact(
        key_name="preferred_ide",
        category="preference",
        value_data={"text": "Visual Studio Code"},
        confidence_score=1.0,
        provenance="user_explicit"
    )
    assert fact["key_name"] == "preferred_ide"
    assert fact["confidence_score"] == 1.0

    # 2. Retrieve fact
    retrieved = profile_memory.get_fact("preferred_ide")
    assert retrieved is not None
    assert retrieved["value_data"]["text"] == "Visual Studio Code"

    # 3. Auto-extraction of facts from user prompt
    extracted = profile_memory.auto_extract_facts_from_text("My exam is on Tuesday morning")
    assert len(extracted) >= 1
    assert any(e["category"] == "academic" for e in extracted)

    # 4. Delete fact
    fact_id = fact["id"]
    deleted = profile_memory.delete_fact(fact_id)
    assert deleted is True
    assert profile_memory.get_fact("preferred_ide") is None


def test_semantic_vector_search():
    # Upsert known memory chunk
    semantic_memory.upsert_memory(
        memory_id="test_exam_point",
        text="Computer Networks examination covering Dijkstra algorithm and TCP",
        category="academic"
    )

    # Query with semantic keywords
    matches = semantic_memory.search_memory("Dijkstra routing algorithm exam", limit=2)
    assert len(matches) >= 1
    assert "Computer Networks" in matches[0]["text"]
    assert matches[0]["score"] > 0.1

    # Cleanup
    semantic_memory.delete_memory("test_exam_point")


def test_memory_rest_endpoints():
    with TestClient(app) as client:
        # 1. Add memory entity via API
        create_res = client.post("/api/memory/entities", json={
            "key_name": "primary_project",
            "category": "project",
            "value_data": {"text": "Autonomous Warehouse AI"}
        })
        assert create_res.status_code == 200
        data = create_res.json()
        assert data["key_name"] == "primary_project"
        fact_id = data["id"]

        # 2. List entities
        list_res = client.get("/api/memory/entities?category=project")
        assert list_res.status_code == 200
        entities = list_res.json()
        assert any(e["id"] == fact_id for e in entities)

        # 3. Semantic search
        search_res = client.get("/api/memory/search?q=Warehouse")
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert "results" in search_data

        # 4. Delete memory
        del_res = client.delete(f"/api/memory/entities/{fact_id}")
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True
