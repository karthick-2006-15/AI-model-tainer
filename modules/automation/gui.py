"""
GUI, Keyboard & Mouse Automation Interface
Provides hotkeys, typing, and desktop screenshot capabilities via pyautogui and Win32.
"""

import os
import logging
from typing import Dict, Any, List, Optional
import pyautogui

# Reduce PyAutoGUI default pause for responsive interaction
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True

logger = logging.getLogger("jarvis.automation.gui")


class GUIController:
    @staticmethod
    def take_screenshot(output_path: str) -> Dict[str, Any]:
        """Captures a screenshot of the primary monitor and saves to disk."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            screenshot = pyautogui.screenshot()
            screenshot.save(output_path)
            logger.info(f"Captured screenshot to: {output_path}")
            return {
                "success": True,
                "path": output_path,
                "width": screenshot.width,
                "height": screenshot.height
            }
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def press_hotkey(keys: List[str]) -> Dict[str, Any]:
        """Presses a hotkey combination (e.g. ['ctrl', 'c'] or ['alt', 'tab'])."""
        try:
            pyautogui.hotkey(*keys)
            return {"success": True, "hotkey": "+".join(keys)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def type_text(text: str) -> Dict[str, Any]:
        """Types a string of text at the current cursor focus."""
        try:
            pyautogui.write(text, interval=0.01)
            return {"success": True, "typed_length": len(text)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global singleton instance
gui_controller = GUIController()
