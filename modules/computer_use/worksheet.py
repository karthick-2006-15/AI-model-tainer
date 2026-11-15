"""
Online Worksheet & Form Automation Engine
Extracts questions, analyzes input types, researches factual answers,
maps fields, reviews filled answers, and enforces Level 3 confirmation before submission.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from modules.computer_use.native_uia import native_uia
from modules.computer_use.mouse_kb import mouse_kb
from modules.research.search import web_search_client
from modules.research.synthesizer import research_synthesizer
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.computer_use.worksheet")


class WorksheetAutomationEngine:
    """Automates form and worksheet question answering with research verification and submission guards."""

    def __init__(self):
        self._current_worksheet_session: Optional[Dict[str, Any]] = None

    def extract_questions_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """Parses HTML DOM to extract structured form fields and questions."""
        soup = BeautifulSoup(html_content, "html.parser")
        extracted: List[Dict[str, Any]] = []

        # Find all fieldsets, form groups, or question blocks
        question_index = 1

        # Look for standard form labels and inputs
        forms = soup.find_all(["form", "div", "fieldset"])
        seen_fields = set()

        for el in soup.find_all(["label", "p", "div", "h3", "h4"]):
            text = el.get_text().strip()
            # Heuristic check for question markers (ends with '?', has 'Question', or is an explicit label)
            is_question = bool(re.search(r"(\?|\b(?:question|enter|select|choose|fill)\b)", text, re.IGNORECASE))
            if not is_question or len(text) < 4 or len(text) > 250:
                continue

            # Associated input
            inp_id = el.get("for")
            input_tag = None
            if inp_id:
                input_tag = soup.find(id=inp_id)
            if not input_tag:
                input_tag = el.find_next(["input", "textarea", "select"])

            if not input_tag:
                continue

            field_name = input_tag.get("name") or input_tag.get("id") or f"field_{question_index}"
            if field_name in seen_fields:
                continue
            seen_fields.add(field_name)

            tag_name = input_tag.name
            inp_type = input_tag.get("type", "text").lower()

            q_type = "text"
            options = []

            if tag_name == "textarea":
                q_type = "textarea"
            elif tag_name == "select":
                q_type = "dropdown"
                options = [opt.get_text().strip() for opt in input_tag.find_all("option") if opt.get_text().strip()]
            elif inp_type in ("radio", "checkbox"):
                q_type = "multiple_choice" if inp_type == "radio" else "multi_select"
                # Find sibling options
                parent = input_tag.find_parent(["div", "fieldset"]) or el.parent
                if parent:
                    options = [opt.get_text().strip() for opt in parent.find_all("label") if opt.get_text().strip()]
            elif inp_type == "number":
                q_type = "numeric"

            extracted.append({
                "question_id": f"q_{question_index}",
                "prompt": text,
                "field_name": field_name,
                "question_type": q_type,
                "options": options[:6],
                "input_tag": tag_name,
                "answered": False,
                "answer": None
            })
            question_index += 1

            if len(extracted) >= 20:
                break

        return extracted

    async def research_answers(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Researches factual answers for each extracted question using JARVIS Internet Intelligence."""
        researched: List[Dict[str, Any]] = []

        for q in questions:
            prompt = q.get("prompt", "")
            q_type = q.get("question_type", "text")
            options = q.get("options", [])

            # Conduct concise web search for question
            search_query = re.sub(r"^(?:question\s*\d*[:.-]?\s*)", "", prompt, flags=re.IGNORECASE)
            search_query = search_query.strip(" ?.")

            answer_text = ""
            confidence = 0.5
            source = "heuristics"

            try:
                results = await web_search_client.search(query=search_query, max_results=2)
                if results and results[0].get("snippet"):
                    snippet = results[0]["snippet"]
                    source = results[0].get("url", "web_search")

                    # If multiple choice, match snippet to available options
                    if q_type == "multiple_choice" and options:
                        best_opt = None
                        for opt in options:
                            if opt.lower() in snippet.lower():
                                best_opt = opt
                                confidence = 0.85
                                break
                        answer_text = best_opt or options[0]
                    else:
                        answer_text = snippet[:150]
                        confidence = 0.75
                else:
                    answer_text = f"Researched context for: {search_query}"
            except Exception as e:
                logger.warning(f"Error researching answer for '{prompt}': {e}")
                answer_text = "Answer requires manual review."
                confidence = 0.2

            researched.append({
                **q,
                "answer": answer_text,
                "confidence": confidence,
                "source": source,
                "needs_review": (confidence < 0.6)
            })

        return researched

    def fill_answers(self, answered_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fills answers into the form fields via UI Automation or keyboard input."""
        filled_count = 0
        details = []

        for item in answered_questions:
            answer = item.get("answer")
            field_name = item.get("field_name")
            q_type = item.get("question_type")

            if not answer:
                continue

            # Try UI Automation edit control
            ctrl = native_uia.find_control(name=field_name, control_type="Edit")
            if ctrl:
                ctrl.SetFocus()
                native_uia.type_into_element(str(answer))
                filled_count += 1
                details.append({"field": field_name, "status": "filled_via_UIA", "answer": answer})
            else:
                # Fallback to general input field filling
                details.append({"field": field_name, "status": "staged_for_entry", "answer": answer})

        return {
            "success": True,
            "total_questions": len(answered_questions),
            "filled_count": filled_count,
            "details": details
        }

    def review_answers(self, answered_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates a structured completion summary before form submission."""
        summary_items = []
        low_confidence_count = 0

        for q in answered_questions:
            conf = q.get("confidence", 0.0)
            if conf < 0.6:
                low_confidence_count += 1
            summary_items.append({
                "prompt": q.get("prompt"),
                "answer": q.get("answer"),
                "confidence": f"{int(conf * 100)}%",
                "needs_review": q.get("needs_review", False)
            })

        self._current_worksheet_session = {
            "questions": answered_questions,
            "summary": summary_items,
            "ready_for_submission": True
        }

        return {
            "success": True,
            "total": len(answered_questions),
            "low_confidence_count": low_confidence_count,
            "summary": summary_items,
            "message": f"Review complete. {len(answered_questions)} questions processed. Awaiting authorization to submit."
        }

    def submit_worksheet(self, skip_permission_check: bool = False) -> Dict[str, Any]:
        """
        Submits the completed worksheet.
        STRICT LEVEL 3 EXTERNAL ACTION:
        Requires explicit user authorization before pressing the submit button.
        """
        if permission_engine.is_emergency_stopped():
            return {"success": False, "error": "Operation blocked: Global Emergency Stop is ACTIVE."}

        # Level 3 Authorization Check
        if not skip_permission_check:
            allowed, reason, challenge = permission_engine.evaluate_request(
                tool_name="worksheet.submit",
                permission_level=permission_engine.LEVEL_3_EXTERNAL_ACTION,
                target_resource="Online Worksheet Final Submission",
                arguments={"session_data": "current_worksheet_session"}
            )
            if not allowed:
                return {
                    "success": False,
                    "awaiting_authorization": True,
                    "error": reason,
                    "challenge": challenge,
                    "instructions": "Confirm aloud with 'Yes' / 'Submit' or deny with 'No' / 'Cancel'."
                }

        # Find and click Submit button via UI Automation or Mouse
        btn_submit = native_uia.find_control(name="Submit", control_type="Button")
        if not btn_submit:
            btn_submit = native_uia.find_control(name="Submit form", control_type="Button")

        if btn_submit:
            btn_submit.Click()
            return {
                "success": True,
                "status": "submitted",
                "message": "Worksheet submitted successfully after user authorization."
            }

        # Fallback: search submit button on screen
        return {
            "success": True,
            "status": "authorized_and_ready",
            "message": "Submission authorized. Please press the final submit button on screen."
        }


# Global singleton instance
worksheet_engine = WorksheetAutomationEngine()
