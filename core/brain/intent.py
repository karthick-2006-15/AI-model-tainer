"""
Fast Intent Classifier & Entity Extractor
Categorizes incoming natural language prompts into actionable categories.
"""

import re
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class IntentCategory(str, Enum):
    CONVERSATIONAL = "conversational"
    SYSTEM_CONTROL = "system_control"
    FILE_OPERATION = "file_operation"
    RESEARCH = "research"
    COMPLEX_TASK = "complex_task"


@dataclass
class IntentClassification:
    category: IntentCategory
    confidence: float
    target_tool: Optional[str] = None
    extracted_params: Dict[str, Any] = None


class IntentClassifier:
    GREETING_PATTERNS = [
        r"^(?:hi|hello|hey|hey\s+jarvis|greetings|good\s+(?:morning|afternoon|evening|day)|yo|howdy)[!.]*$",
        r"^(?:who\s+are\s+you|what\s+are\s+you|introduce\s+yourself)[?.]*$",
        r"^(?:what\s+can\s+you\s+do|what\s+are\s+your\s+capabilities|help|list\s+capabilities)[?.]*$",
        r"^(?:how\s+are\s+you|how\s+are\s+things|status\s+report|system\s+status)[?.]*$",
        r"\b(?:give\s+me\s+my\s+briefing|daily\s+briefing|morning\s+briefing)\b"
    ]
    EMERGENCY_STOP_PATTERNS = [
        r"\b(?:emergency\s+stop|abort\s+all|kill\s+all|stop\s+everything|halt|abort)\b"
    ]
    WHATSAPP_MESSAGE_PATTERNS = [
        r"\b(?:send|whatsapp)\s+(?:message\s+)?['\"]?([^'\"]+?)['\"]?\s+to\s+(?:my\s+)?([a-zA-Z0-9_\-\s]+)",
        r"\b(?:send\s+to\s+(?:my\s+)?([a-zA-Z0-9_\-\s]+?))\s+(?:message\s+)?['\"]?([^'\"]+?)['\"]?$"
    ]
    SCREEN_INTELLIGENCE_PATTERNS = [
        r"\b(?:read|what is|what's|explain)\s+(?:on\s+my\s+screen|visible\s+screen|my\s+screen|the\s+screen)\b"
    ]
    WORKSHEET_PATTERNS = [
        r"\b(?:explore|fill|solve|read)\s+(?:this\s+)?(?:online\s+)?(?:worksheet|form|exam|quiz)\b"
    ]
    COMPUTER_NAV_PATTERNS = [
        r"\b(?:click|press)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+button)?$",
        r"\b(?:scroll)\s+(up|down)\b"
    ]
    APP_LAUNCH_PATTERNS = [
        r"\b(?:open|launch|start|run|bring\s+up|switch\s+to)\s+(?:the\s+)?(?:app\s+|application\s+)?([a-zA-Z0-9_\-\s]+)",
        r"\b(?:open|launch|start|run)\s+up\s+(?:the\s+)?(?:app\s+|application\s+)?([a-zA-Z0-9_\-\s]+)",
    ]
    SYSTEM_METRIC_PATTERNS = [
        r"\b(?:check|show|what is|get)\s+(?:my\s+)?(?:laptop|pc|system|cpu|ram|memory|battery|storage|disk)\b",
        r"\b(?:storage|disk|memory|battery)\s+(?:status|usage|check)\b"
    ]
    FILE_PATTERNS = [
        r"\b(?:find|search|locate|look for|list)\s+(?:all\s+)?(?:files|documents|pdfs|code)\b",
        r"\b(?:read|open|show|inspect)\s+(?:file|document|code)\b"
    ]
    RESEARCH_PATTERNS = [
        r"\b(?:research|search the web|google|look up|find info on)\b",
    ]
    COMPLEX_TASK_PATTERNS = [
        r"\b(?:prepare me for|organize my|setup development|build a study plan)\b"
    ]

    def classify(self, text: str) -> IntentClassification:
        cleaned = text.lower().strip()
        params: Dict[str, Any] = {}

        # 0. Global Emergency Stop Check
        for p in self.EMERGENCY_STOP_PATTERNS:
            if re.search(p, cleaned):
                params["reason"] = "User verbal or text emergency abort"
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=1.0,
                    target_tool="trigger_emergency_stop",
                    extracted_params=params
                )

        # 1. WhatsApp Messaging Check ("send Hi to my father", "send hello to dad")
        for p in self.WHATSAPP_MESSAGE_PATTERNS:
            match = re.search(p, cleaned)
            if match:
                msg = match.group(1).strip()
                recip = match.group(2).strip()
                # Swap if matched the second pattern
                if "send to" in cleaned:
                    recip, msg = match.group(1).strip(), match.group(2).strip()
                # Clean polite words
                recip = re.sub(r"\s+(?:please|now|for\s+me)$", "", recip).strip()
                params["recipient"] = recip
                params["message"] = msg
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.96,
                    target_tool="whatsapp.prepare_message",
                    extracted_params=params
                )

        # 2. Screen Intelligence & Visual Error Analysis Check
        for p in self.SCREEN_INTELLIGENCE_PATTERNS:
            if re.search(p, cleaned):
                params["focus_area"] = "Full Screen"
                return IntentClassification(
                    category=IntentCategory.RESEARCH,
                    confidence=0.95,
                    target_tool="explain_screen",
                    extracted_params=params
                )

        # 3. Worksheet & Online Form Exploration Check
        for p in self.WORKSHEET_PATTERNS:
            if re.search(p, cleaned):
                params["source_type"] = "active_browser"
                return IntentClassification(
                    category=IntentCategory.COMPLEX_TASK,
                    confidence=0.92,
                    target_tool="worksheet.extract_questions",
                    extracted_params=params
                )

        # 4. Computer Navigation (click, scroll)
        for p in self.COMPUTER_NAV_PATTERNS:
            match = re.search(p, cleaned)
            if match:
                if "scroll" in cleaned:
                    direction = match.group(1)
                    params["direction"] = direction
                    params["clicks"] = 4
                    return IntentClassification(
                        category=IntentCategory.SYSTEM_CONTROL,
                        confidence=0.92,
                        target_tool="computer.scroll",
                        extracted_params=params
                    )
                else:
                    el_name = match.group(1).strip()
                    params["element_name"] = el_name
                    return IntentClassification(
                        category=IntentCategory.SYSTEM_CONTROL,
                        confidence=0.91,
                        target_tool="computer.click_element",
                        extracted_params=params
                    )

        # 5. Greetings & Core Conversational Queries Check
        for p in self.GREETING_PATTERNS:
            if re.search(p, cleaned):
                params["query"] = cleaned
                return IntentClassification(
                    category=IntentCategory.CONVERSATIONAL,
                    confidence=0.98,
                    target_tool="built_in_conversational_kernel",
                    extracted_params=params
                )

        # 1. System Metrics Check
        for p in self.SYSTEM_METRIC_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.95,
                    target_tool="get_system_telemetry",
                    extracted_params=params
                )

        # 2. Application Launch Check
        for p in self.APP_LAUNCH_PATTERNS:
            match = re.search(p, cleaned)
            if match:
                raw_app = match.group(1).strip()
                # Clean conversational modifiers like "in window", "app", "please", "for me", etc.
                app_name = re.sub(r"\s+(?:in\s+window|in\s+a\s+window|window|app|application|please|now|for\s+me)$", "", raw_app).strip()
                app_name = re.sub(r"\s+(?:please|now|for\s+me)$", "", app_name).strip()
                app_name = app_name.strip(" .,!?:;'\"")

                # Ignore non-apps like file extensions (e.g. "report.pdf", "data.csv") unless it's file explorer
                is_file_doc = any(app_name.endswith(ext) for ext in [".pdf", ".txt", ".docx", ".xlsx", ".csv", ".py", ".json"])
                if app_name and len(app_name) < 40 and not is_file_doc and not any(k in app_name for k in ["pdf", "storage status"]):
                    params["app_name"] = app_name
                    return IntentClassification(
                        category=IntentCategory.SYSTEM_CONTROL,
                        confidence=0.92,
                        target_tool="open_application",
                        extracted_params=params
                    )

        # 3. File Operations Check
        for p in self.FILE_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.FILE_OPERATION,
                    confidence=0.88,
                    target_tool="search_workspace_files",
                    extracted_params=params
                )

        # 4. Complex Tasks Check
        for p in self.COMPLEX_TASK_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.COMPLEX_TASK,
                    confidence=0.85,
                    extracted_params=params
                )

        # 5. Research Check
        for p in self.RESEARCH_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.RESEARCH,
                    confidence=0.85,
                    extracted_params=params
                )

        # 6. Default Conversational
        return IntentClassification(
            category=IntentCategory.CONVERSATIONAL,
            confidence=0.75,
            extracted_params=params
        )


# Global singleton instance
intent_classifier = IntentClassifier()
