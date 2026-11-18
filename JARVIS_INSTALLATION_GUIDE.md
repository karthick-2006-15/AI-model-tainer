# JARVIS AI — INSTALLATION, SETUP & RUNTIME DEPLOYMENT GUIDE

## 1. System Requirements & Prerequisites

- **Operating System**: Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Python**: Python 3.10.x or 3.11.x (with `pip` and Windows environment variable `PATH` enabled).
- **Node.js**: Node.js 18.x or 20.x LTS (with `npm`).
- **Hardware Requirements**:
  - Memory: 8 GB RAM minimum (16 GB recommended if running local Ollama).
  - Storage: 5 GB free disk space.
  - Audio: Functional microphone and speakers/headphones.

---

## 2. Quickstart Installation Steps

### Step 1: Clone or Open Repository
```powershell
cd c:\Users\karth\OneDrive\Desktop\sanju
```

### Step 2: Install Python Dependencies
```powershell
pip install -r requirements.txt
```
*Key dependencies installed:*
- `fastapi`, `uvicorn`, `pydantic`
- `sqlalchemy`, `alembic`
- `SpeechRecognition`, `edge-tts`, `pyttsx3`
- `psutil`, `pywin32`, `pyautogui`
- `playwright`, `httpx`
- `pytest`, `pytest-asyncio`

### Step 3: Install Playwright Browser Binaries
```powershell
playwright install chromium
```

### Step 4: Install Frontend Node Dependencies
```powershell
cd ui
npm install
npm run build
cd ..
```

---

## 3. Environment Configuration (`.env`)

Create or update `.env` in the repository root:

```env
# Server Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=false
ENVIRONMENT=production

# AI Intelligence Providers (Optional for Cloud; Ollama is local fallback)
GEMINI_API_KEY=your_google_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_claude_api_key_here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Spotify Integration (Optional for Web API; Desktop GSMTC works natively)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/callback

# Security & Permissions
PERMISSION_LEVEL=1
EMERGENCY_STOP_ENABLED=true
```

---

## 4. Starting the Services

### Option A: Complete All-in-One Startup
Run the master start script or daemonize the 3 processes:

1. **Start Ollama Local AI** (Optional, for offline LLM):
   ```powershell
   ollama serve
   ```
2. **Start JARVIS Core Backend** (Port 8000):
   ```powershell
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```
3. **Start Holographic HUD Frontend** (Port 5173):
   ```powershell
   cd ui
   npm run dev
   ```

### Option B: Floating Robot Desktop Widget Mode
To run the floating robot face widget on your desktop:
1. Open `http://localhost:5173` in Chrome or Edge.
2. Click the `FLOATING WIDGET` button in the top navigation bar.
3. The HUD transitions into a transparent, draggable, always-on-top AI companion.
