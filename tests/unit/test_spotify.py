"""
Unit and Integration Tests for JARVIS Spotify Control System
Covers all 11 core workflows specified in the SMART MUSIC CONTROL SYSTEM requirements.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.brain.intent import IntentClassifier
from core.brain.tools import tool_registry
from core.brain.orchestrator import brain_orchestrator
import spotify_controller as sc
from modules.media.spotify_controller import SpotifyController


@pytest.fixture
def controller():
    """Provides a fresh isolated SpotifyController instance."""
    return SpotifyController()


@pytest.fixture
def classifier():
    """Provides IntentClassifier."""
    return IntentClassifier()


# -----------------------------------------------------------------------------
# Workflow 1: Spotify closed -> voice request -> Spotify opens -> song plays
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_1_spotify_closed_to_playing(classifier):
    with patch.object(sc.spotify_controller, "is_running", return_value=False), \
         patch.object(sc.spotify_controller, "is_installed", return_value=True), \
         patch.object(sc.spotify_controller, "open_spotify", return_value={"success": True, "already_running": False, "message": "Spotify desktop application opened successfully."}), \
         patch.object(sc.spotify_controller, "play_track", return_value={"success": True, "playing": True, "track": "Shape of You", "artist": "Ed Sheeran", "message": "Playing Shape of You by Ed Sheeran."}):

        cmd = "Jarvis, play Shape of You."
        intent = classifier.classify(cmd)
        assert intent.target_tool == "spotify.play"
        assert "shape of you" in intent.extracted_params["query"].lower()

        # Execute through tool registry
        res = await tool_registry.execute(intent.target_tool, intent.extracted_params)
        assert res["success"] is True
        result_data = res["result"]
        assert result_data["success"] is True
        assert result_data["playing"] is True
        assert result_data["track"] == "Shape of You"

        # Check speech response formatting
        speech = brain_orchestrator._format_fast_result(intent.target_tool, result_data)
        assert "Playing Shape of You by Ed Sheeran" in speech


# -----------------------------------------------------------------------------
# Workflow 2: Spotify already open -> new song request -> correct song plays
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_2_spotify_already_open_new_song(classifier):
    with patch.object(sc.spotify_controller, "is_running", return_value=True), \
         patch.object(sc.spotify_controller, "play_track", return_value={"success": True, "playing": True, "track": "Naa Ready", "artist": "Thalapathy Vijay", "message": "Playing Naa Ready by Thalapathy Vijay."}):

        cmd = "Play Naa Ready."
        intent = classifier.classify(cmd)
        assert intent.target_tool == "spotify.play"
        assert intent.extracted_params["query"] == "naa ready"

        res = await tool_registry.execute(intent.target_tool, intent.extracted_params)
        assert res["success"] is True
        result_data = res["result"]
        assert result_data["success"] is True
        assert result_data["track"] == "Naa Ready"

        speech = brain_orchestrator._format_fast_result(intent.target_tool, result_data)
        assert "Playing Naa Ready by Thalapathy Vijay" in speech


# -----------------------------------------------------------------------------
# Workflow 3: Pause -> verify paused state
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_3_pause_and_verify(classifier):
    with patch.object(sc.spotify_controller, "pause_playback", return_value={"success": True, "paused": True, "message": "Music playback paused."}):
        for phrase in ["Pause the music.", "Pause.", "stop the music"]:
            intent = classifier.classify(phrase)
            assert intent.target_tool == "spotify.pause"

        res = await tool_registry.execute("spotify.pause", {})
        assert res["success"] is True
        result_data = res["result"]
        assert result_data["paused"] is True

        speech = brain_orchestrator._format_fast_result("spotify.pause", result_data)
        assert "Paused" in speech


# -----------------------------------------------------------------------------
# Workflow 4: Resume -> verify playback
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_4_resume_and_verify(classifier):
    with patch.object(sc.spotify_controller, "resume_playback", return_value={"success": True, "playing": True, "message": "Playback resumed."}):
        for phrase in ["Resume.", "Continue playing.", "Continue."]:
            intent = classifier.classify(phrase)
            assert intent.target_tool == "spotify.resume"

        res = await tool_registry.execute("spotify.resume", {})
        assert res["success"] is True
        result_data = res["result"]
        assert result_data["playing"] is True

        speech = brain_orchestrator._format_fast_result("spotify.resume", result_data)
        assert "Resumed" in speech


# -----------------------------------------------------------------------------
# Workflow 5: Next -> verify next track
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_5_next_track(classifier):
    with patch.object(sc.spotify_controller, "next_track", return_value={"success": True, "action": "next_track", "current_track": {"title": "Bad Habits"}, "message": "Skipped to next track."}):
        for phrase in ["Next song.", "Next.", "Skip this track.", "Skip"]:
            intent = classifier.classify(phrase)
            assert intent.target_tool == "spotify.next"

        res = await tool_registry.execute("spotify.next", {})
        assert res["success"] is True
        result_data = res["result"]
        assert result_data["action"] == "next_track"

        speech = brain_orchestrator._format_fast_result("spotify.next", result_data)
        assert "Skipped to next track" in speech


# -----------------------------------------------------------------------------
# Workflow 6: Previous -> verify previous track
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_6_previous_track(classifier):
    with patch.object(sc.spotify_controller, "previous_track", return_value={"success": True, "action": "previous_track", "current_track": {"title": "Castle on the Hill"}, "message": "Returned to previous track."}):
        for phrase in ["Previous song.", "Previous.", "Play that song again."]:
            intent = classifier.classify(phrase)
            assert intent.target_tool == "spotify.previous"

        res = await tool_registry.execute("spotify.previous", {})
        assert res["success"] is True
        result_data = res["result"]
        assert result_data["action"] == "previous_track"

        speech = brain_orchestrator._format_fast_result("spotify.previous", result_data)
        assert "previous track" in speech.lower()


# -----------------------------------------------------------------------------
# Workflow 7: Volume changes
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_7_volume_changes(classifier):
    with patch.object(sc.spotify_controller, "set_volume", side_effect=lambda lvl: {"success": True, "volume": lvl, "message": f"Volume set to {lvl}%."}):
        intent_up = classifier.classify("Increase volume.")
        assert intent_up.target_tool == "spotify.set_volume"
        res_up = await tool_registry.execute(intent_up.target_tool, intent_up.extracted_params)
        assert res_up["success"] is True
        assert res_up["result"]["volume"] == 70

        intent_down = classifier.classify("Reduce volume.")
        assert intent_down.target_tool == "spotify.set_volume"
        res_down = await tool_registry.execute(intent_down.target_tool, intent_down.extracted_params)
        assert res_down["success"] is True
        assert res_down["result"]["volume"] == 30

        intent_mute = classifier.classify("Mute the music.")
        assert intent_mute.target_tool == "spotify.set_volume"
        res_mute = await tool_registry.execute(intent_mute.target_tool, intent_mute.extracted_params)
        assert res_mute["success"] is True
        assert res_mute["result"]["volume"] == 0

        intent_exact = classifier.classify("Set volume to 80")
        assert intent_exact.target_tool == "spotify.set_volume"
        res_exact = await tool_registry.execute(intent_exact.target_tool, intent_exact.extracted_params)
        assert res_exact["success"] is True
        assert res_exact["result"]["volume"] == 80


# -----------------------------------------------------------------------------
# Workflow 8: Invalid song search
# -----------------------------------------------------------------------------
def test_workflow_8_invalid_song_search(controller):
    with patch.object(controller, "open_spotify", return_value={"success": True}), \
         patch.object(controller, "resume_playback", return_value={"success": True, "playing": True}), \
         patch.object(controller, "get_playback_state", return_value={"success": True, "is_playing": True}):

        # Empty query resumes playback
        res_empty = controller.play_track("")
        assert res_empty["success"] is True

        # Gibberish search returns clean search result without crashing
        res_gibberish = controller.search_track("asldkfjqwpoeiru1234908")
        assert res_gibberish["success"] is True
        assert "query" in res_gibberish


# -----------------------------------------------------------------------------
# Workflow 9: Spotify unavailable
# -----------------------------------------------------------------------------
def test_workflow_9_spotify_unavailable(controller):
    with patch.object(controller, "is_installed", return_value=False), \
         patch.object(controller, "is_running", return_value=False):

        res = controller.open_spotify()
        assert res["success"] is False
        assert res["installed"] is False
        assert "not installed" in res["message"].lower()


# -----------------------------------------------------------------------------
# Workflow 10: Expired OAuth token graceful fallback
# -----------------------------------------------------------------------------
def test_workflow_10_expired_oauth_token(controller):
    # Mock spotipy client raising token error
    mock_sp = MagicMock()
    mock_sp.search.side_effect = Exception("The access token expired")
    mock_sp.start_playback.side_effect = Exception("The access token expired")
    controller._sp_client = mock_sp

    with patch.object(controller, "open_spotify", return_value={"success": True}), \
         patch.object(controller, "get_playback_state", return_value={"success": True, "is_playing": True}), \
         patch.object(controller, "_send_media_key") as mock_key:

        # Search should gracefully fall back to heuristic format
        search_res = controller.search_track("Blinding Lights by The Weeknd")
        assert search_res["success"] is True
        assert search_res["top_result"]["name"] == "Blinding Lights"
        assert search_res["top_result"]["artist"] == "The Weeknd"

        # Playback should fall back to desktop automation without exception
        play_res = controller.play_track("Blinding Lights")
        assert play_res["success"] is True
        assert mock_key.called


# -----------------------------------------------------------------------------
# Workflow 11: Voice commands during music playback
# -----------------------------------------------------------------------------
def test_workflow_11_voice_commands_during_music_playback(classifier):
    # During music playback, user asks information queries
    info_queries = [
        "What song is playing?",
        "Who is the singer?",
        "How much time is remaining?",
        "Show the current playlist."
    ]

    for q in info_queries:
        intent = classifier.classify(q)
        assert intent.target_tool == "spotify.get_current_track"

    with patch.object(sc.spotify_controller, "get_current_track", return_value={
        "title": "Shape of You",
        "artist": "Ed Sheeran",
        "album": "Divide",
        "is_playing": True,
        "duration_ms": 233000,
        "progress_ms": 75000
    }):
        speech = brain_orchestrator._format_fast_result("spotify.get_current_track", sc.spotify_controller.get_current_track())
        assert "Shape of You" in speech
        assert "Ed Sheeran" in speech
