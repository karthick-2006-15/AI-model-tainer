"""
Autonomous YouTube Automation Engine
Controls YouTube search, video inspection, selection, playback controls, and volume adjustments
via Playwright and direct DOM integration.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from modules.computer_use.browser_playwright import playwright_controller
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.computer_use.youtube")


class YouTubeAutomation:
    """Automates YouTube browsing, search, video picking, and playback controls."""

    def __init__(self):
        self._last_search_results: List[Dict[str, Any]] = []

    def open_youtube(self) -> Dict[str, Any]:
        """Navigates the browser directly to YouTube homepage."""
        logger.info("Opening YouTube...")
        return playwright_controller.open("https://www.youtube.com")

    def search(self, query: str) -> Dict[str, Any]:
        """
        Searches YouTube for a topic, inspects video results, and extracts titles and links.
        Expected workflow:
        1. Open YouTube or navigate to search results.
        2. Identify search box.
        3. Enter query & execute.
        4. Inspect results: title, channel, views, URL.
        5. Report structured results.
        """
        if permission_engine.is_emergency_stopped():
            return {"success": False, "error": "Emergency stop active."}

        logger.info(f"Searching YouTube for: '{query}'")
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        open_res = playwright_controller.open(search_url)

        if not open_res.get("success"):
            return open_res

        # Allow results to render
        page = playwright_controller.current_page
        try:
            page.wait_for_selector("ytd-video-renderer, #contents", timeout=8000)
        except Exception:
            pass

        # Extract top video results
        results = page.evaluate("""() => {
            const items = [];
            const renderers = document.querySelectorAll('ytd-video-renderer');
            for (let i = 0; i < Math.min(renderers.length, 8); i++) {
                const el = renderers[i];
                const titleEl = el.querySelector('#video-title');
                const channelEl = el.querySelector('#channel-name, ytd-channel-name');
                const metadataEl = el.querySelector('#metadata-line');
                
                if (titleEl && titleEl.innerText.trim()) {
                    items.push({
                        index: i + 1,
                        title: titleEl.innerText.trim(),
                        url: titleEl.href || (titleEl.getAttribute('href') ? 'https://www.youtube.com' + titleEl.getAttribute('href') : ''),
                        channel: channelEl ? channelEl.innerText.trim() : 'Unknown Creator',
                        metadata: metadataEl ? metadataEl.innerText.replace(/\\n/g, ' • ').trim() : ''
                    });
                }
            }
            return items;
        }""")

        self._last_search_results = results

        # Format spoken summary
        titles_summary = ""
        if results:
            first_three = [f"#{r['index']}: {r['title']}" for r in results[:3]]
            titles_summary = f"I found {len(results)} videos for '{query}'. Top results: {'; '.join(first_three)}."
        else:
            titles_summary = f"Search executed for '{query}', but no video elements were immediately parsed."

        return {
            "success": True,
            "query": query,
            "results_count": len(results),
            "results": results,
            "summary": titles_summary
        }

    def play_video(self, result_index: int = 1, video_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Plays a specific video from the search results (e.g. index 1 = first video, index 3 = third result).
        """
        if permission_engine.is_emergency_stopped():
            return {"success": False, "error": "Emergency stop active."}

        target_url = video_url
        target_title = "Selected Video"

        if not target_url and self._last_search_results:
            for item in self._last_search_results:
                if item.get("index") == result_index:
                    target_url = item.get("url")
                    target_title = item.get("title", target_title)
                    break

        if not target_url and self._last_search_results:
            target_url = self._last_search_results[0].get("url")
            target_title = self._last_search_results[0].get("title", target_title)

        if not target_url:
            # Fallback to clicking first video title element on active page
            page = playwright_controller.current_page
            try:
                first_link = page.locator("#video-title").nth(max(0, result_index - 1))
                if first_link.count() > 0:
                    first_link.click(timeout=5000)
                    return {
                        "success": True,
                        "action": "click_result",
                        "index": result_index,
                        "report": f"Playing video #{result_index} from search results."
                    }
            except Exception as e:
                return {"success": False, "error": f"Could not locate video #{result_index}: {e}"}

        # Navigate directly to target URL
        open_res = playwright_controller.open(target_url)
        return {
            "success": open_res.get("success", False),
            "video_title": target_title,
            "url": target_url,
            "report": f"Now playing: {target_title}."
        }

    def control_playback(self, action: str) -> Dict[str, Any]:
        """
        Controls YouTube player playback:
        'play', 'pause', 'toggle', 'mute', 'unmute', 'volume_up', 'volume_down', 'fullscreen'.
        Uses YouTube native keyboard shortcuts.
        """
        page = playwright_controller.current_page
        act = action.lower().strip()

        key_map = {
            "play": "k",
            "pause": "k",
            "toggle": "k",
            "mute": "m",
            "unmute": "m",
            "volume_up": "ArrowUp",
            "volume_down": "ArrowDown",
            "fullscreen": "f",
            "seek_forward": "l",
            "seek_backward": "j"
        }

        target_key = key_map.get(act, "k")

        try:
            # Focus on player and send shortcut
            page.keyboard.press(target_key)
            logger.info(f"YouTube playback control executed: '{act}' (key: {target_key})")
            return {
                "success": True,
                "action": act,
                "key_dispatched": target_key,
                "report": f"YouTube video {act} executed successfully."
            }
        except Exception as e:
            logger.error(f"Playback control failed: {e}")
            return {"success": False, "error": str(e)}


# Global singleton instance
youtube_automation = YouTubeAutomation()
