"""
File Indexer, Hasher & Semantic Chunking Engine
Maintains SHA-256 duplicate identification and semantic vector chunking in Qdrant.
"""

import os
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from storage.db.connection import SessionLocal
from storage.db.models import IndexedFile
from modules.files.parsers import DocumentParser
from core.memory.semantic import semantic_memory, LocalVectorEncoder, VECTOR_DIM
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger("jarvis.files.indexer")


class FileIndexer:
    CHUNKS_COLLECTION = "file_chunks"
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx",
        ".txt", ".md", ".csv", ".py", ".ts", ".js", ".json", ".html", ".cpp"
    }

    def __init__(self):
        self._ensure_chunks_collection()

    def _ensure_chunks_collection(self):
        """Initializes the file_chunks vector collection in Qdrant."""
        try:
            if not semantic_memory.client.collection_exists(self.CHUNKS_COLLECTION):
                semantic_memory.client.create_collection(
                    collection_name=self.CHUNKS_COLLECTION,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
                )
                logger.info(f"Initialized Qdrant collection: {self.CHUNKS_COLLECTION}")
        except Exception as e:
            logger.warning(f"File chunks collection check: {e}")

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Computes SHA-256 hash of a file for duplicate detection."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 600, overlap: int = 60) -> List[str]:
        """Splits long document text into overlapping chunks for semantic retrieval."""
        if not text:
            return []
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - overlap

        return chunks

    def index_single_file(self, file_path: str) -> Dict[str, Any]:
        """Parses, hashes, records in SQLite, and chunks into vector memory."""
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path) or os.path.isdir(abs_path):
            return {"success": False, "error": "Invalid file path."}

        _, ext = os.path.splitext(abs_path)
        if ext.lower() not in self.SUPPORTED_EXTENSIONS:
            return {"success": False, "error": f"Unsupported extension: {ext}"}

        stat = os.stat(abs_path)
        content_hash = self.compute_sha256(abs_path)
        file_name = os.path.basename(abs_path)

        # 1. Parse Document Text
        parsed = DocumentParser.parse_file(abs_path)
        extracted_text = parsed.get("extracted_text", "")
        summary = extracted_text[:250].replace("\n", " ").strip() if extracted_text else ""

        # 2. Record in Relational Database
        with SessionLocal() as db:
            record = db.query(IndexedFile).filter(IndexedFile.file_path == abs_path).first()
            if record:
                record.file_size_bytes = stat.st_size
                record.content_hash = content_hash
                record.last_modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                record.summary = summary
                record.is_indexed_in_vector = True
                db.commit()
                db.refresh(record)
                file_id = record.id
            else:
                record = IndexedFile(
                    file_path=abs_path,
                    file_name=file_name,
                    file_extension=ext.lower(),
                    file_size_bytes=stat.st_size,
                    content_hash=content_hash,
                    last_modified=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                    summary=summary,
                    is_indexed_in_vector=True
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                file_id = record.id

        # 3. Chunk Text & Embed into Qdrant
        chunks = self.chunk_text(extracted_text)
        points = []
        for i, chunk in enumerate(chunks):
            chunk_vector = LocalVectorEncoder.encode(chunk)
            chunk_id_str = f"{file_id}_chunk_{i}"
            point_id = int(hashlib.md5(chunk_id_str.encode("utf-8")).hexdigest()[:15], 16)

            points.append(PointStruct(
                id=point_id,
                vector=chunk_vector,
                payload={
                    "file_id": file_id,
                    "file_path": abs_path,
                    "file_name": file_name,
                    "chunk_index": i,
                    "content": chunk,
                    "extension": ext.lower()
                }
            ))

        if points:
            try:
                semantic_memory.client.upsert(
                    collection_name=self.CHUNKS_COLLECTION,
                    points=points
                )
                logger.info(f"Indexed {len(points)} chunks for '{file_name}'")
            except Exception as e:
                logger.error(f"Failed to upsert chunks into Qdrant: {e}")

        return {
            "success": True,
            "file_id": file_id,
            "file_name": file_name,
            "chunks_count": len(chunks),
            "content_hash": content_hash
        }

    def scan_and_index_directory(self, folder_path: str, max_files: int = 50) -> Dict[str, Any]:
        """Recursively scans and indexes supported files in an authorized directory."""
        norm_folder = os.path.abspath(os.path.expanduser(folder_path))
        if not os.path.exists(norm_folder) or not os.path.isdir(norm_folder):
            return {"success": False, "error": f"Directory '{folder_path}' does not exist."}

        indexed = []
        for root, _, files in os.walk(norm_folder):
            if any(ign in root for ign in [".git", "node_modules", ".venv", "__pycache__", "dist"]):
                continue
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in self.SUPPORTED_EXTENSIONS:
                    full_p = os.path.join(root, file)
                    res = self.index_single_file(full_p)
                    if res["success"]:
                        indexed.append(res)
                    if len(indexed) >= max_files:
                        break
            if len(indexed) >= max_files:
                break

        return {
            "success": True,
            "folder": norm_folder,
            "indexed_count": len(indexed),
            "files": indexed
        }

    @staticmethod
    def find_duplicate_files() -> List[Dict[str, Any]]:
        """Finds all duplicate files across indexed paths by matching content SHA-256 hashes."""
        duplicates = []
        with SessionLocal() as db:
            from sqlalchemy import func, select
            subq = (
                select(IndexedFile.content_hash)
                .group_by(IndexedFile.content_hash)
                .having(func.count(IndexedFile.id) > 1)
                .scalar_subquery()
            )
            dupe_records = db.query(IndexedFile).filter(IndexedFile.content_hash.in_(subq)).all()

            # Group by hash
            by_hash: Dict[str, List[IndexedFile]] = {}
            for rec in dupe_records:
                by_hash.setdefault(rec.content_hash, []).append(rec)

            for h, recs in by_hash.items():
                duplicates.append({
                    "content_hash": h,
                    "count": len(recs),
                    "files": [r.file_path for r in recs],
                    "file_name": recs[0].file_name
                })

        return duplicates


# Global singleton instance
file_indexer = FileIndexer()
