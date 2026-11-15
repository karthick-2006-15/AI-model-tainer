# JARVIS-7: GUI & Computer-Use Automation Tools Catalog

This document details all 25 tools registered in the JARVIS Mark VII brain across the four computer-use namespaces: `computer.*`, `browser.*`, `whatsapp.*`, and `worksheet.*`.

All tools adhere to strict JSON schema validation, permission checks, execution boundaries, and audit logging.

---

## 1. `computer.*` Namespace (10 Tools)

### 1.1 `computer.capture_screen`
- **Description:** Captures the current desktop screen and saves it as an image file. Returns file path and base64 string.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `save_path` *(string, optional)*: Specific file path to save the screenshot.
  - `include_base64` *(boolean, optional, default: false)*: Whether to include base64 string.
- **Invocation Example:**
  ```json
  { "include_base64": false }
  ```

### 1.2 `computer.get_active_window`
- **Description:** Retrieves information about the currently focused desktop window (title, process, HWND, geometry).
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:** None.
- **Invocation Example:**
  ```json
  {}
  ```

### 1.3 `computer.inspect_ui`
- **Description:** Walks the Windows Accessibility Tree (UIA) to discover interactive controls (buttons, textboxes, lists) in the active window.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `max_depth` *(integer, optional, default: 3)*: Tree traversal depth.
- **Invocation Example:**
  ```json
  { "max_depth": 3 }
  ```

### 1.4 `computer.click_element`
- **Description:** Clicks an on-screen element identified either by UI Automation name/control type or by desktop (X, Y) coordinates.
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `name` *(string, optional)*: Target element name in accessibility tree.
  - `control_type` *(string, optional)*: UIA control type (e.g. `ButtonControl`).
  - `x` *(integer, optional)*: X coordinate.
  - `y` *(integer, optional)*: Y coordinate.
- **Invocation Example:**
  ```json
  { "name": "Submit", "control_type": "ButtonControl" }
  ```

### 1.5 `computer.type_text`
- **Description:** Types text into the active field or target control with humanized keystroke timing.
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `text` *(string, required)*: Text string to type.
  - `interval` *(number, optional, default: 0.05)*: Delay in seconds between keystrokes.
- **Invocation Example:**
  ```json
  { "text": "Hello world", "interval": 0.04 }
  ```

### 1.6 `computer.press_key`
- **Description:** Presses a specific keyboard key or key combination (e.g. `enter`, `tab`, `ctrl+s`, `esc`).
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `key` *(string, required)*: Key name or combination string.
- **Invocation Example:**
  ```json
  { "key": "enter" }
  ```

### 1.7 `computer.scroll`
- **Description:** Scrolls the active window vertically or horizontally.
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `clicks` *(integer, required)*: Scroll amount (positive for up, negative for down).
  - `x` *(integer, optional)*: Cursor X coordinate before scrolling.
  - `y` *(integer, optional)*: Cursor Y coordinate before scrolling.
- **Invocation Example:**
  ```json
  { "clicks": -5 }
  ```

### 1.8 `computer.open_application`
- **Description:** Launches a Windows desktop application (e.g. VS Code, Chrome, WhatsApp, Notepad, Calculator).
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `app_name` *(string, required)*: Application name or path.
- **Invocation Example:**
  ```json
  { "app_name": "vscode" }
  ```

### 1.9 `computer.switch_window`
- **Description:** Brings a window matching a specific title substring or process name to the foreground.
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `title_match` *(string, required)*: Substring to match in window title.
- **Invocation Example:**
  ```json
  { "title_match": "Visual Studio Code" }
  ```

### 1.10 `computer.verify_action`
- **Description:** Compares before and after visual screen states to verify whether a requested action succeeded.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `before_path` *(string, required)*: Path to pre-action screenshot.
  - `after_path` *(string, required)*: Path to post-action screenshot.
  - `expected_window_title` *(string, optional)*: Expected foreground title.
- **Invocation Example:**
  ```json
  { "before_path": "storage/cache/before.png", "after_path": "storage/cache/after.png" }
  ```

---

## 2. `browser.*` Namespace (5 Tools)

### 2.1 `browser.get_active_tab`
- **Description:** Identifies the active browser window and URL/title.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:** None.
- **Invocation Example:**
  ```json
  {}
  ```

### 2.2 `browser.inspect_page`
- **Description:** Inspects the current webpage DOM, extracting structure, headings, form inputs, and buttons.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `url` *(string, optional)*: Optional URL to fetch if not using current tab.
- **Invocation Example:**
  ```json
  {}
  ```

### 2.3 `browser.extract_questions`
- **Description:** Scans the active webpage for form fields, questionnaire questions, and interactive inputs.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `html_content` *(string, optional)*: Direct HTML string to parse.
- **Invocation Example:**
  ```json
  {}
  ```

### 2.4 `browser.fill_field`
- **Description:** Fills a web input field or selects a radio/checkbox option using DOM selector or label.
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `selector` *(string, required)*: CSS or XPath selector of input element.
  - `value` *(string, required)*: Text value or option to select.
- **Invocation Example:**
  ```json
  { "selector": "#full_name", "value": "Karthik" }
  ```

### 2.5 `browser.click_element`
- **Description:** Clicks an interactive DOM element on the active browser page.
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `selector` *(string, required)*: CSS or XPath selector of clickable element.
- **Invocation Example:**
  ```json
  { "selector": "button.submit-btn" }
  ```

---

## 3. `whatsapp.*` Namespace (5 Tools)

### 3.1 `whatsapp.find_contact`
- **Description:** Resolves contact queries (names, relation aliases like father, dad, mom) against profile memory.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `query` *(string, required)*: Contact name or relation alias.
- **Invocation Example:**
  ```json
  { "query": "father" }
  ```

### 3.2 `whatsapp.open_conversation`
- **Description:** Opens WhatsApp Desktop or WhatsApp Web and navigates to the target contact chat.
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `contact_name` *(string, required)*: Resolved recipient name.
- **Invocation Example:**
  ```json
  { "contact_name": "Father" }
  ```

### 3.3 `whatsapp.prepare_message`
- **Description:** Drafts a message and creates a Level 3 confirmation challenge before sending.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `recipient` *(string, required)*: Recipient contact name.
  - `message` *(string, required)*: Text message content.
- **Invocation Example:**
  ```json
  { "recipient": "Father", "message": "Hi" }
  ```

### 3.4 `whatsapp.send_message`
- **Description:** Sends the prepared message. Strictly requires prior user confirmation.
- **Permission Level:** `LEVEL_3_EXTERNAL_ACTION`
- **Parameters:**
  - `recipient` *(string, required)*: Target recipient.
  - `message_text` *(string, required)*: Content to send.
  - `skip_permission_check` *(boolean, optional, default: false)*: Only passed when confirmation was resolved out-of-band.
- **Invocation Example:**
  ```json
  { "recipient": "Father", "message_text": "Hi" }
  ```

### 3.5 `whatsapp.verify_message`
- **Description:** Inspects the active chat bubble history to verify that the outgoing message was delivered.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `expected_snippet` *(string, required)*: Expected message text substring.
- **Invocation Example:**
  ```json
  { "expected_snippet": "Hi" }
  ```

---

## 4. `worksheet.*` Namespace (5 Tools)

### 4.1 `worksheet.extract_questions`
- **Description:** Parses an online worksheet or form, extracting questions, input types, and required statuses.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `html_source` *(string, optional)*: HTML content of worksheet.
- **Invocation Example:**
  ```json
  {}
  ```

### 4.2 `worksheet.research_answers`
- **Description:** Researches answers to extracted questions using local memory and web search client.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:**
  - `questions` *(array of objects, required)*: Questions to research.
- **Invocation Example:**
  ```json
  { "questions": [{"index": 1, "text": "What is the capital of France?"}] }
  ```

### 4.3 `worksheet.fill_answers`
- **Description:** Populates worksheet fields with researched answers.
- **Permission Level:** `LEVEL_2_MODIFY`
- **Parameters:**
  - `answers` *(array of objects, required)*: List of `{index, answer}` pairs.
- **Invocation Example:**
  ```json
  { "answers": [{"index": 1, "answer": "Paris"}] }
  ```

### 4.4 `worksheet.review_answers`
- **Description:** Generates a structured summary review of all filled answers prior to final submission.
- **Permission Level:** `LEVEL_1_READ`
- **Parameters:** None.
- **Invocation Example:**
  ```json
  {}
  ```

### 4.5 `worksheet.submit`
- **Description:** Submits the completed online worksheet. Strictly requires explicit user confirmation.
- **Permission Level:** `LEVEL_3_EXTERNAL_ACTION`
- **Parameters:**
  - `skip_permission_check` *(boolean, optional, default: false)*: Only passed when confirmation was resolved out-of-band.
- **Invocation Example:**
  ```json
  {}
  ```
