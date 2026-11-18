# JARVIS AI — COMPLETE FEATURE INVENTORY & CAPABILITY CATALOGUE

## 1. Overview
This document provides an exhaustive inventory of all functional capabilities, REST API endpoints, WebSocket channels, tool definitions, and voice interactions supported by the JARVIS AI platform.

---

## 2. Functional Domains & Capabilities

### Domain 1: Multi-Turn AI Brain & Reasoning
- Dynamic multi-turn conversational context with SQLite history retrieval.
- Autonomous intent classification (chat vs external action vs multi-step plan).
- Quad-tier provider fallback: Google Gemini API -> Anthropic Claude -> Local Ollama (llama3.2:3b) -> Safe Mock.
- Structured tool schema calling and parameter coercion.
- Error self-correction and retry loops.

### Domain 2: Advanced Voice & Audio Subsystem
- Always-on microphone listening with continuous noise calibration.
- Wake-word activation on "Hey Jarvis", "Jarvis", "Ok Jarvis", "Hi Jarvis".
- Central `VoiceStateMachine` managing 7 states: `IDLE`, `LISTENING`, `PROCESSING`, `THINKING`, `SPEAKING`, `INTERRUPTED`, `ERROR`.
- Acoustic duplex barge-in: instantaneous audio termination (<50ms) upon user speech onset.
- Dual-tier Speech-to-Text: Local neural Whisper + Google STT fallback.
- Dual-tier Text-to-Speech: Edge-TTS neural high-fidelity streaming in English & Tamil + Windows SAPI5 pyttsx3 fallback.
- Continuous multi-turn conversation window (15s timeout without repeating wake-word).
- Multilingual Tamil, Tanglish, Hindi, Hinglish, and English parsing and localized vocal responses.

### Domain 3: Authentic Spotify Integration
- Zero simulation: 100% real playback state inspection via Windows GSMTC and Web API.
- Track search by song title, artist, album, and playlist.
- Playback control: play, pause, resume, next track, previous track, volume adjustments (0-100), mute.
- Track metadata extraction: track name, artist name, album name, album artwork URL, duration, progress.
- Active device detection and automatic desktop process launch via portable `%APPDATA%` paths.
- Floating robot avatar emotional synchronization during playback (happy on play, idle on pause, thinking on search).

### Domain 4: Universal Windows Desktop Automation
- Application discovery across Start Menu, Registry, UWP AppX Store packages, App Aliases, and PATH variables (140+ applications).
- Application lifecycle: launch, focus, verify, graceful termination, and force close.
- Window management: list open windows, bring window to front, maximize, minimize, restore.
- UI Automation (UIA) tree inspection and native accessibility controls.
- Keyboard and mouse interaction: coordinate clicks, typing text, keyboard shortcuts (`Alt+Tab`, `Win+D`, `Ctrl+C`).
- Full-screen and window-specific screenshot capture.
- System controls: lock workstation (`LockWorkStation`), master volume controls, sleep, restart, shutdown (with Level 3 confirmation).
- Sandboxed PowerShell command execution with AST syntax guardrails blocking destructive commands.

### Domain 5: Intelligent Browser Automation & Web Scraping
- Playwright Chromium and Edge browser control with headless and headed modes.
- URL navigation, link clicking, form filling, text extraction, scrolling.
- Multi-tab management: open tab, list tabs, switch tab, close tab.
- Bot verification sentinel: detects Cloudflare Turnstile, reCAPTCHA, and hCaptcha bot gates without attempting bypass; alerts user for manual verification.
- LeetCode & Coding Practice Engine: curated problem lookup, problem description parsing, and test case extraction.

### Domain 6: Persistent Storage, Memory & DAG Planning
- SQLite relational database (`jarvis.db`) with SQLAlchemy ORM.
- Session and message history with cascading deletion endpoints.
- DAG Task Planner: goal decomposition into subtasks with wave-based concurrent execution.
- Subtask execution result persistence and restart recovery.
- Semantic vector memory and knowledge graph entity extraction.

### Domain 7: Futuristic Cybernetic HUD & Robot Avatar
- Cybernetic SVG holographic AI robot face with animated eyes, brows, mouth, polygonal facets, and compass reticles.
- 4 Holographic color themes: Classic Cyan, Arc Gold, Quantum Violet, Matrix Emerald.
- 3 Size presets: Compact Floating Widget (180px), Standard Desktop (240px), Command HUD (320px).
- Phoneme-based lip-sync animation and voice waveform visualizer.
- System telemetry panel: live CPU load, RAM usage, C: drive storage, battery percentage, active task count.
- Music control card: album artwork, playback buttons, progress bar, volume slider.
- Zero decorative or non-functional controls: all buttons wired to live backend endpoints.

---

## 3. REST API Directory

| Method | Endpoint | Description | Permission Level |
|---|---|---|---|
| `GET` | `/health` | Subsystem health status check | Public |
| `GET` | `/api/voice/status` | Current voice engine status & supported languages | Level 1 |
| `GET` | `/api/voice/voices` | Catalogue of Edge-TTS and offline voices | Level 1 |
| `POST` | `/api/voice/interrupt` | Trigger immediate acoustic barge-in / speech halt | Level 1 |
| `GET` | `/api/tasks` | List all active and recent DAG execution plans | Level 1 |
| `POST` | `/api/tasks/plan` | Decompose goal into acyclic directed graph (DAG) | Level 2 |
| `POST` | `/api/tasks/{id}/execute` | Execute prepared PlanDAG by ID | Level 2 |
| `POST` | `/api/tasks/plan-and-execute` | Plan and execute goal in a single pipeline | Level 2 |
| `GET` | `/api/tasks/{id}` | Get status and progress of specific DAG plan | Level 1 |
| `DELETE` | `/api/tasks/{id}` | Purge task plan from memory and SQLite | Level 2 |
| `GET` | `/api/sessions` | List all conversation sessions | Level 1 |
| `POST` | `/api/sessions` | Create new conversation session | Level 1 |
| `GET` | `/api/sessions/{id}` | Retrieve session message history | Level 1 |
| `DELETE` | `/api/sessions/{id}` | Delete conversation session and messages | Level 2 |
| `GET` | `/api/automation/windows` | List visible desktop application windows | Level 1 |
| `POST` | `/api/automation/windows/focus`| Bring specific window title to front | Level 2 |
| `POST` | `/api/automation/apps/launch` | Launch application or program by name | Level 2 |
| `POST` | `/api/automation/apps/close` | Terminate application process | Level 2 |
| `POST` | `/api/automation/shell` | Execute sandboxed PowerShell command | Level 3 (Guardrail) |
| `POST` | `/api/automation/challenges/resolve` | Resolve Level 3 interactive authorization challenge | Level 3 |
| `GET` | `/api/spotify/playback` | Get real-time Spotify playback status via GSMTC/API | Level 1 |
| `POST` | `/api/spotify/play` | Start playback or search and play track | Level 2 |
| `POST` | `/api/spotify/pause` | Pause active playback | Level 1 |
| `POST` | `/api/spotify/next` | Skip to next track | Level 1 |
| `POST` | `/api/spotify/previous` | Skip to previous track | Level 1 |
| `POST` | `/api/spotify/volume` | Set playback volume level (0 to 100) | Level 1 |

---

## 4. WebSocket Interface (`/ws/hud`)

- **Protocol**: JSON-over-WebSocket
- **Client Inbound Message Types**:
  - `chat_input`: `{"type": "chat_input", "text": "...", "session_id": "..."}`
  - `ping`: `{"type": "ping", "timestamp": 123456789}`
  - `abort_task`: `{"type": "abort_task", "reason": "..."}`
  - `set_avatar_state`: `{"type": "set_avatar_state", "state": "thinking", "message": "..."}`
  - `avatar_expression`: `{"type": "avatar_expression", "expression": "wink", "duration": 3.0}`
  - `avatar_lip_sync`: `{"type": "avatar_lip_sync", "amplitude": 0.85, "phoneme": "O"}`
  - `permission_response`: `{"type": "permission_response", "request_id": "...", "granted": true}`
- **Server Outbound Broadcast Types**:
  - `agent_state`: `{"type": "agent_state", "state": "speaking", "message": "..."}`
  - `voice_state`: `{"type": "voice_state", "state": "listening", "reason": "..."}`
  - `avatar_state`: `{"type": "avatar_state", "avatar": {...}}`
  - `telemetry`: `{"type": "telemetry", "data": {...}}` (broadcast every 1.0s)
  - `token_chunk`: `{"type": "token_chunk", "chunk": "...", "tool_executed": "...", "verified": true}`
  - `permission_resolved`: `{"type": "permission_resolved", "request_id": "...", "granted": true}`

---

## 5. Central Tool Registry Catalogue

1. **System & Telemetry Tools**:
   - `get_system_telemetry` (Level 1)
   - `system.get_network_status` (Level 1)
   - `system.get_startup_apps` (Level 1)
   - `system.analyze_storage` (Level 1)
   - `system.troubleshoot` (Level 1)
   - `system.lock_workstation` (Level 1)
   - `system.adjust_volume` (Level 1)
   - `system.power_action` (Level 3 - Confirmation Required)
2. **Computer Use & Desktop Tools**:
   - `computer_use.launch_application` (Level 2)
   - `computer_use.close_application` (Level 2)
   - `computer_use.list_open_windows` (Level 1)
   - `computer_use.focus_window` (Level 2)
   - `computer_use.take_screenshot` (Level 1)
   - `computer_use.click_coordinate` (Level 2)
   - `computer_use.type_text` (Level 2)
   - `computer_use.press_hotkey` (Level 2)
3. **Browser & Web Tools**:
   - `browser.open_url` (Level 2)
   - `browser.click_element` (Level 2)
   - `browser.fill_form` (Level 2)
   - `browser.extract_content` (Level 1)
   - `browser.detect_bot_challenges` (Level 1)
   - `leetcode.search_problems` (Level 1)
   - `leetcode.get_problem` (Level 1)
   - `leetcode.extract_test_cases` (Level 1)
4. **Media & Spotify Tools**:
   - `spotify.search_and_play` (Level 2)
   - `spotify.playback_control` (Level 1)
   - `spotify.get_playback_state` (Level 1)
   - `spotify.set_volume` (Level 1)
5. **Productivity & Task Tools**:
   - `productivity.create_task` (Level 2)
   - `productivity.list_tasks` (Level 1)
   - `productivity.schedule_reminder` (Level 2)
6. **Avatar & Face Tools**:
   - `avatar.set_state` (Level 1)
   - `avatar.set_expression` (Level 1)
   - `avatar.set_theme` (Level 1)
   - `avatar.get_status` (Level 1)
