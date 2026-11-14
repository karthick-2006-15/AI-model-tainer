"""
Optical Character Recognition & Visual Error Signature Detector
Extracts text from screenshots and identifies stack traces, compiler errors, and dialog text.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from PIL import Image

logger = logging.getLogger("jarvis.vision.ocr")


class ScreenOCR:
    """Extracts text and error signatures from desktop screen captures."""

    ERROR_PATTERNS = [
        r"(?i)\b(?:error|fatal|exception|traceback|syntaxerror|typeerror|valueerror|importerror|filenotfounderror)\b[^\n]*",
        r"(?i)\b(?:failed to (?:load|connect|bind|launch|execute)|connection refused|access denied)\b[^\n]*",
        r"(?i)\b(?:winerror\s+\d+|status code\s+[45]\d{2}|exit code\s+[1-9]\d*)\b[^\n]*",
        r"(?i)\b(?:nullpointerexception|segmentation fault|stack overflow|out of memory)\b[^\n]*"
    ]

    def __init__(self):
        self._has_tesseract = False
        try:
            import pytesseract
            self._pytesseract = pytesseract
            self._has_tesseract = True
            logger.info("pytesseract engine available for optical character recognition.")
        except ImportError:
            self._pytesseract = None
            logger.info("pytesseract not installed. Using structural error parsing mode.")

    def extract_text_from_image(self, image_input: Any) -> str:
        """
        Extracts raw textual strings from a PIL Image or file path.
        """
        try:
            if isinstance(image_input, str):
                img = Image.open(image_input)
            else:
                img = image_input

            if self._has_tesseract and self._pytesseract:
                return self._pytesseract.image_to_string(img).strip()
            
            return ""
        except Exception as e:
            logger.warning(f"OCR text extraction encountered exception: {e}")
            return ""

    def detect_error_signatures(self, text: str) -> List[str]:
        """
        Scans extracted text or terminal dumps for programming errors and failure messages.
        """
        if not text:
            return []

        detected = []
        for pattern in self.ERROR_PATTERNS:
            matches = re.findall(pattern, text)
            for m in matches:
                clean_match = m.strip()
                if clean_match and clean_match not in detected:
                    detected.append(clean_match)

        return detected


# Global OCR singleton
screen_ocr = ScreenOCR()
