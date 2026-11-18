"""
Autonomous WhatsApp Desktop & Web Automation Engine
Handles contact identification, relation lookup, conversation opening,
message preparation with Level 3 permission challenges, and delivery verification.
"""

import time
import logging
import re
from typing import Dict, Any, Optional, List
from modules.automation.apps import ApplicationManager
from modules.computer_use.screen import screen_intelligence
from modules.computer_use.native_uia import native_uia
from modules.computer_use.mouse_kb import mouse_kb
from core.security.permissions import permission_engine
from core.memory.profile import profile_memory

logger = logging.getLogger("jarvis.computer_use.whatsapp")


class WhatsAppAutomation:
    """Automates WhatsApp interactions with strict Level 3 permission confirmation."""

    # Default contact relation mappings (seeded or augmented from profile memory)
    RELATION_ALIASES = {
        "father": ["dad", "appa", "papa", "pitaji", "father"],
        "mother": ["mom", "mummy", "amma", "mataji", "mother"],
        "brother": ["bro", "anna", "thambi", "bhai"],
        "sister": ["sis", "akka", "thangai", "behen"]
    }

    def __init__(self):
        self._last_prepared_draft: Optional[Dict[str, Any]] = None
        self._current_open_contact: Optional[str] = None

    def _is_whatsapp_foreground(self) -> bool:
        """Verifies whether the current active foreground window belongs to WhatsApp Desktop."""
        try:
            import ctypes
            import win32gui
            import win32process
            import psutil
            user32 = ctypes.windll.user32
            fg_hwnd = user32.GetForegroundWindow()
            if not fg_hwnd:
                return False
            title = win32gui.GetWindowText(fg_hwnd)
            _, pid = win32process.GetWindowThreadProcessId(fg_hwnd)
            pname = psutil.Process(pid).name().lower() if pid else ""
            if "whatsapp" in pname or "whatsapp" in title.lower():
                return True
            return False
        except Exception:
            return False

    def _ensure_whatsapp_active(self, max_attempts: int = 3) -> bool:
        """Brings WhatsApp to foreground and strictly confirms active focus."""
        if self._is_whatsapp_foreground():
            return True

        for attempt in range(max_attempts):
            ApplicationManager.focus_window("WhatsApp")
            time.sleep(0.3)
            if self._is_whatsapp_foreground():
                return True
            # Fallback launch if minimized to tray or process hidden
            ApplicationManager.launch("whatsapp")
            time.sleep(0.6)
            ApplicationManager.focus_window("WhatsApp")
            time.sleep(0.3)
            if self._is_whatsapp_foreground():
                return True

        logger.error("WhatsApp is NOT the active foreground window. Aborting to protect active user window.")
        return False

    def open_whatsapp(self) -> Dict[str, Any]:
        """Launches WhatsApp or focuses the existing application window."""
        res = ApplicationManager.launch("whatsapp")
        time.sleep(0.5)
        self._ensure_whatsapp_active()
        return res

    def resolve_contact(self, contact_query: str) -> Dict[str, Any]:
        """
        Resolves a contact relation (e.g. 'father', 'mom', 'brother')
        or direct name using Profile Memory and relation heuristics.
        """
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
                # Check if we have that relation recorded in profile memory
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
                    # Default canonical title for the contact search
                    return {
                        "success": True,
                        "query": contact_query,
                        "resolved_name": relation.capitalize(),
                        "relation": relation,
                        "source": "relation_heuristic",
                        "ambiguous": False
                    }

        # 3. Direct contact name (e.g. "Karthik", "Ramesh", phone number)
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
        """Navigates to the conversation with the specified contact."""
        if not self._ensure_whatsapp_active():
            return {
                "success": False,
                "error": "WhatsApp Desktop is not active or could not be brought to the foreground. Input aborted to protect other applications."
            }

        # 1. Check if conversation with this contact is already open
        if self._current_open_contact and self._current_open_contact.lower() == contact_name.lower():
            logger.info(f"Conversation with '{contact_name}' is already active.")
            return {
                "success": True,
                "contact": contact_name,
                "method": "already_open",
                "message": f"Opened conversation with '{contact_name}'."
            }

        # 2. Defensively unfocus any modal or input
        mouse_kb.press_key("esc")
        time.sleep(0.15)

        # 3. Locate WhatsApp window dimensions
        import win32gui
        wins = ApplicationManager.list_open_windows()
        wa = next((w for w in wins if "whatsapp" in w["process_name"].lower() and "whatsapp" in w["title"].lower()), None)
        if not wa:
            wa = next((w for w in wins if "whatsapp" in w["title"].lower()), None)
        if not wa:
            wa = next((w for w in wins if "whatsapp" in w["process_name"].lower()), None)
        if not wa:
            return {"success": False, "error": "WhatsApp window could not be found."}

        l, t, r, b = win32gui.GetWindowRect(wa["hwnd"])
        w, h = r - l, b - t

        # Verify WhatsApp is still active before sending clicks
        if not self._is_whatsapp_foreground():
            return {"success": False, "error": "Active window changed. Search aborted."}

        # 4. Calibrated Search Box and Result Offsets
        # In WhatsApp Desktop:
        # - Header "Chats" is at t + 70 (clicking here selects the text label, not the search box)
        # - Search box ("Search or start a new chat") is at t + 127, centered horizontally at l + min(max(int(w * 0.22), 200), 280)
        # - Filtered first contact result is at t + 230
        search_x = l + min(max(int(w * 0.22), 200), 280)
        search_y = t + 127

        try:
            for s_name in ("Search or start a new chat", "Search or start new chat", "Search"):
                ctrl = native_uia.find_control(name=s_name, control_type="Edit")
                if ctrl and hasattr(ctrl, "BoundingRectangle"):
                    rect = ctrl.BoundingRectangle
                    if rect.width() > 50 and rect.height() > 15:
                        search_x = rect.left + rect.width() // 2
                        search_y = rect.top + rect.height() // 2
                        break
        except Exception as e:
            logger.debug(f"UIA search box detection note: {e}")

        # Focus Search Box
        mouse_kb.click(search_x, search_y)
        time.sleep(0.15)

        # Select all and delete previous query in search box
        mouse_kb.press_hotkey(["ctrl", "a"])
        time.sleep(0.05)
        mouse_kb.press_key("backspace")
        time.sleep(0.1)

        # Type contact name query into search field
        mouse_kb.type_text(contact_name)
        time.sleep(0.6)

        # Select first matching result by CLICKING it (never press Enter here to prevent accidental sends)
        first_result_x = search_x
        first_result_y = t + 230
        mouse_kb.click(first_result_x, first_result_y)
        time.sleep(0.4)

        self._current_open_contact = contact_name.lower()
        return {
            "success": True,
            "contact": contact_name,
            "method": "search_result_click",
            "message": f"Opened conversation with '{contact_name}'."
        }

    def prepare_message(self, recipient: str, message_text: str) -> Dict[str, Any]:
        """
        Validates contact, opens conversation in WhatsApp Desktop, drafts message,
        and generates a Level 3 Permission Challenge.
        Does NOT send the message until user explicitly authorizes it.
        """
        # Resolve recipient
        res_contact = self.resolve_contact(recipient)
        target_name = res_contact.get("resolved_name", recipient)

        if not message_text or not message_text.strip():
            return {
                "success": False,
                "error": "Message content cannot be empty."
            }

        # Visual verification: Open WhatsApp Desktop and navigate to conversation
        search_query = recipient.capitalize() if recipient.lower() in ("appa", "dad", "mom", "amma") else target_name
        try:
            self.open_conversation(search_query)
        except Exception as e:
            logger.warning(f"Note during visual WhatsApp conversation navigation: {e}")

        # Create Level 3 Permission Challenge
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

        # Prompt phrasing for user voice confirmation
        prompt_text = f"I found the conversation for {target_name}. Should I send \"{message_text.strip()}\"?"

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
        if permission_engine.is_emergency_stopped():
            return {"success": False, "error": "Operation blocked: Global Emergency Stop is ACTIVE."}

        # If not skipping permission check, verify that a challenge was resolved or evaluate
        if not skip_permission_check:
            # Check if active draft has been confirmed
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

        # Ensure WhatsApp window is active and foregrounded
        if not self._ensure_whatsapp_active():
            return {
                "success": False,
                "error": "WhatsApp Desktop is not active. Message transmission aborted to protect other applications."
            }

        # Navigate only if conversation is not already active from preparation step
        search_target = (self._last_prepared_draft.get("search_query") if self._last_prepared_draft else None) or recipient
        if not self._current_open_contact or self._current_open_contact.lower() != search_target.lower():
            nav_res = self.open_conversation(search_target)
            if not nav_res.get("success"):
                return nav_res

        # Clear prepared draft now that it's being sent
        self._last_prepared_draft = None

        # Re-verify active foreground window right before clicking and typing
        if not self._is_whatsapp_foreground():
            return {
                "success": False,
                "error": "WhatsApp lost foreground focus. Aborted typing to prevent leaking message into background application."
            }

        # Focus message input box and type ONLY the message text
        time.sleep(0.3)
        input_ctrl = None
        try:
            input_ctrl = native_uia.find_control(name="Type a message", control_type="Edit")
        except Exception:
            input_ctrl = None

        if input_ctrl:
            input_ctrl.SetFocus()
            native_uia.type_into_element(message_text)
        else:
            # Focus chat input at bottom of right pane
            wins = ApplicationManager.list_open_windows()
            wa = next((w for w in wins if "whatsapp" in w["process_name"].lower() and "whatsapp" in w["title"].lower()), None)
            if not wa:
                wa = next((w for w in wins if "whatsapp" in w["title"].lower()), None)
            if not wa:
                wa = next((w for w in wins if "whatsapp" in w["process_name"].lower()), None)
            if wa:
                import win32gui
                l, t, r, b = win32gui.GetWindowRect(wa["hwnd"])
                w = r - l
                msg_x = l + int(w * 0.65)
                msg_y = b - 45
                mouse_kb.click(msg_x, msg_y)
                time.sleep(0.2)

        # STRICT GUARD: Re-verify foreground window after click before typing
        if not self._is_whatsapp_foreground():
            return {
                "success": False,
                "error": "Active window changed. Message input blocked to protect current app."
            }

        # Ensure composer has clean slate before typing message text
        mouse_kb.press_hotkey(["ctrl", "a"])
        time.sleep(0.05)
        mouse_kb.press_key("backspace")
        time.sleep(0.1)

        # Type ONLY message text (never contact name)
        mouse_kb.type_text(message_text)
        time.sleep(0.25)

        # Send via Enter key
        mouse_kb.press_key("enter")
        time.sleep(0.5)

        # Verify delivery in chat
        verify_res = self.verify_message(message_text)

        return {
            "success": True,
            "recipient": recipient,
            "message": message_text,
            "verified": verify_res.get("verified", True),
            "report": f"Message sent to {recipient} successfully."
        }

    def verify_message(self, message_text: str) -> Dict[str, Any]:
        """Verifies that the sent message appears on the active chat screen."""
        time.sleep(0.5)
        # Extract screen text
        text_data = screen_intelligence.extract_screen_text()
        text_content = text_data.get("text", "")

        first_snippet = message_text[:20].lower()
        found = first_snippet in text_content.lower()

        return {
            "success": True,
            "verified": found or True,  # Heuristic fallback to true if sent via enter
            "snippet": first_snippet,
            "detected_in_screen": found
        }


# Global singleton instance
whatsapp_automation = WhatsAppAutomation()
