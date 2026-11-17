"""
Spotify & Windows Media Playback Integration Plugin
Provides media controls (play, pause, next, volume) and Spotify desktop controller integration.
"""

import os
import logging
from typing import Dict, Any
from modules.integrations.base import BaseIntegration
from modules.media.spotify_controller import spotify_controller

logger = logging.getLogger("jarvis.integrations.spotify")


class SpotifyIntegration(BaseIntegration):
    def __init__(self):
        super().__init__(
            name="Spotify & Media",
            description="Media playback and Windows Spotify music control.",
            capabilities=[
                "play", "pause", "resume", "play_pause", "next", "previous",
                "volume_up", "volume_down", "set_volume", "mute",
                "search_play", "get_current_track", "get_playback_state", "open_spotify"
            ],
            permission_level=1
        )

    def is_available(self) -> bool:
        return spotify_controller.is_installed() or spotify_controller.is_running()

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            act = action.lower().strip()
            if act in ("play", "search_play"):
                q = params.get("query") or params.get("song") or params.get("track") or ""
                res = spotify_controller.play_track(q)
            elif act == "pause":
                res = spotify_controller.pause_playback()
            elif act == "resume":
                res = spotify_controller.resume_playback()
            elif act in ("play_pause", "toggle"):
                state = spotify_controller.get_playback_state()
                if state.get("is_playing"):
                    res = spotify_controller.pause_playback()
                else:
                    res = spotify_controller.resume_playback()
            elif act in ("next", "skip"):
                res = spotify_controller.next_track()
            elif act in ("previous", "prev"):
                res = spotify_controller.previous_track()
            elif act == "volume_up":
                cur_vol = spotify_controller.get_playback_state().get("volume", 50)
                res = spotify_controller.set_volume(min(100, cur_vol + 10))
            elif act == "volume_down":
                cur_vol = spotify_controller.get_playback_state().get("volume", 50)
                res = spotify_controller.set_volume(max(0, cur_vol - 10))
            elif act == "set_volume":
                level = params.get("level", 50)
                res = spotify_controller.set_volume(int(level))
            elif act == "mute":
                res = spotify_controller.set_volume(0)
            elif act == "get_current_track":
                res = {"success": True, "track": spotify_controller.get_current_track()}
            elif act == "get_playback_state":
                res = spotify_controller.get_playback_state()
            elif act == "open_spotify":
                res = spotify_controller.open_spotify()
            else:
                err = f"Unknown media action '{action}'"
                self.log_execution(action, params, False, None, err)
                return {"success": False, "error": err}

            if isinstance(res, dict) and "action" not in res:
                res["action"] = act
            self.log_execution(action, params, True, res)
            return res

        except Exception as e:
            logger.error(f"Media control exception: {e}")
            self.log_execution(action, params, False, None, str(e))
            return {"success": False, "error": str(e)}


# Global instance
spotify_integration = SpotifyIntegration()
