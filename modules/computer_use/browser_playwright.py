"""
JARVIS Universal Playwright Browser Automation Controller
Coordinates Chrome, Edge, and Chromium browser instances with multi-tab support,
DOM inspection, resilient element locating, form filling, text extraction, and visual capture.
"""

import os
import time
import logging
import datetime
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page, Locator
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.computer_use.playwright")


class PlaywrightBrowserController:
    """Universal browser control engine powered by Playwright."""

    def __init__(self, headless: bool = True, storage_dir: str = "storage/media/browser_captures"):
        self.headless = headless
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._pages: List[Page] = []
        self._active_page_index: int = 0

    def _ensure_browser(self):
        """Initializes Playwright browser instance if not already running."""
        if permission_engine.is_emergency_stopped():
            raise RuntimeError("Emergency stop active. Browser operation aborted.")

        if self._playwright is None:
            self._playwright = sync_playwright().start()

        if self._browser is None or not self._browser.is_connected():
            try:
                # Attempt to launch bundled Chromium
                self._browser = self._playwright.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
            except Exception as e:
                logger.warning(f"Chromium launch note: {e}. Attempting msedge channel...")
                self._browser = self._playwright.chromium.launch(
                    channel="msedge",
                    headless=self.headless
                )

            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 JARVIS/10.0"
            )
            # Create primary page
            page = self._context.new_page()
            self._pages = [page]
            self._active_page_index = 0

    @property
    def current_page(self) -> Page:
        self._ensure_browser()
        if not self._pages or self._active_page_index >= len(self._pages):
            page = self._context.new_page()
            self._pages.append(page)
            self._active_page_index = len(self._pages) - 1
        return self._pages[self._active_page_index]

    def open(self, url: str) -> Dict[str, Any]:
        """Navigates the active tab to the specified URL."""
        if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("about:"):
            url = f"https://{url}"

        try:
            page = self.current_page
            logger.info(f"Navigating browser to: {url}")
            response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            status = response.status if response else 200

            title = page.title()
            return {
                "success": True,
                "url": page.url,
                "title": title,
                "status_code": status,
                "tab_count": len(self._pages)
            }
        except Exception as e:
            logger.error(f"Failed to open URL '{url}': {e}")
            return {"success": False, "url": url, "error": str(e)}

    def inspect(self, selector: Optional[str] = None) -> Dict[str, Any]:
        """Inspects page structure, active elements, inputs, buttons, and links."""
        try:
            page = self.current_page
            title = page.title()
            url = page.url

            # Extract inputs
            inputs_data = page.evaluate("""() => {
                const results = [];
                const inputs = document.querySelectorAll('input, textarea, select');
                for (let i = 0; i < Math.min(inputs.length, 25); i++) {
                    const el = inputs[i];
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        name: el.name || '',
                        type: el.type || '',
                        placeholder: el.placeholder || '',
                        value: (el.type !== 'password' ? el.value : '[HIDDEN]'),
                        aria_label: el.getAttribute('aria-label') || ''
                    });
                }
                return results;
            }""")

            # Extract buttons
            buttons_data = page.evaluate("""() => {
                const results = [];
                const buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]');
                for (let i = 0; i < Math.min(buttons.length, 20); i++) {
                    const btn = buttons[i];
                    const text = btn.innerText || btn.value || btn.getAttribute('aria-label') || '';
                    if (text.trim()) {
                        results.push(text.trim());
                    }
                }
                return results;
            }""")

            # Extract links
            links_data = page.evaluate("""() => {
                const results = [];
                const links = document.querySelectorAll('a[href]');
                for (let i = 0; i < Math.min(links.length, 15); i++) {
                    const a = links[i];
                    const text = (a.innerText || a.getAttribute('aria-label') || '').trim();
                    if (text && !a.href.startsWith('javascript:')) {
                        results.push({ text: text, href: a.href });
                    }
                }
                return results;
            }""")

            # Headings
            headings = page.evaluate("""() => {
                const headers = Array.from(document.querySelectorAll('h1, h2, h3')).slice(0, 10);
                return headers.map(h => h.innerText.trim()).filter(t => t.length > 0);
            }""")

            return {
                "success": True,
                "url": url,
                "title": title,
                "headings": headings,
                "inputs": inputs_data,
                "buttons": buttons_data,
                "links": links_data
            }
        except Exception as e:
            logger.error(f"Error inspecting page: {e}")
            return {"success": False, "error": str(e)}

    def search(self, query: str, engine: str = "google") -> Dict[str, Any]:
        """Executes a search query in Google, YouTube, or DuckDuckGo."""
        engine_lower = engine.lower()
        if "youtube" in engine_lower:
            url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        elif "duckduckgo" in engine_lower:
            url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
        else:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

        return self.open(url)

    def click(self, selector_or_text: str) -> Dict[str, Any]:
        """Clicks an element by CSS selector, text content, or accessibility label."""
        page = self.current_page
        try:
            # 1. Try direct selector
            locator = page.locator(selector_or_text)
            if locator.count() > 0 and locator.first.is_visible():
                locator.first.click(timeout=5000)
                return {"success": True, "target": selector_or_text, "method": "css_selector"}

            # 2. Try text matching
            text_locator = page.get_by_text(selector_or_text, exact=False)
            if text_locator.count() > 0 and text_locator.first.is_visible():
                text_locator.first.click(timeout=5000)
                return {"success": True, "target": selector_or_text, "method": "text_match"}

            # 3. Try role button/link matching
            btn_locator = page.get_by_role("button", name=selector_or_text)
            if btn_locator.count() > 0 and btn_locator.first.is_visible():
                btn_locator.first.click(timeout=5000)
                return {"success": True, "target": selector_or_text, "method": "role_button"}

            # Fallback evaluate click
            clicked = page.evaluate(f"""() => {{
                const els = Array.from(document.querySelectorAll('button, a, input, div, span'));
                const target = els.find(el => (el.innerText || el.value || '').toLowerCase().includes('{selector_or_text.lower()}'));
                if (target) {{
                    target.click();
                    return true;
                }}
                return false;
            }}""")

            if clicked:
                return {"success": True, "target": selector_or_text, "method": "dom_eval_click"}

            return {"success": False, "error": f"Element '{selector_or_text}' not found or not clickable."}
        except Exception as e:
            logger.error(f"Click failed on '{selector_or_text}': {e}")
            return {"success": False, "target": selector_or_text, "error": str(e)}

    def fill(self, selector_or_name: str, value: str) -> Dict[str, Any]:
        """Fills an input, textarea, or contenteditable field with text."""
        page = self.current_page
        try:
            # Try direct CSS
            loc = page.locator(selector_or_name)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.fill(value, timeout=5000)
                return {"success": True, "field": selector_or_name, "value": value}

            # Try by placeholder
            loc_ph = page.get_by_placeholder(selector_or_name)
            if loc_ph.count() > 0 and loc_ph.first.is_visible():
                loc_ph.first.fill(value, timeout=5000)
                return {"success": True, "field": selector_or_name, "value": value}

            # Try by label
            loc_label = page.get_by_label(selector_or_name)
            if loc_label.count() > 0 and loc_label.first.is_visible():
                loc_label.first.fill(value, timeout=5000)
                return {"success": True, "field": selector_or_name, "value": value}

            # Fallback DOM evaluation
            filled = page.evaluate(f"""() => {{
                const inputs = Array.from(document.querySelectorAll('input, textarea'));
                const target = inputs.find(el => 
                    (el.name && el.name.toLowerCase() === '{selector_or_name.lower()}') ||
                    (el.id && el.id.toLowerCase() === '{selector_or_name.lower()}') ||
                    (el.placeholder && el.placeholder.toLowerCase().includes('{selector_or_name.lower()}'))
                );
                if (target) {{
                    target.value = '{value}';
                    target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            }}""")

            if filled:
                return {"success": True, "field": selector_or_name, "value": value, "method": "dom_eval"}

            return {"success": False, "error": f"Input field '{selector_or_name}' not found."}
        except Exception as e:
            logger.error(f"Fill failed on '{selector_or_name}': {e}")
            return {"success": False, "field": selector_or_name, "error": str(e)}

    def extract_text(self, selector: Optional[str] = None) -> Dict[str, Any]:
        """Extracts clean inner text or markdown content from the page or selector."""
        page = self.current_page
        try:
            if selector:
                loc = page.locator(selector)
                if loc.count() > 0:
                    text = loc.first.inner_text(timeout=4000)
                    return {"success": True, "selector": selector, "text": text.strip(), "char_count": len(text)}

            # Page-wide clean text extraction
            text = page.evaluate("""() => {
                const article = document.querySelector('article, main, #content, .content');
                if (article) return article.innerText;
                return document.body ? document.body.innerText : '';
            }""")
            return {
                "success": True,
                "url": page.url,
                "title": page.title(),
                "text": text.strip(),
                "char_count": len(text)
            }
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return {"success": False, "error": str(e)}

    def get_tabs(self) -> List[Dict[str, Any]]:
        """Lists all open tabs in the browser context."""
        self._ensure_browser()
        tabs: List[Dict[str, Any]] = []
        for idx, p in enumerate(self._pages):
            try:
                tabs.append({
                    "tab_index": idx,
                    "is_active": (idx == self._active_page_index),
                    "title": p.title(),
                    "url": p.url
                })
            except Exception:
                pass
        return tabs

    def switch_tab(self, index: int) -> Dict[str, Any]:
        """Switches the active tab by index."""
        self._ensure_browser()
        if 0 <= index < len(self._pages):
            self._active_page_index = index
            self._pages[index].bring_to_front()
            return {
                "success": True,
                "active_tab": index,
                "title": self._pages[index].title(),
                "url": self._pages[index].url
            }
        return {"success": False, "error": f"Tab index {index} out of range (0..{len(self._pages)-1})."}

    def new_tab(self, url: str = "about:blank") -> Dict[str, Any]:
        """Creates a new browser tab and navigates to the given URL."""
        self._ensure_browser()
        page = self._context.new_page()
        self._pages.append(page)
        self._active_page_index = len(self._pages) - 1
        if url != "about:blank":
            return self.open(url)
        return {"success": True, "tab_index": self._active_page_index, "url": url}

    def close_tab(self, index: Optional[int] = None) -> Dict[str, Any]:
        """Closes a tab by index, or the active tab if None."""
        self._ensure_browser()
        target_idx = self._active_page_index if index is None else index
        if 0 <= target_idx < len(self._pages):
            p = self._pages.pop(target_idx)
            try:
                p.close()
            except Exception:
                pass

            if not self._pages:
                new_p = self._context.new_page()
                self._pages = [new_p]
                self._active_page_index = 0
            else:
                self._active_page_index = max(0, min(self._active_page_index, len(self._pages) - 1))

            return {"success": True, "closed_tab": target_idx, "remaining_tabs": len(self._pages)}
        return {"success": False, "error": f"Invalid tab index: {target_idx}"}

    def screenshot(self, output_path: Optional[str] = None, full_page: bool = False) -> Dict[str, Any]:
        """Captures a screenshot of the active page."""
        page = self.current_page
        if not output_path:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_path = os.path.join(self.storage_dir, f"browser_{timestamp}.png")

        try:
            page.screenshot(path=output_path, full_page=full_page)
            return {
                "success": True,
                "file_path": output_path,
                "url": page.url,
                "title": page.title()
            }
        except Exception as e:
            logger.error(f"Browser screenshot failed: {e}")
            return {"success": False, "error": str(e)}

    def scroll(self, direction: str = "down", amount: int = 500) -> Dict[str, Any]:
        """Scrolls the active webpage."""
        page = self.current_page
        delta = amount if direction.lower() == "down" else -amount
        try:
            page.evaluate(f"window.scrollBy(0, {delta});")
            return {"success": True, "direction": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def detect_bot_challenges(self) -> Dict[str, Any]:
        """
        Detects bot verification gates (Cloudflare Turnstile, Google reCAPTCHA, hCaptcha, Arkose).
        Crucial Safety Rule: Never attempts to solve, click through, or bypass a CAPTCHA.
        Reports presence to user for human verification.
        """
        page = self.current_page
        try:
            detected_types = []
            
            # 1. Cloudflare Turnstile / Challenge
            has_cf = page.evaluate("""() => {
                return !!(
                    document.querySelector('iframe[src*="challenges.cloudflare.com"]') ||
                    document.querySelector('#cf-challenge-running') ||
                    document.querySelector('.cf-turnstile') ||
                    document.querySelector('[id*="cf-turnstile"]') ||
                    (document.title && document.title.includes('Just a moment...'))
                );
            }""")
            if has_cf:
                detected_types.append("Cloudflare Turnstile / Challenge")

            # 2. Google reCAPTCHA
            has_recaptcha = page.evaluate("""() => {
                return !!(
                    document.querySelector('iframe[src*="google.com/recaptcha"]') ||
                    document.querySelector('iframe[src*="recaptcha.net"]') ||
                    document.querySelector('.g-recaptcha') ||
                    document.querySelector('[id*="recaptcha"]')
                );
            }""")
            if has_recaptcha:
                detected_types.append("Google reCAPTCHA")

            # 3. hCaptcha
            has_hcaptcha = page.evaluate("""() => {
                return !!(
                    document.querySelector('iframe[src*="hcaptcha.com"]') ||
                    document.querySelector('.h-captcha') ||
                    document.querySelector('[id*="hcaptcha"]')
                );
            }""")
            if has_hcaptcha:
                detected_types.append("hCaptcha")

            if detected_types:
                challenge_name = ", ".join(detected_types)
                logger.warning(f"Bot verification challenge detected on page '{page.url}': {challenge_name}")
                return {
                    "detected": True,
                    "challenge_types": detected_types,
                    "url": page.url,
                    "action_required": "USER_MANUAL_VERIFICATION",
                    "message": f"A bot verification challenge ({challenge_name}) was detected on this webpage. In accordance with safety policies, automated bypass is prohibited. Please solve the challenge directly in your browser."
                }

            return {"detected": False, "challenge_types": [], "url": page.url}
        except Exception as e:
            logger.debug(f"Error checking bot challenges: {e}")
            return {"detected": False, "error": str(e), "url": getattr(page, "url", "")}

    def close(self):
        """Cleanly closes browser context and stops Playwright."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self._context = None
            self._browser = None
            self._playwright = None
            self._pages.clear()
            self._active_page_index = 0


# Global singleton instance
playwright_controller = PlaywrightBrowserController(headless=True)
