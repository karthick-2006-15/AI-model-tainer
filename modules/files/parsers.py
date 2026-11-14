"""
Multimodal Document Parser Engine
Supports PDF, DOCX, XLSX, PPTX, TXT, CSV, Code, and Image metadata extraction.
"""

import os
import csv
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("jarvis.files.parsers")


class DocumentParser:
    @classmethod
    def parse_file(cls, file_path: str, max_chars: int = 50000) -> Dict[str, Any]:
        """
        Auto-detects file format and extracts structured text, metadata, and page counts.
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File '{file_path}' does not exist."}

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        try:
            if ext == ".pdf":
                return cls.parse_pdf(file_path, max_chars=max_chars)
            elif ext in (".docx", ".doc"):
                return cls.parse_docx(file_path, max_chars=max_chars)
            elif ext in (".xlsx", ".xls"):
                return cls.parse_xlsx(file_path)
            elif ext == ".pptx":
                return cls.parse_pptx(file_path)
            elif ext == ".csv":
                return cls.parse_csv(file_path)
            elif ext in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
                return cls.parse_image(file_path)
            else:
                # Text or source code (.py, .ts, .js, .json, .md, .txt, etc.)
                return cls.parse_text_or_code(file_path, max_chars=max_chars)
        except Exception as e:
            logger.error(f"Error parsing file '{file_path}': {e}")
            return {"success": False, "error": str(e), "file_path": file_path}

    @classmethod
    def parse_pdf(cls, file_path: str, max_chars: int = 50000) -> Dict[str, Any]:
        """Extracts text and page count from PDF using pypdf."""
        import pypdf
        reader = pypdf.PdfReader(file_path)
        num_pages = len(reader.pages)
        pages_text = []
        total_chars = 0

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages_text.append({"page": i + 1, "text": text.strip()})
            total_chars += len(text)
            if total_chars >= max_chars:
                break

        full_text = "\n\n".join(f"[Page {p['page']}]: {p['text']}" for p in pages_text if p['text'])
        return {
            "success": True,
            "format": "pdf",
            "page_count": num_pages,
            "extracted_text": full_text[:max_chars],
            "file_path": file_path
        }

    @classmethod
    def parse_docx(cls, file_path: str, max_chars: int = 50000) -> Dict[str, Any]:
        """Extracts paragraphs and tables from DOCX using python-docx."""
        import docx
        doc = docx.Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        # Also extract table text
        table_lines = []
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    table_lines.append(row_text)

        full_text = "\n".join(paragraphs + table_lines)
        return {
            "success": True,
            "format": "docx",
            "paragraph_count": len(paragraphs),
            "extracted_text": full_text[:max_chars],
            "file_path": file_path
        }

    @classmethod
    def parse_xlsx(cls, file_path: str, max_rows: int = 200) -> Dict[str, Any]:
        """Extracts sheet names and rows from Excel using openpyxl."""
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet_summaries = []
        total_text = []

        for name in wb.sheetnames:
            sheet = wb[name]
            rows = []
            for i, row in enumerate(sheet.iter_rows(values_only=True)):
                if i >= max_rows:
                    break
                row_str = " | ".join(str(val) for val in row if val is not None)
                if row_str:
                    rows.append(row_str)
            sheet_text = f"Sheet: {name}\n" + "\n".join(rows)
            sheet_summaries.append({"sheet": name, "rows_read": len(rows)})
            total_text.append(sheet_text)

        return {
            "success": True,
            "format": "xlsx",
            "sheets": sheet_summaries,
            "extracted_text": "\n\n".join(total_text),
            "file_path": file_path
        }

    @classmethod
    def parse_pptx(cls, file_path: str) -> Dict[str, Any]:
        """Extracts slide content from PowerPoint using python-pptx."""
        from pptx import Presentation
        prs = Presentation(file_path)
        slides_text = []

        for i, slide in enumerate(prs.slides):
            slide_lines = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_lines.append(text)
            if slide_lines:
                slides_text.append(f"[Slide {i+1}]: " + " | ".join(slide_lines))

        return {
            "success": True,
            "format": "pptx",
            "slide_count": len(prs.slides),
            "extracted_text": "\n".join(slides_text),
            "file_path": file_path
        }

    @classmethod
    def parse_csv(cls, file_path: str, max_rows: int = 200) -> Dict[str, Any]:
        """Extracts rows from CSV file."""
        lines = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                if any(row):
                    lines.append(" | ".join(row))

        return {
            "success": True,
            "format": "csv",
            "row_count": len(lines),
            "extracted_text": "\n".join(lines),
            "file_path": file_path
        }

    @classmethod
    def parse_image(cls, file_path: str) -> Dict[str, Any]:
        """Extracts image properties and EXIF metadata using Pillow."""
        from PIL import Image
        with Image.open(file_path) as img:
            w, h = img.size
            fmt = img.format
            mode = img.mode

        return {
            "success": True,
            "format": "image",
            "width": w,
            "height": h,
            "image_format": fmt,
            "color_mode": mode,
            "extracted_text": f"Image file ({fmt}, {w}x{h}, {mode})",
            "file_path": file_path
        }

    @classmethod
    def parse_text_or_code(cls, file_path: str, max_chars: int = 50000) -> Dict[str, Any]:
        """Extracts text or source code files."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(max_chars)

        return {
            "success": True,
            "format": "text",
            "char_count": len(content),
            "extracted_text": content,
            "file_path": file_path
        }
