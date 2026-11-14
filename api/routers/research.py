"""
Internet Intelligence & Research REST Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from modules.research.search import web_search_client
from modules.research.scraper import web_scraper
from modules.research.synthesizer import research_synthesizer

router = APIRouter(prefix="/api/research", tags=["Research"])


class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5


class ScrapeRequest(BaseModel):
    url: str
    max_chars: Optional[int] = 10000


class ResearchReportRequest(BaseModel):
    topic: str
    max_sources: Optional[int] = 3


@router.post("/search")
async def execute_web_search(request: SearchRequest):
    """Executes a privacy-preserving web search via DuckDuckGo."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    results = await web_search_client.search(request.query, max_results=request.max_results or 5)
    return {"query": request.query, "count": len(results), "results": results}


@router.post("/scrape")
async def scrape_web_page(request: ScrapeRequest):
    """Scrapes clean article content from a web page and sanitizes output."""
    if not request.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme (must start with http/https).")
    res = await web_scraper.scrape_url(request.url, max_chars=request.max_chars or 10000)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res


@router.post("/report")
async def generate_research_report(request: ResearchReportRequest):
    """Autonomous multi-source research workflow with factual synthesis and source citations."""
    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")
    report = await research_synthesizer.conduct_research(request.topic, max_sources=request.max_sources or 3)
    if not report["success"]:
        raise HTTPException(status_code=500, detail=report.get("error"))
    return report
