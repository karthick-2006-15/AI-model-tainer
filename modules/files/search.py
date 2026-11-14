"""
Hybrid Document Search Engine
Combines semantic vector search over document chunks with full-text keyword indexing.
"""

import logging
from typing import List, Dict, Any
from storage.db.connection import SessionLocal
from storage.db.models import IndexedFile
from core.memory.semantic import semantic_memory, LocalVectorEncoder
from modules.files.indexer import FileIndexer

logger = logging.getLogger("jarvis.files.search")


class FileSearchEngine:
    @staticmethod
    def search_documents(query: str, limit: int = 5, score_threshold: float = 0.20) -> List[Dict[str, Any]]:
        """
        Executes hybrid search across document chunks and relational metadata.
        Returns exact file paths, relevant excerpts, and confidence scores.
        """
        results: List[Dict[str, Any]] = []
        seen_files = set()

        # 1. Semantic Vector Search on Document Chunks
        try:
            query_vector = LocalVectorEncoder.encode(query)
            search_res = semantic_memory.client.query_points(
                collection_name=FileIndexer.CHUNKS_COLLECTION,
                query=query_vector,
                limit=limit * 2
            )

            for hit in search_res.points:
                score = getattr(hit, "score", 0.0)
                if score >= score_threshold:
                    payload = hit.payload or {}
                    file_path = payload.get("file_path")
                    if file_path:
                        results.append({
                            "file_name": payload.get("file_name"),
                            "file_path": file_path,
                            "match_snippet": payload.get("content", "")[:350],
                            "score": round(score, 3),
                            "match_type": "semantic_vector",
                            "chunk_index": payload.get("chunk_index", 0)
                        })
                        seen_files.add(file_path)
        except Exception as e:
            logger.warning(f"Semantic chunk search failed: {e}")

        # 2. Keyword & Filename Search in Relational Database
        with SessionLocal() as db:
            keyword_matches = (
                db.query(IndexedFile)
                .filter(
                    (IndexedFile.file_name.ilike(f"%{query}%")) |
                    (IndexedFile.summary.ilike(f"%{query}%"))
                )
                .limit(limit)
                .all()
            )

            for rec in keyword_matches:
                if rec.file_path not in seen_files:
                    results.append({
                        "file_name": rec.file_name,
                        "file_path": rec.file_path,
                        "match_snippet": rec.summary or "",
                        "score": 0.85,
                        "match_type": "keyword_exact",
                        "chunk_index": 0
                    })
                    seen_files.add(rec.file_path)

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


# Global singleton instance
file_search_engine = FileSearchEngine()
