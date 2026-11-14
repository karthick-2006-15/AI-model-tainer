"""
Web Page Scraper & Content Extractor
Fetches full web pages and extracts readable text, stripping boilerplate and ads.
"""

import httpx
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any
from modules.research.sanitizer import content_sanitizer

logger = logging.getLogger("jarvis.research.scraper")


class WebScraper:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    async def scrape_url(self, url: str, max_chars: int = 10000) -> Dict[str, Any]:
        """
        Fetches and extracts clean readable article content from a web page URL.
        """
        logger.info(f"Scraping web page: '{url}'")
        headers = {"User-Agent": self.USER_AGENT}

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove navigation, styles, scripts, and footers
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg"]):
                tag.decompose()

            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else url

            # Extract text from main container or paragraphs
            main_elem = soup.find("main") or soup.find("article") or soup.body
            if main_elem:
                paragraphs = [p.get_text(strip=True) for p in main_elem.find_all(["p", "h1", "h2", "h3", "li"])]
                raw_text = "\n\n".join(p for p in paragraphs if len(p) > 20)
            else:
                raw_text = soup.get_text(separator="\n", strip=True)

            sanitized_content = content_sanitizer.sanitize_untrusted_text(
                raw_text,
                source=url,
                max_chars=max_chars
            )

            return {
                "success": True,
                "url": url,
                "title": title,
                "char_count": len(raw_text),
                "sanitized_content": sanitized_content,
                "raw_text": raw_text[:max_chars]
            }

        except Exception as e:
            logger.error(f"Failed to scrape '{url}': {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }


# Global singleton instance
web_scraper = WebScraper()
