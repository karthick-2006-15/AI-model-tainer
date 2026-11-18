# JARVIS AI — KNOWN ARCHITECTURAL LIMITATIONS & PLATFORM CONSTRAINTS

## 1. Operating System Dependencies
- **Target OS**: JARVIS is intentionally tailored for Windows 10/11 (64-bit). Subsystems relying on Windows APIs include:
  - *Global System Media Transport Controls (GSMTC)*: Uses Windows RT WinRT media broker to inspect active Spotify audio sessions and control playback.
  - *pywin32 / user32.dll / ctypes*: Used for native desktop window manipulation (`SetForegroundWindow`, `ShowWindow`, `GetWindowText`, `LockWorkStation`).
  - *PowerShell Engine*: Shell automation utilizes Windows PowerShell (`powershell.exe`).
- **Non-Windows Environments**: On Linux or macOS, desktop automation falls back to headless browser actions and mocked OS controls.

---

## 2. Spotify Account & Web API Restrictions
- **Spotify Free vs. Premium**:
  - *Free Tier*: Supports Windows desktop application launching, track search, metadata inspection, and media key hardware controls (Play/Pause, Next Track, Previous Track, Volume Adjustments) via GSMTC. Remote Web API playback transfer (`/v1/me/player/play`) requires Spotify Premium per Spotify Developer Terms.
  - *Premium Tier*: Supports full programmatic Spotify Web API device targeting and queue manipulation.
- **Client Credentials**: Spotify catalog search requires user-provided `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `.env`.

---

## 3. Browser Bot Verification (CAPTCHA) Safeguards
- **Policy Compliance**: In compliance with AI cybersecurity and safety standards, JARVIS **never** attempts to bypass, reverse engineer, solve, or click through bot verification challenges (Cloudflare Turnstile, Google reCAPTCHA, hCaptcha).
- **Behavior**: When a bot challenge is detected, automation is paused and the user is requested to solve the challenge directly in the visible browser before automation resumes.

---

## 4. Voice & Speech Hardware Sensitivity
- **Microphone Hardware**: Accurate wake-word detection and Speech-to-Text transcription require an active, properly calibrated microphone input. In extremely noisy environments, false wake-word rejections may occur until ambient noise recalibrates.
- **Offline Speech Recognition**: Local Whisper transcription (`faster-whisper`) requires GPU acceleration (CUDA) or a multi-core CPU for sub-second latency. When running purely on low-power CPUs, online Google STT provides faster transcription.
- **Audio Output Device**: Edge-TTS streaming requires an active internet connection to synthesize Microsoft neural voices. When offline, JARVIS seamlessly falls back to local Windows SAPI5 voices (`pyttsx3`).

---

## 5. Local LLM Hardware Requirements
- **Local Ollama Daemon**: Running `llama3.2:3b` locally requires at least 4 GB of available system RAM or dedicated VRAM. If Ollama is not running and cloud API keys (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`) are not configured, JARVIS operates in deterministic fallback mode with full OS tool access.
