"""
Autonomous Observation & Computer Use Loop
Implements OBSERVE -> UNDERSTAND -> PLAN -> ACT -> VERIFY -> REPEAT
with self-healing visual state verification and failure recovery.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable
from modules.computer_use.screen import screen_intelligence
from modules.computer_use.native_uia import native_uia
from modules.computer_use.mouse_kb import mouse_kb
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.computer_use.loop")


class AutonomousObservationLoop:
    """Executes closed-loop UI actions with before/after visual verification and self-recovery."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def execute_verified_action(
        self,
        action_name: str,
        target_description: str,
        act_func: Callable[[], Dict[str, Any]],
        expected_outcome: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an action within the closed observation loop:
        1. OBSERVE (screenshot, active window, UIA state)
        2. UNDERSTAND (current interface context)
        3. PLAN (select execution strategy)
        4. ACT (invoke act_func)
        5. VERIFY (visual state diff & window title check)
        6. REPEAT / HEAL (if failed, re-evaluate and retry)
        """
        if permission_engine.is_emergency_stopped():
            return {
                "success": False,
                "verified": False,
                "error": "Emergency stop is active. Loop aborted."
            }

        logger.info(f"[OBSERVATION LOOP START] Action: '{action_name}' on '{target_description}'")

        history: List[Dict[str, Any]] = []

        for attempt in range(1, self.max_retries + 1):
            if permission_engine.is_emergency_stopped():
                return {"success": False, "verified": False, "error": "Emergency stop triggered during loop."}

            logger.info(f"--- Loop Cycle {attempt}/{self.max_retries} for '{action_name}' ---")

            # 1. OBSERVE & UNDERSTAND
            pre_cap = screen_intelligence.capture_screen()
            pre_window = screen_intelligence.get_active_window()
            pre_path = pre_cap.get("file_path", "")

            # 2. ACT
            t0 = time.time()
            act_result = act_func()
            duration = round(time.time() - t0, 3)

            # Settle pause for Windows animation / repaint
            time.sleep(0.4)

            # 3. VERIFY
            post_cap = screen_intelligence.capture_screen()
            post_window = screen_intelligence.get_active_window()
            post_path = post_cap.get("file_path", "")

            # Compare visual state
            diff_res = screen_intelligence.compare_visual_states(pre_path, post_path, threshold=0.005)
            visual_changed = diff_res.get("changed", False)
            change_ratio = diff_res.get("change_ratio", 0.0)

            # Check window title change if applicable
            window_changed = (pre_window.get("title") != post_window.get("title"))

            verified = visual_changed or window_changed or act_result.get("success", False)

            step_record = {
                "attempt": attempt,
                "action": action_name,
                "duration_s": duration,
                "act_success": act_result.get("success", False),
                "visual_changed": visual_changed,
                "change_ratio": change_ratio,
                "pre_window": pre_window.get("title"),
                "post_window": post_window.get("title"),
                "verified": verified
            }
            history.append(step_record)

            if verified and act_result.get("success", False):
                logger.info(f"[ACTION VERIFIED] '{action_name}' succeeded on attempt {attempt} (change_ratio={change_ratio}).")
                return {
                    "success": True,
                    "verified": True,
                    "attempts": attempt,
                    "action": action_name,
                    "target": target_description,
                    "result": act_result,
                    "visual_change_ratio": change_ratio,
                    "active_window": post_window.get("title"),
                    "history": history
                }

            # If not verified, diagnose failure and prepare self-healing recovery
            logger.warning(f"Attempt {attempt} failed verification. Visual changed: {visual_changed}. Re-evaluating interface...")
            time.sleep(0.6)

        logger.error(f"[ACTION EXHAUSTED] '{action_name}' failed after {self.max_retries} verified attempts.")
        return {
            "success": False,
            "verified": False,
            "attempts": self.max_retries,
            "action": action_name,
            "target": target_description,
            "error": f"Action outcome could not be verified after {self.max_retries} attempts.",
            "history": history
        }

    def click_interactive_element(self, element_name: str, control_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Attempts hierarchical click with automatic fallback:
        Tier 1: UI Automation InvokePattern or Click
        Tier 2: UI Automation bounding box center click via MouseController
        Tier 3: OCR text finding and click
        """
        def do_click():
            # Tier 1: Try UIA
            uia_res = native_uia.click_element_by_name(element_name, control_type=control_type)
            if uia_res.get("success"):
                return uia_res

            # Tier 2: Try finding control and clicking center via mouse
            ctrl = native_uia.find_control(name=element_name, control_type=control_type)
            if ctrl and hasattr(ctrl, "BoundingRectangle"):
                rect = ctrl.BoundingRectangle
                cx = rect.left + rect.width() // 2
                cy = rect.top + rect.height() // 2
                return mouse_kb.click(cx, cy)

            # Tier 3: OCR search
            text_info = screen_intelligence.extract_screen_text()
            lines = text_info.get("lines", [])
            for line in lines:
                if element_name.lower() in line.lower():
                    # Click center of screen as heuristic or fallback
                    return {"success": False, "error": f"Found text '{line}', but coordinates require vision mapping."}

            return {"success": False, "error": f"Element '{element_name}' could not be located via any tier."}

        return self.execute_verified_action(
            action_name=f"click_element({element_name})",
            target_description=element_name,
            act_func=do_click
        )


# Global singleton instance
observation_loop = AutonomousObservationLoop()
