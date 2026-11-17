"""
Fast Intent Classifier & Entity Extractor
Categorizes incoming natural language prompts into actionable categories.
"""

import re
from enum import Enum
from typing import Dict, Any, Optional, Tuple
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
        r"\b(?:can\s+you\s+hear(?:\s+me)?|do\s+you\s+hear(?:\s+me)?|are\s+you\s+listening(?:\s+to\s+me)?|listen\s+to\s+me|mic(?:\s+check)?|microphone\s+check|test\s+(?:mic|microphone|audio|sound)|audio\s+check|sound\s+check)\b",
        r"\b(?:can\s+you\s+speak|speak\s+to\s+me|say\s+something|talk\s+to\s+me)\b",
        r"\b(?:are\s+you\s+there|you\s+there(?:\s+jarvis)?|are\s+you\s+online|are\s+you\s+awake|wake\s+up(?:\s+jarvis)?)\b",
        r"\b(?:thank\s+you(?:\s+(?:very\s+much|so\s+much|jarvis))?|thanks(?:\s+jarvis)?|good\s+job|great\s+job|well\s+done)\b",
        r"\b(?:stand\s+by(?:\s+jarvis)?|go\s+to\s+sleep|sleep\s+mode|good\s+night(?:\s+jarvis)?)\b",
        r"^(?:ok|okay|alright|fine|understood|got\s+it)(?:\s+jarvis)?[!.]*$",
        r"^(?:hi|hello|hey|hey\s+jarvis|greetings|good\s+(?:morning|afternoon|evening|day)|yo|howdy)(?:\s+jarvis)?\s*[!.,?]*$",
        r"\b(?:who\s+are\s+you|what\s+are\s+you|introduce\s+yourself|tell\s+me\s+about\s+yourself|your\s+name|what\s+is\s+your\s+name)\b",
        r"\b(?:what\s+can\s+you\s+do|what\s+are\s+your\s+capabilities|help|list\s+capabilities|what\s+do\s+you\s+do)\b",
        r"\b(?:how\s+are\s+you|how\s+are\s+things|status\s+report|system\s+status|system\s+health)\b",
        r"\b(?:what\s+time\s+is\s+it|current\s+time|tell\s+me\s+the\s+time|what\s+is\s+the\s+time|time\s+now|time)\b",
        r"\b(?:what\s+is\s+today's\s+date|what's\s+the\s+date|today's\s+date|what\s+date\s+is\s+it|what\s+day\s+is\s+it)\b",
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
        r"\b(?:open|launch|start|run|bring\s+up)\s+(?:the\s+)?(?:app\s+|application\s+)?([a-zA-Z0-9_\-\s]+)",
        r"\b(?:open|launch|start|run)\s+up\s+(?:the\s+)?(?:app\s+|application\s+)?([a-zA-Z0-9_\-\s]+)",
    ]
    APP_CLOSE_PATTERNS = [
        r"\b(?:close|quit|exit|kill)\s+(?:the\s+)?(?:app\s+|application\s+)?([a-zA-Z0-9_\-\s]+)"
    ]
    APP_RESTART_PATTERNS = [
        r"\b(?:restart|re-open|reload)\s+(?:the\s+)?(?:app\s+|application\s+)?([a-zA-Z0-9_\-\s]+)"
    ]
    APP_SWITCH_PATTERNS = [
        r"\b(?:switch\s+to|bring\s+to\s+front|focus)\s+(?:the\s+)?(?:app\s+|application\s+)?([a-zA-Z0-9_\-\s]+)"
    ]
    RUNNING_APPS_PATTERNS = [
        r"\b(?:what apps are running|list running apps|show running apps|running applications|what is running|active windows)\b"
    ]
    INSTALLED_APPS_PATTERNS = [
        r"\b(?:find all installed|list installed apps|show installed apps|what apps are installed)\s*([a-zA-Z0-9_\-\s]*)"
    ]
    APP_BY_DESC_PATTERNS = [
        r"\b(?:open|launch|find|what is)\s+(?:the\s+)?(?:app|application)?\s*(?:i\s+use\s+for|that\s+i\s+use\s+for|used\s+for)\s+([a-zA-Z0-9_\-\s]+)",
        r"\b(?:open|launch)\s+my\s+(music player|music|code editor|browser|photo editor)\b"
    ]
    FOLDER_PATTERNS = [
        r"\b(?:open|show)\s+(?:my\s+)?(downloads|documents|desktop|pictures|videos|music)\s+folder\b"
    ]
    SYSTEM_METRIC_PATTERNS = [
        r"\b(?:check|show|what is|get)\s+(?:my\s+)?(?:laptop|pc|system|cpu|ram|memory|battery|storage|disk)\b",
        r"\b(?:storage|disk|memory|battery)\s+(?:status|usage|check)\b"
    ]
    FILE_SEARCH_PATTERNS = [
        r"\b(?:find|search|locate|look\s+for|list)\s+(?:all\s+)?([a-zA-Z0-9_\*\.\-]+)?\s*(?:files|documents)?\s*(?:in|inside|from|under)\s+(?:my\s+)?([a-zA-Z0-9_\-\\/\.\s]+)\b"
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
    MULTI_APP_WORKFLOW_PATTERNS = [
        r"\bresearch\s+(.+?)(?:,\s*|\s+and\s+)(?:prepare|create|write)\s+(?:a\s+)?report\s+and\s+(?:create|generate|make)\s+(?:a\s+)?presentation\b",
        r"\bresearch\s+(.+?)\s+and\s+(?:create|make|generate)\s+(?:a\s+)?presentation\b"
    ]
    REMINDER_PATTERNS = [
        r"\b(?:remind me to|set a reminder to|schedule a reminder)\s+(.+)"
    ]
    YOUTUBE_SEARCH_PATTERNS = [
        r"\b(?:open\s+)?youtube(?:\s+and\s+search\s+(?:for\s+)?|\s+search\s+(?:for\s+)?)(.+)",
        r"\bsearch\s+youtube\s+for\s+(.+)",
        r"\byoutube\s+la\s+(.+?)\s+search\s+pannu\b",
        r"\byoutube\s+mein\s+(.+?)\s+search\s+karo\b"
    ]
    YOUTUBE_PLAY_PATTERNS = [
        r"\bplay\s+(?:the\s+)?(?:first|1st)\s+video\b",
        r"\bplay\s+(?:the\s+)?(?:second|2nd)\s+video\b",
        r"\b(?:open|play)\s+(?:the\s+)?(?:third|3rd)\s+(?:result|video)\b",
        r"\b(?:open|play)\s+result\s+(\d+)\b"
    ]
    YOUTUBE_CONTROL_PATTERNS = [
        r"\b(pause|resume|play|mute|unmute|fullscreen)\s+(?:the\s+)?(?:video|youtube)\b",
        r"\b(increase|decrease|raise|lower)\s+(?:the\s+)?(?:video\s+|youtube\s+)volume\b"
    ]
    PAGE_ANALYZE_PATTERNS = [
        r"\banalyze\s+(?:this\s+)?(?:webpage|page|website)(?:\s+and\s+follow\s+my\s+instructions)?\b",
        r"\bindha\s+page\s+analyse\s+panni\b",
        r"\bread\s+(?:this\s+)?(?:article|webpage|page)\b"
    ]
    SPOTIFY_INFO_PATTERNS = [
        r"\b(?:what\s+(?:song|track|music)\s+is\s+playing|what\s+is\s+playing|what's\s+playing|current\s+(?:song|track)|who\s+is\s+(?:the\s+)?(?:singer|artist)|who\s+is\s+singing|how\s+much\s+time\s+is\s+remaining|show\s+(?:the\s+)?current\s+playlist)\b"
    ]
    SPOTIFY_PAUSE_PATTERNS = [
        r"^(?:jarvis\s*[,:]?\s*)?(?:pause\s+(?:the\s+)?(?:music|song|playback|spotify)?|pause|stop\s+(?:the\s+)?(?:music|song|playback|spotify)?)[!.]*$",
        r"\b(?:pause\s+(?:the\s+)?(?:music|song|playback)|stop\s+(?:the\s+)?(?:music|song))\b"
    ]
    SPOTIFY_RESUME_PATTERNS = [
        r"^(?:jarvis\s*[,:]?\s*)?(?:resume\s+(?:the\s+)?(?:music|song|playback|spotify)?|resume|continue\s+playing|continue|unpause)[!.]*$",
        r"\b(?:resume\s+(?:the\s+)?(?:music|song|playback)|continue\s+playing)\b"
    ]
    SPOTIFY_NEXT_PATTERNS = [
        r"^(?:jarvis\s*[,:]?\s*)?(?:next\s+song|next\s+track|skip\s+(?:this\s+)?track|skip\s+(?:this\s+)?song|skip|next)[!.]*$",
        r"\b(?:next\s+song|next\s+track|skip\s+this\s+track|skip\s+track)\b"
    ]
    SPOTIFY_PREV_PATTERNS = [
        r"^(?:jarvis\s*[,:]?\s*)?(?:previous\s+song|previous\s+track|previous|play\s+that\s+song\s+again|go\s+back)[!.]*$",
        r"\b(?:previous\s+song|previous\s+track|play\s+that\s+song\s+again)\b"
    ]
    SPOTIFY_VOLUME_PATTERNS = [
        r"\b(?:increase|raise|turn\s+up)\s+(?:the\s+)?(?:music\s+|spotify\s+)?volume\b",
        r"\b(?:reduce|decrease|lower|turn\s+down)\s+(?:the\s+)?(?:music\s+|spotify\s+)?volume\b",
        r"\b(?:mute\s+(?:the\s+)?(?:music|spotify|audio)|mute)\b",
        r"\bset\s+(?:the\s+)?volume\s+to\s+(\d+)(?:%|\s*percent)?\b",
        r"\bvolume\s+(\d+)(?:%|\s*percent)?\b"
    ]
    SPOTIFY_PLAY_PATTERNS = [
        r"^(?:hey\s+)?(?:jarvis\s*[,:]?\s*)?(?:open\s+spotify\s+and\s+)?play\s+(.+)$",
        r"^(?:hey\s+)?(?:jarvis\s*[,:]?\s*)?open\s+spotify(?:\s+and\s+play\s+music)?$",
        r"\b(?:put\s+on|play\s+some|play\s+songs?\s+by|play\s+music\s+by)\s+(.+)$"
    ]


    def _parse_whatsapp_instruction(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extracts recipient and message cleanly from natural WhatsApp commands."""
        c = text.strip()
        # 1. Strip trailing conversation modifiers or auxiliary clauses like:
        # "it have to sent message to app", "in whatsapp", "on whatsapp", "please"
        c = re.sub(
            r"\s+(?:it\s+have\s+to\s+.*|it\s+has\s+to\s+.*|in\s+app|on\s+whatsapp|in\s+whatsapp|via\s+whatsapp|please|now|for\s+me)$",
            "",
            c,
            flags=re.IGNORECASE
        ).strip()

        # 2. Strip leading wake-words and app-open prefixes
        # e.g. "hey jarvis, open whatsapp and ...", "open whatsapp and ..."
        c = re.sub(
            r"^(?:hey\s+jarvis\s*[,:]?\s*)?(?:open\s+whatsapp\s+(?:and\s+|,?\s*))?",
            "",
            c,
            flags=re.IGNORECASE
        ).strip()

        # Pattern A: send/sent/whatsapp [message] to [recipient]
        p_a = r"^(?:send|sent|text|message|whatsapp)\s+(?:a\s+)?(?:message\s+)?['\"]?(.+?)['\"]?\s+to\s+(?:my\s+)?([a-zA-Z0-9_\-\s]+)$"
        m_a = re.search(p_a, c, flags=re.IGNORECASE)
        if m_a:
            raw_msg = m_a.group(1).strip()
            raw_recip = m_a.group(2).strip()
            msg = re.sub(r"\s+message$", "", raw_msg, flags=re.IGNORECASE).strip()
            recip = re.sub(r"\s+(?:please|now|for\s+me)$", "", raw_recip, flags=re.IGNORECASE).strip()
            if recip and msg:
                return recip, msg

        # Pattern B: send to [recipient] [message]
        p_b = r"^(?:send|sent|text|message)\s+to\s+(?:my\s+)?([a-zA-Z0-9_\-\s]+?)\s+(?:message\s+)?['\"]?(.+?)['\"]?$"
        m_b = re.search(p_b, c, flags=re.IGNORECASE)
        if m_b:
            recip = m_b.group(1).strip()
            raw_msg = m_b.group(2).strip()
            msg = re.sub(r"\s+message$", "", raw_msg, flags=re.IGNORECASE).strip()
            if recip and msg:
                return recip, msg

        # Pattern C: Fallback to existing WHATSAPP_MESSAGE_PATTERNS
        for p in self.WHATSAPP_MESSAGE_PATTERNS:
            m = re.search(p, text.lower().strip())
            if m:
                msg = m.group(1).strip()
                recip = m.group(2).strip()
                if "send to" in text.lower():
                    recip, msg = m.group(1).strip(), m.group(2).strip()
                msg = re.sub(r"^(?:and\s+)?(?:send|sent)\s+", "", msg).strip()
                recip = re.sub(r"\s+(?:please|now|for\s+me)$", "", recip).strip()
                return recip, msg

        return None, None

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

        # 0b. Multi-Application Cross-App Workflow ("Research autonomous warehouse robots, prepare a report and create a presentation")
        for p in self.MULTI_APP_WORKFLOW_PATTERNS:
            m_flow = re.search(p, cleaned)
            if m_flow:
                topic = m_flow.group(1).strip()
                params["topic"] = topic
                return IntentClassification(
                    category=IntentCategory.COMPLEX_TASK,
                    confidence=0.97,
                    target_tool="orchestration.run_multi_app_workflow",
                    extracted_params=params
                )

        # 0c. Natural Voice Reminder Check ("remind me to submit my assignment tomorrow at 9 AM")
        for p in self.REMINDER_PATTERNS:
            if re.search(p, cleaned):
                params["command"] = cleaned
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.96,
                    target_tool="productivity.schedule_reminder",
                    extracted_params=params
                )

        # 0d. YouTube Search & Navigation ("Open YouTube and search for Java DSA tutorials")
        for p in self.YOUTUBE_SEARCH_PATTERNS:
            m_yt = re.search(p, cleaned)
            if m_yt:
                query = m_yt.group(1).strip()
                params["query"] = query
                return IntentClassification(
                    category=IntentCategory.RESEARCH,
                    confidence=0.98,
                    target_tool="youtube.search",
                    extracted_params=params
                )

        # 0e. YouTube Video Selection ("Play the first video", "Open the third result")
        for p in self.YOUTUBE_PLAY_PATTERNS:
            m_yt_play = re.search(p, cleaned)
            if m_yt_play:
                idx = 1
                if "third" in cleaned or "3rd" in cleaned:
                    idx = 3
                elif "second" in cleaned or "2nd" in cleaned:
                    idx = 2
                elif m_yt_play.groups() and m_yt_play.group(1):
                    idx = int(m_yt_play.group(1))
                params["result_index"] = idx
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.97,
                    target_tool="youtube.play_video",
                    extracted_params=params
                )

        # 0f. YouTube Playback Controls ("pause the video", "increase volume", "mute")
        for p in self.YOUTUBE_CONTROL_PATTERNS:
            m_yt_ctrl = re.search(p, cleaned)
            if m_yt_ctrl:
                act = m_yt_ctrl.group(1).lower()
                if "increase" in act or "raise" in act:
                    action_mapped = "volume_up"
                elif "decrease" in act or "lower" in act:
                    action_mapped = "volume_down"
                else:
                    action_mapped = act
                params["action"] = action_mapped
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.96,
                    target_tool="youtube.control_playback",
                    extracted_params=params
                )

        # 0g. Universal Page Analysis ("analyze this page and follow my instructions")
        for p in self.PAGE_ANALYZE_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.RESEARCH,
                    confidence=0.95,
                    target_tool="page.analyze",
                    extracted_params={"url": ""}
                )

        # 1. WhatsApp Messaging Check ("send Hi to my father", "open whatsapp and send hi message to appa")
        wa_recip, wa_msg = self._parse_whatsapp_instruction(text)
        if wa_recip and wa_msg:
            params["recipient"] = wa_recip
            params["message"] = wa_msg
            return IntentClassification(
                category=IntentCategory.SYSTEM_CONTROL,
                confidence=0.96,
                target_tool="whatsapp.prepare_message",
                extracted_params=params
            )

        # 1b. Spotify Track Information Queries ("what song is playing?", "who is the singer?", "how much time is remaining?", "show the current playlist")
        for p in self.SPOTIFY_INFO_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.97,
                    target_tool="spotify.get_current_track",
                    extracted_params={}
                )

        # 1c. Spotify Pause Playback ("pause the music", "pause", "stop the music")
        for p in self.SPOTIFY_PAUSE_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.97,
                    target_tool="spotify.pause",
                    extracted_params={}
                )

        # 1d. Spotify Resume Playback ("resume", "continue playing", "continue")
        for p in self.SPOTIFY_RESUME_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.97,
                    target_tool="spotify.resume",
                    extracted_params={}
                )

        # 1e. Spotify Next Track ("next song", "next", "skip this track", "skip")
        for p in self.SPOTIFY_NEXT_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.97,
                    target_tool="spotify.next",
                    extracted_params={}
                )

        # 1f. Spotify Previous Track ("previous song", "previous", "play that song again", "go back")
        for p in self.SPOTIFY_PREV_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.97,
                    target_tool="spotify.previous",
                    extracted_params={}
                )

        # 1g. Spotify Volume Controls ("increase volume", "reduce volume", "mute the music", "set volume to 80")
        for p in self.SPOTIFY_VOLUME_PATTERNS:
            m_vol = re.search(p, cleaned)
            if m_vol:
                if "mute" in cleaned:
                    params["level"] = 0
                elif m_vol.groups() and m_vol.group(1):
                    params["level"] = int(m_vol.group(1))
                elif any(k in cleaned for k in ["increase", "raise", "turn up"]):
                    params["level"] = 70
                elif any(k in cleaned for k in ["reduce", "decrease", "lower", "turn down"]):
                    params["level"] = 30
                else:
                    params["level"] = 50
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.96,
                    target_tool="spotify.set_volume",
                    extracted_params=params
                )

        # 1h. Spotify Music Play Commands ("play Shape of You", "play songs by Anirudh", "play my favourite playlist", "play Naa Ready", "open spotify and play music")
        for p in self.SPOTIFY_PLAY_PATTERNS:
            m_play = re.search(p, cleaned)
            if m_play:
                q = ""
                if m_play.groups() and m_play.group(1):
                    q = m_play.group(1).strip().strip(" .,!?:;'\"")
                if not q or q in ("music", "spotify"):
                    q = ""
                params["query"] = q
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.96,
                    target_tool="spotify.play",
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

        # 2a. Special User Folders Check ("open my Downloads folder")
        for p in self.FOLDER_PATTERNS:
            m_f = re.search(p, cleaned)
            if m_f:
                folder_name = m_f.group(1).strip()
                params["app_name"] = f"{folder_name} folder"
                params["app_name_or_id"] = f"{folder_name} folder"
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.95,
                    target_tool="open_application",
                    extracted_params=params
                )

        # 2b. Close Application Check ("close Notepad", "quit Chrome")
        for p in self.APP_CLOSE_PATTERNS:
            m_c = re.search(p, cleaned)
            if m_c:
                target_app = m_c.group(1).strip()
                target_app = re.sub(r"\s+(?:please|now|for\s+me)$", "", target_app).strip()
                params["app_name_or_process"] = target_app
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.94,
                    target_tool="computer.close_app",
                    extracted_params=params
                )

        # 2c. Restart Application Check ("restart VS Code")
        for p in self.APP_RESTART_PATTERNS:
            m_r = re.search(p, cleaned)
            if m_r:
                target_app = m_r.group(1).strip()
                target_app = re.sub(r"\s+(?:please|now|for\s+me)$", "", target_app).strip()
                params["app_name_or_process"] = target_app
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.94,
                    target_tool="computer.restart_app",
                    extracted_params=params
                )

        # 2d. Switch Window / Bring to Front Check ("switch to Chrome")
        for p in self.APP_SWITCH_PATTERNS:
            m_s = re.search(p, cleaned)
            if m_s:
                target_app = m_s.group(1).strip()
                target_app = re.sub(r"\s+(?:please|now|for\s+me)$", "", target_app).strip()
                params["app_name_or_window"] = target_app
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.94,
                    target_tool="computer.switch_app",
                    extracted_params=params
                )

        # 2e. Running Applications Check ("what apps are running", "list running apps")
        for p in self.RUNNING_APPS_PATTERNS:
            if re.search(p, cleaned):
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.95,
                    target_tool="computer.get_running_apps",
                    extracted_params={}
                )

        # 2f. Installed Applications Listing ("find all installed browsers", "list installed apps")
        for p in self.INSTALLED_APPS_PATTERNS:
            m_inst = re.search(p, cleaned)
            if m_inst:
                cat = m_inst.group(1).strip() if m_inst.groups() else ""
                cat = re.sub(r"\s+(?:please|now|for\s+me)$", "", cat).strip()
                params["category"] = cat
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.93,
                    target_tool="computer.list_installed_apps",
                    extracted_params=params
                )

        # 2g. Find App by Description ("open the application I use for Python", "open my music player")
        for p in self.APP_BY_DESC_PATTERNS:
            m_desc = re.search(p, cleaned)
            if m_desc:
                desc = m_desc.group(1).strip()
                params["description"] = desc
                return IntentClassification(
                    category=IntentCategory.SYSTEM_CONTROL,
                    confidence=0.93,
                    target_tool="computer.find_app_by_description",
                    extracted_params=params
                )

        # 2h. Application Launch Check
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

        # 2i. Targeted Recursive File Search ("find all PDFs in Downloads", "search python files in desktop")
        for p in self.FILE_SEARCH_PATTERNS:
            m_fs = re.search(p, cleaned)
            if m_fs:
                raw_type = (m_fs.group(1) or "").strip().lower()
                raw_folder = (m_fs.group(2) or "").strip()
                raw_folder = re.sub(r"\s+(?:folder|directory|please|now|for\s+me)$", "", raw_folder).strip()

                ext_map = {
                    "pdf": "*.pdf",
                    "pdfs": "*.pdf",
                    "python": "*.py",
                    "py": "*.py",
                    "word": "*.docx",
                    "doc": "*.docx",
                    "docs": "*.docx",
                    "docx": "*.docx",
                    "excel": "*.xlsx",
                    "sheet": "*.xlsx",
                    "sheets": "*.xlsx",
                    "xlsx": "*.xlsx",
                    "csv": "*.csv",
                    "image": "*.png",
                    "images": "*.png",
                    "png": "*.png",
                    "jpg": "*.jpg",
                    "jpeg": "*.jpg",
                    "text": "*.txt",
                    "txt": "*.txt",
                }
                if raw_type in ext_map:
                    query_val = ext_map[raw_type]
                elif raw_type in ("files", "documents", "all", ""):
                    query_val = ""
                elif raw_type.startswith("*"):
                    query_val = raw_type
                else:
                    query_val = f"*{raw_type}*"

                params["query"] = query_val
                params["root_dir"] = raw_folder.capitalize() if raw_folder else "Downloads"
                return IntentClassification(
                    category=IntentCategory.FILE_OPERATION,
                    confidence=0.95,
                    target_tool="files.recursive_search",
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
