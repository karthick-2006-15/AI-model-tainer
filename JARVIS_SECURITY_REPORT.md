# JARVIS AI — CYBERSECURITY, PERMISSION GUARD & AUDIT REPORT

## 1. Security Architecture & Threat Model

JARVIS is designed to act on a user's operating system, files, applications, and networks. Because autonomous AI agents can be susceptible to prompt injection, hallucinated file operations, and unauthorized privilege escalation, JARVIS employs a multi-layered defense-in-depth security model.

```
+-------------------------------------------------------------+
|                Incoming Instruction / Voice                 |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                   Permission Engine (RBAC)                  |
|  - Level 1: Read-Safe (Auto-Approved)                       |
|  - Level 2: Standard Action (Authenticated)                 |
|  - Level 3: Sensitive / Destructive (Requires User Challenge)|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|               Sandbox Guardrails & Verification             |
|  - Shell Command AST Parser & Destructive Pattern Filter   |
|  - File Path Jailkeeper (Prevents C:\Windows\System32 mod)   |
|  - Bot Sentinel (Cloudflare, reCAPTCHA, hCaptcha detection) |
|  - Biometric / Voice Confirmation for Irreversible Actions  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     Execution Subsystems                    |
|    (Win32 Apps, Playwright Browser, GSMTC Media, SQLite)    |
+-------------------------------------------------------------+
```

---

## 2. The 3-Tier Permission Hierarchy

| Permission Level | Classification | Behavior | Examples |
|---|---|---|---|
| **Level 1** | Read-Safe | Automatically executed without user confirmation | System hardware telemetry, window listing, reading open tabs, checking current song metadata, listing tasks |
| **Level 2** | Standard Action | Allowed for authenticated sessions; logs execution | Launching/focusing apps, navigating browser URLs, adjusting volume, creating tasks |
| **Level 3** | Sensitive / Destructive | **Blocked until explicitly approved** via interactive HUD challenge or voice confirmation | WhatsApp message sending, form submissions, system restart/shutdown, destructive PowerShell commands, file deletion |

### Level 3 Confirmation Resolution
When a Level 3 action is prepared:
1. The backend pauses execution and issues an approval challenge containing `challenge_id`, `action_name`, `target_resource`, and a clear explanation.
2. The HUD displays an interactive modal with "Approve" and "Deny" buttons.
3. Alternatively, the user can say "Yes", "Aama", "Haan" or "No", "Cancel" to confirm via voice.
4. If denied or timed out, the action is safely cancelled and rolled back.

---

## 3. Shell Sandboxing & Destructive Command Defense

The PowerShell execution engine (`modules/automation/shell.py`) intercepts all shell requests and inspects the command string before invocation:

1. **Blocked Destructive Commands**:
   - `Format-Volume`, `Format-`
   - `Remove-Item` with `-Recurse` on root or system directories
   - `del /f /s /q`, `rmdir /s /q`
   - Registry manipulation (`reg delete`, `Set-ItemProperty` on security hives)
   - Disabling Windows Defender or Firewall (`Set-MpPreference -DisableRealtimeMonitoring`)
2. **Shell Injection Prevention**:
   - Command chaining with `;`, `&&`, `|` is scrutinized for nested dangerous statements.
   - Working directories are clamped to user profile and project folders.
3. **Execution Timeout**:
   - Commands default to a 30-second timeout to prevent runaway processes or fork bombs.

---

## 4. Bot Gate & CAPTCHA Sentinel Compliance

JARVIS adheres strictly to AI safety policies regarding human verification challenges:
- **Zero Automated Bypass**: JARVIS never attempts to solve, click through, reverse-engineer, or bypass Cloudflare Turnstile, Google reCAPTCHA, hCaptcha, or proof-of-work challenges.
- **Automated Detection**: The Playwright engine (`browser_playwright.py`) continuously scans DOM iframes, IDs, and challenge attributes.
- **User Notification**: When a challenge is detected, JARVIS pauses automation and issues an alert:
  > *"A bot verification challenge was detected on this webpage. In accordance with safety policies, automated bypass is prohibited. Please solve the challenge directly in your browser."*

---

## 5. Token Safety & Credential Protection

- **Environment Variable Isolation**: API keys (Gemini, Claude, Spotify Client Secret) are loaded via `.env` and never committed to source control.
- **Spotify OAuth Credentials**: Spotify passwords are never requested or stored. Playback relies strictly on temporary OAuth access tokens refreshed via authorized Spotify token servers.
- **Zero Plaintext Credentials in Logs**: Sensitive payload fields (`password`, `secret`, `token`, `auth`) are redacted in telemetry logs.

---

## 6. Emergency Abort & Killswitch

JARVIS features a system-wide emergency abort button prominently displayed on the HUD interface:
- **Frontend**: Clicking the `EMERGENCY ABORT` button sends `abort_task` over WebSocket.
- **Backend Response**:
  1. Instantly terminates `tts_engine` audio playback.
  2. Sets `permission_engine.set_emergency_stopped(True)`.
  3. Cancels all pending and in-progress DAG plan tasks.
  4. Changes avatar state to `error` and halts all active browser/desktop loops.
