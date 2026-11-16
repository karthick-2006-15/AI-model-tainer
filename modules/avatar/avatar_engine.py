"""
JARVIS Avatar Engine
Coordinates avatar animation states, facial expressions, eye posture, lip-sync visemes, and holographic themes.
"""

import time
import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger("jarvis.avatar")


class AvatarEngine:
    VALID_STATES = {
        "idle",
        "listening",
        "thinking",
        "speaking",
        "happy",
        "confused",
        "error",
        "warning",
        "sleeping",
        "success"
    }

    VALID_THEMES = {
        "classic_cyan",
        "arc_gold",
        "quantum_violet",
        "matrix_emerald"
    }

    VALID_SIZES = {"small", "medium", "large"}

    def __init__(self):
        self._lock = threading.Lock()
        self._current_state = "idle"
        self._current_expression = "neutral"
        self._expression_expiry = 0.0
        self._status_message = "JARVIS Virtual Face Initialized."
        self._lip_sync = {
            "amplitude": 0.0,
            "mouth_open": 0.0,
            "phoneme": "",
            "last_updated": time.time()
        }
        self._settings = {
            "theme": "classic_cyan",
            "size": "medium",
            "glow_intensity": 0.85,
            "scanlines_enabled": True,
            "click_through": False,
            "always_on_top": True,
            "speech_sync_enabled": True,
            "gaze_tracking_enabled": True
        }
        self._eye_metrics = {
            "left_pupil": {"x": 0.0, "y": 0.0, "dilation": 1.0},
            "right_pupil": {"x": 0.0, "y": 0.0, "dilation": 1.0},
            "eyelid_open": 1.0,
            "eyebrow_tilt": 0.0
        }

    def set_state(self, state: str, message: Optional[str] = None) -> bool:
        """Sets the primary animation state of the avatar."""
        s = state.lower().strip()
        if s not in self.VALID_STATES:
            logger.warning(f"Invalid avatar state requested: {state}. Defaulting to 'idle'.")
            s = "idle"

        with self._lock:
            self._current_state = s
            if message:
                self._status_message = message
            
            # Adjust eye metrics based on state
            if s == "idle":
                self._eye_metrics["eyelid_open"] = 1.0
                self._eye_metrics["eyebrow_tilt"] = 0.0
                self._lip_sync["mouth_open"] = 0.0
            elif s == "listening":
                self._eye_metrics["eyelid_open"] = 1.05
                self._eye_metrics["eyebrow_tilt"] = 0.1
                self._eye_metrics["left_pupil"]["dilation"] = 1.15
                self._eye_metrics["right_pupil"]["dilation"] = 1.15
            elif s == "thinking":
                self._eye_metrics["eyelid_open"] = 0.95
                self._eye_metrics["eyebrow_tilt"] = -0.15
                self._eye_metrics["left_pupil"]["x"] = 0.25
                self._eye_metrics["right_pupil"]["x"] = 0.25
            elif s == "speaking":
                self._eye_metrics["eyelid_open"] = 1.0
                self._eye_metrics["eyebrow_tilt"] = 0.05
            elif s == "happy" or s == "success":
                self._eye_metrics["eyelid_open"] = 0.85
                self._eye_metrics["eyebrow_tilt"] = 0.25
            elif s == "confused":
                self._eye_metrics["eyelid_open"] = 1.0
                self._eye_metrics["eyebrow_tilt"] = -0.3
            elif s == "error":
                self._eye_metrics["eyelid_open"] = 0.9
                self._eye_metrics["eyebrow_tilt"] = -0.4
            elif s == "warning":
                self._eye_metrics["eyelid_open"] = 1.05
                self._eye_metrics["eyebrow_tilt"] = -0.2
            elif s == "sleeping":
                self._eye_metrics["eyelid_open"] = 0.1
                self._eye_metrics["eyebrow_tilt"] = 0.0
                self._lip_sync["mouth_open"] = 0.0

        logger.info(f"Avatar state shifted to '{s}': {self._status_message}")
        return True

    def get_state(self) -> Dict[str, Any]:
        """Returns the current avatar visual and animation state."""
        now = time.time()
        with self._lock:
            # Check if temporary emotional expression expired
            active_expression = self._current_expression
            if self._expression_expiry > 0 and now > self._expression_expiry:
                self._current_expression = "neutral"
                active_expression = "neutral"
                self._expression_expiry = 0.0

            return {
                "state": self._current_state,
                "expression": active_expression,
                "status_message": self._status_message,
                "eye_metrics": dict(self._eye_metrics),
                "lip_sync": dict(self._lip_sync),
                "theme": self._settings["theme"],
                "size": self._settings["size"],
                "glow_intensity": self._settings["glow_intensity"],
                "scanlines_enabled": self._settings["scanlines_enabled"],
                "always_on_top": self._settings["always_on_top"],
                "timestamp": now
            }

    def trigger_expression(self, expression: str, duration: float = 3.0) -> bool:
        """Triggers a transient emotional expression (e.g. happy, confused, alert)."""
        expr = expression.lower().strip()
        with self._lock:
            self._current_expression = expr
            self._expression_expiry = time.time() + max(0.1, duration)
        logger.info(f"Avatar expression triggered: '{expr}' for {duration}s")
        return True

    def update_lip_sync(self, amplitude: float, phoneme: Optional[str] = None) -> Dict[str, Any]:
        """Updates real-time mouth opening height and phoneme for speech synchronization."""
        clamped_amp = max(0.0, min(1.0, float(amplitude)))
        with self._lock:
            self._lip_sync["amplitude"] = clamped_amp
            self._lip_sync["mouth_open"] = round(clamped_amp * 1.0, 3)
            if phoneme is not None:
                self._lip_sync["phoneme"] = phoneme
            self._lip_sync["last_updated"] = time.time()
            return dict(self._lip_sync)

    def get_settings(self) -> Dict[str, Any]:
        """Returns current avatar configuration settings."""
        with self._lock:
            return dict(self._settings)

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Updates avatar customization settings."""
        with self._lock:
            if "theme" in new_settings and new_settings["theme"] in self.VALID_THEMES:
                self._settings["theme"] = new_settings["theme"]
            if "size" in new_settings and new_settings["size"] in self.VALID_SIZES:
                self._settings["size"] = new_settings["size"]
            if "glow_intensity" in new_settings:
                self._settings["glow_intensity"] = max(0.1, min(1.0, float(new_settings["glow_intensity"])))
            if "scanlines_enabled" in new_settings:
                self._settings["scanlines_enabled"] = bool(new_settings["scanlines_enabled"])
            if "click_through" in new_settings:
                self._settings["click_through"] = bool(new_settings["click_through"])
            if "always_on_top" in new_settings:
                self._settings["always_on_top"] = bool(new_settings["always_on_top"])
            if "speech_sync_enabled" in new_settings:
                self._settings["speech_sync_enabled"] = bool(new_settings["speech_sync_enabled"])
            if "gaze_tracking_enabled" in new_settings:
                self._settings["gaze_tracking_enabled"] = bool(new_settings["gaze_tracking_enabled"])
            return dict(self._settings)

    def reset_to_idle(self):
        """Resets avatar to standard neutral idle state."""
        self.set_state("idle", "Standing by.")


# Global singleton instance
avatar_engine = AvatarEngine()
