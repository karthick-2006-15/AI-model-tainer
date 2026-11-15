"""
Multilingual Communication & Code-Switching Engine
Detects English, Tamil, Tanglish, Hindi, and Hinglish.
Normalizes colloquial mixed-language instructions and generates culturally natural voice responses.
"""

import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("jarvis.voice.multilingual")


class MultilingualEngine:
    """Understands and speaks English, Tamil, Tanglish, Hindi, and Hinglish."""

    TANGLISH_MARKERS = [
        r"\b(?:pannu|pannunga|kudu|kudunga|sollu|sollunga|kelu|kelunga)\b",
        r"\b(?:indha|andha|enna|edhu|eppadi|engae|en|unnoda)\b",
        r"\b(?:ku|la|oda|kitta)\b",
        r"\b(?:irukku|illa|illai|aama|aamam|sari|podu|anuppu|anupu)\b",
        r"\b(?:paaru|paarunga|seiyyi|seiyunga|vendaam)\b"
    ]

    HINGLISH_MARKERS = [
        r"\b(?:kholo|khol|bhejo|bhej|batao|bataiye|suno|karo|kijiye)\b",
        r"\b(?:yeh|woh|kya|kaise|kahan|mera|mere|meri|tumhara|aapka)\b",
        r"\b(?:ko|se|mein|par|ke\s+liye)\b",
        r"\b(?:hai|hain|nahi|nahin|haan|theek|chalao|dikhao|band)\b"
    ]

    def detect_language(self, text: str) -> str:
        """
        Detects language of spoken text:
        'ta' (Tamil script), 'tanglish' (Tamil in Roman script),
        'hi' (Hindi script), 'hinglish' (Hindi in Roman script),
        or 'en' (English).
        """
        if not text:
            return "en"

        # 1. Unicode checks
        if any("\u0B80" <= ch <= "\u0BFF" for ch in text):
            return "ta"
        if any("\u0900" <= ch <= "\u097F" for ch in text):
            return "hi"

        cleaned = text.lower()

        # 2. Tanglish check
        tanglish_hits = sum(1 for p in self.TANGLISH_MARKERS if re.search(p, cleaned))
        if tanglish_hits >= 1:
            return "tanglish"

        # 3. Hinglish check
        hinglish_hits = sum(1 for p in self.HINGLISH_MARKERS if re.search(p, cleaned))
        if hinglish_hits >= 1:
            return "hinglish"

        return "en"

    def normalize_code_switching(self, text: str) -> Tuple[str, str]:
        """
        Converts Tanglish/Hinglish speech into canonical command instructions while preserving target entities.
        Returns:
            (canonical_english_instruction: str, detected_language: str)
        Examples:
            "WhatsApp open pannu" -> ("open WhatsApp", "tanglish")
            "en father ku Hi message send pannu" -> ("send Hi to father", "tanglish")
            "Chrome kholo" -> ("open Chrome", "hinglish")
            "indha question ku answer find pannu" -> ("find answer for this question", "tanglish")
        """
        lang = self.detect_language(text)
        cleaned = text.strip()
        c_lower = cleaned.lower()

        if lang == "en":
            return cleaned, "en"

        # 1. Tanglish Normalizations
        if lang in ("tanglish", "ta"):
            # Close app: "X ah close pannu" / "X close pannunga" -> "close X"
            m_close = re.search(r"([a-zA-Z0-9_\-\s]+?)(?:\s+ah|\s+a)?\s+(?:close\s+pannu|close\s+seiyyi|close\s+pannunga|moodu)", c_lower)
            if m_close:
                return f"close {m_close.group(1).strip()}", lang

            # Switch app: "X ku switch pannu" / "X ku mathu" -> "switch to X"
            m_switch = re.search(r"([a-zA-Z0-9_\-\s]+?)\s+ku\s+(?:switch\s+pannu|switch\s+pannunga|mathu|focus\s+pannu)", c_lower)
            if m_switch:
                return f"switch to {m_switch.group(1).strip()}", lang

            # Open folder / app: "X open pannu" / "X open seiyyi" -> "open X"
            m_open = re.search(r"([a-zA-Z0-9_\-\s]+?)\s+(?:open\s+pannu|open\s+seiyyi|open\s+pannunga|khol)", c_lower)
            if m_open:
                return f"open {m_open.group(1).strip()}", lang

            # Send message: "en father ku Hi message send pannu" -> "send Hi to father"
            m_msg = re.search(r"(?:en\s+)?([a-zA-Z0-9_\-]+)\s+ku\s+(.+?)\s+(?:message\s+)?(?:send\s+pannu|anuppu|anupu)", c_lower)
            if m_msg:
                recipient = m_msg.group(1).strip()
                msg = m_msg.group(2).strip()
                # Clean word 'message' if attached
                msg = re.sub(r"\bmessage\b", "", msg).strip()
                return f"send {msg} to {recipient}", lang

            # Screen query: "screen la enna irukku" / "screen read pannu" -> "read what's on my screen"
            if "screen" in c_lower and any(w in c_lower for w in ["enna", "read", "paaru", "irukku"]):
                return "read what is on my screen", lang

            # Answer finding: "indha question ku answer find pannu" -> "find answer for this question"
            if "question" in c_lower and any(w in c_lower for w in ["answer", "find", "kandu"]):
                return "find the answers for this worksheet", lang

        # 2. Hinglish Normalizations
        if lang in ("hinglish", "hi"):
            # Close app: "X band karo" / "X close karo" -> "close X"
            m_close_hi = re.search(r"([a-zA-Z0-9_\-\s]+?)\s+(?:band\s+karo|band\s+kar\s+do|close\s+karo)", c_lower)
            if m_close_hi:
                return f"close {m_close_hi.group(1).strip()}", lang

            # Switch app: "X par switch karo" / "X dikhao" -> "switch to X"
            m_switch_hi = re.search(r"([a-zA-Z0-9_\-\s]+?)\s+(?:par\s+switch\s+karo|par\s+jaao|mein\s+jaao)", c_lower)
            if m_switch_hi:
                return f"switch to {m_switch_hi.group(1).strip()}", lang

            # Open app: "Chrome kholo" / "WhatsApp chalao" -> "open Chrome"
            m_open_hi = re.search(r"([a-zA-Z0-9_\-\s]+?)\s+(?:kholo|chalao|khol\s+do)", c_lower)
            if m_open_hi:
                return f"open {m_open_hi.group(1).strip()}", lang

            # Send message: "mere father ko Hi message bhejo" -> "send Hi to father"
            m_msg_hi = re.search(r"(?:mere\s+)?([a-zA-Z0-9_\-]+)\s+ko\s+(.+?)\s+(?:message\s+)?(?:bhejo|bhej\s+do)", c_lower)
            if m_msg_hi:
                recipient = m_msg_hi.group(1).strip()
                msg = m_msg_hi.group(2).strip()
                msg = re.sub(r"\bmessage\b", "", msg).strip()
                return f"send {msg} to {recipient}", lang

            # Screen query: "screen par kya hai" / "screen padho" -> "read what's on my screen"
            if "screen" in c_lower and any(w in c_lower for w in ["kya", "padho", "dekho", "hai"]):
                return "read what is on my screen", lang

        return cleaned, lang

    def localize_response(self, english_response: str, target_lang: str) -> str:
        """Translates concise functional status responses into the speaker's language."""
        if target_lang == "en":
            return english_response

        # Quick dictionary for concise conversational responses
        T_MAP = {
            "tanglish": {
                "Yes, I'm listening.": "Sollunga, naan kettuட்டு irukken.",
                "Standing by.": "Standing by, sollunga.",
                "Standing by, sir.": "Standing by, sollunga sir.",
                "WhatsApp is open. What would you like me to do?": "WhatsApp open aaiduchu. Next enna pannanum?",
                "Message sent successfully.": "Message successfully anupiyaachu.",
                "Chrome is open.": "Chrome open aaiduchu.",
                "VS Code is open.": "VS Code open aaiduchu.",
                "I'm searching the web.": "Naan web la search panren.",
                "The report is ready.": "Report ready aaiduchu.",
                "Action cancelled.": "Action cancel panniyachu."
            },
            "hinglish": {
                "Yes, I'm listening.": "Haan, main sun raha hoon.",
                "Standing by.": "Main taiyaar hoon, boliye.",
                "Standing by, sir.": "Taiyaar hoon sir, boliye.",
                "WhatsApp is open. What would you like me to do?": "WhatsApp khul gaya hai. Kya karna hai?",
                "Message sent successfully.": "Message safaltaapoorvak bhej diya gaya hai.",
                "Chrome is open.": "Chrome khul gaya hai.",
                "VS Code is open.": "VS Code khul gaya hai.",
                "I'm searching the web.": "Main web par search kar raha hoon.",
                "The report is ready.": "Report taiyaar hai.",
                "Action cancelled.": "Action cancel kar diya gaya hai."
            }
        }

        lang_dict = T_MAP.get(target_lang, {})
        for eng, localized in lang_dict.items():
            if eng.lower() in english_response.lower() or english_response.lower() in eng.lower():
                return localized

        # Dynamic template replacement
        if target_lang == "tanglish":
            m = re.match(r"Application '([^']+)' (?:launched|focused)", english_response)
            if m:
                return f"{m.group(1)} open aaiduchu."
            if "sent" in english_response.lower() and "successfully" in english_response.lower():
                return "Message anupiyaachu."

        elif target_lang == "hinglish":
            m = re.match(r"Application '([^']+)' (?:launched|focused)", english_response)
            if m:
                return f"{m.group(1)} khul gaya hai."
            if "sent" in english_response.lower() and "successfully" in english_response.lower():
                return "Message bhej diya gaya hai."

        return english_response


# Global singleton instance
multilingual_engine = MultilingualEngine()
