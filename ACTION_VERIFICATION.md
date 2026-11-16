# JARVIS-10: Action Verification & Self-Healing Loop

## 1. Verification Principles

An autonomous computer operator cannot assume that issuing an operating system command or simulating a mouse click guarantees success. Windows may open an unexpected dialog, an input field might lack focus, or a web element might still be rendering.

JARVIS-10 enforces verifiable execution via the **Autonomous Observation Loop** (`modules/computer_use/loop.py`):

$$\text{OBSERVE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{PLAN} \longrightarrow \text{ACT} \longrightarrow \text{VERIFY} \longrightarrow \text{REPEAT}$$

```mermaid
sequenceDiagram
    participant User
    participant Loop as Autonomous Observation Loop
    participant Env as Windows / Browser Environment
    participant Verifier as Result Verifier & Visual Diff

    User->>Loop: Execute Action (e.g. "Click Search")
    Loop->>Env: Pre-Capture: Screenshot & Window State
    Loop->>Env: Dispatch Action (UIA / Mouse / Keyboard)
    Note over Env: UI updates & animations settle (0.4s)
    Loop->>Env: Post-Capture: Screenshot & Window State
    Loop->>Verifier: Compare Pre & Post States
    alt Verification Success (State Changed)
        Verifier-->>Loop: State Satisfied (Verified = True)
        Loop-->>User: Report Success
    else Verification Failed (No Change or Error)
        Verifier-->>Loop: Action Failed / No Visual Diff
        Loop->>Loop: Analyze Error & Replan Alternative
        Loop->>Env: Retry Action (Attempt 2/3)
    end
```

---

## 2. Multi-Tier Verification Checks

| Verification Strategy | Scope | Evaluation Method |
|---|---|---|
| **Visual Diff Ratio** | Full Screen / Window | Pixel-level difference $\Delta > 0.5\%$ confirms UI response |
| **Window Title Shift** | OS Applications | Detects navigation between views or file loads |
| **UIA Control State** | Native Controls | Validates that an element is selected, checked, or active |
| **DOM Value Inspection** | Web Pages | Reads `element.value` or `element.innerText` after fill |
| **Binary Magic Header** | Generated Files | Checks `PK\x03\x04` for Office documents, `%PDF-` for PDFs |

---

## 3. Failure Recovery & Self-Healing

When an action fails:
1. **Focus Recovery**: If typing failed because the target input was not focused, the engine invokes `SetFocus()` or clicks the element center before re-typing.
2. **Strategy Fallback**:
   - Primary: Windows UI Automation invoke.
   - Secondary: Playwright DOM locator click.
   - Tertiary: Smooth humanized coordinate mouse click with PyAutoGUI.
3. **Graceful Timeout & Abort**:
   - Configurable retry limit (default: 3 cycles).
   - If emergency stop is engaged at any point, the loop halts immediately and reports `SAFE_MODE` status.
