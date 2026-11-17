"""
Intelligent File Management Engine
Provides recursive search, semantic search, categorization, duplicate detection,
metadata extraction, document summarization, preview-guarded organization,
format conversion, and integrity verification.
"""

import os
import re
import time
import shutil
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from modules.files.parsers import DocumentParser
from modules.files.indexer import file_indexer
from modules.automation.file_ops import FileOperationsManager
from core.security.permissions import permission_engine
from core.memory.semantic import semantic_memory

logger = logging.getLogger("jarvis.files.manager")


class IntelligentFileManager:
    """Unified controller for all intelligent file operations, analysis, and organization."""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # =========================================================================
    # RECURSIVE & SEMANTIC SEARCH
    # =========================================================================

    def search_files_recursive(
        self,
        query: str,
        root_dir: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Recursively searches directories for files matching query in name or path.
        Resolves well-known user folders (Downloads, Desktop, Documents, etc.),
        supports wildcard patterns (*.pdf), filters by extension, and excludes build/cache dirs.
        """
        import fnmatch

        user_home = os.path.expanduser("~")
        special_folders = {
            "downloads": [os.path.join(user_home, "Downloads"), os.path.join(user_home, "OneDrive", "Downloads")],
            "desktop": [os.path.join(user_home, "OneDrive", "Desktop"), os.path.join(user_home, "Desktop")],
            "documents": [os.path.join(user_home, "OneDrive", "Documents"), os.path.join(user_home, "Documents")],
            "pictures": [os.path.join(user_home, "Pictures"), os.path.join(user_home, "OneDrive", "Pictures")],
            "videos": [os.path.join(user_home, "Videos")],
            "music": [os.path.join(user_home, "Music")],
        }

        search_root = None
        if root_dir:
            cleaned = os.path.expandvars(os.path.expanduser(root_dir.strip())).strip("'\"")
            lower_name = cleaned.lower()
            if lower_name in special_folders:
                for candidate in special_folders[lower_name]:
                    if os.path.exists(candidate):
                        search_root = candidate
                        break
            if not search_root:
                if os.path.isabs(cleaned) and os.path.exists(cleaned):
                    search_root = cleaned
                else:
                    cand = os.path.abspath(cleaned)
                    if os.path.exists(cand):
                        search_root = cand

        if not search_root:
            search_root = self.project_root

        if not os.path.exists(search_root):
            return []

        q = (query or "").lower().strip()
        exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions] if extensions else None

        results = []
        ignore_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".pytest_cache"}

        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                file_lower = file.lower()
                _, ext = os.path.splitext(file)
                if exts and ext.lower() not in exts:
                    continue

                # Match wildcard query, extension, or substring
                matched = False
                if not q:
                    matched = True
                elif "*" in q or "?" in q:
                    matched = fnmatch.fnmatch(file_lower, q)
                else:
                    matched = (q in file_lower)

                if matched:
                    full_p = os.path.join(root, file)
                    try:
                        stat = os.stat(full_p)
                        results.append({
                            "file_name": file,
                            "path": full_p,
                            "size_bytes": stat.st_size,
                            "extension": ext.lower(),
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    except Exception:
                        continue

                    if len(results) >= max_results:
                        return results

        return results

    def semantic_search_files(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches indexed document chunks in semantic vector memory (Qdrant)."""
        from modules.files.search import semantic_file_searcher
        return semantic_file_searcher.search(query=query, limit=limit)

    # =========================================================================
    # METADATA EXTRACTION & INTEGRITY VERIFICATION
    # =========================================================================

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extracts complete file metadata: size, SHA-256, format, timestamps, word/page counts."""
        abs_p = os.path.abspath(file_path)
        if not os.path.exists(abs_p):
            return {"success": False, "error": f"File '{file_path}' not found."}

        stat = os.stat(abs_p)
        _, ext = os.path.splitext(abs_p)
        ext = ext.lower()

        # Compute SHA-256
        sha256_hash = file_indexer.compute_sha256(abs_p)

        # Document specific analysis if supported
        doc_analysis = {}
        if ext in (".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".csv", ".py", ".json", ".html"):
            parsed = DocumentParser.parse_file(abs_p, max_chars=10000)
            if parsed.get("success"):
                text = parsed.get("extracted_text", "")
                doc_analysis = {
                    "page_count": parsed.get("page_count", 1),
                    "character_count": len(text),
                    "word_count": len(text.split()),
                    "format": parsed.get("format", ext.replace(".", ""))
                }

        return {
            "success": True,
            "file_name": os.path.basename(abs_p),
            "file_path": abs_p,
            "size_bytes": stat.st_size,
            "format": ext.replace(".", "") or "unknown",
            "sha256": sha256_hash,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "document_info": doc_analysis
        }

    def verify_file_integrity(self, file_path: str, expected_hash: Optional[str] = None) -> Dict[str, Any]:
        """Validates file existence, non-empty status, and optional SHA-256 hash match."""
        meta = self.extract_metadata(file_path)
        if not meta["success"]:
            return meta

        current_hash = meta["sha256"]
        hash_matched = True if not expected_hash else (current_hash.lower() == expected_hash.lower())

        return {
            "success": True,
            "file_path": meta["file_path"],
            "file_name": meta["file_name"],
            "sha256": current_hash,
            "expected_hash": expected_hash,
            "hash_matched": hash_matched,
            "is_valid": meta["size_bytes"] > 0 and hash_matched,
            "message": "File integrity verified." if hash_matched else "Hash verification failed: content mismatch."
        }

    # =========================================================================
    # DOCUMENT SUMMARIZATION & ANALYSIS
    # =========================================================================

    def summarize_document(self, file_path: str, max_summary_chars: int = 500) -> Dict[str, Any]:
        """Parses a document (PDF, DOCX, PPTX, TXT) and generates an executive summary."""
        abs_p = os.path.abspath(file_path)
        parsed = DocumentParser.parse_file(abs_p, max_chars=30000)
        if not parsed.get("success"):
            return {"success": False, "error": parsed.get("error", "Failed to parse document.")}

        text = parsed.get("extracted_text", "").strip()
        if not text:
            return {"success": False, "error": "Document contains no readable text."}

        # Extract executive summary (first few paragraphs or key lines)
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
        summary_text = " ".join(paragraphs[:3])[:max_summary_chars]

        return {
            "success": True,
            "file_name": os.path.basename(abs_p),
            "format": parsed.get("format", "text"),
            "page_count": parsed.get("page_count", 1),
            "total_characters": len(text),
            "summary": summary_text,
            "key_excerpts": paragraphs[:4]
        }

    # =========================================================================
    # DUPLICATE DETECTION & CATEGORIZATION
    # =========================================================================

    def detect_duplicates(self, folder_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Finds exact duplicate files by hashing files with identical byte sizes.
        Does not require full pre-indexing in database.
        """
        scan_dir = os.path.abspath(folder_path) if folder_path else self.project_root
        size_map: Dict[int, List[str]] = {}

        # 1. Group by size
        for root, dirs, files in os.walk(scan_dir):
            if any(ign in root for ign in [".git", "node_modules", ".venv", "__pycache__"]):
                continue
            for f in files:
                full_p = os.path.join(root, f)
                try:
                    sz = os.path.getsize(full_p)
                    if sz > 0:
                        size_map.setdefault(sz, []).append(full_p)
                except Exception:
                    continue

        # 2. Hash only files that share identical sizes
        duplicates = []
        for sz, candidates in size_map.items():
            if len(candidates) < 2:
                continue

            hash_map: Dict[str, List[str]] = {}
            for path in candidates:
                try:
                    h = file_indexer.compute_sha256(path)
                    hash_map.setdefault(h, []).append(path)
                except Exception:
                    continue

            for h, paths in hash_map.items():
                if len(paths) > 1:
                    duplicates.append({
                        "content_hash": h,
                        "size_bytes": sz,
                        "count": len(paths),
                        "files": paths
                    })

        return duplicates

    def categorize_files(self, folder_path: str) -> Dict[str, List[str]]:
        """Classifies files in a folder into functional categories (Documents, Images, Archives, Code, Installers)."""
        norm_dir = os.path.abspath(folder_path)
        if not os.path.exists(norm_dir) or not os.path.isdir(norm_dir):
            return {}

        categories: Dict[str, List[str]] = {cat: [] for cat in FileOperationsManager.ORGANIZATION_MAP.keys()}
        categories["Other"] = []

        for item in os.listdir(norm_dir):
            full_p = os.path.join(norm_dir, item)
            if os.path.isdir(full_p):
                continue

            _, ext = os.path.splitext(item)
            ext = ext.lower()

            placed = False
            for cat, exts in FileOperationsManager.ORGANIZATION_MAP.items():
                if ext in exts:
                    categories[cat].append(item)
                    placed = True
                    break

            if not placed:
                categories["Other"].append(item)

        return categories

    # =========================================================================
    # PREVIEW-GUARDED FOLDER ORGANIZATION
    # =========================================================================

    def organize_folder_with_preview(self, folder_path: str, execute: bool = False) -> Dict[str, Any]:
        """
        Organizes a folder into categorized subdirectories.
        If execute=False: Generates a complete preview plan showing files to be moved, without touching disk.
        If execute=True: Performs the verified moves.
        """
        norm_dir = os.path.abspath(folder_path)
        if not os.path.exists(norm_dir) or not os.path.isdir(norm_dir):
            return {"success": False, "error": f"Folder '{folder_path}' does not exist."}

        categorized = self.categorize_files(norm_dir)
        planned_moves = []

        for cat, file_list in categorized.items():
            if cat == "Other" or not file_list:
                continue
            for fname in file_list:
                src = os.path.join(norm_dir, fname)
                dst = os.path.join(norm_dir, cat, fname)
                planned_moves.append({
                    "file_name": fname,
                    "category": cat,
                    "from_path": src,
                    "to_path": dst
                })

        if not execute:
            return {
                "success": True,
                "preview_mode": True,
                "folder": norm_dir,
                "total_files_to_move": len(planned_moves),
                "planned_moves": planned_moves,
                "message": f"Organization preview ready: {len(planned_moves)} files will be organized into category subfolders. Awaiting user confirmation to execute."
            }

        # Execution Mode
        executed_moves = []
        for move in planned_moves:
            src = move["from_path"]
            dst = move["to_path"]
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(src, dst)
                executed_moves.append(move)
            except Exception as e:
                logger.warning(f"Failed to move '{move['file_name']}': {e}")

        return {
            "success": True,
            "preview_mode": False,
            "folder": norm_dir,
            "moved_count": len(executed_moves),
            "executed_moves": executed_moves,
            "message": f"Successfully organized {len(executed_moves)} files."
        }

    # =========================================================================
    # FILE CONVERSION
    # =========================================================================

    def convert_file(self, source_path: str, target_format: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Converts files between text/markdown, DOCX, and other structured formats.
        """
        abs_src = os.path.abspath(source_path)
        if not os.path.exists(abs_src):
            return {"success": False, "error": f"Source file '{source_path}' does not exist."}

        _, src_ext = os.path.splitext(abs_src)
        src_ext = src_ext.lower().replace(".", "")
        tgt_fmt = target_format.lower().replace(".", "")

        if src_ext == tgt_fmt:
            return {"success": True, "file_path": abs_src, "message": "Source and target formats are identical."}

        # Conversion A: Markdown / TXT -> DOCX
        if src_ext in ("md", "txt", "markdown") and tgt_fmt == "docx":
            from modules.files.office_generator import office_generator
            with open(abs_src, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            title = os.path.splitext(os.path.basename(abs_src))[0].replace("_", " ").title()
            paragraphs = content.split("\n\n")
            sections = [{"heading": "Content", "content": p} for p in paragraphs if p.strip()]

            dest = output_path or abs_src.rsplit(".", 1)[0] + ".docx"
            res = office_generator.create_word_report(
                title=title,
                executive_summary=paragraphs[0] if paragraphs else "Converted Document",
                sections=sections,
                output_path=dest
            )
            return res

        # Conversion B: DOCX -> TXT / Markdown
        elif src_ext == "docx" and tgt_fmt in ("txt", "md"):
            parsed = DocumentParser.parse_file(abs_src)
            if not parsed.get("success"):
                return parsed

            dest = output_path or abs_src.rsplit(".", 1)[0] + f".{tgt_fmt}"
            with open(dest, "w", encoding="utf-8") as f:
                f.write(parsed.get("extracted_text", ""))

            return {
                "success": True,
                "file_path": dest,
                "format": tgt_fmt,
                "file_size_bytes": os.path.getsize(dest),
                "message": f"Converted DOCX to {tgt_fmt.upper()} successfully."
            }

        return {
            "success": False,
            "error": f"Conversion from '{src_ext}' to '{tgt_fmt}' is currently not supported."
        }


# Global singleton instance
intelligent_file_manager = IntelligentFileManager()
