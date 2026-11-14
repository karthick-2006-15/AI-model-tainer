"""
Privacy-Preserving Web Search Client
Queries DuckDuckGo HTML / JSON endpoints without requiring subscription API keys.
"""

import httpx
import re
import urllib.parse
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from modules.research.sanitizer import content_sanitizer

logger = logging.getLogger("jarvis.research.search")


class WebSearchClient:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Conducts an async privacy-preserving web search using DuckDuckGo.
        Returns a list of structured results: title, url, snippet.
        """
        logger.info(f"Conducting web search for: '{query}'")
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9"
        }

        results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            result_elements = soup.find_all("div", class_="result")

            for elem in result_elements:
                title_elem = elem.find("a", class_="result__a")
                snippet_elem = elem.find("a", class_="result__snippet")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                raw_href = title_elem.get("href", "")
                
                # DuckDuckGo wraps target URLs in /l/?uddg=...
                actual_url = raw_href
                if "uddg=" in raw_href:
                    match = re.search(r"uddg=([^&]+)", raw_href)
                    if match:
                        actual_url = urllib.parse.unquote(match.group(1))

                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                if title and actual_url and actual_url.startswith("http"):
                    results.append({
                        "title": title,
                        "url": actual_url,
                        "snippet": content_sanitizer.sanitize_untrusted_text(snippet, source=actual_url, max_chars=300),
                        "raw_snippet": snippet
                    })

                if len(results) >= max_results:
                    break

        except Exception as e:
            logger.warning(f"DuckDuckGo search error: {e}")
            # Fallback mock search for offline / restricted environments
            results.append({
                "title": f"Search Results for: {query}",
                "url": f"https://duckduckgo.com/?q={encoded_query}",
                "snippet": content_sanitizer.sanitize_untrusted_text(f"Search query: {query}", source="fallback"),
                "raw_snippet": f"Search query: {query}"
            })

        return results


# Global singleton instance
web_search_client = WebSearchClient()
