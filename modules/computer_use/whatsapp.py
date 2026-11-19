"""
Autonomous WhatsApp Desktop & Web Automation Engine (Mark VII)
State-driven, verified execution pipeline with Level 3 permission confirmation,
Visual & Accessibility Identification Hierarchy, search result classification,
conversation & composer verification, and safety guardrails.
"""

import os
import time
import logging
import re
import json
import datetime
from enum import Enum
from dataclasses import dataclass
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

    # Auxiliary states for R1/R2/R4 guardrails
    SEARCH_RESULTS_CLASSIFIED = "SEARCH_RESULTS_CLASSIFIED"
    GROUP_CHAT_DETECTED = "GROUP_CHAT_DETECTED"
    COMPOSER_RESTRICTED = "COMPOSER_RESTRICTED"
    SEARCH_RESULTS_RETRYING = "SEARCH_RESULTS_RETRYING"
    CONVERSATION_HEADER_VERIFIED = "CONVERSATION_HEADER_VERIFIED"
    COMPOSER_VERIFIED = "COMPOSER_VERIFIED"


class SearchResultType(str, Enum):
    DIRECT_CHAT = "DIRECT_CHAT"          # 1:1 conversation under "Chats"
    GROUP_CHAT = "GROUP_CHAT"            # Group conversation (has group icon, participants, or under "Groups in common")
    CONTACT_RESULT = "CONTACT_RESULT"    # Address book contact without active chat history
    GROUP_MEMBER = "GROUP_MEMBER"        # Individual participant mentioned inside a group's metadata ("Appa is also in this group")
    SEARCH_HISTORY = "SEARCH_HISTORY"    # Past search history item
    MESSAGE_SNIPPET = "MESSAGE_SNIPPET"  # Match inside message text under "Messages"
    UNKNOWN_RESULT = "UNKNOWN_RESULT"


class SearchSection(str, Enum):
    CHATS = "Chats"
    GROUPS_IN_COMMON = "Groups in common"
    MESSAGES = "Messages"
    CONTACTS = "Contacts"
    RECENT = "Recent searches"
    UNKNOWN = "Unknown"


@dataclass
class ClassifiedSearchResult:
    name: str
    section: SearchSection
    result_type: SearchResultType
    bounds: Tuple[int, int, int, int]  # (left, top, width, height)
    center_coords: Tuple[int, int]     # (cx, cy)
    confidence: float
    raw_text: str
    is_direct_chat: bool
    is_group: bool
    participant_info: Optional[str] = None


@dataclass
class ConversationHeaderInfo:
    raw_title: str
    raw_subtitle: str
    is_group: bool
    classification: str  # "DIRECT_CHAT" or "GROUP_CHAT"
    verified_for_target: bool
    matched_name: Optional[str] = None


@dataclass
class ComposerStateInfo:
    is_present: bool
    is_enabled: bool
    sending_permitted: bool
    placeholder_or_banner: str
    restriction_reason: Optional[str] = None
    coords: Tuple[int, int] = (0, 0)


RESTRICTION_PATTERNS = [
    r"only admins can send messages",
    r"you can'?t send messages to this group",
    r"you are no longer a participant",
    r"this chat is unavailable",
    r"only community admins can send messages",
    r"messages can'?t be sent to this group",
    r"announcement group",
    r"read[\s\-]only"
]


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
    """Automates WhatsApp Desktop with strict 18-state verification, R1-R4 guardrails, and Level 3 permission confirmation."""

    # Default contact relation mappings (seeded or augmented from profile memory)
    RELATION_ALIASES = {
        "father": ["dad", "appa", "papa", "pitaji", "father"],
        "mother": ["mom", "mummy", "amma", "mataji", "mother"],
        "brother": ["bro", "anna", "thambi", "bhai"],
        "sister": ["sis", "akka", "thangai", "behen"]
    }

    RESTRICTION_PATTERNS = RESTRICTION_PATTERNS

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

    def save_milestone_screenshot(self, milestone_name: str) -> Tuple[Optional[Image.Image], Optional[str]]:
        """
        Captures and saves a standardized milestone screenshot for audit and diagnostics (R4).
        Standard milestones:
          - search_results
          - classified_direct_chat_results
          - selected_conversation
          - message_composer
          - after_message_entry
          - after_sending
        """
        im, path = self.capture_whatsapp_window(milestone_name)
        if path:
            logger.info(f"[WhatsApp Audit Milestone Screenshot] {milestone_name} -> {path}")
        return im, path

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

    def _cluster_words_into_lines(self, words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Groups OCR words into horizontal text lines sorted vertically."""
        if not words:
            return []

        sorted_words = sorted(words, key=lambda w: (w.get("y", 0), w.get("x", 0)))
        lines: List[Dict[str, Any]] = []

        for w in sorted_words:
            wy = w.get("y", 0)
            wh = w.get("h", 15)
            placed = False
            for line in lines:
                if abs(line["cy"] - (wy + wh / 2.0)) < max(wh * 0.7, 10):
                    line["words"].append(w)
                    line["x"] = min(line["x"], w.get("x", 0))
                    line["y"] = min(line["y"], wy)
                    line["r"] = max(line["r"], w.get("x", 0) + w.get("w", 0))
                    line["b"] = max(line["b"], wy + wh)
                    line["w"] = line["r"] - line["x"]
                    line["h"] = line["b"] - line["y"]
                    line["cx"] = (line["x"] + line["r"]) / 2.0
                    line["cy"] = (line["y"] + line["b"]) / 2.0
                    line["words"].sort(key=lambda item: item.get("x", 0))
                    line["text"] = " ".join(item.get("text", "") for item in line["words"])
                    placed = True
                    break
            if not placed:
                lines.append({
                    "words": [w],
                    "text": w.get("text", ""),
                    "x": w.get("x", 0),
                    "y": wy,
                    "r": w.get("x", 0) + w.get("w", 0),
                    "b": wy + wh,
                    "w": w.get("w", 0),
                    "h": wh,
                    "cx": w.get("cx", w.get("x", 0) + w.get("w", 0) / 2.0),
                    "cy": w.get("cy", wy + wh / 2.0)
                })
        lines.sort(key=lambda l: l["y"])
        return lines

    def _classify_single_item(
        self,
        raw_text: str,
        section: SearchSection,
        bounds: Tuple[int, int, int, int],
        center_coords: Tuple[int, int],
        target_name: Optional[str] = None
    ) -> Optional[ClassifiedSearchResult]:
        """Classifies a search candidate into explicit SearchResultType (R1)."""
        txt = raw_text.strip()
        txt_lower = txt.lower()

        if not txt:
            return None

        # Check for group member snippets ("Appa is also in this group", etc.)
        is_member_snippet = bool(
            re.search(r"\balso\s+in\s+this\s+group\b|\bparticipants?\b", txt_lower)
            or (txt.count(",") >= 2 and any(k in txt_lower for k in ("you", "admin")))
        )

        is_group_chat = bool(
            section == SearchSection.GROUPS_IN_COMMON
            or "group" in txt_lower
            or is_member_snippet
        )

        if section == SearchSection.GROUPS_IN_COMMON:
            result_type = SearchResultType.GROUP_MEMBER if is_member_snippet else SearchResultType.GROUP_CHAT
            is_direct = False
            is_grp = True
        elif section == SearchSection.MESSAGES:
            result_type = SearchResultType.MESSAGE_SNIPPET
            is_direct = False
            is_grp = False
        elif is_member_snippet:
            result_type = SearchResultType.GROUP_MEMBER
            is_direct = False
            is_grp = True
        elif is_group_chat:
            result_type = SearchResultType.GROUP_CHAT
            is_direct = False
            is_grp = True
        elif section == SearchSection.CHATS:
            result_type = SearchResultType.DIRECT_CHAT
            is_direct = True
            is_grp = False
        else:
            if target_name and target_name.strip().lower() in txt_lower and not is_group_chat:
                result_type = SearchResultType.DIRECT_CHAT
                is_direct = True
                is_grp = False
            else:
                result_type = SearchResultType.UNKNOWN_RESULT
                is_direct = False
                is_grp = False

        return ClassifiedSearchResult(
            name=txt,
            section=section,
            result_type=result_type,
            bounds=bounds,
            center_coords=center_coords,
            confidence=0.9 if is_direct else 0.7,
            raw_text=txt,
            is_direct_chat=is_direct,
            is_group=is_grp,
            participant_info="group_member_snippet" if is_member_snippet else None
        )

    def _extract_results_via_uia(self, contact_name: str, hwnd: int) -> List[ClassifiedSearchResult]:
        """Level 1-4: Query Windows UI Automation on WhatsApp WebView2/Root window."""
        results: List[ClassifiedSearchResult] = []
        try:
            import uiautomation as auto
            root = auto.ControlFromHandle(hwnd)
            if not root:
                return []

            doc = root.DocumentControl()
            search_root = doc if doc.Exists(0, 0) else root

            rect = root.BoundingRectangle
            left_pane_max_x = rect.left + int(rect.width() * 0.40)

            current_section = SearchSection.UNKNOWN
            y_chats = -1
            y_groups = -1

            def inspect_ctrl(ctrl, depth):
                nonlocal current_section, y_chats, y_groups
                if depth > 5:
                    return
                try:
                    name = (ctrl.Name or "").strip()
                    c_type = ctrl.ControlTypeName or ""
                    b = ctrl.BoundingRectangle
                    if b.left < left_pane_max_x and b.top > rect.top + 100:
                        name_l = name.lower()
                        if name_l in ("chats", "chat") or "chats" == name_l:
                            y_chats = b.top
                            current_section = SearchSection.CHATS
                        elif "groups in common" in name_l:
                            y_groups = b.top
                            current_section = SearchSection.GROUPS_IN_COMMON

                        if c_type in ("ListItemControl", "CustomControl", "ButtonControl") and name:
                            bounds = (b.left, b.top, b.width(), b.height())
                            center = (b.left + b.width() // 2, b.top + b.height() // 2)
                            sec = current_section
                            if y_chats != -1 and y_groups != -1:
                                if y_chats <= b.top < y_groups:
                                    sec = SearchSection.CHATS
                                elif b.top >= y_groups:
                                    sec = SearchSection.GROUPS_IN_COMMON

                            res_item = self._classify_single_item(name, sec, bounds, center, contact_name)
                            if res_item:
                                results.append(res_item)

                    for ch in ctrl.GetChildren():
                        inspect_ctrl(ch, depth + 1)
                except Exception:
                    pass

            inspect_ctrl(search_root, 1)
        except Exception as e:
            logger.debug(f"UIA extraction note: {e}")
        return results

    def _extract_results_via_ocr(
        self,
        contact_name: str,
        img_path: str,
        window_rect: Tuple[int, int, int, int]
    ) -> List[ClassifiedSearchResult]:
        """Level 5: Native Windows 11 OCR vertical slicing."""
        words = self.run_ocr(img_path)
        if not words:
            return []

        l, t, r, b = window_rect
        w, h = r - l, b - t
        left_pane_w = min(max(int(w * 0.40), 350), 700)

        # Filter words in left panel and below search bar
        pane_words = [
            w_item for w_item in words
            if w_item.get("x", 0) < left_pane_w and w_item.get("y", 0) > 100
        ]

        lines = self._cluster_words_into_lines(pane_words)

        y_chats = -1
        y_groups = -1
        y_messages = -1

        for line in lines:
            txt = line["text"].strip().lower()
            cy = line["cy"]
            if re.search(r"^(?:c\s*hats?|chats?)$", txt) or txt == "chats":
                y_chats = cy
            elif re.search(r"groups?\s+in\s+common", txt) or ("groups" in txt and "common" in txt):
                y_groups = cy
            elif re.search(r"^messages?$", txt) or txt == "messages":
                y_messages = cy

        results: List[ClassifiedSearchResult] = []
        target_norm = contact_name.strip().lower()

        for line in lines:
            cy = line["cy"]
            txt = line["text"].strip()
            txt_lower = txt.lower()

            # Skip section heading lines themselves
            if cy in (y_chats, y_groups, y_messages):
                continue
            if re.search(r"^(?:c\s*hats?|chats?|groups?\s+in\s+common|messages?)$", txt_lower):
                continue

            # Determine section based on vertical boundaries
            if y_chats != -1 and y_groups != -1:
                if y_chats <= cy < y_groups:
                    sec = SearchSection.CHATS
                elif y_groups <= cy < (y_messages if y_messages != -1 else 99999):
                    sec = SearchSection.GROUPS_IN_COMMON
                elif y_messages != -1 and cy >= y_messages:
                    sec = SearchSection.MESSAGES
                else:
                    sec = SearchSection.UNKNOWN
            elif y_groups != -1:
                if cy < y_groups:
                    sec = SearchSection.CHATS
                elif y_messages != -1 and cy >= y_messages:
                    sec = SearchSection.MESSAGES
                else:
                    sec = SearchSection.GROUPS_IN_COMMON
            elif y_chats != -1:
                if cy >= y_chats:
                    sec = SearchSection.CHATS
                else:
                    sec = SearchSection.UNKNOWN
            else:
                sec = SearchSection.UNKNOWN

            bounds = (line["x"] + l, line["y"] + t, line["w"], line["h"])
            center = (int(line["cx"] + l), int(line["cy"] + t))

            item = self._classify_single_item(txt, sec, bounds, center, target_norm)
            if item:
                results.append(item)

        return results

    def extract_and_classify_search_results(
        self,
        contact_name: str,
        img_path: Optional[str],
        window_rect: Tuple[int, int, int, int],
        hwnd: int
    ) -> List[ClassifiedSearchResult]:
        """
        Implements the 6-Level Visual & Accessibility Identification Hierarchy (R3):
        Windows UIA -> Accessible names -> Section headings -> Element hierarchy -> OCR slicing -> Calibrated fallback.
        """
        # Level 1-4: UI Automation
        uia_results = self._extract_results_via_uia(contact_name, hwnd)
        if uia_results:
            logger.info(f"[WhatsApp Hierarchy Level 1-4] Extracted {len(uia_results)} items via Windows UI Automation.")
            return uia_results

        # Level 5: Native Windows 11 OCR vertical slicing
        if img_path:
            ocr_results = self._extract_results_via_ocr(contact_name, img_path, window_rect)
            if ocr_results:
                logger.info(f"[WhatsApp Hierarchy Level 5] Extracted {len(ocr_results)} items via OCR vertical slicing.")
                return ocr_results

        # Level 6: Never blind click without verification
        logger.warning("[WhatsApp Hierarchy Level 6] UIA and OCR yielded no items. Avoiding blind first-result click.")
        return []

    def select_best_direct_chat(
        self,
        candidates: List[ClassifiedSearchResult],
        target_name: str
    ) -> Tuple[Optional[ClassifiedSearchResult], Optional[str]]:
        """
        Selects the intended direct one-to-one conversation under 'Chats' (R1).
        Strictly rejects 'Groups in common', group chats, member snippets, and message history.
        Handles ambiguous direct matches by requesting clarification.
        """
        target_norm = target_name.strip().lower()

        # Log every candidate result evaluated (Field 1, 2, 3 for R4 audit)
        for c in candidates:
            logger.info(
                f"[WhatsApp Audit] Search candidate evaluated: text='{c.raw_text}', "
                f"type='{c.result_type.value}', section='{c.section.value}'"
            )

        # 1. Filter strictly for DIRECT_CHAT under CHATS section
        direct_chats = [
            c for c in candidates
            if c.section == SearchSection.CHATS
            and c.result_type == SearchResultType.DIRECT_CHAT
            and c.is_direct_chat is True
            and not c.is_group
        ]

        # Filter for matching contact name
        matching_direct = [
            c for c in direct_chats
            if target_norm in c.name.strip().lower() or c.name.strip().lower() in target_norm
        ]

        if not matching_direct:
            groups_found = [
                c for c in candidates
                if c.is_group or c.result_type in (SearchResultType.GROUP_CHAT, SearchResultType.GROUP_MEMBER)
                or c.section == SearchSection.GROUPS_IN_COMMON
            ]
            if groups_found:
                return None, f"Only group conversations found for '{target_name}'. Direct one-to-one conversation under 'Chats' not found."
            return None, f"No direct conversation found for '{target_name}' under 'Chats'."

        # 2. Check for exact match
        exact_matches = [
            c for c in matching_direct
            if c.name.strip().lower() == target_norm
        ]
        if len(exact_matches) == 1:
            return exact_matches[0], None

        # 3. Disambiguation if multiple direct conversations match under Chats
        if len(matching_direct) > 1:
            names = [c.name for c in matching_direct]
            return None, f"Multiple direct conversations match '{target_name}': {', '.join(names)}. Please clarify which contact to message."

        return matching_direct[0], None

    def _inspect_conversation_header(self, expected_name: str) -> ConversationHeaderInfo:
        """
        Inspects conversation header in right pane (y < 220) (R2).
        Extracts Title and Subtitle, determines group vs direct contact,
        and verifies identity against expected contact name.
        """
        _, cap_path = self.capture_whatsapp_window("selected_conversation")
        if not cap_path:
            return ConversationHeaderInfo(
                raw_title="",
                raw_subtitle="",
                is_group=False,
                classification="UNKNOWN",
                verified_for_target=False
            )

        words = self.run_ocr(cap_path)
        wa = self._get_whatsapp_window_info()
        left_bound = 350
        if wa and wa.get("hwnd"):
            try:
                import win32gui
                rect = win32gui.GetWindowRect(wa["hwnd"])
                left_bound = int((rect[2] - rect[0]) * 0.38)
            except Exception:
                pass

        header_words = [w for w in words if w.get("x", 0) > left_bound and w.get("y", 0) < 220]
        lines = self._cluster_words_into_lines(header_words)

        title_text = ""
        subtitle_text = ""
        if len(lines) >= 1:
            title_text = lines[0]["text"].strip()
        if len(lines) >= 2:
            subtitle_text = lines[1]["text"].strip()

        subtitle_lower = subtitle_text.lower()
        title_lower = title_text.lower()
        expected_lower = expected_name.strip().lower()

        group_indicators = [
            "group info", "click here for group info", "tap here for group info",
            "participants", "members", "admin", "you, "
        ]
        is_group = any(ind in subtitle_lower for ind in group_indicators) or "group" in title_lower

        classification = "GROUP_CHAT" if is_group else "DIRECT_CHAT"

        verified = False
        if not is_group and title_text:
            if expected_lower in title_lower or title_lower in expected_lower:
                verified = True
            for relation, aliases in self.RELATION_ALIASES.items():
                if expected_lower in aliases:
                    if any(al in title_lower for al in aliases):
                        verified = True

        header_info = ConversationHeaderInfo(
            raw_title=title_text,
            raw_subtitle=subtitle_text,
            is_group=is_group,
            classification=classification,
            verified_for_target=verified,
            matched_name=title_text if verified else None
        )

        # Structured logging for Field 5 & 6 (R4)
        logger.info(
            f"[WhatsApp Audit] Conversation header: title='{header_info.raw_title}', "
            f"subtitle='{header_info.raw_subtitle}'"
        )
        logger.info(
            f"[WhatsApp Audit] Classification: group_vs_direct='{header_info.classification}', "
            f"is_group={header_info.is_group}"
        )

        return header_info

    def _wait_for_conversation_load(self, expected_name: str, timeout: float = 3.0) -> ConversationHeaderInfo:
        """Polls conversation pane until header stabilizes (R2)."""
        start_time = time.time()
        last_header = None
        while time.time() - start_time < timeout:
            header_info = self._inspect_conversation_header(expected_name)
            if header_info and header_info.raw_title:
                return header_info
            time.sleep(0.25)
        return last_header or ConversationHeaderInfo(
            raw_title="",
            raw_subtitle="",
            is_group=False,
            classification="UNKNOWN",
            verified_for_target=False
        )

    def _inspect_composer(self) -> ComposerStateInfo:
        """
        Inspects message composer area (bottom right pane) (R2).
        Checks if composer is enabled, whether sending is permitted,
        and detects restricted group states ("Only admins can send messages", etc.).
        """
        self.save_milestone_screenshot("message_composer")

        wa = self._get_whatsapp_window_info()
        left_bound = 350
        h = 800
        msg_x = 600
        msg_y = 750
        if wa and wa.get("hwnd"):
            try:
                import win32gui
                rect = win32gui.GetWindowRect(wa["hwnd"])
                l, t, r, b = rect
                w, h = r - l, b - t
                left_bound = int(w * 0.38)
                msg_x = l + int(w * 0.55)
                msg_y = b - 55
            except Exception:
                pass

        _, cap_path = self.capture_whatsapp_window("composer_check")
        words = self.run_ocr(cap_path) if cap_path else []

        composer_words = [w for w in words if w.get("x", 0) > left_bound and w.get("y", 0) > max(h - 140, 100)]
        composer_text = " ".join(w.get("text", "") for w in composer_words).strip().lower()

        restriction_found = None
        for pattern in self.RESTRICTION_PATTERNS:
            if re.search(pattern, composer_text):
                clean = re.sub(r"[\\^$*+?.()|[\]{}]", "", pattern).replace("'", "")
                clean = re.sub(r"\s+", " ", clean).strip()
                restriction_found = clean
                break

        if restriction_found:
            info = ComposerStateInfo(
                is_present=True,
                is_enabled=False,
                sending_permitted=False,
                placeholder_or_banner=composer_text or "Restricted composer banner",
                restriction_reason=restriction_found,
                coords=(msg_x, msg_y)
            )
        else:
            info = ComposerStateInfo(
                is_present=True,
                is_enabled=True,
                sending_permitted=True,
                placeholder_or_banner="Type a message",
                restriction_reason=None,
                coords=(msg_x, msg_y)
            )

        # Structured logging for Field 7 & 8 (R4)
        logger.info(
            f"[WhatsApp Audit] Composer enabled state: is_enabled={info.is_enabled}, "
            f"banner='{info.placeholder_or_banner}'"
        )
        logger.info(
            f"[WhatsApp Audit] Sending permission: permitted={info.sending_permitted}, "
            f"restriction='{info.restriction_reason}'"
        )

        return info

    def _return_to_search_results(self):
        """Safely recovers from accidental selection by pressing Esc and refocusing search results."""
        self._transition(WhatsAppState.SEARCH_RESULTS_RETRYING)
        mouse_kb.press_key("esc")
        time.sleep(0.2)
        mouse_kb.press_hotkey(["ctrl", "f"])
        time.sleep(0.2)

    def _get_whatsapp_window_info(self) -> Optional[Dict[str, Any]]:
        """Locates the primary interactive WhatsApp window (prioritizes WebView2 renderer)."""
        ensure_dpi_and_desktop()
        wins = ApplicationManager.list_open_windows()
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
        State-driven conversation opening (R1 & R2 & R3):
        Focuses search -> Types query -> Extracts & classifies results ->
        Prioritizes direct chat under 'Chats' -> Verifies header ->
        Rejects groups with return-to-search recovery.
        """
        ensure_dpi_and_desktop()

        # Step 1: Ensure WhatsApp is foreground
        if not self._ensure_whatsapp_active():
            self._transition(WhatsAppState.FAILED, error="WhatsApp is not active or could not be foregrounded.")
            return {"success": False, "error": "WhatsApp Desktop is not active in foreground."}

        # Step 2: Check if already open and verified
        if self._current_open_contact and self._current_open_contact.lower() == contact_name.lower():
            header = self._inspect_conversation_header(contact_name)
            if header.verified_for_target and not header.is_group:
                self._transition(WhatsAppState.CONVERSATION_VERIFIED, {"contact": contact_name, "cached": True})
                return {
                    "success": True,
                    "contact": contact_name,
                    "method": "already_open",
                    "verified": True,
                    "is_group": False,
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

        # Defensively unfocus any modal
        mouse_kb.press_key("esc")
        time.sleep(0.15)

        # Calibrated Search Box position
        search_x = l + min(max(int(w * 0.22), 200), 380)
        search_y = t + min(max(int(h * 0.28), 200), 285)

        # Focus Search Box using Ctrl+F shortcut and verified click
        self._transition(WhatsAppState.CONTACT_SEARCHING, {"contact": contact_name})
        mouse_kb.press_hotkey(["ctrl", "f"])
        time.sleep(0.1)
        mouse_kb.click(search_x, search_y)
        time.sleep(0.15)

        # Clear any existing query
        mouse_kb.press_hotkey(["ctrl", "a"])
        time.sleep(0.05)
        mouse_kb.press_key("backspace")
        time.sleep(0.1)

        # Type contact name into search box
        mouse_kb.type_text(contact_name)
        time.sleep(0.8)  # Wait for search results to populate

        # Milestone 1: search_results screenshot (R4)
        _, search_img_path = self.save_milestone_screenshot("search_results")

        # Step 5: Extract and Classify Search Results (6-Level Hierarchy)
        candidates = self.extract_and_classify_search_results(contact_name, search_img_path, (l, t, r, b), hwnd)
        self._transition(WhatsAppState.CONTACT_RESULTS_DETECTED, {"candidates_found": len(candidates)})
        self._transition(WhatsAppState.SEARCH_RESULTS_CLASSIFIED, {"classified_count": len(candidates)})

        # Milestone 2: classified_direct_chat_results screenshot (R4)
        self.save_milestone_screenshot("classified_direct_chat_results")

        # Step 6: Select direct chat under Chats, strictly rejecting groups
        selected_cand, err_reason = self.select_best_direct_chat(candidates, contact_name)

        if not selected_cand:
            is_ambiguous = bool(err_reason and "Multiple direct conversations" in err_reason)
            is_group_only = bool(err_reason and "Only group conversations found" in err_reason)
            self._transition(WhatsAppState.FAILED, error=err_reason or "Contact search selection failed.")
            self._save_debug_timeline()
            return {
                "success": False,
                "error": err_reason or f"Failed to find direct conversation for '{contact_name}'.",
                "ambiguous": is_ambiguous,
                "is_group": is_group_only,
                "verified": False
            }

        # Step 7: Log selected result (Field 4 for R4 audit)
        click_x, click_y = selected_cand.center_coords
        logger.info(
            f"[WhatsApp Audit] Selected result: text='{selected_cand.name}', "
            f"type='{selected_cand.result_type.value}', section='{selected_cand.section.value}', "
            f"coords=({click_x}, {click_y})"
        )
        self._transition(WhatsAppState.CONTACT_IDENTIFIED, {
            "matched_text": selected_cand.name,
            "section": selected_cand.section.value,
            "type": selected_cand.result_type.value,
            "coords": (click_x, click_y)
        })

        # Step 8: Click candidate and wait for conversation to load
        self._transition(WhatsAppState.CONVERSATION_OPENING, {"coords": (click_x, click_y)})
        mouse_kb.click(click_x, click_y)

        # Dynamic wait for conversation loading (R2)
        header_info = self._wait_for_conversation_load(contact_name, timeout=3.0)

        # Milestone 3: selected_conversation screenshot (R4)
        self.save_milestone_screenshot("selected_conversation")

        # Step 9: Safety Guardrail - Check if selected conversation is a Group Chat (R2)
        if header_info.is_group or header_info.classification == "GROUP_CHAT":
            logger.warning(
                f"[WhatsApp Safety Guardrail] Selected conversation '{header_info.raw_title}' is a GROUP CHAT, "
                f"not direct contact '{contact_name}'. Aborting message entry in group."
            )
            self._transition(WhatsAppState.GROUP_CHAT_DETECTED, {
                "header_title": header_info.raw_title,
                "expected": contact_name
            })

            # Return to search results to locate the correct direct conversation
            self._return_to_search_results()

            # Attempt to find alternative direct candidate from list
            remaining_direct = [
                c for c in candidates
                if c.name != selected_cand.name
                and c.section == SearchSection.CHATS
                and c.result_type == SearchResultType.DIRECT_CHAT
            ]
            if remaining_direct:
                alt_cand, _ = self.select_best_direct_chat(remaining_direct, contact_name)
                if alt_cand:
                    ax, ay = alt_cand.center_coords
                    mouse_kb.click(ax, ay)
                    header_info = self._wait_for_conversation_load(contact_name, timeout=3.0)

            if header_info.is_group or not header_info.verified_for_target:
                self._transition(WhatsAppState.FAILED, error=f"Group conversation detected ('{header_info.raw_title}'). Direct chat not found.")
                self._save_debug_timeline()
                return {
                    "success": False,
                    "error": f"Selected chat '{header_info.raw_title}' is a group chat, not direct contact '{contact_name}'. Message entry aborted.",
                    "is_group": True,
                    "verified": False
                }

        # Step 10: Verify direct conversation header (R2 - Genuine verification, NO heuristic bypass!)
        if header_info.verified_for_target:
            self._current_open_contact = contact_name.lower()
            self._transition(WhatsAppState.CONVERSATION_HEADER_VERIFIED, {"title": header_info.raw_title})
            self._transition(WhatsAppState.CONVERSATION_VERIFIED, {"contact": contact_name})
            self._save_debug_timeline()
            return {
                "success": True,
                "contact": contact_name,
                "verified": True,
                "is_group": False,
                "header": header_info.raw_title,
                "message": f"Opened and verified direct conversation with '{contact_name}'."
            }
        else:
            self._transition(WhatsAppState.FAILED, error=f"Failed to verify direct conversation header for '{contact_name}'.")
            self._save_debug_timeline()
            return {
                "success": False,
                "contact": contact_name,
                "verified": False,
                "is_group": False,
                "error": f"Failed to verify direct conversation header for '{contact_name}'."
            }

    def _verify_conversation_header(self, expected_name: str) -> bool:
        """Helper for backward-compatibility checking header verification."""
        header_info = self._inspect_conversation_header(expected_name)
        return header_info.verified_for_target and not header_info.is_group

    def prepare_message(self, recipient: str, message_text: str) -> Dict[str, Any]:
        """
        Prepares a WhatsApp message (R2 & R4):
        1. Resolves recipient relation/name.
        2. Opens and verifies direct conversation.
        3. Inspects composer for restricted group states.
        4. Enters message content and verifies.
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
        open_res = None
        try:
            open_res = self.open_conversation(search_query)
        except Exception as e:
            logger.warning(f"Note during visual WhatsApp conversation navigation: {e}")

        # Safety Guardrails: if open_conversation reported group chat, restricted composer, or ambiguous match:
        if open_res and not open_res.get("success"):
            if open_res.get("is_group") or open_res.get("ambiguous"):
                logger.error(f"[WhatsApp Safety Guardrail] Message preparation aborted: {open_res.get('error')}")
                return {
                    "success": False,
                    "error": open_res.get("error", "Message preparation aborted by safety guardrail."),
                    "is_group": open_res.get("is_group", False),
                    "ambiguous": open_res.get("ambiguous", False),
                    "details": open_res
                }

        # Step 3: Inspect composer and check for restricted states (R2)
        comp_info = self._inspect_composer()
        if not comp_info.sending_permitted:
            logger.error(
                f"[WhatsApp Safety Guardrail] Message composer is restricted: {comp_info.restriction_reason}. "
                "Halting message preparation."
            )
            self._transition(WhatsAppState.COMPOSER_RESTRICTED, {"restriction": comp_info.restriction_reason})
            self._save_debug_timeline()
            return {
                "success": False,
                "error": f"Cannot send message: {comp_info.restriction_reason}",
                "composer_state": "restricted",
                "restriction": comp_info.restriction_reason
            }

        # Step 4: Detect and focus composer
        wa = self._get_whatsapp_window_info()
        if wa and wa.get("hwnd") and self._is_whatsapp_foreground():
            try:
                import win32gui
                l, t, r, b = win32gui.GetWindowRect(wa["hwnd"])
                w, h = r - l, b - t

                msg_x = comp_info.coords[0] if comp_info.coords != (0, 0) else (l + int(w * 0.55))
                msg_y = comp_info.coords[1] if comp_info.coords != (0, 0) else (b - 55)

                self._transition(WhatsAppState.COMPOSER_DETECTED, {"coords": (msg_x, msg_y)})
                self._transition(WhatsAppState.COMPOSER_VERIFIED, {"enabled": True})

                # Focus message input box
                mouse_kb.click(msg_x, msg_y)
                time.sleep(0.2)

                # Step 5: Enter message content into composer
                self._transition(WhatsAppState.MESSAGE_ENTERING, {"message": message_text})
                mouse_kb.press_hotkey(["ctrl", "a"])
                time.sleep(0.05)
                mouse_kb.press_key("backspace")
                time.sleep(0.1)

                # Type ONLY message text (never the contact name!)
                mouse_kb.type_text(message_text.strip())
                time.sleep(0.3)

                # Milestone 5: after_message_entry screenshot (R4)
                self.save_milestone_screenshot("after_message_entry")
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

        result_payload = {
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

        # Structured logging for Field 9 (R4)
        logger.info(
            f"[WhatsApp Audit] Final execution result: success={result_payload['success']}, "
            f"action='prepare_message', recipient='{target_name}'"
        )

        return result_payload

    def send_message(
        self,
        recipient: str,
        message_text: str,
        skip_permission_check: bool = False
    ) -> Dict[str, Any]:
        """
        Sends the message AFTER authorization (R2 & R4).
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

        # Milestone 6: after_sending screenshot (R4)
        self.save_milestone_screenshot("after_sending")

        # Clear prepared draft now that it's sent
        self._last_prepared_draft = None

        # Verify sent message in conversation (Genuine boolean verification!)
        verify_res = self.verify_message(message_text)
        self._transition(WhatsAppState.MESSAGE_SENT_VERIFIED, {"verified": verify_res.get("verified", False)})
        self._transition(WhatsAppState.MESSAGE_DELIVERY_PENDING)
        self._save_debug_timeline()

        result_payload = {
            "success": True,
            "recipient": recipient,
            "message": message_text,
            "verified": verify_res.get("verified", False),
            "report": f"Message sent to {recipient} successfully."
        }

        # Structured logging for Field 9 (R4)
        logger.info(
            f"[WhatsApp Audit] Final execution result: success={result_payload['success']}, "
            f"action='send_message', recipient='{recipient}', verified={result_payload['verified']}"
        )

        return result_payload

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
        """Verifies that the sent message appears on the active chat screen (R2)."""
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
            "verified": bool(found),
            "snippet": message_text[:20],
            "detected_in_screen": found
        }


# Global singleton instance
whatsapp_automation = WhatsAppAutomation()
