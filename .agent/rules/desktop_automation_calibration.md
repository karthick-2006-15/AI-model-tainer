# Windows Desktop App UI Automation & Calibration Rules

When automating or interacting with native or hybrid Windows desktop applications (WhatsApp, Spotify, VS Code, Discord, Teams, Slack):

## 1. Foreground & Window Identification
- Never rely on exact window title equality (e.g., `title == "whatsapp"`). Applications often append notification counts, unread message badges, or document names (e.g., `"(44) WhatsApp"`, `"document.txt - Notepad"`). Always use case-insensitive substring checks (`"whatsapp" in title.lower()`) combined with process name verification (`"whatsapp" in process_name.lower()`).
- Always check both parent host process (`WhatsApp.Root.exe`) and child renderers (`msedgewebview2.exe`).

## 2. Coordinate Calibration vs Static Header Traps
- In hybrid/WebView2 UI layouts, static pane headers (e.g., "Chats", "Search", "Library") frequently occupy the top 50–85px of the window.
- Never place search click coordinates in the top 50–90px range unless verified against the accessibility tree.
- For WhatsApp Desktop on Windows 11:
  - Header "Chats": $y \approx t + 70$ (do NOT click; selecting it highlights the text heading and blocks input).
  - Search Input ("Search or start a new chat"): center $y \approx t + 127$, $x \approx l + 250$ (or $l + \min(\max(0.22 \times w, 200), 280)$).
  - Filtered 1st Contact Result: center $y \approx t + 230$, $x \approx l + 250$.
  - Chat Message Composer: center $y \approx b - 45$, $x \approx l + 0.65 \times w$.

## 3. UI Automation & WebView2 COM Exception Guards
- UI Automation (`native_uia`, `uiautomation`, `pywinauto`) calls on WebView2 renderers must always be wrapped in `try/except Exception:` blocks to prevent COM marshaling crashes (`-2147220991`).
- Always provide immediate coordinate-based fallback if UIA returns `None` or fails.

## 4. Safety Invariants During Contact Search
- During contact navigation (`open_conversation`), NEVER press the `Enter` key.
- Always navigate by clicking the target search result item at its verified position.
- Strictly maintain Level 3 authorization before typing or transmitting outgoing messages.
