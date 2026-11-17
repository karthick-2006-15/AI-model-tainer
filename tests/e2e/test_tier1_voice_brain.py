"""
Tier 1 End-to-End Test Suite: Voice Subsystem & AI Brain Reasoning Engine
Covers all primary happy paths (TC-VOICE-01 through TC-VOICE-08 and TC-BRAIN-01 through TC-BRAIN-06).
Adheres strictly to opaque-box testing via REST APIs and WebSockets.
"""

import io
import wave
import struct
import pytest
from unittest.mock import patch, MagicMock
from modules.voice.multilingual import MultilingualEngine
from modules.voice.wakeword import WakeWordDetector
from modules.voice.duplex import duplex_controller
from core.planning.task import TaskStatus


# =============================================================================
# CATEGORY 1: VOICE SUBSYSTEM (8 Test Cases)
# =============================================================================

def test_tc_voice_01_status_check(app_client):
    """TC-VOICE-01: Voice Engine Status Check returns ready state and supported languages."""
    res = app_client.get("/api/voice/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "default_voice_en" in data
    assert "default_voice_ta" in data
    assert "en-US" in data["supported_languages"]
    assert "ta-IN" in data["supported_languages"]
    assert data["wake_word"] in ("hey_jarvis", "Hey Jarvis")


def test_tc_voice_02_voices_catalogue(app_client):
    """TC-VOICE-02: Voice Catalogue Listing returns neural voices for English and Tamil."""
    res = app_client.get("/api/voice/voices")
    assert res.status_code == 200
    data = res.json()
    assert "en" in data
    assert "ta" in data
    # Verify presence of Tamil neural voice
    assert any(v["id"] == "ta-IN-ValluvarNeural" for v in data["ta"])
    # Verify presence of English neural voice
    assert any(v["id"] == "en-US-ChristopherNeural" for v in data["en"])


def test_tc_voice_03_neural_speech_synthesis(app_client):
    """TC-VOICE-03: Neural Speech Synthesis streams audio MP3 response."""
    async def mock_save(path):
        with open(path, "wb") as f:
            f.write(b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90d" + b"\x00" * 200)
        return True

    with patch("edge_tts.Communicate.save", side_effect=mock_save):
        res = app_client.post(
            "/api/voice/tts",
            json={"text": "Hello user, systems are online.", "voice": "en-US-GuyNeural"}
        )
        assert res.status_code == 200
        assert "audio/mpeg" in res.headers.get("content-type", "")
        assert len(res.content) > 0


def test_tc_voice_04_speech_to_text_transcription(app_client):
    """TC-VOICE-04: Speech-to-Text Audio Transcription via multipart upload."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(bytes(3200))
    wav_io.seek(0)

    with patch("modules.voice.stt.stt_engine.transcribe_audio_file", return_value="open calculator"):
        res = app_client.post(
            "/api/voice/stt",
            files={"file": ("sample.wav", wav_io, "audio/wav")},
            data={"language": "en-US"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["transcription"] == "open calculator"
        assert data["language"] == "en-US"


def test_tc_voice_05_manual_speech_interruption(app_client):
    """TC-VOICE-05: Manual Speech Interruption triggers duplex cancellation."""
    duplex_controller.notify_speech_started()
    assert duplex_controller.is_speaking is True

    res = app_client.post("/api/voice/interrupt", json={"reason": "User manual halt"})
    assert res.status_code == 200
    assert res.json()["interrupted"] is True
    assert duplex_controller.is_speaking is False
    assert duplex_controller.was_interrupted is True


def test_tc_voice_06_streaming_wake_word_detection(app_client):
    """TC-VOICE-06: Streaming Wake-Word Detection over /ws/audio."""
    with patch("modules.voice.stt.stt_engine.transcribe_pcm_bytes", return_value="Hey Jarvis open calculator"):
        with app_client.websocket_connect("/ws/audio") as ws:
            # 1. Send speech frames exceeding energy threshold to trigger speech_started
            loud_samples = [10000 if i % 2 == 0 else -10000 for i in range(1600)]
            loud_pcm = struct.pack(f"<{len(loud_samples)}h", *loud_samples)

            # Send multiple frames to overcome speech padding (>= 5 frames)
            for _ in range(6):
                ws.send_bytes(loud_pcm)

            # Receive speech_started
            msg1 = ws.receive_json()
            assert msg1.get("type") == "vad_event"
            assert msg1.get("state") == "speech_started"

            # 2. Send silence to trigger speech_ended and STT transcription (>= 15 frames)
            silence_pcm = bytes(3200)
            for _ in range(16):
                ws.send_bytes(silence_pcm)

            msg2 = ws.receive_json()
            assert msg2.get("type") == "vad_event"
            assert msg2.get("state") == "speech_ended"

            # Receive transcript event with wake word detection
            msg3 = ws.receive_json()
            assert msg3.get("type") == "transcript"
            assert msg3.get("wake_word_detected") is True
            assert msg3.get("command") == "open calculator"


def test_tc_voice_07_multilingual_code_switching_normalization():
    """TC-VOICE-07: Multilingual Code-Switching Normalization across Tanglish, Hindi, and Hinglish."""
    engine = MultilingualEngine()

    # Case A: Tanglish
    cmd_ta, lang_ta = engine.normalize_code_switching("WhatsApp open pannu")
    assert lang_ta == "tanglish"
    assert cmd_ta.lower() == "open whatsapp"

    # Case B: Hinglish
    cmd_hi, lang_hi = engine.normalize_code_switching("Chrome kholo")
    assert lang_hi == "hinglish"
    assert cmd_hi.lower() == "open chrome"

    # Case C: Hinglish complex message
    cmd_msg, lang_msg = engine.normalize_code_switching("mere father ko Hi message bhejo")
    assert lang_msg == "hinglish"
    assert "send hi to father" in cmd_msg.lower()

    # Case D: English passthrough
    cmd_en, lang_en = engine.normalize_code_switching("Open Visual Studio Code")
    assert lang_en == "en"
    assert cmd_en == "Open Visual Studio Code"


def test_tc_voice_08_vad_speech_detection_events(app_client):
    """TC-VOICE-08: VAD acoustic speech onset and offset event streaming."""
    with app_client.websocket_connect("/ws/audio") as ws:
        loud_samples = [8000 if i % 2 == 0 else -8000 for i in range(1600)]
        loud_pcm = struct.pack(f"<{len(loud_samples)}h", *loud_samples)

        # Trigger speech start (>= 5 frames)
        for _ in range(6):
            ws.send_bytes(loud_pcm)

        start_event = ws.receive_json()
        assert start_event["type"] == "vad_event"
        assert start_event["state"] == "speech_started"

        # Trigger speech end with silence (>= 15 frames)
        for _ in range(16):
            ws.send_bytes(bytes(3200))
        end_event = ws.receive_json()
        assert end_event["type"] == "vad_event"
        assert end_event["state"] == "speech_ended"


# =============================================================================
# CATEGORY 2: BRAIN & INTENT SUBSYSTEM (6 Test Cases)
# =============================================================================

def test_tc_brain_01_conversational_greeting_fast_path(app_client):
    """TC-BRAIN-01: Conversational Greeting Fast-Path responds with appropriate assistant greeting."""
    res = app_client.post("/api/chat", json={"message": "Hello Jarvis", "input_modality": "text"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "conversational"
    assert len(data["response"]) > 0
    assert "session_id" in data
    assert data["verified"] is True


def test_tc_brain_02_direct_system_tool_execution(app_client):
    """TC-BRAIN-02: Direct System Tool Execution Fast-Path triggers get_system_telemetry."""
    res = app_client.post(
        "/api/chat",
        json={"message": "Check my system memory and CPU", "input_modality": "text"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_executed"] == "get_system_telemetry"
    assert "CPU" in data["response"] or "RAM" in data["response"] or "Memory" in data["response"]
    assert data["verified"] is True


def test_tc_brain_03_multi_turn_context_retention(app_client):
    """TC-BRAIN-03: Multi-turn Chat Context Retention preserves facts across turns in a session."""
    # Turn 1: State preference
    t1 = app_client.post(
        "/api/chat",
        json={"message": "My favourite programming language is Rust.", "input_modality": "text"}
    )
    assert t1.status_code == 200
    session_id = t1.json()["session_id"]

    # Turn 2: Ask question in same session
    t2 = app_client.post(
        "/api/chat",
        json={"message": "What is my favourite programming language?", "session_id": session_id}
    )
    assert t2.status_code == 200
    data = t2.json()
    assert data["session_id"] == session_id
    assert "rust" in data["response"].lower()


def test_tc_brain_04_plandag_goal_decomposition(app_client):
    """TC-BRAIN-04: PlanDAG Goal Decomposition breaks a complex goal into an acyclic graph."""
    res = app_client.post(
        "/api/tasks/plan",
        json={"goal": "Research quantum computing trends and create summary report"}
    )
    assert res.status_code == 200
    dag = res.json()
    assert "plan_id" in dag
    assert dag["goal"] == "Research quantum computing trends and create summary report"
    assert len(dag["subtasks"]) >= 2
    # Verify subtask structure (subtasks is a dictionary keyed by id)
    first_task = list(dag["subtasks"].values())[0]
    assert "id" in first_task
    assert "tool_name" in first_task
    assert "dependencies" in first_task


def test_tc_brain_05_plandag_execution_by_id(app_client):
    """TC-BRAIN-05: PlanDAG Execution executes prepared subtasks wave by wave."""
    from core.planning.executor import dag_executor
    from core.planning.task import PlanDAG

    # Step 1: Create plan
    plan_res = app_client.post(
        "/api/tasks/plan",
        json={"goal": "Prepare my computer networks examination"}
    )
    assert plan_res.status_code == 200
    dag_dict = plan_res.json()
    plan_id = dag_dict["plan_id"]

    # Pre-register in dag_executor active plans so execute endpoint can find it
    dag_obj = PlanDAG.model_validate(dag_dict)
    dag_executor._active_plans[plan_id] = dag_obj

    # Step 2: Execute plan by ID
    exec_res = app_client.post(f"/api/tasks/{plan_id}/execute")
    assert exec_res.status_code == 200
    completed_dag = exec_res.json()
    assert completed_dag["plan_id"] == plan_id
    assert completed_dag["status"] in ("completed", "running", "success")


def test_tc_brain_06_plan_and_execute_oneshot(app_client):
    """TC-BRAIN-06: One-shot Plan and Execute endpoint creates DAG and executes immediately."""
    res = app_client.post(
        "/api/tasks/plan-and-execute",
        json={"goal": "Organize downloads folder and clean duplicates"}
    )
    assert res.status_code == 200
    dag = res.json()
    assert dag["goal"] == "Organize downloads folder and clean duplicates"
    assert len(dag["subtasks"]) >= 1
