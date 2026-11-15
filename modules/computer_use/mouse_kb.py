"""
Human-Like Mouse & Keyboard Automation Controller
Safe coordinate-based fallback execution with bounds checking and emergency stop integration.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import pyautogui
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.computer_use.mouse_kb")

# Safety parameters
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True


class MouseKeyboardController:
    """Controls mouse and keyboard inputs with safety guardrails and humanized movements."""

    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()

    def _check_safety(self) -> Tuple[bool, Optional[str]]:
        """Ensures emergency stop is not engaged before taking physical computer action."""
        if permission_engine.is_emergency_stopped():
            return False, "Action blocked: Global Emergency Stop is ACTIVE."
        return True, None

    def _validate_coords(self, x: int, y: int) -> Tuple[int, int]:
        """Clamps coordinates safely within physical monitor bounds."""
        safe_x = max(0, min(x, self.screen_width - 1))
        safe_y = max(0, min(y, self.screen_height - 1))
        return safe_x, safe_y

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        human_move: bool = True
    ) -> Dict[str, Any]:
        """Moves cursor smoothly and clicks at coordinates."""
        safe, err = self._check_safety()
        if not safe:
            return {"success": False, "error": err}

        safe_x, safe_y = self._validate_coords(x, y)
        try:
            if human_move:
                pyautogui.moveTo(safe_x, safe_y, duration=0.25, tween=pyautogui.easeOutQuad)
            else:
                pyautogui.moveTo(safe_x, safe_y)

            pyautogui.click(x=safe_x, y=safe_y, clicks=clicks, button=button)
            logger.info(f"Mouse click ({button}, clicks={clicks}) at ({safe_x}, {safe_y})")
            return {
                "success": True,
                "x": safe_x,
                "y": safe_y,
                "button": button,
                "clicks": clicks
            }
        except Exception as e:
            logger.error(f"Click failed at ({x}, {y}): {e}")
            return {"success": False, "error": str(e)}

    def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        """Simulates human typing with configurable character interval."""
        safe, err = self._check_safety()
        if not safe:
            return {"success": False, "error": err}

        try:
            pyautogui.write(text, interval=interval)
            logger.info(f"Typed {len(text)} characters safely.")
            return {"success": True, "char_count": len(text)}
        except Exception as e:
            logger.error(f"Type text error: {e}")
            return {"success": False, "error": str(e)}

    def press_key(self, key_name: str) -> Dict[str, Any]:
        """Presses an individual keyboard key (e.g. 'enter', 'tab', 'esc', 'backspace')."""
        safe, err = self._check_safety()
        if not safe:
            return {"success": False, "error": err}

        try:
            pyautogui.press(key_name.lower())
            logger.info(f"Pressed key: {key_name}")
            return {"success": True, "key": key_name}
        except Exception as e:
            logger.error(f"Press key error ({key_name}): {e}")
            return {"success": False, "error": str(e)}

    def press_hotkey(self, keys: List[str]) -> Dict[str, Any]:
        """Presses a hotkey combination (e.g. ['ctrl', 'c'], ['alt', 'tab'], ['ctrl', 'a'])."""
        safe, err = self._check_safety()
        if not safe:
            return {"success": False, "error": err}

        try:
            pyautogui.hotkey(*[k.lower() for k in keys])
            logger.info(f"Executed hotkey: {'+'.join(keys)}")
            return {"success": True, "keys": keys}
        except Exception as e:
            logger.error(f"Hotkey execution error ({keys}): {e}")
            return {"success": False, "error": str(e)}

    def scroll(self, clicks: int, direction: str = "down") -> Dict[str, Any]:
        """Scrolls vertically (direction='up' or 'down')."""
        safe, err = self._check_safety()
        if not safe:
            return {"success": False, "error": err}

        try:
            amount = -abs(clicks) if direction.lower() == "down" else abs(clicks)
            pyautogui.scroll(amount)
            logger.info(f"Scrolled {direction} by {clicks} steps.")
            return {"success": True, "direction": direction, "steps": clicks}
        except Exception as e:
            logger.error(f"Scroll error: {e}")
            return {"success": False, "error": str(e)}


# Global singleton instance
mouse_kb = MouseKeyboardController()
