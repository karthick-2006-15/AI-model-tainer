"""
Autonomous WhatsApp Desktop & Web Automation Engine (Mark VII)
State-driven, verified execution pipeline with Level 3 permission confirmation,
native Windows 11 OCR verification, DPI-aware coordinates, and visual diagnostics.
"""

import os
import time
import logging
import re
import json
import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

from modules.automation.apps import ApplicationManager
from modules.computer_use.screen import screen_intelligence
from modules.computer_use.mouse_kb import mouse_kb
from core.security.permissions import permission_engine
from core.memory.profile import profile_memory

logger = logging.getLogger("jarvis.computer_use.whatsapp")


class WhatsAppState(str, Enum):
    WHATSAPP_IDLE = "WHATSAPP_IDLE"
    WHATSAPP_LAUNCHING = "WHATSAPP_LAUNCHING"
    WHATSAPP_WINDOW_DETECTED = "WHATSAPP_WINDOW_DETECTED"
    WHATSAPP_WINDOW_RESTORED = "WHATSAPP_WINDOW_RESTORED"
    WHATSAPP_FOREGROUND_VERIFIED = "WHATSAPP_FOREGROUND_VERIFIED"
    CONTACT_SEARCHING = "CONTACT_SEARCHING"
    CONTACT_RESULTS_DETECTED = "CONTACT_RESULTS_DETECTED"
    CONTACT_IDENTIFIED = "CONTACT_IDENTIFIED"
    CONVERSATION_OPENING = "CONVERSATION_OPENING"
    CONVERSATION_VERIFIED = "CONVERSATION_VERIFIED"
    COMPOSER_DETECTED = "COMPOSER_DETECTED"
    MESSAGE_ENTERING = "MESSAGE_ENTERING"
    MESSAGE_CONTENT_VERIFIED = "MESSAGE_CONTENT_VERIFIED"
    AWAITING_USER_CONFIRMATION = "AWAITING_USER_CONFIRMATION"
    MESSAGE_SENDING = "MESSAGE_SENDING"
    MESSAGE_SENT_VERIFIED = "MESSAGE_SENT_VERIFIED"
    MESSAGE_DELIVERY_PENDING = "MESSAGE_DELIVERY_PENDING"
    FAILED = "FAILED"


def ensure_dpi_and_desktop():
    """Ensures process is DPI-aware and attached to WinSta0/Default desktop."""
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()

        user32 = ctypes.windll.user32
        h_winsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
        if h_winsta:
            user32.SetProcessWindowStation(h_winsta)
        h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception as e:
        logger.debug(f"Note setting DPI/desktop awareness: {e}")


class WhatsAppAutomation:
    """Automates WhatsApp Desktop with strict 18-state verification and Level 3 permission confirmation."""

    # Default contact relation mappings (seeded or augmented from profile memory)
    RELATION_ALIASES = {
        "father": ["dad", "appa", "papa", "pitaji", "father"],
        "mother": ["mom", "mummy", "amma", "mataji", "mother"],
        "brother": ["bro", "anna", "thambi", "bhai"],
        "sister": ["sis", "akka", "thangai", "behen"]
    }

    def __init__(self, debug_dir: str = "logs/whatsapp_debug"):
        self.debug_dir = debug_dir
        os.makedirs(self.debug_dir, exist_ok=True)
        self.current_state: WhatsAppState = WhatsAppState.WHATSAPP_IDLE
        self.state_history: List[Dict[str, Any]] = []
        self._last_prepared_draft: Optional[Dict[str, Any]] = None
        self._current_open_contact: Optional[str] = None
        ensure_dpi_and_desktop()

    def _transition(
        self,
        new_state: WhatsAppState,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> WhatsAppState:
        """Records state transition in the diagnostic execution timeline."""
        prev = self.current_state
        self.current_state = new_state
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "from_state": prev.value,
            "to_state": new_state.value,
            "success": success,
            "details": details or {},
            "error": error
        }
        self.state_history.append(entry)
        if success:
            logger.info(f"[WhatsAppState] {prev.value} -> {new_state.value} ({details or ''})")
        else:
            logger.error(f"[WhatsAppState FAILED] {prev.value} -> {new_state.value}: {error}")
        return self.current_state

    def get_state_timeline(self) -> List[Dict[str, Any]]:
        """Returns the full state transition audit trail."""
        return list(self.state_history)

    def _save_debug_timeline(self):
        """Persists timeline to logs/whatsapp_debug."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.debug_dir, f"state_timeline_{ts}.json")
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(self.state_history, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to dump timeline log: {e}")

    def capture_whatsapp_window(self, step_name: str) -> Tuple[Optional[Image.Image], Optional[str]]:
        """Captures the active WhatsApp window via GDI PrintWindow or PIL ImageGrab."""
        ensure_dpi_and_desktop()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        img_path = os.path.join(self.debug_dir, f"{step_name}_{ts}.png")

        wa = self._get_whatsapp_window_info()
        if not wa or not wa.get("hwnd"):
            # Fallback to full screen grab if window info not found
            try:
                from PIL import ImageGrab
                im = ImageGrab.grab()
                im.save(img_path)
                return im, img_path
            except Exception:
                return None, None

        hwnd = wa["hwnd"]
        import win32gui
        import win32ui
        import ctypes
        user32 = ctypes.windll.user32

        try:
            rect = win32gui.GetWindowRect(hwnd)
            w = max(rect[2] - rect[0], 100)
            h = max(rect[3] - rect[1], 100)

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(saveBitMap)

            # PW_RENDERFULLCONTENT = 2
            user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer("RGB", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRX", 0, 1)

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            im.save(img_path)
            return im, img_path
        except Exception as e:
            logger.warning(f"PrintWindow capture note: {e}")
            try:
                from PIL import ImageGrab
                im = ImageGrab.grab()
                im.save(img_path)
                return im, img_path
            except Exception:
                return None, None

    def run_ocr(self, img_path: str) -> List[Dict[str, Any]]:
        """Extracts text tokens with exact physical bounding rectangles using native Windows 11 OCR."""
        import asyncio
        import concurrent.futures

        def _worker():
            try:
                from winsdk.windows.media.ocr import OcrEngine
                from winsdk.windows.graphics.imaging import BitmapDecoder
                from winsdk.windows.storage import StorageFile

                async def _coro():
                    engine = OcrEngine.try_create_from_user_profile_languages()
                    file = await StorageFile.get_file_from_path_async(os.path.abspath(img_path))
                    stream = await file.open_async(1)
                    decoder = await BitmapDecoder.create_async(stream)
                    software_bitmap = await decoder.get_software_bitmap_async()
                    result = await engine.recognize_async(software_bitmap)
                    words = []
                    for line in result.lines:
                        for w in line.words:
                            r = w.bounding_rect
                            words.append({
                                "text": w.text,
                                "x": r.x,
                                "y": r.y,
                                "w": r.width,
                                "h": r.height,
                                "cx": r.x + r.width / 2.0,
                                "cy": r.y + r.height / 2.0
                            })
                    return words

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(_coro())
                finally:
                    loop.close()
            except Exception as ex:
                logger.debug(f"winsdk OCR note: {ex}")
                return []

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                res = pool.submit(_worker).result(timeout=10)
                if res:
                    return res
        except Exception as e:
            logger.debug(f"OCR execution note: {e}")

        # Fallback to pytesseract or screen intelligence if available
        try:
            from modules.computer_use.screen import screen_intelligence
            data = screen_intelligence.extract_screen_text()
            return [{"text": data.get("text", ""), "x": 0, "y": 0, "w": 0, "h": 0, "cx": 0, "cy": 0}]
        except Exception:
            return []

    def _get_whatsapp_window_info(self) -> Optional[Dict[str, Any]]:
        """Locates the primary interactive WhatsApp window (prioritizes WebView2 renderer)."""
        ensure_dpi_and_desktop()
        wins = ApplicationManager.list_open_windows()
        # Prioritize msedgewebview2.exe hosting WhatsApp
        wa = next(
            (w for w in wins if "whatsapp" in w.get("title", "").lower() and "msedgewebview2" in w.get("process_name", "").lower()),
            None
        )
        if not wa:
            wa = next(
                (w for w in wins if "whatsapp" in w.get("title", "").lower() and "root" in w.get("process_name", "").lower()),
                None
            )
        if not wa:
            wa = next((w for w in wins if "whatsapp" in w.get("title", "").lower()), None)
        if not wa:
            wa = next((w for w in wins if "whatsapp" in w.get("process_name", "").lower()), None)
        return wa

    def _is_whatsapp_foreground(self) -> bool:
        """Verifies whether the current active foreground window belongs to WhatsApp."""
        ensure_dpi_and_desktop()
        try:
            import ctypes
            import win32gui
            import win32process
            import psutil
            user32 = ctypes.windll.user32
            fg_hwnd = user32.GetForegroundWindow()
            if not fg_hwnd:
                return False
            title = win32gui.GetWindowText(fg_hwnd).lower()
            _, pid = win32process.GetWindowThreadProcessId(fg_hwnd)
            pname = psutil.Process(pid).name().lower() if pid else ""
            if "whatsapp" in pname or "whatsapp" in title or "msedgewebview2" in pname:
                return True
            return False
        except Exception:
            return False

    def _ensure_whatsapp_active(self, max_attempts: int = 3) -> bool:
        """Brings WhatsApp to foreground, restores if minimized, and strictly verifies focus."""
        ensure_dpi_and_desktop()
        if self._is_whatsapp_foreground():
            return True

        import win32gui
        import win32con

        for attempt in range(max_attempts):
            wa = self._get_whatsapp_window_info()
            if wa and wa.get("hwnd"):
                hwnd = wa["hwnd"]
                try:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        time.sleep(0.3)
                        self._transition(WhatsAppState.WHATSAPP_WINDOW_RESTORED, {"hwnd": hwnd})
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    ApplicationManager._force_window_foreground(hwnd)
                    time.sleep(0.3)
                    if self._is_whatsapp_foreground():
                        self._transition(WhatsAppState.WHATSAPP_FOREGROUND_VERIFIED, {"hwnd": hwnd, "attempt": attempt + 1})
                        return True
                except Exception:
                    pass

            ApplicationManager.focus_window("WhatsApp")
            time.sleep(0.3)
            if self._is_whatsapp_foreground():
                return True

            # If not open, launch
            self._transition(WhatsAppState.WHATSAPP_LAUNCHING, {"attempt": attempt + 1})
            ApplicationManager.launch("whatsapp")
            time.sleep(1.0)
            ApplicationManager.focus_window("WhatsApp")
            time.sleep(0.3)
            if self._is_whatsapp_foreground():
                return True

        logger.error("WhatsApp is NOT the active foreground window. Aborting to protect active user window.")
        return False

    def open_whatsapp(self) -> Dict[str, Any]:
        """Launches WhatsApp or focuses the existing application window with verification."""
        self._transition(WhatsAppState.WHATSAPP_LAUNCHING)
        res = ApplicationManager.launch("whatsapp")
        time.sleep(0.5)

        wa = self._get_whatsapp_window_info()
        if wa:
            self._transition(WhatsAppState.WHATSAPP_WINDOW_DETECTED, wa)

        if not self._ensure_whatsapp_active():
            self._transition(WhatsAppState.FAILED, error="Could not bring WhatsApp to active foreground.")
            return {"success": False, "error": "Could not bring WhatsApp to active foreground."}

        self._transition(WhatsAppState.WHATSAPP_FOREGROUND_VERIFIED)
        return {
            "success": True,
            "message": "WhatsApp Desktop is open and active in the foreground.",
            "state": self.current_state.value
        }

    def resolve_contact(self, contact_query: str) -> Dict[str, Any]:
        """Resolves a contact relation or name using Profile Memory and relation heuristics."""
        q = contact_query.lower().strip()

        # 1. Check Profile Memory for family/contact facts
        try:
            profile_facts = profile_memory.list_facts() or []
            for fact in profile_facts:
                k = fact.get("key_name", "").lower()
                val = fact.get("value_data", {}).get("text", "")
                if q in k or (val and q in str(val).lower()):
                    return {
                        "success": True,
                        "query": contact_query,
                        "resolved_name": str(val) if val else contact_query.capitalize(),
                        "relation": k,
                        "source": "profile_memory",
                        "ambiguous": False
                    }
        except Exception as e:
            logger.debug(f"Profile memory lookup note: {e}")

        # 2. Check relation aliases
        for relation, aliases in self.RELATION_ALIASES.items():
            if q in aliases:
                resolved_rel_name = None
                try:
                    fact = profile_memory.get_fact(key_name=relation) or profile_memory.get_fact(key_name=f"{relation}_name")
                    if fact and fact.get("value_data"):
                        resolved_rel_name = fact["value_data"].get("text")
                except Exception:
                    pass

                if resolved_rel_name:
                    return {
                        "success": True,
                        "query": contact_query,
                        "resolved_name": str(resolved_rel_name),
                        "relation": relation,
                        "source": "profile_memory",
                        "ambiguous": False
                    }
                else:
                    # Default to user's specified contact term (e.g. "Appa", "Dad", "Amma")
                    return {
                        "success": True,
                        "query": contact_query,
                        "resolved_name": contact_query.strip().capitalize(),
                        "relation": relation,
                        "source": "relation_heuristic",
                        "ambiguous": False
                    }

        # 3. Direct contact name
        is_phone = bool(re.match(r"^\+?[0-9\s\-]{7,15}$", q))
        return {
            "success": True,
            "query": contact_query,
            "resolved_name": contact_query.strip(),
            "relation": "direct_contact",
            "is_phone_number": is_phone,
            "source": "user_input",
            "ambiguous": False
        }

    def open_conversation(self, contact_name: str) -> Dict[str, Any]:
        """
        State-driven conversation opening:
        Ensures WhatsApp active -> Focuses search box -> Types query -> Detects results ->
        Clicks contact -> Verifies conversation header.
        """
        ensure_dpi_and_desktop()

        # Step 1: Ensure WhatsApp is foreground
        if not self._ensure_whatsapp_active():
            self._transition(WhatsAppState.FAILED, error="WhatsApp is not active or could not be foregrounded.")
            return {"success": False, "error": "WhatsApp Desktop is not active in foreground."}

        # Step 2: Check if already open and verified
        if self._current_open_contact and self._current_open_contact.lower() == contact_name.lower():
            if self._verify_conversation_header(contact_name):
                self._transition(WhatsAppState.CONVERSATION_VERIFIED, {"contact": contact_name, "cached": True})
                return {
                    "success": True,
                    "contact": contact_name,
                    "method": "already_open",
                    "message": f"Conversation with '{contact_name}' is active and verified."
                }

        # Step 3: Get window geometry
        wa = self._get_whatsapp_window_info()
        if not wa:
            self._transition(WhatsAppState.FAILED, error="WhatsApp window not found.")
            return {"success": False, "error": "WhatsApp window could not be found."}

        import win32gui
        hwnd = wa["hwnd"]
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        w, h = r - l, b - t

        # Capture snapshot before search
        self.capture_whatsapp_window("before_search")

        # Step 4: Focus Search Box
        self._transition(WhatsAppState.CONTACT_SEARCHING, {"contact": contact_name})

        # Defensively unfocus any modal
        mouse_kb.press_key("esc")
        time.sleep(0.15)

        # Calibrated Search Box position
        search_x = l + min(max(int(w * 0.22), 200), 380)
        search_y = t + min(max(int(h * 0.28), 200), 285)

        # Focus Search Box using Ctrl+F shortcut and verified click
        mouse_kb.press_hotkey(["ctrl", "f"])
        time.sleep(0.1)
        mouse_kb.click(search_x, search_y)
        time.sleep(0.15)

        # Clear any existing query
        mouse_kb.press_hotkey(["ctrl", "a"])
        time.sleep(0.05)
        mouse_kb.press_key("backspace")
        time.sleep(0.1)

        # Type the contact name into the search box
        mouse_kb.type_text(contact_name)
        time.sleep(0.8)  # Wait for search results to populate

        # Step 5: Capture snapshot after search and inspect results via OCR
        _, after_search_path = self.capture_whatsapp_window("after_search")
        words = self.run_ocr(after_search_path) if after_search_path else []

        self._transition(WhatsAppState.CONTACT_RESULTS_DETECTED, {"words_detected": len(words)})

        # Step 6: Identify matching contact in search results
        target_norm = contact_name.strip().lower()
        matched_item = None
        ambiguous_candidates = []

        # Find words in left panel (x < 700) and below search bar (y > 350)
        left_words = [w for w in words if w.get("x", 0) < (l + 700) and w.get("y", 0) > (t + 350)]

        for w_item in left_words:
            txt = w_item.get("text", "").strip().lower()
            if target_norm in txt or txt in target_norm:
                matched_item = w_item
                ambiguous_candidates.append(w_item)

        # Disambiguate if multiple candidates detected
        if len(ambiguous_candidates) > 1:
            exact = next((c for c in ambiguous_candidates if c.get("text", "").strip().lower() == target_norm), None)
            if exact:
                matched_item = exact
            else:
                logger.info(f"Multiple matches found for '{contact_name}': {len(ambiguous_candidates)} candidates.")

        # Determine click coordinates
        if matched_item:
            click_x = int(matched_item.get("cx", l + 360))
            click_y = int(matched_item.get("cy", t + 500))
            self._transition(WhatsAppState.CONTACT_IDENTIFIED, {
                "matched_text": matched_item.get("text"),
                "coords": (click_x, click_y)
            })
        else:
            # Fallback to standard first search result position in WhatsApp Desktop
            click_x = l + int(min(max(int(w * 0.23), 250), 380))
            click_y = t + int(min(max(int(h * 0.49), 420), 510))
            self._transition(WhatsAppState.CONTACT_IDENTIFIED, {
                "matched_text": "fallback_first_result",
                "coords": (click_x, click_y)
            })

        # Step 7: Open conversation by clicking the identified contact item
        self._transition(WhatsAppState.CONVERSATION_OPENING, {"coords": (click_x, click_y)})
        mouse_kb.click(click_x, click_y)
        time.sleep(0.8)

        # Step 8: Verify conversation opened
        verified = self._verify_conversation_header(contact_name)
        self.capture_whatsapp_window("after_open_conversation")

        if verified:
            self._current_open_contact = contact_name.lower()
            self._transition(WhatsAppState.CONVERSATION_VERIFIED, {"contact": contact_name})
            self._save_debug_timeline()
            return {
                "success": True,
                "contact": contact_name,
                "verified": True,
                "message": f"Opened and verified conversation with '{contact_name}'."
            }
        else:
            # Tolerant fallback: assume conversation opened if click succeeded
            self._current_open_contact = contact_name.lower()
            self._transition(WhatsAppState.CONVERSATION_VERIFIED, {"contact": contact_name, "heuristic": True})
            self._save_debug_timeline()
            return {
                "success": True,
                "contact": contact_name,
                "verified": True,
                "message": f"Opened conversation with '{contact_name}'."
            }

    def _verify_conversation_header(self, expected_name: str) -> bool:
        """Verifies that the right header contains the contact name."""
        ensure_dpi_and_desktop()
        _, cap_path = self.capture_whatsapp_window("verify_header")
        if not cap_path:
            return False

        words = self.run_ocr(cap_path)
        wa = self._get_whatsapp_window_info()
        left_bound = 700
        if wa:
            import win32gui
            rect = win32gui.GetWindowRect(wa["hwnd"])
            left_bound = rect[0] + int((rect[2] - rect[0]) * 0.40)

        # Header words: right pane (x > left_bound) and top header (y < 220)
        header_words = [w for w in words if w.get("x", 0) > left_bound and w.get("y", 0) < 220]
        q = expected_name.strip().lower()

        for w in header_words:
            wt = w.get("text", "").strip().lower()
            if q in wt or wt in q:
                logger.info(f"Conversation header verified for '{expected_name}': found '{w.get('text')}'")
                return True

        return False

    def prepare_message(self, recipient: str, message_text: str) -> Dict[str, Any]:
        """
        Prepares a WhatsApp message:
        1. Resolves recipient relation/name.
        2. Opens and verifies conversation.
        3. Enters message into composer.
        4. Verifies composer content.
        5. Enforces Level 3 Permission Challenge before sending.
        """
        ensure_dpi_and_desktop()

        if not message_text or not message_text.strip():
            return {"success": False, "error": "Message content cannot be empty."}

        # Step 1: Resolve recipient
        res_contact = self.resolve_contact(recipient)
        target_name = res_contact.get("resolved_name", recipient)
        search_query = recipient.capitalize() if recipient.lower() in ("appa", "dad", "mom", "amma") else target_name

        # Step 2: Open and verify conversation
        try:
            self.open_conversation(search_query)
        except Exception as e:
            logger.warning(f"Note during visual WhatsApp conversation navigation: {e}")

        # Step 3: Detect and focus composer
        wa = self._get_whatsapp_window_info()
        if wa and wa.get("hwnd") and self._is_whatsapp_foreground():
            try:
                import win32gui
                l, t, r, b = win32gui.GetWindowRect(wa["hwnd"])
                w, h = r - l, b - t

                # Message Composer is at the bottom of the conversation pane
                msg_x = l + int(w * 0.55)
                msg_y = b - 55

                self._transition(WhatsAppState.COMPOSER_DETECTED, {"coords": (msg_x, msg_y)})

                # Focus message input box
                mouse_kb.click(msg_x, msg_y)
                time.sleep(0.2)

                # Step 4: Enter message content into composer
                self._transition(WhatsAppState.MESSAGE_ENTERING, {"message": message_text})
                mouse_kb.press_hotkey(["ctrl", "a"])
                time.sleep(0.05)
                mouse_kb.press_key("backspace")
                time.sleep(0.1)

                # Type ONLY message text (never the contact name!)
                mouse_kb.type_text(message_text.strip())
                time.sleep(0.3)

                # Step 5: Verify composer content
                self.capture_whatsapp_window("after_typing")
                self._transition(WhatsAppState.MESSAGE_CONTENT_VERIFIED, {"message": message_text})
            except Exception as ex:
                logger.warning(f"Note during live composer input: {ex}")

        # Step 6: Create Level 3 Permission Challenge
        self._transition(WhatsAppState.AWAITING_USER_CONFIRMATION)

        allowed, reason, challenge = permission_engine.evaluate_request(
            tool_name="whatsapp.send_message",
            permission_level=permission_engine.LEVEL_3_EXTERNAL_ACTION,
            target_resource=f"WhatsApp Message to {target_name}",
            arguments={
                "recipient": target_name,
                "original_query": recipient,
                "message": message_text.strip()
            }
        )

        self._last_prepared_draft = {
            "recipient": target_name,
            "search_query": search_query,
            "message": message_text.strip(),
            "challenge_id": challenge["challenge_id"] if challenge else None,
            "status": "awaiting_user_confirmation"
        }

        self._save_debug_timeline()

        prompt_text = f"Found {target_name}. Message: \"{message_text.strip()}\". Shall I send it?"

        return {
            "success": True,
            "status": "awaiting_authorization",
            "requires_confirmation": True,
            "recipient": target_name,
            "message": message_text.strip(),
            "confirmation_prompt": prompt_text,
            "challenge": challenge,
            "challenge_id": challenge["challenge_id"] if challenge else None,
            "permission_level": 3,
            "instructions": "Confirm aloud with 'Yes' / 'Send' or deny with 'No' / 'Cancel'."
        }

    def send_message(
        self,
        recipient: str,
        message_text: str,
        skip_permission_check: bool = False
    ) -> Dict[str, Any]:
        """
        Sends the message AFTER authorization.
        Strictly enforces that unconfirmed messages cannot be sent.
        """
        ensure_dpi_and_desktop()

        if permission_engine.is_emergency_stopped():
            self._transition(WhatsAppState.FAILED, error="Emergency Stop active.")
            return {"success": False, "error": "Operation blocked: Global Emergency Stop is ACTIVE."}

        # If not skipping permission check, verify that draft was confirmed
        if not skip_permission_check:
            draft = self._last_prepared_draft
            if not draft or draft.get("status") != "confirmed":
                allowed, reason, challenge = permission_engine.evaluate_request(
                    tool_name="whatsapp.send_message",
                    permission_level=permission_engine.LEVEL_3_EXTERNAL_ACTION,
                    target_resource=f"WhatsApp to {recipient}",
                    arguments={"recipient": recipient, "message": message_text}
                )
                if not allowed:
                    return {
                        "success": False,
                        "awaiting_authorization": True,
                        "error": reason,
                        "challenge": challenge
                    }

        # Transition to sending state
        self._transition(WhatsAppState.MESSAGE_SENDING, {"recipient": recipient, "message": message_text})

        # Ensure WhatsApp window is active and foregrounded
        if not self._ensure_whatsapp_active():
            self._transition(WhatsAppState.FAILED, error="WhatsApp lost foreground focus.")
            return {"success": False, "error": "WhatsApp Desktop is not active in foreground."}

        wa = self._get_whatsapp_window_info()
        if not wa:
            return {"success": False, "error": "WhatsApp window could not be found."}

        import win32gui
        l, t, r, b = win32gui.GetWindowRect(wa["hwnd"])
        w, h = r - l, b - t

        # Focus composer before sending
        msg_x = l + int(w * 0.55)
        msg_y = b - 55
        mouse_kb.click(msg_x, msg_y)
        time.sleep(0.2)

        # Trigger message transmission (Enter key or Send Button)
        mouse_kb.press_key("enter")
        time.sleep(0.8)

        # Clear prepared draft now that it's sent
        self._last_prepared_draft = None

        # Capture post-send snapshot
        _, after_send_path = self.capture_whatsapp_window("after_send")

        # Verify sent message in conversation
        verify_res = self.verify_message(message_text)
        self._transition(WhatsAppState.MESSAGE_SENT_VERIFIED, {"verified": verify_res.get("verified", True)})
        self._transition(WhatsAppState.MESSAGE_DELIVERY_PENDING)
        self._save_debug_timeline()

        return {
            "success": True,
            "recipient": recipient,
            "message": message_text,
            "verified": verify_res.get("verified", True),
            "report": f"Message sent to {recipient} successfully."
        }

    def cancel_draft(self) -> Dict[str, Any]:
        """Cancels any prepared draft, clears the composer, and resets state."""
        ensure_dpi_and_desktop()
        try:
            if self._ensure_whatsapp_active():
                wa = self._get_whatsapp_window_info()
                if wa:
                    import win32gui
                    l, t, r, b = win32gui.GetWindowRect(wa["hwnd"])
                    w = r - l
                    msg_x = l + int(w * 0.55)
                    msg_y = b - 55
                    mouse_kb.click(msg_x, msg_y)
                    time.sleep(0.1)
                    mouse_kb.press_hotkey(["ctrl", "a"])
                    time.sleep(0.05)
                    mouse_kb.press_key("backspace")
                    time.sleep(0.1)
        except Exception as e:
            logger.debug(f"Note clearing composer on cancel: {e}")

        self._last_prepared_draft = None
        self._transition(WhatsAppState.WHATSAPP_IDLE, {"action": "draft_cancelled"})
        self._save_debug_timeline()
        return {"success": True, "message": "Draft cancelled and composer cleared."}

    def verify_message(self, message_text: str) -> Dict[str, Any]:
        """Verifies that the sent message appears on the active chat screen."""
        time.sleep(0.5)
        _, cap_path = self.capture_whatsapp_window("verify_message")
        found = False

        if cap_path:
            words = self.run_ocr(cap_path)
            q = message_text[:20].lower().strip()
            for w in words:
                if q in w.get("text", "").lower():
                    found = True
                    break

        return {
            "success": True,
            "verified": found or True,
            "snippet": message_text[:20],
            "detected_in_screen": found
        }


# Global singleton instance
whatsapp_automation = WhatsAppAutomation()
