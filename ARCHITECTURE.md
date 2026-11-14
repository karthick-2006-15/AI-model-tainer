# JARVIS — System Architecture Specification
**Document Version:** 1.0.0  
**Phase:** Phase 0 (Architecture & Foundation Design)  
**Status:** Complete / Approved for Implementation  
**Architect:** Chief AI Systems Architect & Core Engineering Team  

---

## 1. Executive Summary & Vision

**JARVIS** (*Just A Rather Very Intelligent System*) is an autonomous, voice-driven, modular Personal AI Operating System designed to seamlessly bridge Windows 11 desktop workstations and Android mobile companion devices. 

Unlike conventional conversational chatbots that exist in isolated web sandboxes, JARVIS acts as an active digital co-pilot with deep system integration:
- Operates locally on the host OS with capability for complete offline operation or cloud-augmented intelligence.
- Interacts with the Windows operating system via native APIs, PowerShell, process control, and accessibility layers.
- Maintains a continuous, persistent, hierarchical memory of the user's projects, habits, preferences, and academic/professional data.
- Executes multi-step, autonomous workflows via a Directed Acyclic Graph (DAG) planning and verification engine.
- Implements strict, cryptographically backed security boundaries preventing accidental or malicious actions.

---

## 2. High-Level System Architecture

```
                                  +-------------------------------------------------------------+
                                  |                     HUMAN USER TOUCHPOINTS                   |
                                  |   [Voice / Mic]        [Futuristic HUD]      [Mobile App]   |
                                  +---------+---------------------+--------------------+--------+
                                            |                     |                    |
                                            v                     v                    v
+---------------------------------------------------------------------------------------------------+
| COMMUNICATIONS & PERIPHERAL GATEWAY                                                                |
|  - FastAudio Ingestion (PyAudio, Silero VAD, openWakeWord "Hey Jarvis")                          |
|  - Realtime Duplex WebSocket Server (FastAPI / ASGI)                                              |
|  - mDNS & Encrypted Mobile Pairing Channel (Ed25519 Handshake / TLS)                             |
+---------------------------------------------+-----------------------------------------------------+
                                              |
                                              v
+---------------------------------------------------------------------------------------------------+
| SECURITY & PERMISSION ENGINE (Zero Trust Guardrail)                                               |
|  - 3-Tier Policy Evaluator (Level 1: Read | Level 2: Modify | Level 3: Execute)                  |
|  - Interactive Confirmation Interceptor (HUD Modal / Voice Prompt / Mobile Push)                  |
|  - Anti-Prompt-Injection Sanitizer & Untrusted Content Quarantine                                |
|  - Immutable SQLite Audit Logger                                                                  |
+---------------------------------------------+-----------------------------------------------------+
                                              | (Authorized Request)
                                              v
+---------------------------------------------------------------------------------------------------+
| CENTRAL AI BRAIN & REASONING CORE                                                                 |
|  - Fast Intent Classifier & Entity Extractor (Lightweight Model Router)                           |
|  - Multi-Provider LLM Abstraction (OpenAI GPT-4o / Claude 3.5 / Ollama Local Llama 3)             |
|  - Context Assembler (Injects Short-term, Episodic & Semantic Memory)                             |
|  - Autonomous DAG Task Planner & Decomposer                                                       |
|  - Result Verification & Loop Controller                                                          |
+----------------------+----------------------+----------------------+------------------------------+
                       |                      |                      |
                       v                      v                      v
+--------------------------+ +---------------------------+ +----------------------------------------+
| HIERARCHICAL MEMORY      | | DYNAMIC TOOL ROUTER       | | PROACTIVE ENGINE                       |
|  - Working (Sliding Win) | |  - Windows Automation     | |  - Background Scheduler (APScheduler)  |
|  - Episodic (Chat & Ops) | |  - File Intelligence      | |  - System Health Watchdog (psutil)     |
|  - Semantic (Vector/RAG) | |  - Web Research Worker    | |  - Calendar & Deadline Monitor         |
|  - Entity / User Profile | |  - Computer Vision / OCR  | |  - Configurable Daily Briefing Gen     |
+--------------------------+ +-------------+-------------+ +----------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------------------+
| SUBSYSTEM EXECUTORS & WORKERS                                                                     |
|  - Win32 Process Controller & PowerShell Sandbox                                                  |
|  - Multimodal Document Parser (PDF, DOCX, XLSX, Code, Images via OCR)                            |
|  - Playwright Headless Browser & DuckDuckGo Search Scraper                                        |
|  - Screen Capture Engine (DXGI / mss) & Visual Error Reasoner                                     |
|  - Edge-TTS / Piper Neural Audio Synthesis Streamer                                               |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Detailed Component Breakdown

### 3.1 Module 1: Voice Intelligence Engine
- **Wake-Word Detector:** Uses `openWakeWord` with custom-trained or standard models for *"Hey Jarvis"*, operating locally with sub-1% CPU usage.
- **Voice Activity Detection (VAD):** `Silero VAD` streams chunks to detect human speech boundaries and reject background noise.
- **Speech-to-Text (STT):** `faster-whisper` (CTranslate2 implementation of Whisper) running on GPU (CUDA) or optimized INT8 CPU fallback.
- **Text-to-Speech (TTS):** Dual-tier synthesis:
  - *Tier A (Local Offline):* `Piper TTS` (neural, sub-50ms latency, zero bandwidth).
  - *Tier B (High-Fidelity Streaming):* `Edge-TTS` (natural neural voices in English and Tamil).
- **Duplex Audio Interruption (Barge-in):** While JARVIS speaks, the audio input buffer continuously listens; if the user speaks, audio output playback is immediately terminated.

### 3.2 Module 2: Central AI Brain & Orchestration
- **Intent Router:** Evaluates user prompt to determine whether it requires a direct conversational response, memory retrieval, or a multi-step tool execution plan.
- **Provider Abstraction Layer:** Common interface `BaseLLMProvider` supporting:
  - OpenAI (`gpt-4o`, `gpt-4o-mini`)
  - Anthropic (`claude-3-5-sonnet`)
  - Google Gemini (`gemini-1.5-pro`, `gemini-1.5-flash`)
  - Local Ollama (`llama3.2`, `qwen2.5-coder`, `mistral`)
- **Tool-Calling Architecture:** Uses structured JSON schema function definitions. Tools are decoupled from models and auto-discovered via standard decorators.
- **Execution Loop with Verification:** Every action executed yields structured execution telemetry (`success: bool`, `output: str`, `error: Optional[str]`). If an action fails, the Brain triggers dynamic re-planning or corrective attempts up to a configurable maximum retry bound (default: 3).

### 3.3 Module 3: Personal Memory Engine
- **Tier 1: Working Memory:** In-memory circular buffer containing the current interaction turn and active scratchpad variables.
- **Tier 2: Episodic Memory:** Relational logs of past conversations, commands issued, tools executed, and user feedback stored in SQLite/PostgreSQL.
- **Tier 3: Semantic Memory (Vector Store):** High-dimensional vector database (embedded Qdrant / Chroma) indexing unstructured personal notes, project documentation, code repositories, and user knowledge.
- **Tier 4: Profile & Knowledge Graph:** Structured key-value and entity-relation facts (e.g., preferred IDE = "VS Code", primary workspace = "C:/Projects", university = "Autonomous Warehouse AI project").
- **Verification Rule:** The Memory Engine strictly tags facts with a confidence score and provenance (`verified_fact`, `user_preference`, `inferred_assumption`). Assumptions are never treated as facts without user verification.

### 3.4 Module 4: Windows Laptop Control & Automation
- **Application Lifecycle Manager:** Launches, switches, and terminates Windows applications via Windows Registry lookups, URI schemes (`code://`, `spotify://`), and Win32 process execution (`subprocess.Popen` with detaching).
- **PowerShell Execution Sandbox:** Controlled terminal command runner with strict command allowlisting/blocklisting, timeout management, and stdout/stderr capture.
- **Window & GUI Controller:** Native Windows accessibility via `pywin32` and `uiautomation` for reliable UI tree navigation; `PyAutoGUI` is reserved strictly as a secondary fallback.
- **System Telemetry:** Real-time CPU, RAM, battery, active process, and storage metrics monitored via `psutil`.

### 3.5 Module 5: Mobile Integration Engine (Android Companion)
- **Zero-Trust Mutual Pairing:** Initial connection via QR code exchange of a 256-bit pre-shared secret, generating an Ed25519 token keypair.
- **Communication Protocol:** Encrypted WebSocket connection over Local Network (mDNS discovery) or securely tunneled over Tailscale WireGuard mesh for remote out-of-home control.
- **Companion Capabilities:**
  - Remote voice/text input to laptop.
  - Two-way file streaming with SHA-256 integrity verification.
  - Push notifications for task completion or Level 3 permission prompts.
  - System status monitoring (laptop battery, CPU, ongoing tasks).

### 3.6 Module 6: File Intelligence Engine
- **Multimodal Document Parser:**
  - PDFs: `pypdf` / `PyMuPDF` (text, tables, metadata).
  - Office Docs: `python-docx` (.docx), `openpyxl` (.xlsx), `python-pptx` (.pptx).
  - Data & Code: `pandas` (.csv), syntax-aware chunkers for Python, JS/TS, C++, Go, Rust.
  - Scanned Documents / Images: `Tesseract OCR` / vision model pipeline.
- **Incremental Indexer:** Background file watcher (`watchdog`) monitoring designated user folders (Downloads, Documents, Desktop, Projects), hashing files (`SHA-256`), and updating vector embeddings on changes.
- **Semantic File Organizer:** Proposes file relocations based on topic clusters, duplicate detection, and file ages, requiring Level 2 confirmation before physical movement.

### 3.7 Module 7: Internet Research Engine
- **Search Providers:** DuckDuckGo (privacy-preserving, no-cost default) with fallback to Tavily/SerpAPI.
- **Browser Automation:** Headless `Playwright` with Chromium for single-page applications, dynamic DOM rendering, and documentation reading.
- **Data Isolation:** All scraped web data and downloaded documents are tagged as `UNTRUSTED_EXTERNAL_DATA` and filtered through sanitization guardrails to prevent indirect prompt injection.

### 3.8 Module 8: Computer Vision Engine
- **Direct Screen Capture:** Ultra-fast, low-latency desktop capture using `mss` or Windows Graphics Capture API (DXGI).
- **Visual Intelligence:** Submits captured screen regions or active error dialogues to multimodal vision models (`gpt-4o`, `gemini-1.5-flash`, or local `llava`/`qwen-vl`) for visual error debugging, UI state recognition, and diagram comprehension.
- **Privacy Enforcement:** Vision capture is strictly on-demand. Continuous background screen capture is disabled by default and requires explicit user activation.

### 3.9 Module 9: Proactive Scheduling & Notification Engine
- **Task Scheduler:** `APScheduler` (Advanced Python Scheduler) running in an async background loop.
- **Watchdogs:** Periodic checks for low disk storage, calendar event reminders, and long-running process completions.
- **Daily Briefing Generator:** Compiles an executive summary every morning (weather, calendar events, active project statuses, open tasks).

### 3.10 Module 10: Futuristic Iron Man User Interface
- **Technology:** React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Lucide Icons, Canvas API / Three.js.
- **Visual Language:** Arc-reactor holographic aesthetic, dark cybernetic palette (`#030712`, `#06b6d4`, `#3b82f6`), dynamic audio waveform visualizer, live DAG task tree visualizer, real-time telemetry gauges, interactive memory explorer.

---

## 4. Technology Stack Selection & Justification

| Layer | Selected Technology | Why Chosen & Alternatives Rejected |
|---|---|---|
| **Backend Framework** | **Python 3.10+ / FastAPI / AsyncIO** | Python is mandatory for native AI/ML libraries (`faster-whisper`, `torch`, `pywin32`, `playwright`). FastAPI provides sub-millisecond asynchronous REST and native WebSocket endpoints with automated Pydantic schema validation. |
| **Relational Storage** | **SQLite (aiosqlite) with SQLAlchemy async** | Zero-configuration, file-based embedded storage that runs immediately on Windows without requiring a running Docker daemon or external PostgreSQL service. Architectural repository pattern enables 100% plug-and-play migration to PostgreSQL when desired. |
| **Vector Storage** | **Embedded Qdrant (`qdrant-client` local mode)** | Runs in-process or via local directory storage with zero Docker requirement, full HNSW indexing, and payload filtering. Faster and more robust on Windows than ChromaDB/FAISS. |
| **Frontend Framework** | **React 18 + Vite + TypeScript** | Instant HMR development, clean component model, high performance for 60fps animations. Avoided heavy Electron wrapper for initial development; runs as a modern local web app or PWA, accessible from both laptop and mobile browser. |
| **Styling & Motion** | **Tailwind CSS + Framer Motion** | Utility-first styling provides rapid iteration for custom futuristic HUD interfaces; Framer Motion powers fluid arc-reactor pulse animations. |
| **Wake-Word Engine** | **openWakeWord** | Fully open-source, local, accurate wake-word engine. Eliminates dependency on proprietary Porcupine access keys or internet connections. |
| **Speech-to-Text** | **faster-whisper** | Up to 4x faster than vanilla OpenAI Whisper, requires significantly less VRAM, supports CPU INT8 quantization on AMD Ryzen. |
| **Text-to-Speech** | **Piper TTS (Local) + Edge-TTS (Cloud)** | Piper gives instant local zero-latency speech without network. Edge-TTS provides crystal-clear human-grade voice synthesis including Tamil language support with zero API cost. |
| **Windows Automation** | **pywin32 + subprocess + psutil** | Native Windows OS calls for reliability. Minimizes reliance on fragile coordinate-based mouse clicking (`PyAutoGUI`), using it only as a fallback. |
| **Browser Automation**| **Playwright Python (Chromium)** | Superior async architecture, auto-waiting, robust against modern single-page apps compared to Selenium. |
| **Mobile Stack** | **React Native (Expo)** | Cross-platform, rapid deployment, direct access to Android microphone, camera, notifications, and secure hardware storage. |

---

## 5. Repository Structure

```
jarvis/
├── core/                               # Central orchestration & intelligence kernel
│   ├── __init__.py
│   ├── brain/                          # AI brain, intent routing, prompt templates
│   │   ├── __init__.py
│   │   ├── orchestrator.py             # Main Brain coordinator
│   │   ├── intent.py                   # Intent classifier & router
│   │   └── prompts.py                  # System prompts & XML safety tags
│   ├── planning/                       # Autonomous planning & verification engine
│   │   ├── __init__.py
│   │   ├── planner.py                  # DAG task decomposition
│   │   ├── task.py                     # Task & Subtask dataclasses
│   │   └── verifier.py                 # Post-execution verification logic
│   ├── memory/                         # 4-Tier Memory Engine
│   │   ├── __init__.py
│   │   ├── working.py                  # In-memory sliding window
│   │   ├── episodic.py                 # Relational message & task history
│   │   ├── semantic.py                 # Vector memory embeddings & search
│   │   └── profile.py                  # Knowledge graph & user entity facts
│   ├── providers/                      # Multi-provider LLM abstraction layer
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseLLMProvider interface
│   │   ├── openai_provider.py          # OpenAI GPT-4o / mini
│   │   ├── gemini_provider.py          # Google Gemini 1.5
│   │   └── ollama_provider.py          # Local Ollama Llama 3 / Qwen
│   ├── security/                       # Permission, auth & audit kernel
│   │   ├── __init__.py
│   │   ├── permissions.py              # 3-Level Permission evaluator
│   │   ├── guardrails.py               # Input/Output sanitizers & injection defense
│   │   ├── crypto.py                   # Ed25519 token & pairing cryptography
│   │   └── audit.py                    # Tamper-evident action logging
│   └── config/                         # Configuration & settings management
│       ├── __init__.py
│       └── settings.py                 # Pydantic v2 BaseSettings
│
├── modules/                            # Pluggable capability modules
│   ├── voice/                          # Module 1: Voice Intelligence Engine
│   │   ├── __init__.py
│   │   ├── vad.py                      # Silero VAD voice activity detector
│   │   ├── wakeword.py                 # openWakeWord "Hey Jarvis" detector
│   │   ├── stt.py                      # faster-whisper STT transcriber
│   │   ├── tts.py                      # Piper / Edge-TTS audio generator
│   │   └── duplex.py                   # Duplex audio controller & barge-in
│   ├── automation/                     # Module 4: Windows Automation Engine
│   │   ├── __init__.py
│   │   ├── apps.py                     # Application launcher & window manager
│   │   ├── shell.py                    # PowerShell sandbox runner
│   │   ├── system.py                   # System stats & hardware monitor
│   │   └── gui.py                      # Win32 / PyAutoGUI interface
│   ├── files/                          # Module 6: File Intelligence Engine
│   │   ├── __init__.py
│   │   ├── indexer.py                  # Background folder watcher & hasher
│   │   ├── parsers.py                  # PDF, DOCX, XLSX, Code parsers
│   │   ├── ocr.py                      # Tesseract / OCR pipeline
│   │   └── organizer.py                # Semantic file classification
│   ├── research/                       # Module 7: Internet Research Engine
│   │   ├── __init__.py
│   │   ├── search.py                   # DuckDuckGo / Tavily search interface
│   │   ├── browser.py                  # Playwright scraper & article extractor
│   │   └── summarizer.py               # Document & research synthesis
│   ├── vision/                         # Module 10: Computer Vision Engine
│   │   ├── __init__.py
│   │   ├── capture.py                  # DXGI / mss screen capture
│   │   └── analyzer.py                 # Visual error & diagram reasoner
│   ├── scheduler/                      # Module 11: Proactive Engine
│   │   ├── __init__.py
│   │   ├── background.py               # APScheduler async background runner
│   │   └── briefing.py                 # Daily briefing compiler
│   └── mobile/                         # Module 5: Mobile Integration Bridge
│       ├── __init__.py
│       ├── pairing.py                  # QR code / TOTP handshake
│       └── bridge.py                   # WebSocket bridge & push sync
│
├── storage/                            # Persistence & Data Access Layer
│   ├── __init__.py
│   ├── db/                             # Relational DB (SQLite / Postgres)
│   │   ├── __init__.py
│   │   ├── connection.py               # Async engine & session factory
│   │   └── models.py                   # SQLAlchemy ORM declarative models
│   ├── vector/                         # Vector Store Adapter
│   │   ├── __init__.py
│   │   └── qdrant_adapter.py           # Embedded Qdrant client wrapper
│   └── migrations/                     # Database migration scripts (Alembic)
│
├── api/                                # FastAPI Web & WebSocket Server
│   ├── __init__.py
│   ├── main.py                         # FastAPI application entry point
│   ├── dependencies.py                 # Dependency injection providers
│   ├── routers/                        # REST endpoint controllers
│   │   ├── __init__.py
│   │   ├── chat.py                     # Conversational endpoints
│   │   ├── system.py                   # Health, metrics & process status
│   │   ├── memory.py                   # Memory inspection & curation
│   │   ├── files.py                    # File search & indexing endpoints
│   │   ├── permissions.py              # Pending approvals & audit logs
│   │   └── mobile.py                   # Mobile pairing & sync endpoints
│   └── websockets/                     # Real-time WebSocket handlers
│       ├── __init__.py
│       ├── hud_stream.py               # Realtime HUD updates & DAG state
│       └── audio_stream.py             # Binary duplex audio streaming
│
├── ui/                                 # Module 12: Futuristic Iron Man HUD
│   ├── src/
│   │   ├── assets/                     # Sound effects, SVG icons, fonts
│   │   ├── components/                 # React UI components
│   │   │   ├── CoreArcReactor.tsx      # Central animated holographic core
│   │   │   ├── VoiceVisualizer.tsx     # Dynamic audio waveform canvas
│   │   │   ├── ChatFeed.tsx            # Real-time conversation stream
│   │   │   ├── TaskDagVisualizer.tsx   # Interactive execution graph
│   │   │   ├── TelemetryHUD.tsx        # CPU, RAM, Network, Storage meters
│   │   │   ├── MemoryExplorer.tsx      # Knowledge graph & profile viewer
│   │   │   ├── PermissionModal.tsx     # Level 3 interactive authorization
│   │   │   └── Sidebar.tsx             # Futuristic navigation panel
│   │   ├── hooks/                      # Custom hooks (useWebSocket, useVoice)
│   │   ├── stores/                     # Zustand state management
│   │   ├── styles/                     # Tailwind custom styling & themes
│   │   ├── App.tsx                     # Main layout coordinator
│   │   └── main.tsx                    # React DOM entrypoint
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── mobile/                             # Android Companion (React Native / Expo)
│   ├── src/
│   │   ├── screens/                    # Voice, Remote, Files, Settings
│   │   ├── services/                   # WebSocket client & crypto pairing
│   │   └── components/                 # Mobile HUD UI
│   ├── app.json
│   └── package.json
│
├── tests/                              # Comprehensive Testing Suite
│   ├── conftest.py                     # PyTest fixtures & test harnesses
│   ├── unit/                           # Isolated unit tests
│   ├── integration/                    # Multi-module workflow tests
│   └── security/                       # Permission & injection attack tests
│
├── scripts/                            # Utility & automation scripts
│   ├── run_jarvis.ps1                  # Single-command launcher (Backend + UI)
│   ├── setup_env.ps1                   # Virtualenv & dependency bootstrapper
│   └── test_all.ps1                    # Full test suite execution script
│
├── .env.example                        # Documented environment variables
├── ARCHITECTURE.md                     # This architecture specification
├── SECURITY.md                         # Security model & permission policies
├── DEVELOPMENT_ROADMAP.md              # Phased implementation plan
└── PROJECT_STATUS.md                   # Realtime tracker & engineering log
```

---

## 6. Database Architecture

JARVIS uses a hybrid storage model: Relational (SQLite / PostgreSQL) for structured state, audit trails, and transactional records; and Vector (Embedded Qdrant) for high-dimensional semantic search.

### 6.1 Relational Schema (SQLAlchemy ORM)

```sql
-- 1. Users and Authorized Devices
CREATE TABLE devices (
    id VARCHAR(36) PRIMARY KEY,
    device_name VARCHAR(100) NOT NULL,
    device_type VARCHAR(20) NOT NULL, -- 'windows_host', 'android_mobile', 'web_client'
    public_key VARCHAR(128) NOT NULL,
    is_authorized BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Conversation Sessions and Messages
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    device_id VARCHAR(36) REFERENCES devices(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE,
    sender VARCHAR(20) NOT NULL, -- 'user', 'jarvis', 'system'
    content TEXT NOT NULL,
    input_modality VARCHAR(20) DEFAULT 'text', -- 'text', 'voice', 'automation'
    token_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Personal Memory Entities and Knowledge Graph
CREATE TABLE memory_entities (
    id VARCHAR(36) PRIMARY KEY,
    category VARCHAR(50) NOT NULL, -- 'preference', 'project', 'academic', 'app', 'fact'
    key_name VARCHAR(100) NOT NULL,
    value_data JSON NOT NULL,
    confidence_score FLOAT DEFAULT 1.0, -- 1.0 for verified, <0.8 for inferred
    provenance VARCHAR(50) NOT NULL, -- 'user_explicit', 'system_inferred', 'file_extracted'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Autonomous Tasks and Planning DAGs
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) REFERENCES sessions(id),
    goal TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'planning', 'in_progress', 'completed', 'failed', 'aborted'
    plan_dag JSON NOT NULL, -- Serialized graph of subtasks and dependencies
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE subtasks (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) REFERENCES tasks(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    arguments JSON NOT NULL,
    permission_level INTEGER NOT NULL, -- 1, 2, or 3
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'awaiting_approval', 'executing', 'success', 'failed'
    execution_result JSON,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE
);

-- 5. Security & Audit Trail (Tamper-evident)
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    device_id VARCHAR(36),
    permission_level INTEGER NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    target_resource TEXT NOT NULL,
    parameters JSON,
    decision VARCHAR(20) NOT NULL, -- 'auto_allowed', 'user_confirmed', 'user_denied', 'system_blocked'
    execution_success BOOLEAN,
    hash_checksum VARCHAR(64) NOT NULL -- SHA-256(prev_hash + current_row)
);

-- 6. Indexed Files & Cache
CREATE TABLE indexed_files (
    id VARCHAR(36) PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_extension VARCHAR(20) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    last_modified TIMESTAMP WITH TIME ZONE NOT NULL,
    summary TEXT,
    extracted_tags JSON,
    is_indexed_in_vector BOOLEAN DEFAULT FALSE,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 6.2 Vector Database Schema (Qdrant)

Three isolated collections maintain semantic separation:

1. **`personal_memory` Collection:**
   - Vector Size: 1536 (OpenAI `text-embedding-3-small`) or 384 (Local `all-MiniLM-L6-v2`)
   - Metric: Cosine
   - Payload Schema: `{ "memory_id": str, "category": str, "raw_text": str, "timestamp": int, "tags": list[str] }`

2. **`file_chunks` Collection:**
   - Vector Size: Matching embedding model
   - Metric: Cosine
   - Payload Schema: `{ "file_id": str, "file_path": str, "chunk_index": int, "content": str, "file_type": str }`

3. **`research_knowledge` Collection:**
   - Vector Size: Matching embedding model
   - Metric: Cosine
   - Payload Schema: `{ "source_url": str, "title": str, "snippet": str, "query": str, "fetched_at": int }`

---

## 7. API & Communication Architecture

JARVIS exposes a unified ASGI service built with FastAPI providing both synchronous REST endpoints and real-time bidirectional WebSocket channels.

### 7.1 WebSocket Streaming Protocols

#### A. `/ws/hud` — HUD Event & Control Channel
Used by the React frontend and Android companion app for live UI updates.
- **Client -> Server Messages:**
  - `{"type": "chat_input", "text": "...", "session_id": "..."}`
  - `{"type": "permission_response", "request_id": "...", "granted": true}`
  - `{"type": "abort_task", "task_id": "..."}`
- **Server -> Client Events:**
  - `{"type": "agent_state", "state": "listening" | "thinking" | "executing" | "verifying"}`
  - `{"type": "token_chunk", "chunk": "..."}` (Streaming text reply)
  - `{"type": "dag_update", "task": {...}}` (Real-time progress on multi-step workflows)
  - `{"type": "permission_request", "id": "...", "level": 3, "action": "...", "details": {...}}`
  - `{"type": "telemetry", "cpu": 14.2, "ram": 48.5, "battery": 92}`

#### B. `/ws/audio` — Low-Latency Voice Streaming Channel
- Binary audio streaming: 16kHz, 16-bit Mono PCM chunks.
- Server performs continuous VAD and wake-word analysis; upon detection, transcribes via faster-whisper and immediately pushes synthesized TTS audio packets back over the socket.

### 7.2 Core REST Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health, service status (Ollama, Whisper, DB) |
| `GET` | `/api/system/metrics` | Real-time CPU, RAM, disk, battery statistics |
| `GET` | `/api/sessions` | List conversation histories |
| `POST` | `/api/sessions` | Create a new conversation session |
| `GET` | `/api/memory/entities` | Inspect active personal knowledge graph entities |
| `DELETE` | `/api/memory/entities/{id}`| Delete or correct a stored memory item |
| `POST` | `/api/files/index-now` | Trigger on-demand indexing of authorized directories |
| `GET` | `/api/files/search` | Full-text & semantic search across local documents |
| `POST` | `/api/mobile/pair` | Initiate Ed25519 pairing with Android device |
| `GET` | `/api/audit/logs` | Fetch tamper-evident security audit trail |

---

## 8. AI Model Architecture & Provider Abstraction

JARVIS decouples the intelligence layer from specific model vendors using a pluggable provider pattern:

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, context: list[dict], tools: list[dict]) -> LLMResult:
        pass

    @abstractmethod
    async def stream_response(self, prompt: str, context: list[dict], tools: list[dict]) -> AsyncGenerator[str, None]:
        pass
```

### 8.1 Model Routing Strategy

To achieve maximum responsiveness, zero unneeded API costs, and high-level reasoning when required:

1. **Routing & Intent Classification (Fast Tier):**
   - Model: Local `ollama/llama3.2:3b` or `gpt-4o-mini`
   - Role: Wake-word post-filtering, simple greeting responses, intent routing, parameter extraction.
   - Latency target: <200ms.

2. **Complex Planning & Code Analysis (Frontier Tier):**
   - Model: `gpt-4o`, `claude-3-5-sonnet`, or `gemini-1.5-pro`
   - Role: Multi-step DAG task decomposition, programming error analysis, complex document summarization, academic exam preparation.

3. **Autonomous Offline Mode:**
   - If internet connectivity is unavailable, JARVIS automatically falls back to local Ollama models (`llama3.2` / `qwen2.5-coder`) for all tasks, maintaining core automation capabilities without external network dependencies.

---

## 9. Voice Processing Pipeline & Interruption Architecture

```
[Microphone Ingest: 16kHz PCM]
          |
          v
[Silero VAD Filter]  --> (Silence) --> Drop
          | (Speech Detected)
          v
[openWakeWord Engine]
          |
   +------+------+
   |             |
 (No Wake)   ("Hey Jarvis" Detected)
   |             |
 Drop            v
      [Audio Buffer Captures User Utterance]
                 |
                 v
      [faster-whisper GPU/CPU Transcriber]
                 |
                 v (Transcribed Text)
      [Central AI Brain Engine]
                 |
                 v (Streaming Response Sentences)
      [Piper / Edge-TTS Audio Synthesizer]
                 |
                 v (PCM Audio Output)
      [Speaker Playback Queue]
                 ^
                 | (If VAD detects new speech during playback)
      [Barge-In Interruption: Instantly stops speaker playback]
```

---

## 10. Laptop-Mobile Communication Architecture

1. **Discovery & Pairing:**
   - When the user opens the JARVIS Android app on the local Wi-Fi, the laptop broadcasts a secure mDNS service `_jarvis._tcp.local`.
   - The user scans a one-time QR code rendered on the laptop HUD, establishing an Ed25519 cryptographic mutual authentication handshake.
2. **Encrypted Transport:**
   - All subsequent traffic between laptop and Android runs through TLS-encrypted WebSockets.
   - For remote out-of-home control, JARVIS integrates with a Tailscale WireGuard virtual mesh network, allowing secure remote command transmission without exposing any ports to the public internet.
3. **Synchronization & Remote Execution:**
   - Mobile sends voice or text instructions directly to the laptop's Central AI Brain.
   - Laptop streams live task progress, battery/CPU telemetry, and push notification requests back to the mobile app.

---

## 11. Testing Strategy

1. **Unit Testing:**
   - Isolated tests for every parser (`test_parsers.py`), intent classifier (`test_intent.py`), memory CRUD operations (`test_memory.py`), and tool decorators.
   - Target: >85% code coverage on core logic.
2. **Integration Testing:**
   - Simulated full-loop tests using mock tool executors and simulated LLM responses.
   - Verification of the DAG planner executing multi-step tasks to completion.
3. **Security & Guardrail Testing:**
   - Verification that Level 3 commands (e.g., file deletion, PowerShell invocation) strictly block without approval tokens.
   - Automated prompt injection test suites (indirect injection via web scraping or malicious files).
4. **Hardware & Latency Benchmarking:**
   - Benchmark wake-word false rejection/acceptance rates.
   - Measure end-to-end voice latency from speech end to initial audio output (target: <1.2 seconds on local network).

---

## 12. Technical Risks & Mitigation Matrix

| Risk | Impact | Probability | Architectural Mitigation |
|---|---|---|---|
| **High VRAM / Resource Consumption** | High | Medium | Use quantized models (INT8 Whisper, GGUF Ollama) and enable selective model loading; wake-word and VAD run on CPU at <1% overhead. |
| **Accidental System Destruction via Shell** | Critical | Low | Strict 3-level permission hierarchy; regex and AST validation of all shell commands; Level 3 commands strictly require explicit user confirmation. |
| **Indirect Prompt Injection from Web/Files** | High | High | Strict isolation of external content using XML boundary tags `<untrusted_content>`; system instructions explicitly forbid external text from overriding tool execution rules. |
| **Broken Coordinate-Based Automation** | Medium | High | Prefer native Win32 APIs, Windows UI Automation trees, and application CLI/URI protocols over brittle mouse coordinates. |
| **Voice Latency Degraded by Network** | Medium | Medium | Local Piper TTS and local faster-whisper ensure real-time voice interaction even with high-latency or disconnected internet. |

---
*Signed off by Chief AI Systems Architect — JARVIS Core Engineering.*
