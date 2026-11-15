# JARVIS Mark VII: Updated Project Status & Operations Guide

## 1. System Overview

**JARVIS Mark VII** is an autonomous personal AI operating system featuring computer-use automation, visual intelligence, and a voice-first communication pipeline. It integrates native Windows UI Automation, browser DOM manipulation, visual state diffing, and speech recognition with multilingual support (English, Tamil, Tanglish, Hindi, Hinglish).

---

## 2. Capability Matrix

| Feature | Subsystem | Status | Key Modules |
| :--- | :--- | :---: | :--- |
| **Autonomous Computer Use** | `modules/computer_use/` | **COMPLETE** | [screen.py](file:///c:/Users/karth/OneDrive/Desktop/sanju/modules/computer_use/screen.py), [native_uia.py](file:///c:/Users/karth/OneDrive/Desktop/sanju/modules/computer_use/native_uia.py), [mouse_kb.py](file:///c:/Users/karth/OneDrive/Desktop/sanju/modules/computer_use/mouse_kb.py), [loop.py](file:///c:/Users/karth/OneDrive/Desktop/sanju/modules/computer_use/loop.py) |
| **WhatsApp Automation** | `modules/computer_use/whatsapp.py` | **COMPLETE** | Contact resolution, relation aliases, confirmation challenges, delivery verification |
| **Worksheet & Form Engine** | `modules/computer_use/worksheet.py` | **COMPLETE** | Question extraction, classification, search-based research, field filling, Level 3 submit guard |
| **Always-On Startup Daemon** | `jarvis_service.py` & VBScript | **COMPLETE** | Auto-starts on boot via Windows Startup folder, vocal welcome on login |
| **Voice-First Pipeline** | `modules/voice/` | **COMPLETE** | OpenWakeWord/Whisper, VAD, continuous conversation mode (15s sliding window), barge-in |
| **Multilingual Voice** | `modules/voice/multilingual.py` | **COMPLETE** | Auto language detection, code-switching normalization, localized spoken responses |
| **Dual-Gate Safety Model** | `core/security/permissions.py` | **COMPLETE** | 3-tier permissions (`READ`, `MODIFY`, `EXTERNAL_ACTION`), global emergency stop |
| **Tool Registry (25+ Tools)** | `core/brain/tools.py` | **COMPLETE** | `computer.*` (10), `browser.*` (5), `whatsapp.*` (5), `worksheet.*` (5) |
| **Holographic Core HUD** | `ui/` (React + Vite + Tailwind) | **COMPLETE** | Real-time WebSocket telemetry, voice visualizer, emergency abort button |

---

## 3. Auto-Start & Always-Active Architecture

JARVIS is configured to run silently in the background whenever your laptop is turned on or logged into:

1. **Windows Startup Registration:**
   - Location: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS_AutoStart.vbs`
   - Target: `pythonw.exe jarvis_service.py` (windowless execution without console popups).
2. **Boot Lifecycle:**
   - On Windows logon, the VBScript starts `jarvis_service.py`.
   - The ASGI server boots FastAPI on port `8000`.
   - The audio device activates and JARVIS announces: *"JARVIS online. Standing by, sir."*
   - The Always-On Voice Listener begins listening for *"Hey Jarvis"*.
   - When spoken to, JARVIS replies aloud and enters continuous conversational mode.

---

## 4. Manual Launch & Operations

If you want to run JARVIS in visible console mode or restart subsystems manually:

### Option A: Complete System Boot (Backend + Frontend)
Run the root launcher:
```powershell
.\start_jarvis.bat
```
Or via PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_jarvis.ps1
```

### Option B: Individual Services
1. **Backend API & Always-On Voice Listener:**
   ```powershell
   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```
2. **Frontend HUD Interface:**
   ```powershell
   cd ui
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

---

## 5. Verification & Test Suite

The entire system test suite passes 100%:
```powershell
python -m pytest tests/unit/ -v
# 77 passed in 77.64s (100% pass rate)
```

---

## 6. Emergency Stop Quick Reference

- **Spoken Command:** Say *"Jarvis, emergency stop"* or *"Stop everything"*.
- **HUD Interface:** Click the red **EMERGENCY ABORT** button in the lower-left corner.
- **REST API:** Send `POST http://127.0.0.1:8000/api/v1/automation/emergency-stop`.
- **Reset:** Say *"Jarvis, resume operations"* or send `POST http://127.0.0.1:8000/api/v1/automation/emergency-reset`.
