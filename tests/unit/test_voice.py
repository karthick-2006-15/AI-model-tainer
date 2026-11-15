"""
Unit tests for Voice Intelligence Engine & Duplex Controller
"""

import pytest
import struct
from starlette.testclient import TestClient
from api.main import app
from modules.voice.vad import VADDetector
from modules.voice.wakeword import WakeWordDetector
from modules.voice.duplex import DuplexController


def test_vad_silence_vs_speech():
    vad = VADDetector(energy_threshold=0.02)

    # 1. Generate 100ms of pure silence (all zeroes)
    silence_pcm = bytes(3200)
    rms_silence = vad.calculate_rms(silence_pcm)
    assert rms_silence == 0.0

    is_speech, just_started = vad.process_frame(silence_pcm)
    assert not is_speech
    assert not just_started

    # 2. Generate simulated loud audio frame (square wave with amplitude 10000)
    loud_samples = [10000 if i % 2 == 0 else -10000 for i in range(1600)]
    loud_pcm = struct.pack(f"<{len(loud_samples)}h", *loud_samples)
    rms_loud = vad.calculate_rms(loud_pcm)
    assert rms_loud > 0.1  # Significant energy

    # Feed enough loud frames to exceed speech_pad_frames
    for _ in range(vad.speech_pad_frames):
        is_speech, just_started = vad.process_frame(loud_pcm)

    assert is_speech


def test_wakeword_detection():
    detector = WakeWordDetector()

    # Exact wake word + instruction
    detected, cmd = detector.check_text("Hey Jarvis open VS Code")
    assert detected is True
    assert cmd == "open VS Code"

    # Lowercase variant
    detected, cmd = detector.check_text("jarvis, organize my downloads")
    assert detected is True
    assert cmd == "organize my downloads"

    # Just greeting
    detected, cmd = detector.check_text("Hello Jarvis")
    assert detected is True
    assert cmd is None

    # Unrelated sentence
    detected, cmd = detector.check_text("What is the weather outside?")
    assert detected is False
    assert cmd is None


def test_duplex_barge_in():
    duplex = DuplexController()
    interrupted_count = 0

    def on_interrupt():
        nonlocal interrupted_count
        interrupted_count += 1

    duplex.register_interruption_handler(on_interrupt)

    # 1. JARVIS begins speaking
    duplex.notify_speech_started()
    assert duplex.is_speaking is True
    assert duplex.was_interrupted is False

    # 2. User interrupts by speaking
    duplex.trigger_interruption(reason="Simulated user voice interrupt")
    assert duplex.is_speaking is False
    assert duplex.was_interrupted is True
    assert interrupted_count == 1


def test_voice_endpoints():
    with TestClient(app) as client:
        # 1. Voice status
        status_res = client.get("/api/voice/status")
        assert status_res.status_code == 200
        data = status_res.json()
        assert data["status"] == "ready"
        assert "default_voice_en" in data
        assert "ta-IN" in data["supported_languages"][1]

        # 2. Supported voices catalogue
        voices_res = client.get("/api/voice/voices")
        assert voices_res.status_code == 200
        catalogue = voices_res.json()
        assert "en" in catalogue
        assert "ta" in catalogue
        assert any(v["id"] == "ta-IN-ValluvarNeural" for v in catalogue["ta"])

        # 3. Manual interrupt trigger
        interrupt_res = client.post("/api/voice/interrupt", json={"reason": "Test halt"})
        assert interrupt_res.status_code == 200
        assert interrupt_res.json()["interrupted"] is True


def test_tts_clean_for_speech():
    from modules.voice.tts import tts_engine
    raw = "**Application** 'VS Code' [link](http://example.com) launched. • Status: `OK`"
    cleaned = tts_engine.clean_for_speech(raw)
    assert "**" not in cleaned
    assert "`" not in cleaned
    assert "http://example.com" not in cleaned
    assert "link" in cleaned
    assert "Application 'VS Code' link launched. Status: OK" in cleaned


def test_voice_listener_registration():
    from modules.voice.listener import VoiceListener
    vl = VoiceListener()
    called = []
    vl.register_command_callback(lambda cmd, resp: called.append((cmd, resp)))
    assert len(vl.on_command_callbacks) == 1
