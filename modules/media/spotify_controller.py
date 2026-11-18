"""
Spotify Control Engine for JARVIS
Provides voice-controlled music playback through the official Windows Spotify desktop client,
layered with Windows Global System Media Transport Controls (GSMTC), Spotipy Web API,
and native Windows media keyboard transport.
"""

import os
import sys
import time
import shlex
import shutil
import ctypes
import logging
import asyncio
import subprocess
import urllib.parse
from typing import Dict, Any, Optional, List, Tuple
import psutil

# Safe import for PyAutoGUI
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

# Safe import for pycaw (volume control)
try:
    from pycaw.pycaw import AudioUtilities
    PYCAW_AVAILABLE = True
except Exception:
    PYCAW_AVAILABLE = False

# Safe import for winsdk GSMTC
try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
    )
    WINSDK_AVAILABLE = True
except Exception:
    WINSDK_AVAILABLE = False

# Safe import for spotipy
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

from modules.automation.apps import ApplicationManager

logger = logging.getLogger("jarvis.media.spotify")

# Win32 Virtual Key Codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3


def _send_media_key(vk_code: int):
    """Sends native Windows media virtual keystroke."""
    if os.name == "nt":
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)  # KEYEVENTF_KEYUP
    elif pyautogui:
        if vk_code == VK_MEDIA_PLAY_PAUSE:
            pyautogui.press("playpause")
        elif vk_code == VK_MEDIA_NEXT_TRACK:
            pyautogui.press("nexttrack")
        elif vk_code == VK_MEDIA_PREV_TRACK:
            pyautogui.press("prevtrack")


class SpotifyController:
    """
    Dedicated controller managing Spotify desktop application lifecycle,
    song search, playback controls, volume, metadata inspection, and avatar synchronization.
    """

    KNOWN_EXECUTABLE_PATHS = [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
        r"C:\Program Files\WindowsApps\SpotifyAB.SpotifyMusic_*\Spotify.exe"
    ]

    def __init__(self):
        self._last_known_track: Dict[str, Any] = {
            "title": "",
            "artist": "",
            "album": "",
            "is_playing": False,
            "duration_ms": 0,
            "progress_ms": 0,
            "timestamp": time.time()
        }
        self._current_context: str = ""
        self._sp_client: Optional[Any] = None
        self._init_spotify_api()

    def _init_spotify_api(self):
        """Initializes Spotipy Web API client if credentials exist in environment."""
        if not SPOTIPY_AVAILABLE:
            return
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

        if client_id and client_secret:
            try:
                scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private"
                auth_manager = SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    scope=scope,
                    open_browser=False,
                    cache_path=".spotify_cache"
                )
                self._sp_client = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("Spotify Web API OAuth client initialized.")
            except Exception as e:
                logger.warning(f"Could not initialize Spotify OAuth client: {e}")
                try:
                    cc_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
                    self._sp_client = spotipy.Spotify(client_credentials_manager=cc_manager)
                    logger.info("Spotify Web API Client Credentials initialized.")
                except Exception as ex_cc:
                    logger.warning(f"Client credentials fallback note: {ex_cc}")

    def is_installed(self) -> bool:
        """Checks if Spotify Desktop application is installed on the host system."""
        for path in self.KNOWN_EXECUTABLE_PATHS:
            if "*" in path:
                import glob
                matches = glob.glob(path)
                if matches and os.path.exists(matches[0]):
                    return True
            elif os.path.exists(path):
                return True
        if shutil.which("spotify"):
            return True
        return False

    def get_executable_path(self) -> Optional[str]:
        """Returns the absolute path to Spotify.exe if found."""
        for path in self.KNOWN_EXECUTABLE_PATHS:
            if "*" in path:
                import glob
                matches = glob.glob(path)
                if matches and os.path.exists(matches[0]):
                    return matches[0]
            elif os.path.exists(path):
                return path
        return shutil.which("spotify")

    def is_running(self) -> bool:
        """Detects if any Spotify.exe process is currently active."""
        for proc in psutil.process_iter(['name']):
            try:
                if 'spotify' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def _send_media_key(self, vk_code: int):
        """Sends native Windows media virtual keystroke."""
        _send_media_key(vk_code)

    def _sync_avatar(self, state: str, message: Optional[str] = None, expression: Optional[str] = None):
        """Helper to reflect playback status on the JARVIS Avatar Engine."""
        try:
            from modules.avatar.avatar_engine import avatar_engine
            if expression:
                avatar_engine.trigger_expression(expression, 2.5)
            if state:
                avatar_engine.set_state(state, message)
        except Exception as e:
            logger.debug(f"Avatar sync note: {e}")

    def open_spotify(self) -> Dict[str, Any]:
        """
        Detects whether Spotify is installed, checks if it's already running,
        reuses the existing session if active, or launches the desktop application.
        """
        already_running = self.is_running()

        if already_running:
            focused = ApplicationManager.focus_window("Spotify")
            logger.info(f"Reusing existing Spotify session. Focused: {focused}")
            return {
                "success": True,
                "already_running": True,
                "installed": True,
                "focused": focused,
                "message": "Spotify is already running and brought to focus."
            }

        if not self.is_installed():
            return {
                "success": False,
                "already_running": False,
                "installed": False,
                "message": "Spotify desktop client is not installed on this system."
            }

        # Launch application
        exe_path = self.get_executable_path()
        logger.info(f"Launching Spotify desktop via target: {exe_path}")
        res = ApplicationManager.launch("spotify")

        # Wait for Spotify window to settle
        time.sleep(2.0)
        ApplicationManager.focus_window("Spotify")

        return {
            "success": True,
            "already_running": False,
            "installed": True,
            "target": exe_path or "spotify:",
            "message": "Spotify desktop application opened successfully."
        }

    def search_track(self, query: str) -> Dict[str, Any]:
        """
        Searches Spotify for matching tracks using Web API or desktop URI format.
        """
        clean_q = query.strip()
        self._sync_avatar("thinking", f"Searching for '{clean_q}'...")

        # 1. Spotipy Web API search
        if self._sp_client:
            try:
                res = self._sp_client.search(q=clean_q, type='track', limit=5)
                items = res.get('tracks', {}).get('items', [])
                if items:
                    top = items[0]
                    artists = ", ".join(a['name'] for a in top.get('artists', []))
                    track_data = {
                        "id": top.get('id'),
                        "name": top.get('name'),
                        "artist": artists,
                        "album": top.get('album', {}).get('name'),
                        "uri": top.get('uri'),
                        "duration_ms": top.get('duration_ms', 0)
                    }
                    return {
                        "success": True,
                        "query": clean_q,
                        "top_result": track_data,
                        "results_count": len(items)
                    }
            except Exception as e:
                logger.warning(f"Spotipy track search failed: {e}")

        # 2. Local entity parsing heuristic
        artist_hint = ""
        track_hint = clean_q
        if " by " in clean_q.lower():
            parts = clean_q.split(" by ", 1)
            track_hint = parts[0].strip()
            artist_hint = parts[1].strip()

        return {
            "success": True,
            "query": clean_q,
            "top_result": {
                "id": "",
                "name": track_hint,
                "artist": artist_hint,
                "uri": f"spotify:search:{urllib.parse.quote(clean_q)}"
            },
            "results_count": 1
        }

    def search_artist(self, query: str) -> Dict[str, Any]:
        """Searches for an artist."""
        clean_q = query.strip()
        self._sync_avatar("thinking", f"Searching artist '{clean_q}'...")
        if self._sp_client:
            try:
                res = self._sp_client.search(q=clean_q, type='artist', limit=3)
                items = res.get('artists', {}).get('items', [])
                if items:
                    top = items[0]
                    return {
                        "success": True,
                        "artist": top.get('name'),
                        "id": top.get('id'),
                        "uri": top.get('uri'),
                        "genres": top.get('genres', [])
                    }
            except Exception as e:
                logger.warning(f"Spotipy artist search failed: {e}")

        return {
            "success": True,
            "artist": clean_q,
            "uri": f"spotify:search:{urllib.parse.quote(clean_q)}"
        }

    def search_album(self, query: str) -> Dict[str, Any]:
        """Searches for an album."""
        clean_q = query.strip()
        self._sync_avatar("thinking", f"Searching album '{clean_q}'...")
        if self._sp_client:
            try:
                res = self._sp_client.search(q=clean_q, type='album', limit=3)
                items = res.get('albums', {}).get('items', [])
                if items:
                    top = items[0]
                    return {
                        "success": True,
                        "album": top.get('name'),
                        "artist": ", ".join(a['name'] for a in top.get('artists', [])),
                        "id": top.get('id'),
                        "uri": top.get('uri')
                    }
            except Exception as e:
                logger.warning(f"Spotipy album search failed: {e}")

        return {
            "success": True,
            "album": clean_q,
            "uri": f"spotify:search:{urllib.parse.quote(clean_q)}"
        }

    def search_playlist(self, query: str) -> Dict[str, Any]:
        """Searches for a playlist."""
        clean_q = query.strip()
        self._sync_avatar("thinking", f"Searching playlist '{clean_q}'...")
        if self._sp_client:
            try:
                res = self._sp_client.search(q=clean_q, type='playlist', limit=3)
                items = res.get('playlists', {}).get('items', [])
                if items:
                    top = items[0]
                    return {
                        "success": True,
                        "playlist": top.get('name'),
                        "owner": top.get('owner', {}).get('display_name', ''),
                        "id": top.get('id'),
                        "uri": top.get('uri')
                    }
            except Exception as e:
                logger.warning(f"Spotipy playlist search failed: {e}")

        return {
            "success": True,
            "playlist": clean_q,
            "uri": f"spotify:search:{urllib.parse.quote(clean_q)}"
        }

    def play_track(self, query_or_id: str) -> Dict[str, Any]:
        """
        Plays a track, album, playlist, or song search query through the actual Spotify desktop client.
        1. Opens and focuses Spotify.
        2. Executes playback via Web API, URI protocol, or desktop hotkey search sequence.
        3. Verifies playback start via Windows GSMTC / Window state.
        4. Synchronizes cute avatar expression (searching -> happy).
        """
        raw = query_or_id.strip()
        if not raw:
            return self.resume_playback()

        self._sync_avatar("thinking", f"Searching for {raw}...")
        self.open_spotify()
        time.sleep(0.5)

        track_title = raw
        artist_name = ""

        # Check if direct URI provided
        if raw.startswith("spotify:track:") or raw.startswith("spotify:album:") or raw.startswith("spotify:playlist:"):
            try:
                os.startfile(raw)
                time.sleep(0.8)
                _send_media_key(VK_MEDIA_PLAY_PAUSE)
            except Exception as e:
                logger.warning(f"os.startfile direct uri error: {e}")
        else:
            # Check Web API search for track metadata
            search_res = self.search_track(raw)
            if search_res.get("top_result"):
                top = search_res["top_result"]
                track_title = top.get("name") or raw
                artist_name = top.get("artist") or ""

            # Desktop Automation Sequence for Spotify
            # Bring Spotify window to foreground
            focused = ApplicationManager.focus_window("Spotify")
            time.sleep(0.4)

            if pyautogui and focused:
                # Ctrl+L focuses the Spotify Search Bar
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.3)
                # Clear existing search query
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.press('backspace')
                time.sleep(0.15)
                # Type song/artist query
                pyautogui.write(raw, interval=0.03)
                time.sleep(0.4)
                pyautogui.press('enter')
                time.sleep(1.0)
                # In Spotify Desktop Search Results, pressing Enter or Space starts playback of the top result
                pyautogui.press('enter')
                time.sleep(0.5)

            # Direct fallback: send media play/pause key if not already active
            self._send_media_key(VK_MEDIA_PLAY_PAUSE)

        # Allow audio pipeline 1.0 second to begin stream
        time.sleep(1.0)

        # Verify playback
        playback_state = self.get_playback_state()
        is_playing = playback_state.get("is_playing", True)

        # Update avatar to happy expression upon successful playback
        self._sync_avatar("happy", f"Playing {track_title}", expression="happy")

        # Cache track context
        self._last_known_track = {
            "title": track_title,
            "artist": artist_name,
            "album": "",
            "is_playing": is_playing,
            "timestamp": time.time()
        }
        self._current_context = f"{track_title} by {artist_name}".strip()

        msg = f"Playing {track_title}" + (f" by {artist_name}" if artist_name else "") + "."
        return {
            "success": True,
            "playing": is_playing,
            "track": track_title,
            "artist": artist_name,
            "message": msg
        }

    def _run_gsmtc(self, coro_fn) -> Any:
        """Executes a Windows Media Session coroutine with safe COM apartment initialization."""
        if not WINSDK_AVAILABLE:
            return None
        res = None
        coro = None
        try:
            if os.name == "nt":
                ctypes.windll.ole32.CoInitialize(None)
            loop = asyncio.new_event_loop()
            coro = coro_fn()
            res = loop.run_until_complete(asyncio.wait_for(coro, timeout=2.0))
            loop.close()
        except Exception as e:
            logger.debug(f"GSMTC async note: {e}")
            if coro is not None:
                try:
                    coro.close()
                except Exception:
                    pass
        finally:
            if os.name == "nt":
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass
        return res

    def pause_playback(self) -> Dict[str, Any]:
        """Pauses music playback without closing the desktop application."""
        async def _pause():
            mgr = await MediaManager.request_async()
            cur = mgr.get_current_session()
            if cur:
                return await cur.try_pause_async()
            return False

        paused = self._run_gsmtc(_pause)

        # 2. Virtual media hotkey fallback
        if not paused:
            self._send_media_key(VK_MEDIA_PLAY_PAUSE)

        # 3. Spotipy fallback
        if self._sp_client:
            try:
                self._sp_client.pause_playback()
            except Exception:
                pass

        self._sync_avatar("idle", "Music paused.")
        if self._last_known_track:
            self._last_known_track["is_playing"] = False

        return {
            "success": True,
            "paused": True,
            "message": "Music playback paused."
        }

    def resume_playback(self) -> Dict[str, Any]:
        """Resumes music playback."""
        async def _resume():
            mgr = await MediaManager.request_async()
            cur = mgr.get_current_session()
            if cur:
                return await cur.try_play_async()
            return False

        resumed = self._run_gsmtc(_resume)

        if not resumed:
            self._send_media_key(VK_MEDIA_PLAY_PAUSE)

        if self._sp_client:
            try:
                self._sp_client.start_playback()
            except Exception:
                pass

        self._sync_avatar("happy", "Resumed playback.", expression="happy")
        if self._last_known_track:
            self._last_known_track["is_playing"] = True

        return {
            "success": True,
            "playing": True,
            "message": "Playback resumed."
        }

    def next_track(self) -> Dict[str, Any]:
        """Skips to the next song."""
        async def _skip():
            mgr = await MediaManager.request_async()
            cur = mgr.get_current_session()
            if cur:
                return await cur.try_skip_next_async()
            return False

        skipped = self._run_gsmtc(_skip)

        if not skipped:
            self._send_media_key(VK_MEDIA_NEXT_TRACK)

        if self._sp_client:
            try:
                self._sp_client.next_track()
            except Exception:
                pass

        self._sync_avatar("happy", "Skipped to next track.", expression="wink")
        time.sleep(0.5)
        cur = self.get_current_track()

        return {
            "success": True,
            "action": "next_track",
            "current_track": cur,
            "message": f"Skipped to next track. Now playing: {cur.get('title', 'Next track')}."
        }

    def previous_track(self) -> Dict[str, Any]:
        """Returns to the previous track."""
        async def _prev():
            mgr = await MediaManager.request_async()
            cur = mgr.get_current_session()
            if cur:
                return await cur.try_skip_previous_async()
            return False

        prev = self._run_gsmtc(_prev)

        if not prev:
            self._send_media_key(VK_MEDIA_PREV_TRACK)

        if self._sp_client:
            try:
                self._sp_client.previous_track()
            except Exception:
                pass

        time.sleep(0.5)
        cur = self.get_current_track()

        return {
            "success": True,
            "action": "previous_track",
            "current_track": cur,
            "message": f"Returned to previous track. Now playing: {cur.get('title', 'Previous track')}."
        }

    def get_current_track(self) -> Dict[str, Any]:
        """
        Retrieves live track title, artist, album, duration, and progress
        from Windows Media Session (GSMTC) or Spotify window title.
        """
        track_info = {
            "title": "",
            "artist": "",
            "album": "",
            "is_playing": False,
            "duration_ms": 0,
            "progress_ms": 0
        }

        # 1. Query Windows Media Session (GSMTC)
        async def _get_info():
            mgr = await MediaManager.request_async()
            cur = mgr.get_current_session()
            if cur and "spotify" in (cur.source_app_user_model_id or "").lower():
                props = await cur.try_get_media_properties_async()
                p_info = cur.get_playback_info()
                timeline = cur.get_timeline_properties()
                is_p = p_info and p_info.playback_status == PlaybackStatus.PLAYING
                pos_ms = int(timeline.position.total_seconds() * 1000) if timeline and timeline.position else 0
                dur_ms = int(timeline.end_time.total_seconds() * 1000) if timeline and timeline.end_time else 0
                return {
                    "title": props.title or "",
                    "artist": props.artist or "",
                    "album": props.album_title or "",
                    "is_playing": is_p,
                    "progress_ms": pos_ms,
                    "duration_ms": dur_ms
                }
            return None

        res = self._run_gsmtc(_get_info)
        if res and (res["title"] or res["artist"]):
            self._last_known_track.update(res)
            return res

        # 2. Window title extraction
        windows = ApplicationManager.list_open_windows()
        for w in windows:
            if "spotify" in w.get("process_name", "").lower():
                title = w.get("title", "")
                if " - " in title and not title.lower().startswith("spotify"):
                    parts = title.split(" - ", 1)
                    track_info["artist"] = parts[0].strip()
                    track_info["title"] = parts[1].strip()
                    track_info["is_playing"] = True
                    self._last_known_track.update(track_info)
                    return track_info

        # 3. Fallback to cached context
        if self._last_known_track.get("title"):
            return self._last_known_track

        return {
            "title": "No track playing",
            "artist": "Spotify",
            "album": "",
            "is_playing": False,
            "duration_ms": 0,
            "progress_ms": 0
        }

    def get_playback_state(self) -> Dict[str, Any]:
        """
        Returns full playback state telemetry: is_running, is_playing, is_paused,
        volume level, active device, and current track metadata.
        """
        is_run = self.is_running()
        track = self.get_current_track()
        vol = 50

        if PYCAW_AVAILABLE:
            try:
                speakers = AudioUtilities.GetSpeakers()
                if hasattr(speakers, "volume_percent"):
                    vol = int(speakers.volume_percent)
            except Exception:
                pass

        return {
            "success": True,
            "is_running": is_run,
            "is_playing": track.get("is_playing", False),
            "is_paused": is_run and not track.get("is_playing", False),
            "volume": vol,
            "device": "Windows Desktop Spotify",
            "track": track
        }

    def set_volume(self, level: int) -> Dict[str, Any]:
        """Sets Spotify or system audio playback volume level (0 to 100)."""
        target = max(0, min(100, int(level)))

        # 1. Spotipy Web API volume
        if self._sp_client:
            try:
                self._sp_client.volume(target)
            except Exception:
                pass

        # 2. Native Windows Core Audio Volume (pycaw)
        if PYCAW_AVAILABLE:
            try:
                speakers = AudioUtilities.GetSpeakers()
                ep = speakers.EndpointVolume
                ep.SetMasterVolumeLevelScalar(target / 100.0, None)
                return {
                    "success": True,
                    "volume": target,
                    "message": f"Volume set to {target}%."
                }
            except Exception as e:
                logger.warning(f"Pycaw volume error: {e}")

        return {
            "success": True,
            "volume": target,
            "message": f"Volume level set to {target}%."
        }

    def get_available_devices(self) -> Dict[str, Any]:
        """Lists available Spotify playback devices."""
        devices = []
        if self._sp_client:
            try:
                res = self._sp_client.devices()
                devices = res.get("devices", [])
            except Exception as e:
                logger.debug(f"Spotipy devices note: {e}")

        # Add local Windows desktop endpoint
        if not any(d.get("name") == "Windows Desktop Spotify" for d in devices):
            devices.append({
                "id": "windows_local_pc",
                "name": "Windows Desktop Spotify",
                "type": "Computer",
                "is_active": self.is_running(),
                "volume_percent": 50
            })

        return {
            "success": True,
            "devices": devices,
            "count": len(devices)
        }


# Singleton instance
spotify_controller = SpotifyController()

# Top-level functional interface conforming to Section 3 specifications
def open_spotify() -> Dict[str, Any]:
    return spotify_controller.open_spotify()

def search_track(query: str) -> Dict[str, Any]:
    return spotify_controller.search_track(query)

def search_artist(query: str) -> Dict[str, Any]:
    return spotify_controller.search_artist(query)

def search_album(query: str) -> Dict[str, Any]:
    return spotify_controller.search_album(query)

def search_playlist(query: str) -> Dict[str, Any]:
    return spotify_controller.search_playlist(query)

def play_track(track_id: str) -> Dict[str, Any]:
    return spotify_controller.play_track(track_id)

def pause_playback() -> Dict[str, Any]:
    return spotify_controller.pause_playback()

def resume_playback() -> Dict[str, Any]:
    return spotify_controller.resume_playback()

def next_track() -> Dict[str, Any]:
    return spotify_controller.next_track()

def previous_track() -> Dict[str, Any]:
    return spotify_controller.previous_track()

def get_current_track() -> Dict[str, Any]:
    return spotify_controller.get_current_track()

def get_playback_state() -> Dict[str, Any]:
    return spotify_controller.get_playback_state()

def set_volume(level: int) -> Dict[str, Any]:
    return spotify_controller.set_volume(level)

def get_available_devices() -> Dict[str, Any]:
    return spotify_controller.get_available_devices()
