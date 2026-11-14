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
    APP_LAUNCH_PATTERNS = [
        r"(?:open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+)",
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
                app_name = match.group(1).strip()
                # Ignore non-apps like "the door" or "my eyes"
                if app_name and len(app_name) < 30 and not any(k in app_name for k in ["pdf", "file", "storage"]):
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
