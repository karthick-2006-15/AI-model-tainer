# JARVIS Holographic HUD Dashboard Specification

## 1. Dashboard Architecture Overview

The **JARVIS Holographic HUD Dashboard** is a responsive, dark glass futuristic command center built with React 18, TypeScript, Tailwind CSS, and WebSockets. It provides complete multimodal control over Windows applications, real-time voice intelligence, task orchestration, memory exploration, and avatar identity.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MARK VII // OPERATING ENVIRONMENT  |  ShieldCheck: Level 1 Read-Safe  |  FLOATING WIDGET  |  WIFI │
├──────────────┬───────────────────────────────────────────────────────────────────────────────────┤
│ SIDEBAR      │ MAIN WORKSPACE VIEW (7 TABS)                                                      │
│              │                                                                                   │
│ [✦] Avatar   │ 1. MAIN AVATAR & HUD:                                                             │
│ [🎤] Voice   │    - Central 3D Animated AI Face (JarvisAvatar)                                   │
│ [⚡] Tasks    │    - Arc Reactor Switcher                                                         │
│ [💻] Computer │    - Real-Time Command & Voice Chat Feed                                          │
│ [🧠] Memory   │    - Real-Time Hardware Telemetry Gauges                                          │
│ [📊] Monitor │                                                                                   │
│ [⚙️] Settings │ 2. VOICE INTERACTION HUB:                                                         │
│              │    - Multilingual Routing (EN, Tamil, Tanglish, Hindi)                            │
│              │    - 48 kHz Live Spectrum Waveform                                                │
│              │    - Zero-Latency Duplex Barge-in & Speech Calibration                             │
│              │                                                                                   │
│ [EMERGENCY]  │ 3. TASK MANAGEMENT & DAG PLANNER:                                                 │
│ [  ABORT  ]  │    - Goal Decomposition & Multi-Step DAG Pipeline                                 │
│              │                                                                                   │
│              │ 4. COMPUTER INTELLIGENCE:                                                         │
│              │    - Screen & Window Observer, Playwright DOM Controller, App Index (148 apps)    │
│              │                                                                                   │
│              │ 5. PERSONAL INTELLIGENCE:                                                         │
│              │    - Semantic Vector Memory Graph, User Facts, Document Intelligence              │
│              │                                                                                   │
│              │ 6. SYSTEM MONITORING:                                                             │
│              │    - CPU Cores, RAM, Storage, Process Count, Latency                              │
│              │                                                                                   │
│              │ 7. SETTINGS & CONFIGURATION:                                                      │
│              │    - Holographic Themes (Cyan, Gold, Violet, Emerald), Scaling, Boot Runner        │
└──────────────┴───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Comprehensive Tab Specifications

### Tab 1: Main Avatar & Holographic HUD (`hud`)
- **Centerpiece:** Interactive 3D Cybernetic Face (`JarvisAvatar.tsx`) displaying expressive digital eyes, natural blinking, 3D head tilts, and audio-reactive lip-sync.
- **Reactor Switcher:** Instant toggle between Avatar Face view and classic Core Arc Reactor view.
- **Telemetry Gauge:** Top-right summary displaying real-time CPU, RAM, and Disk metrics.
- **Chat Feed:** Real-time multimodal command input with voice transcript echoes, tool execution indicators, and verification badges.

### Tab 2: Voice Interaction Hub (`voice`)
- **Live Audio Visualizer:** 48,000 Hz / 16-bit PCM canvas visualizer rendering dynamic acoustic waveforms.
- **Multilingual Mode:** One-click language switching between English (US/UK), Tamil (தமிழ்), Tanglish, Hindi (हिंदी), and Hinglish.
- **Synthesis Tuning:** Real-time speed rate slider ($0.8\times$ to $1.5\times$), pitch slider ($0.8$ to $1.4$), and "Audit Voice Output" sample playback.
- **Continuous Mode & Duplex Controls:** Toggle buttons for continuous conversation turns without wake-word repetition and zero-latency duplex barge-in cancellation.

### Tab 3: Task Management & DAG Planner (`tasks`)
- **DAG Execution Canvas:** Interactive topological DAG graph showing active waves, step dependencies, and execution logs.
- **Task Creator:** Goal decomposition field that transforms natural language requests into multi-step execution plans.
- **Result Verifier:** Real-time status badges (Pending, Running, Completed, Failed) with automated retry and rollback triggers.

### Tab 4: Computer Intelligence (`computer`)
- **Screen Observer:** Active window monitor displaying current application focus, resolution (1920x1080 @ 60 FPS), and detected UIA accessibility elements.
- **Playwright DOM Inspector:** Active browser sessions, connected URLs, selector strategies (Role & Text Locators), and form detection readiness.
- **Universal Application Discovery Index:** Searchable table indexing all installed Windows applications (Start Menu, Registry, App Paths, UWP Store, and PATH) with one-click "Launch / Focus" triggers.

### Tab 5: Personal Intelligence & Memory (`memory`)
- **Memory Explorer:** Semantic vector memory graph browser querying user preferences, project context, and interaction history.
- **Profile Facts:** Editable user profile memory facts with relevance scoring and timestamped origins.
- **Document Intelligence:** Parsed summaries of local documents, spreadsheets, and presentations.

### Tab 6: System Monitoring & Telemetry (`telemetry`)
- **Hardware Telemetry:** Expanded real-time gauges for CPU utilization per core, RAM allocation, NVMe storage breakdown, and battery charging state.
- **Network & Diagnostics:** WebSocket round-trip ping latency, process inspector, and background worker thread status.

### Tab 7: Settings & Configuration (`settings`)
- **Holographic Themes:** Instant switcher between Classic Cyan, Arc Gold, Quantum Violet, and Matrix Emerald.
- **Avatar Scaling:** Proportional scale selector: Compact Widget (180px), Standard Desktop (240px), and Command HUD (320px).
- **Holographic FX:** Sliders for glow intensity (20% to 100%) and toggle for animated top-to-bottom laser scanlines.
- **Desktop Floating Mode:** Button to transition into the frameless desktop floating widget mode with screen position reset options.
- **Windows Integration:** Autostart configuration with Windows boot via silent VBS runner (`scripts/run_jarvis_silent.vbs`).
