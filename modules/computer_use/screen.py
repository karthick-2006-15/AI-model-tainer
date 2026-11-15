"""
Screen Intelligence & Desktop Visual State Engine
Provides active window tracking, screen capture, visual state diffing, and OCR extraction.
"""

import os
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple
import psutil
from PIL import Image, ImageGrab
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import win32gui
    import win32process
    import win32con
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

logger = logging.getLogger("jarvis.computer_use.screen")


class ScreenIntelligence:
    def __init__(self, storage_dir: str = "storage/media/screenshots"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def capture_screen(
        self,
        bounding_box: Optional[Tuple[int, int, int, int]] = None,
        max_dimension: int = 1920
    ) -> Dict[str, Any]:
        """
        Captures the primary desktop monitor or specific region.
        Returns file path, dimensions, and active timestamp.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_path = os.path.join(self.storage_dir, f"capture_{timestamp}.png")

        try:
            if bounding_box:
                img = ImageGrab.grab(bbox=bounding_box)
            else:
                img = ImageGrab.grab()
        except Exception as e:
            logger.warning(f"Interactive screen grab fallback: {e}")
            img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))

        w, h = img.size
        if max(w, h) > max_dimension:
            scale = max_dimension / float(max(w, h))
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            w, h = img.size

        img.save(file_path, format="PNG")
        return {
            "success": True,
            "file_path": file_path,
            "width": w,
            "height": h,
            "timestamp": timestamp
        }

    def get_active_window(self) -> Dict[str, Any]:
        """Detects the current foreground window, title, process name, and bounds."""
        if not PYWIN32_AVAILABLE:
            return {
                "success": False,
                "error": "pywin32 is not installed or available."
            }

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or hwnd == 0:
                hwnd = win32gui.GetDesktopWindow()

            if not hwnd:
                return {"success": False, "error": "No window detected."}

            title = win32gui.GetWindowText(hwnd).strip() or "Windows Desktop"
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            rect = win32gui.GetWindowRect(hwnd)  # (left, top, right, bottom)

            try:
                pname = psutil.Process(pid).name()
            except Exception:
                pname = "unknown"

            # Determine application category
            p_lower = pname.lower()
            t_lower = title.lower()

            app_type = "system"
            if "code" in p_lower or "visual studio" in t_lower:
                app_type = "ide"
            elif any(b in p_lower for b in ["chrome", "edge", "firefox", "brave"]):
                app_type = "browser"
            elif "whatsapp" in p_lower or "whatsapp" in t_lower:
                app_type = "messaging"
            elif any(t in p_lower for t in ["wt", "powershell", "cmd"]):
                app_type = "terminal"
            elif "explorer" in p_lower:
                app_type = "file_manager"

            return {
                "success": True,
                "hwnd": hwnd,
                "title": title,
                "pid": pid,
                "process_name": pname,
                "app_type": app_type,
                "bounds": {
                    "left": rect[0],
                    "top": rect[1],
                    "right": rect[2],
                    "bottom": rect[3],
                    "width": rect[2] - rect[0],
                    "height": rect[3] - rect[1]
                }
            }
        except Exception as e:
            logger.error(f"Failed to inspect active window: {e}")
            return {"success": False, "error": str(e)}

    def extract_screen_text(self, image_path: Optional[str] = None) -> Dict[str, Any]:
        """Extracts visible on-screen text using OCR."""
        target_path = image_path
        if not target_path:
            cap = self.capture_screen()
            target_path = cap.get("file_path")

        if not target_path or not os.path.exists(target_path):
            return {"success": False, "error": "Invalid screenshot path."}

        text = ""
        if PYTESSERACT_AVAILABLE:
            try:
                img = Image.open(target_path)
                text = pytesseract.image_to_string(img)
            except Exception as e:
                logger.warning(f"pytesseract extraction error: {e}")

        # Fallback to visual parsing module if available
        if not text:
            try:
                from modules.vision.ocr import screen_ocr
                text = screen_ocr.extract_text_from_image(target_path)
            except Exception:
                pass

        return {
            "success": True,
            "text": text.strip(),
            "lines": [line.strip() for line in text.splitlines() if line.strip()],
            "image_path": target_path
        }

    def compare_visual_states(self, before_path: str, after_path: str, threshold: float = 0.01) -> Dict[str, Any]:
        """
        Compares two screenshots to verify if an action caused a visible UI state change.
        threshold: minimum percentage of changed pixels to constitute a state transition.
        """
        if not os.path.exists(before_path) or not os.path.exists(after_path):
            return {"success": False, "changed": False, "error": "Image file not found."}

        try:
            img1 = Image.open(before_path).convert("RGB")
            img2 = Image.open(after_path).convert("RGB")

            # Ensure matching sizes
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)

            arr1 = np.array(img1, dtype=np.int16)
            arr2 = np.array(img2, dtype=np.int16)

            diff = np.abs(arr1 - arr2)
            # Count pixels where change in any channel exceeds noise threshold (15/255)
            changed_pixels = np.sum(np.any(diff > 15, axis=2))
            total_pixels = img1.size[0] * img1.size[1]
            change_ratio = float(changed_pixels) / float(total_pixels)

            has_changed = change_ratio >= threshold
            return {
                "success": True,
                "changed": has_changed,
                "change_ratio": round(change_ratio, 4),
                "changed_pixels": int(changed_pixels),
                "total_pixels": total_pixels
            }
        except Exception as e:
            logger.error(f"Visual state comparison failed: {e}")
            return {"success": False, "changed": False, "error": str(e)}


# Global singleton instance
screen_intelligence = ScreenIntelligence()
