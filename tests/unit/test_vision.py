"""
Unit Tests for Phase 10: Computer Vision & Screen Intelligence Engine
Tests screen capture, OCR error signature detection, multimodal vision reasoning, and API endpoints.
"""

import os
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from api.main import app
from modules.vision.capture import screen_capture_manager
from modules.vision.ocr import screen_ocr
from modules.vision.analyzer import vision_engine
from core.brain.tools import tool_registry

client = TestClient(app)


def test_screen_capture_generates_image_and_base64():
    capture_res = screen_capture_manager.capture_screen()
    assert capture_res["success"] is True
    assert os.path.exists(capture_res["file_path"])
    assert capture_res["width"] > 0
    assert capture_res["height"] > 0
    assert len(capture_res["base64"]) > 50
    assert len(capture_res["sha256"]) == 64


def test_screen_ocr_detects_error_signatures():
    sample_terminal_dump = """
    Traceback (most recent call last):
      File "api/main.py", line 42, in <module>
    SyntaxError: invalid syntax
    OSError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
    Connection refused by peer
    HTTP Status Code 500 Internal Server Error
    """
    detected = screen_ocr.detect_error_signatures(sample_terminal_dump)
    assert len(detected) >= 3
    joined = " ".join(detected).lower()
    assert "syntaxerror" in joined or "winerror" in joined or "traceback" in joined


@pytest.mark.asyncio
async def test_vision_engine_explain_screen():
    res = await vision_engine.explain_screen(focus_area="VS Code Terminal")
    assert res["success"] is True
    assert "screenshot_path" in res
    assert os.path.exists(res["screenshot_path"])
    assert isinstance(res["detected_errors"], list)
    assert len(res["explanation"]) > 20


@pytest.mark.asyncio
async def test_vision_engine_analyze_image_file(tmp_path):
    # Create test image file
    test_img_path = str(tmp_path / "test_diagram.png")
    img = Image.new("RGB", (200, 200), color="blue")
    img.save(test_img_path)

    res = await vision_engine.analyze_image_file(test_img_path, query="What color is this diagram?")
    assert res["success"] is True
    assert res["image_path"] == os.path.abspath(test_img_path)
    assert len(res["analysis"]) > 10


def test_vision_rest_endpoints(tmp_path):
    # 1. Capture endpoint
    cap_res = client.post("/api/vision/capture")
    assert cap_res.status_code == 200
    data = cap_res.json()
    assert data["success"] is True
    assert "file_path" in data

    # 2. Explain screen endpoint
    exp_res = client.post("/api/vision/explain-screen", json={"focus_area": "Active Window"})
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["success"] is True
    assert "explanation" in exp_data

    # 3. Analyze image endpoint
    test_img = str(tmp_path / "api_test.png")
    Image.new("RGB", (100, 100), color="red").save(test_img)
    anl_res = client.post("/api/vision/analyze-image", json={"image_path": test_img, "query": "Inspect"})
    assert anl_res.status_code == 200
    assert anl_res.json()["success"] is True


def test_vision_tools_registered_in_brain():
    explain_tool = tool_registry.get_tool("explain_screen")
    analyze_tool = tool_registry.get_tool("analyze_image_file")
    assert explain_tool is not None
    assert analyze_tool is not None
    assert explain_tool.permission_level == 1
    assert analyze_tool.permission_level == 1
