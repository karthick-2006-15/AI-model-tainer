"""
Spotify & Windows Media Playback Integration Plugin
Provides media controls (play, pause, next, volume) and URI playlist/search launching.
"""

import os
import ctypes
import subprocess
import logging
from typing import Dict, Any
from modules.integrations.base import BaseIntegration

logger = logging.getLogger("jarvis.integrations.spotify")

# Win32 Virtual Key Codes for Media Control
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3


def _send_media_key(vk_code: int):
    """Sends a native Windows media virtual keystroke without mouse interaction."""
    if os.name == "nt":
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)  # KEYEVENTF_KEYUP
    else:
        import pyautogui
        pyautogui.press("playpause")


class SpotifyIntegration(BaseIntegration):
    def __init__(self):
        super().__init__(
            name="Spotify & Media",
            description="Media playback and Spotify music control.",
            capabilities=["play_pause", "next", "previous", "volume_up", "volume_down", "mute", "search_play"],
            permission_level=1
        )

    def is_available(self) -> bool:
        return True  # Native Windows media hotkeys work system-wide

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if action in ("play_pause", "toggle"):
                _send_media_key(VK_MEDIA_PLAY_PAUSE)
                res = {"success": True, "action": "play_pause", "message": "Toggled playback state."}
            elif action == "next":
                _send_media_key(VK_MEDIA_NEXT_TRACK)
                res = {"success": True, "action": "next", "message": "Skipped to next track."}
            elif action == "previous":
                _send_media_key(VK_MEDIA_PREV_TRACK)
                res = {"success": True, "action": "previous", "message": "Returned to previous track."}
            elif action == "volume_up":
                _send_media_key(VK_VOLUME_UP)
                res = {"success": True, "action": "volume_up", "message": "Increased volume."}
            elif action == "volume_down":
                _send_media_key(VK_VOLUME_DOWN)
                res = {"success": True, "action": "volume_down", "message": "Decreased volume."}
            elif action == "mute":
                _send_media_key(VK_VOLUME_MUTE)
                res = {"success": True, "action": "mute", "message": "Toggled audio mute."}
            elif action == "search_play":
                query = params.get("query", "Lo-Fi Beats")
                uri = f"spotify:search:{query}"
                subprocess.Popen(f"start {uri}", shell=True)
                res = {"success": True, "action": "search_play", "query": query, "uri": uri}
            else:
                err = f"Unknown media action '{action}'"
                self.log_execution(action, params, False, None, err)
                return {"success": False, "error": err}

            self.log_execution(action, params, True, res)
            return res

        except Exception as e:
            logger.error(f"Media control exception: {e}")
            self.log_execution(action, params, False, None, str(e))
            return {"success": False, "error": str(e)}


# Global instance
spotify_integration = SpotifyIntegration()
