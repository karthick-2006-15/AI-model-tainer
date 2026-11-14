"""
Personal Memory REST Endpoints
Provides full inspection, search, addition, update, and deletion of user memory entities.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from core.memory.profile import profile_memory
from core.memory.semantic import semantic_memory

router = APIRouter(prefix="/api/memory", tags=["Memory"])


class AddFactRequest(BaseModel):
    key_name: str
    category: str = Field(default="general")
    value_data: Any
    confidence_score: Optional[float] = 1.0
    provenance: Optional[str] = "user_explicit"


class FactResponse(BaseModel):
    id: str
    key_name: str
    category: str
    value_data: Any
    confidence_score: float
    provenance: str


class SearchMemoryResponse(BaseModel):
    results: List[Dict[str, Any]]


class ExtractRequest(BaseModel):
    text: str


@router.get("/entities", response_model=List[FactResponse])
def list_entities(category: Optional[str] = None):
    """Lists all stored memory entities, optionally filtered by category."""
    facts = profile_memory.list_facts(category=category)
    return [
        FactResponse(
            id=f["id"],
            key_name=f["key_name"],
            category=f["category"],
            value_data=f["value_data"],
            confidence_score=f["confidence_score"],
            provenance=f["provenance"]
        )
        for f in facts
    ]


@router.post("/entities", response_model=FactResponse)
def add_entity(request: AddFactRequest):
    """Adds or updates a personal fact in memory."""
    if not request.key_name.strip():
        raise HTTPException(status_code=400, detail="key_name cannot be empty.")

    fact = profile_memory.add_or_update_fact(
        key_name=request.key_name.strip(),
        category=request.category,
        value_data=request.value_data,
        confidence_score=request.confidence_score or 1.0,
        provenance=request.provenance or "user_explicit"
    )
    return FactResponse(
        id=fact["id"],
        key_name=fact["key_name"],
        category=fact["category"],
        value_data=fact["value_data"],
        confidence_score=fact["confidence_score"],
        provenance=fact["provenance"]
    )


@router.delete("/entities/{entity_id}")
def delete_entity(entity_id: str):
    """Deletes/forgets a specific memory entity permanently."""
    success = profile_memory.delete_fact(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found.")
    return {"deleted": True, "id": entity_id}


@router.get("/search", response_model=SearchMemoryResponse)
def search_memory(q: str = Query(..., min_length=1), limit: int = 5):
    """Performs semantic similarity search across personal memory vectors."""
    results = semantic_memory.search_memory(query=q, limit=limit)
    return SearchMemoryResponse(results=results)


@router.post("/extract")
def extract_facts(request: ExtractRequest):
    """Extracts facts from natural language text and updates memory."""
    extracted = profile_memory.auto_extract_facts_from_text(request.text)
    return {"extracted_count": len(extracted), "facts": extracted}
