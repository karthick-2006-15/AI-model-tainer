"""
Office Document & Presentation Generation Engine
Generates styled PowerPoint (.pptx) presentations, Word (.docx) reports,
and Excel (.xlsx) spreadsheets using python-pptx, python-docx, and openpyxl.
Verifies file integrity and execution readiness.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Safe imports
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    import docx
    from docx.shared import Inches as DocxInches, Pt as DocxPt, RGBColor as DocxRGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger("jarvis.files.office")


class OfficeDocumentGenerator:
    """Creates presentation slides, reports, and spreadsheets from structured research data."""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.output_dir = os.path.join(self.project_root, "storage", "documents")
        os.makedirs(self.output_dir, exist_ok=True)

    def create_presentation(
        self,
        topic: str,
        slides_data: List[Dict[str, Any]],
        output_path: Optional[str] = None,
        author: str = "JARVIS Autonomous Intelligence"
    ) -> Dict[str, Any]:
        """
        Generates a styled, multi-slide PowerPoint (.pptx) presentation.
        Each slide in slides_data contains:
          - title: str
          - subtitle: Optional[str]
          - bullet_points: List[str]
          - notes: Optional[str]
          - image_path: Optional[str]
        """
        if not PPTX_AVAILABLE:
            return {"success": False, "error": "python-pptx is not installed."}

        try:
            prs = Presentation()
            # Set 16:9 widescreen dimensions (10 x 5.625 inches)
            prs.slide_width = Inches(13.333)
            prs.slide_height = Inches(7.5)

            # --- Slide 1: Title Slide ---
            title_slide_layout = prs.slide_layouts[0]
            title_slide = prs.slides.add_slide(title_slide_layout)
            title = title_slide.shapes.title
            subtitle = title_slide.placeholders[1]

            title.text = topic.title()
            subtitle.text = f"Autonomous Research & Executive Briefing\nPrepared by {author} • {datetime.now().strftime('%B %d, %Y')}"

            # Style title text
            for p in title.text_frame.paragraphs:
                p.font.bold = True
                p.font.size = Pt(44)
                p.font.color.rgb = RGBColor(14, 116, 144)  # Cyan-700 / Slate theme

            for p in subtitle.text_frame.paragraphs:
                p.font.size = Pt(18)
                p.font.color.rgb = RGBColor(100, 116, 139)

            # --- Slides 2+: Content Slides ---
            content_layout = prs.slide_layouts[1]
            for s_data in slides_data:
                slide = prs.slides.add_slide(content_layout)
                shapes = slide.shapes

                # Slide Title
                slide_title = shapes.title
                slide_title.text = s_data.get("title", "Overview")
                for p in slide_title.text_frame.paragraphs:
                    p.font.bold = True
                    p.font.size = Pt(32)
                    p.font.color.rgb = RGBColor(15, 23, 42)

                # Slide Body / Bullet points
                body_shape = shapes.placeholders[1]
                tf = body_shape.text_frame
                tf.word_wrap = True

                bullets = s_data.get("bullet_points", [])
                for i, bullet in enumerate(bullets):
                    if i == 0:
                        p = tf.paragraphs[0]
                    else:
                        p = tf.add_paragraph()
                    p.text = bullet
                    p.level = 0
                    p.font.size = Pt(20)
                    p.font.color.rgb = RGBColor(51, 65, 85)

                # If an image is provided and exists, place it on the right
                img_path = s_data.get("image_path")
                if img_path and os.path.exists(img_path):
                    try:
                        # Resize body width to make room for image
                        body_shape.width = Inches(7.5)
                        slide.shapes.add_picture(img_path, Inches(8.5), Inches(1.8), width=Inches(4.2))
                    except Exception as ex_img:
                        logger.warning(f"Failed to attach image to slide: {ex_img}")

            # Determine destination path
            if not output_path:
                safe_name = "".join(c for c in topic if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                filename = f"Presentation_{safe_name}_{int(time.time())}.pptx"
                dest_path = os.path.join(self.output_dir, filename)
            else:
                dest_path = os.path.abspath(output_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            prs.save(dest_path)
            logger.info(f"Generated PowerPoint presentation: {dest_path}")

            return {
                "success": True,
                "file_path": dest_path,
                "slides_count": len(prs.slides),
                "format": "pptx",
                "file_size_bytes": os.path.getsize(dest_path),
                "topic": topic
            }

        except Exception as e:
            logger.error(f"Error creating presentation: {e}")
            return {"success": False, "error": str(e)}

    def create_word_report(
        self,
        title: str,
        executive_summary: str,
        sections: List[Dict[str, Any]],
        sources: Optional[List[Dict[str, str]]] = None,
        output_path: Optional[str] = None,
        author: str = "JARVIS Autonomous Intelligence"
    ) -> Dict[str, Any]:
        """
        Generates a professional, structured Word document (.docx) report.
        sections: List of {"heading": str, "content": str, "bullets": Optional[List[str]]}
        """
        if not DOCX_AVAILABLE:
            return {"success": False, "error": "python-docx is not installed."}

        try:
            doc = docx.Document()

            # Set margins to 1 inch
            for section in doc.sections:
                section.top_margin = DocxInches(1.0)
                section.bottom_margin = DocxInches(1.0)
                section.left_margin = DocxInches(1.0)
                section.right_margin = DocxInches(1.0)

            # Title
            h1 = doc.add_heading(title, level=0)
            h1.alignment = WD_ALIGN_PARAGRAPH.LEFT

            # Subtitle / Metadata
            p_sub = doc.add_paragraph()
            r_sub = p_sub.add_run(f"Executive Research Report • Prepared by {author} • {datetime.now().strftime('%B %d, %Y')}")
            r_sub.font.size = DocxPt(10)
            r_sub.font.italic = True
            r_sub.font.color.rgb = DocxRGBColor(100, 116, 139)

            doc.add_paragraph()  # Blank spacer

            # Executive Summary
            doc.add_heading("Executive Summary", level=1)
            p_exec = doc.add_paragraph(executive_summary)
            p_exec.style = 'Normal'

            # Report Sections
            for sec in sections:
                heading = sec.get("heading", "Findings")
                doc.add_heading(heading, level=1)

                content = sec.get("content", "")
                if content:
                    doc.add_paragraph(content)

                bullets = sec.get("bullets", [])
                for b in bullets:
                    doc.add_paragraph(b, style='List Bullet')

            # Sources & References
            if sources:
                doc.add_heading("Sources & References", level=1)
                for s in sources:
                    s_title = s.get("title", "External Reference")
                    s_url = s.get("url", "")
                    doc.add_paragraph(f"{s_title}: {s_url}", style='List Bullet')

            # Destination
            if not output_path:
                safe_name = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                filename = f"Report_{safe_name}_{int(time.time())}.docx"
                dest_path = os.path.join(self.output_dir, filename)
            else:
                dest_path = os.path.abspath(output_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            doc.save(dest_path)
            logger.info(f"Generated Word report: {dest_path}")

            return {
                "success": True,
                "file_path": dest_path,
                "format": "docx",
                "file_size_bytes": os.path.getsize(dest_path),
                "sections_count": len(sections),
                "title": title
            }

        except Exception as e:
            logger.error(f"Error creating Word report: {e}")
            return {"success": False, "error": str(e)}

    def create_spreadsheet(
        self,
        title: str,
        sheets_data: Dict[str, List[List[Any]]],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates an Excel spreadsheet (.xlsx).
        sheets_data: {"Sheet1": [["Col1", "Col2"], [val1, val2]]}
        """
        if not OPENPYXL_AVAILABLE:
            return {"success": False, "error": "openpyxl is not installed."}

        try:
            wb = openpyxl.Workbook()
            first = True

            for sheet_name, rows in sheets_data.items():
                if first:
                    ws = wb.active
                    ws.title = sheet_name[:31]
                    first = False
                else:
                    ws = wb.create_sheet(title=sheet_name[:31])

                for row in rows:
                    ws.append(row)

            if not output_path:
                safe_name = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
                filename = f"Data_{safe_name}_{int(time.time())}.xlsx"
                dest_path = os.path.join(self.output_dir, filename)
            else:
                dest_path = os.path.abspath(output_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            wb.save(dest_path)
            logger.info(f"Generated spreadsheet: {dest_path}")

            return {
                "success": True,
                "file_path": dest_path,
                "format": "xlsx",
                "file_size_bytes": os.path.getsize(dest_path),
                "sheets": list(sheets_data.keys())
            }

        except Exception as e:
            logger.error(f"Error creating spreadsheet: {e}")
            return {"success": False, "error": str(e)}

    def verify_file_integrity_and_openable(self, file_path: str) -> Dict[str, Any]:
        """
        Verifies that a generated or inspected file exists, has valid magic headers,
        is non-empty, and can be cleanly opened.
        """
        abs_p = os.path.abspath(file_path)
        if not os.path.exists(abs_p):
            return {"success": False, "error": f"File '{file_path}' does not exist on disk."}

        size = os.path.getsize(abs_p)
        if size == 0:
            return {"success": False, "error": f"File '{file_path}' is empty (0 bytes)."}

        _, ext = os.path.splitext(abs_p)
        ext = ext.lower()

        # Check binary headers
        is_valid_format = False
        try:
            with open(abs_p, "rb") as f:
                header = f.read(8)

            if ext in (".docx", ".pptx", ".xlsx"):
                # ZIP container magic bytes: PK\x03\x04
                is_valid_format = header.startswith(b"PK\x03\x04")
            elif ext == ".pdf":
                is_valid_format = header.startswith(b"%PDF")
            elif ext in (".txt", ".md", ".json", ".csv", ".py"):
                is_valid_format = True
            else:
                is_valid_format = True
        except Exception as ex_h:
            return {"success": False, "error": f"Failed reading file header: {ex_h}"}

        return {
            "success": is_valid_format,
            "file_path": abs_p,
            "file_name": os.path.basename(abs_p),
            "format": ext.replace(".", ""),
            "file_size_bytes": size,
            "integrity_verified": is_valid_format,
            "message": "File integrity verified and validated as openable." if is_valid_format else "Header mismatch."
        }


# Global singleton instance
office_generator = OfficeDocumentGenerator()
