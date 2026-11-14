"""
Multi-Source Research Synthesizer Engine
Conducts autonomous search, content extraction, and structured factual report generation with citations.
"""

import logging
from typing import Dict, Any, List
from modules.research.search import web_search_client
from modules.research.scraper import web_scraper
from core.providers.router import model_router
from core.memory.semantic import semantic_memory

logger = logging.getLogger("jarvis.research.synthesizer")


class ResearchSynthesizer:
    RESEARCH_PROMPT_TEMPLATE = """You are JARVIS. Synthesize an objective, high-density research report based strictly on the retrieved sources below.

Topic: "{topic}"

Retrieved Source Data:
{sources_text}

### Instructions:
1. Provide an Executive Summary.
2. Outline Key Findings with bullet points.
3. Include a "Sources & References" section with URLs.
4. Do not state unverified assumptions as established facts.
"""

    async def conduct_research(
        self,
        topic: str,
        max_sources: int = 3
    ) -> Dict[str, Any]:
        """
        Executes multi-source research workflow:
        Search -> Scrape Top Sources -> Synthesize Factual Brief -> Index in Semantic Memory.
        """
        logger.info(f"Starting autonomous research workflow for: '{topic}'")

        # 1. Search Web
        search_results = await web_search_client.search(topic, max_results=max_sources)
        if not search_results:
            return {
                "success": False,
                "error": "No search results found.",
                "topic": topic
            }

        # 2. Scrape Top Pages
        sources_data = []
        for res in search_results[:max_sources]:
            url = res["url"]
            scrape_res = await web_scraper.scrape_url(url, max_chars=4000)
            if scrape_res["success"]:
                sources_data.append({
                    "title": scrape_res["title"],
                    "url": url,
                    "text": scrape_res["raw_text"]
                })
            else:
                sources_data.append({
                    "title": res["title"],
                    "url": url,
                    "text": res.get("raw_snippet", "")
                })

        # 3. Assemble Source Blocks
        sources_text = ""
        for i, s in enumerate(sources_data):
            sources_text += f"\n--- SOURCE {i+1}: {s['title']} ({s['url']}) ---\n{s['text'][:2000]}\n"

        prompt = self.RESEARCH_PROMPT_TEMPLATE.format(topic=topic, sources_text=sources_text)

        # 4. Synthesize with LLM
        provider = model_router.get_provider()
        try:
            llm_response = await provider.generate([
                {"role": "system", "content": "You are JARVIS, an articulate research synthesis assistant."},
                {"role": "user", "content": prompt}
            ])
            report_text = llm_response.content
        except Exception as e:
            logger.warning(f"Synthesis LLM error: {e}. Generating structured heuristic report.")
            report_text = f"# Research Brief: {topic}\n\n## Sources Found:\n" + "\n".join(
                f"- [{s['title']}]({s['url']})" for s in sources_data
            )

        # 5. Index Findings into Semantic Memory
        semantic_memory.upsert_memory(
            memory_id=f"research_{abs(hash(topic))}",
            text=f"Research on {topic}: {report_text[:600]}",
            category="research",
            metadata={"topic": topic, "sources_count": len(sources_data)}
        )

        return {
            "success": True,
            "topic": topic,
            "sources_count": len(sources_data),
            "sources": [{"title": s["title"], "url": s["url"]} for s in sources_data],
            "report_markdown": report_text
        }


# Global singleton instance
research_synthesizer = ResearchSynthesizer()
