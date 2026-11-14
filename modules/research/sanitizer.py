"""
Anti-Prompt-Injection Sanitizer & Untrusted Content Quarantine
Ensures external web pages and documents cannot hijack JARVIS execution instructions.
"""

import re
import html
from typing import Dict, Any


class ContentSanitizer:
    INJECTION_PATTERNS = [
        r"(?i)\bignore\s+(?:all\s+)?previous\s+instructions\b",
        r"(?i)\byou\s+are\s+now\s+(?:DAN|developer\s+mode|unrestricted)\b",
        r"(?i)\bsystem\s+prompt\s*:\b",
        r"(?i)\boverride\s+(?:all\s+)?safety\s+rules\b",
        r"(?i)\bexecute\s+command\s*:\s*powershell\b",
        r"(?i)\bdelete\s+file\b"
    ]

    def __init__(self):
        self._compiled_injections = [re.compile(p) for p in self.INJECTION_PATTERNS]

    def sanitize_untrusted_text(self, raw_text: str, source: str = "web_search", max_chars: int = 15000) -> str:
        """
        Neutralizes known prompt-injection triggers and encapsulates text in XML boundary tags.
        """
        if not raw_text:
            return ""

        # 1. Clean HTML entities and zero-width spaces
        cleaned = html.unescape(raw_text)
        cleaned = re.sub(r"[\u200B-\u200D\uFEFF]", "", cleaned)

        # 2. Defang adversarial prompt injection triggers
        for pattern in self._compiled_injections:
            cleaned = pattern.sub("[POTENTIAL_INJECTION_DEFANGED]", cleaned)

        # 3. Truncate to maximum character limit
        is_truncated = len(cleaned) > max_chars
        truncated = cleaned[:max_chars].strip()
        if is_truncated:
            truncated += "\n[Truncated by JARVIS]"

        # 4. Wrap inside rigid XML untrusted content container
        return f'<untrusted_content source="{source}" safe_mode="true">\n{truncated}\n</untrusted_content>'


# Global singleton instance
content_sanitizer = ContentSanitizer()
