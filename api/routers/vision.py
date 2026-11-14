"""
Computer Vision & Screen Intelligence REST Endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from modules.vision.capture import screen_capture_manager
from modules.vision.analyzer import vision_engine

router = APIRouter(prefix="/api/vision", tags=["Computer Vision"])


class ExplainScreenRequest(BaseModel):
    focus_area: Optional[str] = "Full Screen"
    prompt_override: Optional[str] = ""


class AnalyzeImageRequest(BaseModel):
    image_path: str
    query: Optional[str] = "Explain this image and its technical components."


@router.post("/capture")
async def capture_screen_endpoint():
    """Captures a screenshot of the primary Windows desktop."""
    res = screen_capture_manager.capture_screen()
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res


@router.post("/explain-screen")
async def explain_screen_endpoint(request: ExplainScreenRequest):
    """Captures desktop screen and synthesizes an intelligent explanation of visible errors or states."""
    res = await vision_engine.explain_screen(
        focus_area=request.focus_area or "Full Screen",
        prompt_override=request.prompt_override or ""
    )
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res


@router.post("/analyze-image")
async def analyze_image_endpoint(request: AnalyzeImageRequest):
    """Analyzes a technical diagram or screenshot image file from disk."""
    res = await vision_engine.analyze_image_file(
        image_path=request.image_path,
        query=request.query or "Explain this image"
    )
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res
