# PROJECT JARVIS // MARK VII
### Personal AI Operating System for Windows 11 with Mobile Companion

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-3178C6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4%2B-646CFF.svg)](https://vitejs.dev/)
[![Tests](https://img.shields.io/badge/Tests-59%20Passing-success.svg)](#testing)

---

## 🌟 Overview

**JARVIS** (*Just A Rather Very Intelligent System*) is a full-stack, local-first personal AI operating system engineered for Windows 11. It bridges natural language intelligence with native OS execution, featuring live system telemetry, automated application management, file indexing, vision-based error explanation, multi-step goal planning, and real-time audio/duplex conversational feeds.

---

## 🏗️ Architecture & Core Subsystems

```
                               ┌────────────────────────────────┐
                               │   React 18 Holographic HUD     │
                               │    (http://localhost:5173)     │
                               └──────────────┬─────────────────┘
                                              │ WebSocket / REST
                               ┌──────────────▼─────────────────┐
                               │    FastAPI Central Core        │
                               │   (http://127.0.0.1:8000)      │
                               └──────────────┬─────────────────┘
                                              │
         ┌───────────────────┬────────────────┼───────────────────┬───────────────────┐
         │                   │                │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌─────▼───────┐ ┌─────────▼─────────┐ ┌───────▼────────┐
│   Core Brain    │ │   Automation    │ │   Memory    │ │ Computer Vision   │ │  Goal Planner  │
│ Intent / Router │ │ Windows Desktop │ │ Qdrant / DB │ │ Screen Capture    │ │ Directed Acyclic│
│ Fast Heuristics │ │ Shell Sandbox   │ │ Entities    │ │ OCR Error Engine  │ │ Execution Graph │
└─────────────────┘ └─────────────────┘ └─────────────┘ └───────────────────┘ └────────────────┘
```

1. **Core Brain & Router (`core/brain/`):** Fast intent classifier with microsecond heuristic tool calling, conversational offline kernel fallback, and support for OpenAI, Anthropic, Gemini, and Ollama.
2. **OS Automation & Telemetry (`modules/automation/`):** Native Windows desktop bridge using Win32 API and Task Scheduler to control applications (`VS Code`, `Chrome`, `Notepad`), windows, and live hardware telemetry (CPU, RAM, Storage, Battery).
3. **Memory & Fact Engine (`core/memory/`):** 4-tier memory architecture (working, episodic, profile entities, and Qdrant semantic vector memory).
4. **Autonomous Goal Planner (`core/planning/`):** Directed Acyclic Graph (DAG) executor that decomposes complex goals into parallel topological execution waves with automatic outcome verifiers.
5. **Computer Vision & OCR (`modules/vision/`):** Instant screen capture, OCR error signature detection, and multi-modal technical explanation.
6. **Voice & Audio (`modules/voice/`):** WebRTC/VAD voice activity detection, wake-word matching (*"Hey JARVIS"*), and neural speech synthesis.
7. **Security Guardrail Engine (`core/security/`):** 3-level permission hierarchy (Level 1 Read-Safe, Level 2 Auto-Approve, Level 3 Explicit Challenge/Approval).
8. **Mobile Companion (`mobile/`):** React Native / Expo companion app with biometrics and secure WebSocket bridge.

---

## 🚀 Quick Start (Windows 11)

### Option 1: 1-Click Startup (Recommended)
Simply double-click:
```cmd
start_jarvis.bat
```
*Or run via PowerShell:*
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_jarvis.ps1
```

### Option 2: Manual Development Setup

1. **Clone & Configure Environment:**
   ```bash
   cp .env.example .env
   ```
2. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Install Frontend Dependencies:**
   ```bash
   cd ui
   npm install
   cd ..
   ```
4. **Launch Backend Server:**
   ```bash
   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
   ```
5. **Launch Frontend HUD:**
   ```bash
   npm --prefix ui run dev
   ```
6. **Access Interfaces:**
   - **JARVIS HUD:** [http://localhost:5173/](http://localhost:5173/)
   - **Interactive API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## ⚙️ Environment Configuration (`.env`)

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `JARVIS_HOST` | `127.0.0.1` | Host address for FastAPI backend |
| `JARVIS_PORT` | `8000` | Port for FastAPI backend |
| `DATABASE_URL` | `sqlite:///./jarvis.db` | SQLite database connection string |
| `QDRANT_STORAGE_PATH` | `./storage/vector_data` | Persistent semantic vector storage directory |
| `OPENAI_API_KEY` | *(optional)* | OpenAI API key for GPT models |
| `ANTHROPIC_API_KEY` | *(optional)* | Anthropic API key for Claude models |
| `GEMINI_API_KEY` | *(optional)* | Google Gemini API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama daemon endpoint |
| `DEFAULT_LOCAL_MODEL` | `llama3.2:3b` | Default Ollama LLM model |
| `DEFAULT_PERMISSION_LEVEL` | `1` | Startup security clearance level |
| `AUTO_APPROVE_LEVEL_2` | `true` | Auto-approve standard operations |
| `LEVEL_3_TIMEOUT_SECONDS` | `60` | Security challenge timeout |

---

## 🧪 Testing

Run the full automated unit and integration test suite:
```bash
python -m pytest tests/unit/ -v
```
All **59 tests** across all 12 modules pass with 100% coverage.

---

## 🛡️ Security Hierarchy

- **Level 1 (Read-Safe):** Telemetry queries, file listings, document reading, and conversations are auto-approved without friction.
- **Level 2 (Active Operations):** Application launching, file organization, and web searches execute with toast notifications.
- **Level 3 (Guarded / Destructive):** System commands, shell scripts, disk modifications, and device restarts generate an interactive challenge ID requiring explicit user confirmation.

---

## 📱 Mobile Companion

The companion app is located in `mobile/`. To run on your Android/iOS device:
```bash
cd mobile
npm install
npx expo start
```
Scan the QR code in the Expo Go app to pair securely with your host laptop.
