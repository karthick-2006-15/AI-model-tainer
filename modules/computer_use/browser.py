"""
Browser DOM Interaction & Tab Inspection Engine
Provides active tab detection, DOM inspection, element locating, and field entry.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup
from modules.computer_use.screen import screen_intelligence
from modules.computer_use.native_uia import native_uia
from modules.computer_use.mouse_kb import mouse_kb

logger = logging.getLogger("jarvis.computer_use.browser")


class BrowserAutomationEngine:
    """Interacts with browser tabs and DOM content."""

    def get_active_tab(self) -> Dict[str, Any]:
        """Detects the currently active browser window and tab title."""
        active = screen_intelligence.get_active_window()
        app_type = active.get("app_type")

        if app_type != "browser":
            # Search if Chrome or Edge is open in the background
            from modules.automation.apps import ApplicationManager
            windows = ApplicationManager.list_open_windows()
            for w in windows:
                p = w.get("process_name", "").lower()
                if "chrome" in p or "msedge" in p:
                    return {
                        "success": True,
                        "is_active_foreground": False,
                        "title": w.get("title"),
                        "process_name": w.get("process_name"),
                        "hwnd": w.get("hwnd")
                    }

        return {
            "success": True,
            "is_active_foreground": (app_type == "browser"),
            "title": active.get("title", "No active browser"),
            "process_name": active.get("process_name", "unknown"),
            "hwnd": active.get("hwnd")
        }

    async def inspect_page(self, url: str) -> Dict[str, Any]:
        """Fetches and inspects the HTML content, title, and interactive elements of a URL."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JARVIS/7.0"})
                html = resp.text

            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"

            inputs = [inp.get("name") or inp.get("id") or inp.get("placeholder", "input") for inp in soup.find_all("input")[:15]]
            buttons = [btn.get_text().strip() for btn in soup.find_all("button")[:10] if btn.get_text().strip()]
            links = [{"text": a.get_text().strip(), "href": a.get("href")} for a in soup.find_all("a")[:10] if a.get_text().strip()]

            return {
                "success": True,
                "url": url,
                "status_code": resp.status_code,
                "title": title,
                "inputs": inputs,
                "buttons": buttons,
                "links": links,
                "html_length": len(html)
            }
        except Exception as e:
            logger.error(f"Error inspecting page '{url}': {e}")
            return {"success": False, "error": str(e)}

    def click_element(self, text_or_name: str) -> Dict[str, Any]:
        """Clicks an element inside the browser window using UI Automation or visual mapping."""
        res_uia = native_uia.click_element_by_name(text_or_name)
        if res_uia.get("success"):
            return res_uia

        return {
            "success": False,
            "error": f"Browser element '{text_or_name}' not found."
        }

    def fill_field(self, field_name: str, value: str) -> Dict[str, Any]:
        """Fills text into a browser input field."""
        res_uia = native_uia.type_into_element(text=value, name=field_name)
        if res_uia.get("success"):
            return res_uia

        # Fallback to focused typing
        mouse_kb.type_text(value)
        return {
            "success": True,
            "method": "keyboard_fallback",
            "field": field_name,
            "value": value
        }


# Global singleton instance
browser_automation = BrowserAutomationEngine()
