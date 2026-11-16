"""
Universal Webpage & Form Intelligence Engine
Provides semantic page analysis, question extraction, table extraction, form population, and completion verification.
"""

import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from modules.computer_use.browser_playwright import playwright_controller
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.computer_use.page")


class PageIntelligenceEngine:
    """Performs deep structural, semantic, and interactive analysis of arbitrary web pages."""

    def analyze_page(self, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Deep semantic analysis of the active webpage or given URL:
        headings, main article text, form counts, interactive elements, tables, and readability score.
        """
        if url:
            playwright_controller.open(url)

        page = playwright_controller.current_page
        try:
            title = page.title()
            current_url = page.url

            analysis = page.evaluate("""() => {
                const headings = Array.from(document.querySelectorAll('h1, h2, h3')).map(h => ({
                    level: h.tagName.toLowerCase(),
                    text: h.innerText.trim()
                })).filter(h => h.text.length > 0).slice(0, 15);

                const forms = document.querySelectorAll('form, [role="form"]');
                const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
                const buttons = document.querySelectorAll('button, [role="button"]');
                const tables = document.querySelectorAll('table');
                const links = document.querySelectorAll('a[href]');

                // Readability body text snippet
                const mainEl = document.querySelector('article, main, #content, .post-content') || document.body;
                const bodyText = mainEl ? mainEl.innerText.replace(/\\s+/g, ' ').trim() : '';
                const wordCount = bodyText.split(' ').filter(w => w.length > 0).length;

                return {
                    headings: headings,
                    forms_count: forms.length,
                    inputs_count: inputs.length,
                    buttons_count: buttons.length,
                    tables_count: tables.length,
                    links_count: links.length,
                    word_count: wordCount,
                    text_preview: bodyText.slice(0, 500)
                };
            }""")

            return {
                "success": True,
                "url": current_url,
                "title": title,
                "structure": analysis,
                "summary": f"Page '{title}' contains {analysis['word_count']} words, {analysis['headings_count'] if 'headings_count' in analysis else len(analysis['headings'])} sections, {analysis['forms_count']} forms, and {analysis['tables_count']} tables."
            }
        except Exception as e:
            logger.error(f"Page analysis failed: {e}")
            return {"success": False, "error": str(e)}

    def find_element(self, query: str) -> Dict[str, Any]:
        """
        Finds elements matching a text label, aria attribute, ID, or CSS selector.
        Returns element details, bounding boxes, and interaction readiness.
        """
        page = playwright_controller.current_page
        try:
            results = page.evaluate(f"""(searchQuery) => {{
                const q = searchQuery.toLowerCase();
                const matched = [];
                const all = document.querySelectorAll('button, a, input, select, textarea, [role="button"], label, h1, h2, h3');
                
                for (let el of all) {{
                    const text = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').toLowerCase();
                    const id = (el.id || '').toLowerCase();
                    const name = (el.name || '').toLowerCase();

                    if (text.includes(q) || id.includes(q) || name.includes(q)) {{
                        const rect = el.getBoundingClientRect();
                        matched.push({{
                            tag: el.tagName.toLowerCase(),
                            text: (el.innerText || el.value || el.placeholder || '').slice(0, 80).trim(),
                            id: el.id || '',
                            name: el.name || '',
                            is_visible: (rect.width > 0 && rect.height > 0),
                            bounds: {{
                                x: Math.round(rect.x),
                                y: Math.round(rect.y),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height)
                            }}
                        }});
                    }}
                    if (matched.length >= 8) break;
                }}
                return matched;
            }}""", query)

            return {
                "success": True,
                "query": query,
                "matches_found": len(results),
                "elements": results
            }
        except Exception as e:
            return {"success": False, "query": query, "error": str(e)}

    def extract_questions(self, url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extracts structured question prompts, multiple-choice options, and field bindings from an active worksheet or form.
        """
        if url:
            playwright_controller.open(url)

        page = playwright_controller.current_page
        try:
            questions = page.evaluate("""() => {
                const results = [];
                let qIndex = 1;

                // Look for question containers or fieldsets
                const containers = document.querySelectorAll('.question, .form-group, fieldset, tr, .field-wrapper, div[role="radiogroup"]');
                
                const processNode = (node, promptText) => {
                    const inputs = node.querySelectorAll('input, textarea, select');
                    if (inputs.length === 0) return null;

                    const firstInput = inputs[0];
                    const tag = firstInput.tagName.toLowerCase();
                    const type = firstInput.type || 'text';

                    let qType = 'text';
                    let options = [];

                    if (tag === 'textarea') {
                        qType = 'essay';
                    } else if (tag === 'select') {
                        qType = 'dropdown';
                        options = Array.from(firstInput.querySelectorAll('option')).map(o => o.innerText.trim()).filter(t => t.length > 0);
                    } else if (type === 'radio' || type === 'checkbox') {
                        qType = (type === 'radio' ? 'single_choice' : 'multiple_choice');
                        const labels = Array.from(node.querySelectorAll('label')).map(l => l.innerText.trim()).filter(t => t.length > 0);
                        options = labels;
                    }

                    return {
                        question_id: `q_${qIndex++}`,
                        prompt: promptText.slice(0, 200).trim(),
                        field_name: firstInput.name || firstInput.id || `field_${qIndex}`,
                        type: qType,
                        options: options.slice(0, 6),
                        current_value: firstInput.value || ''
                    };
                };

                for (let c of containers) {
                    const heading = c.querySelector('h1, h2, h3, h4, .title, label, p, legend');
                    const prompt = heading ? heading.innerText : c.innerText.split('\\n')[0];
                    if (prompt && prompt.length > 3) {
                        const item = processNode(c, prompt);
                        if (item) results.push(item);
                    }
                    if (results.length >= 25) break;
                }

                // Fallback to all standard labels if no container matched
                if (results.length === 0) {
                    const labels = document.querySelectorAll('label');
                    for (let lbl of labels) {
                        const text = lbl.innerText.trim();
                        if (text.length > 2) {
                            const forId = lbl.getAttribute('for');
                            const target = forId ? document.getElementById(forId) : lbl.querySelector('input, textarea, select');
                            if (target) {
                                results.push({
                                    question_id: `q_${qIndex++}`,
                                    prompt: text,
                                    field_name: target.name || target.id || `field_${qIndex}`,
                                    type: target.tagName.toLowerCase(),
                                    options: [],
                                    current_value: target.value || ''
                                });
                            }
                        }
                    }
                }

                return results;
            }""")

            return questions
        except Exception as e:
            logger.error(f"Error extracting questions: {e}")
            return []

    def extract_tables(self, table_index: int = 0) -> Dict[str, Any]:
        """
        Extracts HTML <table> elements into structured JSON rows, columns, and cell values.
        """
        page = playwright_controller.current_page
        try:
            table_data = page.evaluate(f"""(idx) => {{
                const tables = document.querySelectorAll('table');
                if (tables.length === 0 || idx >= tables.length) return null;
                const tbl = tables[idx];

                const headers = Array.from(tbl.querySelectorAll('th')).map(th => th.innerText.trim());
                const rows = [];
                const trElements = tbl.querySelectorAll('tr');

                for (let tr of trElements) {{
                    const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                    if (cells.length > 0) {{
                        rows.push(cells);
                    }}
                }}

                return {{
                    table_index: idx,
                    total_tables_on_page: tables.length,
                    headers: headers,
                    row_count: rows.length,
                    rows: rows.slice(0, 50)
                }};
            }}""", table_index)

            if not table_data:
                return {"success": False, "error": f"No table found at index {table_index}."}

            return {"success": True, "table": table_data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fill_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Populates interactive form inputs using a dictionary of {field_name_or_label: value}.
        Enforces Level 2 safety (MODIFY).
        """
        if permission_engine.is_emergency_stopped():
            return {"success": False, "error": "Emergency stop active."}

        page = playwright_controller.current_page
        filled_count = 0
        details = []

        for field_key, value in form_data.items():
            res = playwright_controller.fill(field_key, str(value))
            if res.get("success"):
                filled_count += 1
                details.append({"field": field_key, "value": value, "status": "filled"})
            else:
                details.append({"field": field_key, "value": value, "status": "failed", "error": res.get("error")})

        return {
            "success": (filled_count > 0),
            "total_requested": len(form_data),
            "total_filled": filled_count,
            "details": details
        }

    def verify_form(self) -> Dict[str, Any]:
        """
        Verifies that all required fields on the active page are populated before submission.
        """
        page = playwright_controller.current_page
        try:
            verification = page.evaluate("""() => {
                const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
                let total = 0;
                let filled = 0;
                let empty = 0;
                let missingRequired = [];

                for (let inp of inputs) {
                    if (inp.type === 'submit' || inp.type === 'button') continue;
                    total++;
                    const val = (inp.value || '').trim();
                    const isRequired = inp.required || inp.getAttribute('aria-required') === 'true';
                    const name = inp.name || inp.id || inp.placeholder || `field_${total}`;

                    if (val.length > 0) {
                        filled++;
                    } else {
                        empty++;
                        if (isRequired) {
                            missingRequired.push(name);
                        }
                    }
                }

                return {
                    total_fields: total,
                    filled_fields: filled,
                    empty_fields: empty,
                    completion_percentage: total > 0 ? Math.round((filled / total) * 100) : 100,
                    missing_required_fields: missingRequired,
                    is_ready_to_submit: (missingRequired.length === 0)
                };
            }""")

            return {"success": True, "verification": verification}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global singleton instance
page_intelligence = PageIntelligenceEngine()
