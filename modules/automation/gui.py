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
    def take_screenshot(output_path: str = "storage/media/screenshots/screenshot.png") -> Dict[str, Any]:
        """Captures a screenshot of the primary monitor and saves to disk."""
        try:
            from modules.vision.capture import screen_capture_manager
            res = screen_capture_manager.capture_screen()
            if res.get("success"):
                import shutil
                if output_path and output_path != res.get("file_path"):
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    shutil.copyfile(res["file_path"], output_path)
                return {
                    "success": True,
                    "path": output_path or res.get("file_path"),
                    "width": res.get("width", 1920),
                    "height": res.get("height", 1080),
                    "message": "Desktop screenshot captured successfully."
                }
            return res
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
