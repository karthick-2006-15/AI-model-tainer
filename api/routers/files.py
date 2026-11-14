"""
File Intelligence & Semantic Document Search REST Endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from storage.db.connection import SessionLocal
from storage.db.models import IndexedFile
from modules.files.indexer import file_indexer
from modules.files.search import file_search_engine
from modules.files.parsers import DocumentParser

router = APIRouter(prefix="/api/files", tags=["Files"])


class IndexPathRequest(BaseModel):
    path: str
    max_files: Optional[int] = 50


class ParseFileRequest(BaseModel):
    file_path: str


@router.get("/indexed")
def list_indexed_files(limit: int = 50, extension: Optional[str] = None):
    """Lists indexed files with metadata, summaries, and SHA-256 hashes."""
    with SessionLocal() as db:
        query = db.query(IndexedFile)
        if extension:
            query = query.filter(IndexedFile.file_extension == extension.lower())
        files = query.order_by(IndexedFile.indexed_at.desc()).limit(limit).all()
        return [
            {
                "id": f.id,
                "file_name": f.file_name,
                "file_path": f.file_path,
                "file_extension": f.file_extension,
                "file_size_bytes": f.file_size_bytes,
                "content_hash": f.content_hash,
                "summary": f.summary,
                "indexed_at": f.indexed_at.isoformat()
            }
            for f in files
        ]


@router.post("/index-path")
def index_path(request: IndexPathRequest):
    """Indexes a single file or an entire directory into relational and vector stores."""
    import os
    if os.path.isdir(request.path):
        return file_indexer.scan_and_index_directory(request.path, max_files=request.max_files or 50)
    elif os.path.isfile(request.path):
        res = file_indexer.index_single_file(request.path)
        if not res["success"]:
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    else:
        raise HTTPException(status_code=404, detail="Path not found.")


@router.get("/search")
def search_files(q: str = Query(..., min_length=1), limit: int = 5):
    """Hybrid semantic vector and full-text search across all indexed documents."""
    results = file_search_engine.search_documents(query=q, limit=limit)
    return {"query": q, "count": len(results), "results": results}


@router.get("/duplicates")
def get_duplicate_files():
    """Identifies identical files with matching SHA-256 hashes."""
    duplicates = file_indexer.find_duplicate_files()
    return {"duplicate_groups_count": len(duplicates), "duplicates": duplicates}


@router.post("/parse")
def parse_document(request: ParseFileRequest):
    """Extracts text, page count, and structure from a supported document."""
    res = DocumentParser.parse_file(request.file_path)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res
