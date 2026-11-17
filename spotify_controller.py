"""
Root workspace proxy for JARVIS Spotify Control Engine.
Exposes all 14 required functions directly.
"""

from modules.media.spotify_controller import (
    SpotifyController,
    spotify_controller,
    open_spotify,
    search_track,
    search_artist,
    search_album,
    search_playlist,
    play_track,
    pause_playback,
    resume_playback,
    next_track,
    previous_track,
    get_current_track,
    get_playback_state,
    set_volume,
    get_available_devices
)

__all__ = [
    "SpotifyController",
    "spotify_controller",
    "open_spotify",
    "search_track",
    "search_artist",
    "search_album",
    "search_playlist",
    "play_track",
    "pause_playback",
    "resume_playback",
    "next_track",
    "previous_track",
    "get_current_track",
    "get_playback_state",
    "set_volume",
    "get_available_devices"
]
