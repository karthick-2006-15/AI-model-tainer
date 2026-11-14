"""
Unit tests for Multimodal File Intelligence, Document Parsing, Indexing & Semantic Search
"""

import pytest
import os
import shutil
import tempfile
import docx
import openpyxl
from starlette.testclient import TestClient
from api.main import app
from modules.files.parsers import DocumentParser
from modules.files.indexer import file_indexer
from modules.files.search import file_search_engine


def test_document_parsers():
    temp_dir = tempfile.mkdtemp(prefix="jarvis_test_parsers_")
    try:
        # 1. Text / Code Parser
        txt_path = os.path.join(temp_dir, "notes.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Dijkstra algorithm computes the shortest path between nodes in a graph.")
        res_txt = DocumentParser.parse_file(txt_path)
        assert res_txt["success"] is True
        assert "Dijkstra" in res_txt["extracted_text"]

        # 2. DOCX Parser
        docx_path = os.path.join(temp_dir, "report.docx")
        doc = docx.Document()
        doc.add_heading("Warehouse AI Project Overview", 0)
        doc.add_paragraph("Autonomous pathfinding implemented with A* search.")
        doc.save(docx_path)
        res_docx = DocumentParser.parse_file(docx_path)
        assert res_docx["success"] is True
        assert "Warehouse AI" in res_docx["extracted_text"]

        # 3. XLSX Parser
        xlsx_path = os.path.join(temp_dir, "data.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Metrics"
        ws.append(["Metric", "Value"])
        ws.append(["Latency", "12ms"])
        wb.save(xlsx_path)
        res_xlsx = DocumentParser.parse_file(xlsx_path)
        assert res_xlsx["success"] is True
        assert "Latency" in res_xlsx["extracted_text"]

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_file_indexer_and_duplicate_detection():
    import uuid
    temp_dir = tempfile.mkdtemp(prefix="jarvis_test_indexer_")
    try:
        # Create two identical files (duplicates) and one unique file
        file1 = os.path.join(temp_dir, "doc1.txt")
        file2 = os.path.join(temp_dir, "doc1_copy.txt")
        file3 = os.path.join(temp_dir, "unique.txt")

        unique_marker = f"Unique content for duplicate testing {uuid.uuid4()}."
        with open(file1, "w", encoding="utf-8") as f: f.write(unique_marker)
        with open(file2, "w", encoding="utf-8") as f: f.write(unique_marker)
        with open(file3, "w", encoding="utf-8") as f: f.write("Totally different content.")

        # Index all files
        res1 = file_indexer.index_single_file(file1)
        res2 = file_indexer.index_single_file(file2)
        res3 = file_indexer.index_single_file(file3)
        assert res1["success"] and res2["success"] and res3["success"]

        # Verify duplicate detection matches file1 and file2
        duplicates = file_indexer.find_duplicate_files()
        assert len(duplicates) >= 1
        dupe_group = next(d for d in duplicates if d["content_hash"] == res1["content_hash"])
        assert dupe_group["count"] == 2
        assert file1 in dupe_group["files"]
        assert file2 in dupe_group["files"]

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_semantic_document_search():
    temp_dir = tempfile.mkdtemp(prefix="jarvis_test_search_")
    try:
        doc_path = os.path.join(temp_dir, "network_study.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("In Computer Networks, Dijkstra shortest path algorithm is used in Link-State routing protocols like OSPF.")
        
        file_indexer.index_single_file(doc_path)

        # Search using semantic query
        matches = file_search_engine.search_documents("Dijkstra link-state routing", limit=2)
        assert len(matches) >= 1
        assert "Dijkstra" in matches[0]["match_snippet"]

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_files_rest_endpoints():
    with TestClient(app) as client:
        # 1. List indexed files
        list_res = client.get("/api/files/indexed")
        assert list_res.status_code == 200
        assert isinstance(list_res.json(), list)

        # 2. Search endpoint
        search_res = client.get("/api/files/search?q=Dijkstra")
        assert search_res.status_code == 200
        data = search_res.json()
        assert "results" in data

        # 3. Duplicates endpoint
        dupes_res = client.get("/api/files/duplicates")
        assert dupes_res.status_code == 200
        assert "duplicates" in dupes_res.json()
