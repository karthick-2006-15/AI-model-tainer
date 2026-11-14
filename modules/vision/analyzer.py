"""
Multimodal Vision Intelligence & Screen Reasoning Engine
Explains technical errors, diagrams, software UI dialogs, and terminal outputs.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from modules.vision.capture import screen_capture_manager
from modules.vision.ocr import screen_ocr
from core.providers.router import model_router

logger = logging.getLogger("jarvis.vision.analyzer")


class VisionIntelligenceEngine:
    """Provides visual understanding, screenshot explanation, and troubleshooting guidance."""

    VISION_ANALYSIS_PROMPT = """You are JARVIS Vision Intelligence.
Analyze the following desktop screen capture or technical diagram.

Focus Area: "{focus_area}"
Detected OCR/Error Signatures:
{error_context}

### Required Output Structure:
1. **Screen Context & Active Window:** What application, terminal, or document is open?
2. **Identified Issue / Technical Error:** What error message, exception, or failure is displayed?
3. **Probable Root Cause:** Why did this error occur?
4. **Actionable Step-by-Step Fix:** Exact terminal commands, code corrections, or system configurations to resolve it.
"""

    async def explain_screen(
        self,
        focus_area: str = "",
        prompt_override: str = ""
    ) -> Dict[str, Any]:
        """
        Captures current desktop screen, scans for errors, and synthesizes an explanation with step-by-step resolution.
        """
        logger.info(f"Initiating screen capture and vision analysis (focus: '{focus_area}')")

        # 1. Capture Desktop Screen
        capture_res = screen_capture_manager.capture_screen()
        if not capture_res["success"]:
            return {
                "success": False,
                "error": f"Screen capture failed: {capture_res.get('error')}"
            }

        screenshot_path = capture_res["file_path"]

        # 2. Extract OCR text and error signatures
        extracted_text = screen_ocr.extract_text_from_image(screenshot_path)
        detected_errors = screen_ocr.detect_error_signatures(extracted_text)

        error_context = "\n".join(f"- {e}" for e in detected_errors) if detected_errors else "No explicit text errors detected via OCR."

        # 3. Multimodal / LLM Synthesis
        provider = model_router.get_provider()
        prompt = prompt_override or self.VISION_ANALYSIS_PROMPT.format(
            focus_area=focus_area or "Full Desktop Screen",
            error_context=error_context
        )

        try:
            llm_response = await provider.generate([
                {"role": "system", "content": "You are JARVIS Vision Intelligence. You analyze screenshots and explain errors concisely."},
                {"role": "user", "content": prompt}
            ])
            explanation = llm_response.content
        except Exception as e:
            logger.warning(f"Vision LLM generation failed: {e}. Formulating structured local diagnosis.")
            explanation = self._formulate_heuristic_explanation(detected_errors, focus_area)

        return {
            "success": True,
            "screenshot_path": screenshot_path,
            "width": capture_res["width"],
            "height": capture_res["height"],
            "detected_errors": detected_errors,
            "ocr_text": extracted_text[:500] if extracted_text else "",
            "explanation": explanation
        }

    async def analyze_image_file(
        self,
        image_path: str,
        query: str = "Explain this image and its technical components."
    ) -> Dict[str, Any]:
        """
        Analyzes a specific image file (diagram, screenshot, photo) from disk.
        """
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image file '{image_path}' not found."
            }

        extracted_text = screen_ocr.extract_text_from_image(image_path)
        detected_errors = screen_ocr.detect_error_signatures(extracted_text)

        prompt = f"Analyze the image located at '{image_path}'.\nUser Query: {query}\nDetected Text:\n{extracted_text[:1000]}"

        provider = model_router.get_provider()
        try:
            llm_response = await provider.generate([
                {"role": "system", "content": "You are JARVIS, analyzing a visual technical document."},
                {"role": "user", "content": prompt}
            ])
            analysis_text = llm_response.content
        except Exception as e:
            analysis_text = f"Analysis of {os.path.basename(image_path)}: Image inspected successfully. Found {len(detected_errors)} potential error signatures."

        return {
            "success": True,
            "image_path": os.path.abspath(image_path),
            "detected_errors": detected_errors,
            "analysis": analysis_text
        }

    def _formulate_heuristic_explanation(self, detected_errors: List[str], focus_area: str) -> str:
        """Fallback diagnostic reasoning when offline or without external cloud vision API."""
        if not detected_errors:
            return (
                "### Screen Analysis\n"
                f"- **Context:** Screen inspected at primary desktop.\n"
                "- **Status:** No severe runtime exceptions or stack traces detected in active windows.\n"
                "- **Recommendation:** If an issue is occurring, please open the relevant error dialog or console window."
            )

        err_list = "\n".join(f"- `{err}`" for err in detected_errors)
        return (
            "### Screen Diagnostic Report\n"
            f"**Detected Errors:**\n{err_list}\n\n"
            "**Probable Cause:** Runtime or compiler exception triggered during process execution.\n\n"
            "**Actionable Steps:**\n"
            "1. Review the stack trace above for the exact line number.\n"
            "2. Ensure all required dependencies and environment variables are active.\n"
            "3. Ask JARVIS to inspect the source file directly for automated repair."
        )


# Global vision singleton
vision_engine = VisionIntelligenceEngine()
