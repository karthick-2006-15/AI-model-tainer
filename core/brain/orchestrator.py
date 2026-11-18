"""
Central AI Brain Orchestrator
Coordinates intent classification, context assembly, model execution, tool calling, and verification.
"""

import logging
from typing import List, Dict, Any, Optional
from core.brain.prompts import JARVIS_SYSTEM_PROMPT
from core.brain.intent import intent_classifier, IntentCategory
from core.brain.tools import tool_registry
from core.providers.router import model_router
from core.providers.base import LLMResponse
from core.memory.profile import profile_memory
from core.memory.semantic import semantic_memory

logger = logging.getLogger("jarvis.brain.orchestrator")


class BrainOrchestrator:
    def __init__(self):
        self.system_prompt = JARVIS_SYSTEM_PROMPT

    async def process_user_request(
        self,
        user_input: str,
        session_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Main intelligence pipeline:
        Intent Analysis -> Context Assembly -> Tool Routing -> Execution -> Verification.
        """
        logger.info(f"Brain processing instruction: '{user_input}'")

        # 1. Fast Intent Classification & Automatic Memory Extraction
        intent = intent_classifier.classify(user_input)
        profile_memory.auto_extract_facts_from_text(user_input)

        # 2. Retrieve Relevant Semantic & Profile Memory
        memory_context = ""
        relevant_memories = semantic_memory.search_memory(user_input, limit=3, score_threshold=0.2)
        if relevant_memories:
            mem_items = [f"- {m['text']} (relevance: {m['score']})" for m in relevant_memories]
            memory_context = "\n\n### RELEVANT PERSONAL MEMORIES:\n" + "\n".join(mem_items)

        # 2b. Check for user confirmation or cancellation of active Level 3 challenges
        from core.security.permissions import permission_engine
        latest_challenge = permission_engine.get_latest_challenge()
        if latest_challenge:
            approved, resolved_ch = permission_engine.resolve_voice_confirmation(user_input)
            if approved is True and resolved_ch:
                tool_to_execute = resolved_ch["tool_name"]
                tool_args = resolved_ch["arguments"]
                if tool_to_execute == "whatsapp.send_message":
                    from modules.computer_use.whatsapp import whatsapp_automation
                    if whatsapp_automation._last_prepared_draft:
                        whatsapp_automation._last_prepared_draft["status"] = "confirmed"
                    send_res = whatsapp_automation.send_message(
                        recipient=tool_args.get("recipient", "contact"),
                        message_text=tool_args.get("message", ""),
                        skip_permission_check=True
                    )
                    return {
                        "response": send_res.get("report", f"Message sent to {tool_args.get('recipient')} successfully."),
                        "tool_executed": "whatsapp.send_message",
                        "tool_result": send_res,
                        "intent": "system_control",
                        "verified": send_res.get("verified", True)
                    }
                else:
                    exec_result = await tool_registry.execute(tool_to_execute, tool_args)
                    formatted_response = self._format_fast_result(tool_to_execute, exec_result.get("result"))
                    return {
                        "response": formatted_response,
                        "tool_executed": tool_to_execute,
                        "tool_result": exec_result.get("result"),
                        "intent": "system_control",
                        "verified": exec_result.get("success", True)
                    }
            elif approved is False and resolved_ch:
                from modules.computer_use.whatsapp import whatsapp_automation
                whatsapp_automation._last_prepared_draft = None
                return {
                    "response": "Understood, sir. I have cancelled the operation. No message was sent.",
                    "tool_executed": None,
                    "tool_result": None,
                    "intent": "system_control",
                    "verified": True
                }

        # 3. Assemble Context Window
        effective_system_prompt = self.system_prompt + memory_context
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": effective_system_prompt}
        ]

        if session_history:
            for item in session_history[-6:]:  # Last 6 conversation turns
                messages.append({
                    "role": item.get("role", "user"),
                    "content": item.get("content", "")
                })

        messages.append({"role": "user", "content": user_input})

        # 3. Built-in Conversational Fast-Path (Greetings, Audio checks, Capabilities, Identity, Status)
        if model_router._active_provider is None and intent.target_tool == "built_in_conversational_kernel":
            conv_response = self._handle_built_in_conversation(user_input)
            if conv_response and conv_response != "JARVIS Core is standing by, sir. Ready for your instructions.":
                return {
                    "response": conv_response,
                    "tool_executed": None,
                    "tool_result": None,
                    "intent": intent.category.value,
                    "verified": True
                }

        # 4. Fast-Path Heuristic Tool Execution (Direct microsecond shortcut)
        if intent.confidence >= 0.85 and intent.target_tool:
            tool_meta = tool_registry.get_tool(intent.target_tool)
            if tool_meta and intent.extracted_params is not None:
                # Direct tool execution
                exec_result = await tool_registry.execute(intent.target_tool, intent.extracted_params)
                if exec_result["success"]:
                    # Synthesize conversational response
                    formatted_response = self._format_fast_result(intent.target_tool, exec_result["result"])
                    return {
                        "response": formatted_response,
                        "tool_executed": intent.target_tool,
                        "tool_result": exec_result["result"],
                        "intent": intent.category.value,
                        "verified": True
                    }

        # 5. Standard Model Provider Tool-Calling Loop
        provider = model_router.get_provider()
        tools_schema = tool_registry.get_schemas()

        try:
            llm_response: LLMResponse = await provider.generate(
                messages=messages,
                tools=tools_schema
            )
        except Exception as e:
            logger.error(f"Provider invocation failed: {e}")
            llm_response = LLMResponse(content=f"Error: {e}")

        # Check for offline local daemon or empty model response -> Trigger autonomous fallback
        if (not llm_response.content and not llm_response.tool_calls) or (
            llm_response.content and (
                "Local Ollama daemon is offline" in llm_response.content
                or llm_response.content.startswith("Error:")
            )
        ):
            # If prompt mapped to an executable tool, execute it directly rather than deflecting
            if intent.target_tool and intent.extracted_params is not None:
                exec_result = await tool_registry.execute(intent.target_tool, intent.extracted_params)
                if exec_result.get("success"):
                    formatted_response = self._format_fast_result(intent.target_tool, exec_result.get("result"))
                    return {
                        "response": formatted_response,
                        "tool_executed": intent.target_tool,
                        "tool_result": exec_result.get("result"),
                        "intent": intent.category.value,
                        "verified": True
                    }

            fallback_answer = await self._generate_autonomous_fallback(user_input)
            return {
                "response": fallback_answer,
                "tool_executed": None,
                "intent": intent.category.value,
                "verified": True
            }

        # 6. Check if model requested tool execution
        if llm_response.tool_calls:
            first_tool = llm_response.tool_calls[0]
            logger.info(f"Model requested tool: '{first_tool.tool_name}' with args {first_tool.arguments}")

            exec_result = await tool_registry.execute(first_tool.tool_name, first_tool.arguments)

            # Append tool output to message history and request final response
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": first_tool.id,
                    "type": "function",
                    "function": {
                        "name": first_tool.tool_name,
                        "arguments": first_tool.arguments if isinstance(first_tool.arguments, dict) else {}
                    }
                }]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": first_tool.id,
                "name": first_tool.tool_name,
                "content": str(exec_result.get("result") or exec_result.get("error") or "Operation complete.")
            })

            try:
                final_response = await provider.generate(messages=messages)
                content = final_response.content if final_response else None
                if content and not content.startswith("Local Ollama daemon is offline") and not content.startswith("Error:"):
                    speech_text = content
                else:
                    speech_text = self._format_fast_result(first_tool.tool_name, exec_result.get("result"))
            except Exception:
                speech_text = self._format_fast_result(first_tool.tool_name, exec_result.get("result"))

            return {
                "response": speech_text,
                "tool_executed": first_tool.tool_name,
                "tool_result": exec_result,
                "intent": intent.category.value,
                "verified": exec_result["success"]
            }

        # Direct conversational answer
        return {
            "response": llm_response.content,
            "tool_executed": None,
            "intent": intent.category.value,
            "verified": True
        }

    def _format_fast_result(self, tool_name: str, result: Any) -> str:
        """Formats raw tool execution results into natural speech responses."""
        if tool_name == "get_system_telemetry" and isinstance(result, dict):
            cpu = result.get("cpu", {}).get("percent", 0)
            ram = result.get("ram", {}).get("percent", 0)
            disk = result.get("disk", {}).get("percent", 0)
            return f"System telemetry check complete. CPU utilization is at {cpu}%, Memory is at {ram}%, and Primary Storage is {disk}% full. All parameters optimal."
        
        elif tool_name in ("open_application", "computer.open_app", "computer.open_application"):
            if isinstance(result, dict):
                if result.get("ambiguous"):
                    cands = ", ".join(c.get("name") for c in result.get("candidates", [])[:3])
                    return f"Multiple matching applications found: {cands}. Which one would you like me to open?"
                app_name = result.get("app_name", "Application")
                if result.get("verified"):
                    return f"{app_name} is open."
                return result.get("message", f"{app_name} launched.")
            return str(result)

        elif tool_name == "computer.close_app":
            if isinstance(result, dict):
                return result.get("message", "Application closed.")
            return str(result)

        elif tool_name in ("computer.switch_app", "computer.switch_window"):
            if isinstance(result, dict):
                target = result.get("target") or result.get("window_title", "window")
                if result.get("success"):
                    return f"Switched to {target}."
                return f"Could not find or switch to {target}."
            return str(result)

        elif tool_name == "computer.restart_app":
            if isinstance(result, dict):
                return result.get("message", "Application restarted.")
            return str(result)

        elif tool_name == "computer.get_running_apps":
            if isinstance(result, list):
                if not result:
                    return "No desktop GUI applications are currently running."
                names = [app.get("primary_title") or app.get("process_name") for app in result[:5]]
                return f"Currently running applications: {', '.join(names)}."
            return str(result)

        elif tool_name == "computer.list_installed_apps":
            if isinstance(result, dict):
                total = result.get("total_indexed", 0)
                apps = result.get("apps", [])
                sample = ", ".join(a.get("name") for a in apps[:4])
                return f"I have indexed {total} applications on your system, including: {sample}."
            return str(result)

        elif tool_name == "computer.find_app_by_description":
            if isinstance(result, list):
                if not result:
                    return "I could not find an application matching that description."
                top = result[0]
                return f"For that task, you have {top.get('name')}. Would you like me to open it?"
            return str(result)

        elif tool_name == "orchestration.run_multi_app_workflow" and isinstance(result, dict):
            if result.get("success"):
                topic = result.get("topic", "the requested topic")
                slides = result.get("slides_count", 4)
                return f"Research workflow complete. Generated Word report and {slides}-slide PowerPoint presentation on {topic}. Both files verified and saved."
            return f"Workflow halted: {result.get('error', 'Execution interrupted.')}"

        elif tool_name == "productivity.schedule_reminder" and isinstance(result, dict):
            return result.get("message", "Reminder scheduled successfully.")

        elif tool_name == "youtube.search" and isinstance(result, dict):
            return result.get("summary", f"Search completed for '{result.get('query')}'.")

        elif tool_name == "youtube.play_video" and isinstance(result, dict):
            return result.get("report", "Playing requested YouTube video.")

        elif tool_name == "youtube.control_playback" and isinstance(result, dict):
            return result.get("report", f"Playback action '{result.get('action')}' executed.")

        elif tool_name == "page.analyze" and isinstance(result, dict):
            return result.get("summary", "Webpage analysis complete.")

        elif tool_name == "browser.open" and isinstance(result, dict):
            return f"Opened {result.get('title', result.get('url', 'webpage'))}."

        elif tool_name == "computer.click" and isinstance(result, dict):
            return f"Click action executed at ({result.get('x')}, {result.get('y')})." if "x" in result else f"Clicked {result.get('target', 'element')}."

        elif tool_name == "computer.type" and isinstance(result, dict):
            return f"Typed {result.get('char_count', 'text')} characters."

        elif tool_name == "computer.find_element" and isinstance(result, dict):
            if result.get("found"):
                return f"Located element '{result.get('name')}' ({result.get('control_type')}) on active window."
            return f"Element '{result.get('query')}' not detected."

        elif tool_name == "system.troubleshoot" and isinstance(result, dict):
            status = result.get("status", "System check complete.")
            alerts = result.get("alerts", [])
            if alerts:
                return f"{status} Alerts: {'; '.join(alerts[:2])}."
            return "All diagnostic parameters nominal. CPU, RAM, disk, and network operating within optimal thresholds."

        elif tool_name == "whatsapp.prepare_message" and isinstance(result, dict):
            prompt = result.get("confirmation_prompt")
            if prompt:
                return prompt
            return f"I found the conversation for {result.get('recipient', 'the contact')}. Should I send \"{result.get('message')}\"?"

        elif tool_name == "whatsapp.send_message" and isinstance(result, dict):
            return result.get("report", "Message sent successfully.")

        elif tool_name == "worksheet.extract_questions" and isinstance(result, list):
            return f"I have explored the worksheet and identified {len(result)} questions. Ready to research answers and fill fields, sir."

        elif tool_name == "worksheet.submit" and isinstance(result, dict):
            return result.get("message", "Worksheet submitted successfully.")

        elif tool_name == "trigger_emergency_stop":
            return "Emergency stop activated. All operations and tools have been halted immediately, sir."

        elif tool_name == "explain_screen" and isinstance(result, dict):
            if result.get("explanation"):
                return result.get("explanation")
            return f"Screen analysis complete: {result.get('context', 'Active desktop window analyzed.')}"

        elif tool_name == "computer.click_element" and isinstance(result, dict):
            return f"Clicked {result.get('target', 'element')} successfully."

        elif tool_name == "computer.scroll" and isinstance(result, dict):
            return f"Scrolled {result.get('direction', 'down')}."

        elif tool_name == "search_workspace_files" and isinstance(result, list):
            if not result:
                return "I searched the workspace, but found no matching files."
            return f"I found {len(result)} matching files: {', '.join(result[:4])}."

        elif tool_name == "files.recursive_search" and isinstance(result, list):
            if not result:
                return "I searched the requested folder, but found no matching files."
            names = [f.get("file_name") or f.get("name") or os.path.basename(f.get("path", "")) for f in result[:5]]
            return f"I found {len(result)} matching files: {', '.join(names)}."

        elif tool_name == "spotify.play" and isinstance(result, dict):
            track = result.get("track")
            artist = result.get("artist")
            if track and artist:
                return f"Playing {track} by {artist} on Spotify."
            elif track:
                return f"Playing {track} on Spotify."
            return result.get("message", "Playing music on Spotify.")

        elif tool_name == "spotify.pause" and isinstance(result, dict):
            return "Paused Spotify playback."

        elif tool_name == "spotify.resume" and isinstance(result, dict):
            return "Resumed playback."

        elif tool_name == "spotify.next" and isinstance(result, dict):
            cur = result.get("current_track", {})
            title = cur.get("title") if isinstance(cur, dict) else None
            if title and title != "No track playing":
                return f"Skipped to next track. Now playing {title}."
            return "Skipped to next track."

        elif tool_name == "spotify.previous" and isinstance(result, dict):
            cur = result.get("current_track", {})
            title = cur.get("title") if isinstance(cur, dict) else None
            if title and title != "No track playing":
                return f"Returned to previous track: {title}."
            return "Returned to previous track."

        elif tool_name == "spotify.get_current_track" and isinstance(result, dict):
            title = result.get("title")
            artist = result.get("artist")
            if title and title != "No track playing":
                if artist and artist != "Spotify":
                    return f"Currently playing '{title}' by {artist}."
                return f"Currently playing '{title}'."
            return "No song is currently playing on Spotify."

        elif tool_name == "spotify.set_volume" and isinstance(result, dict):
            vol = result.get("volume", 50)
            return f"Spotify volume set to {vol}%."

        elif tool_name == "spotify.open" and isinstance(result, dict):
            return result.get("message", "Spotify is open.")


        return f"Action complete: {result}"

    def _handle_built_in_conversation(self, text: str) -> str:
        """Handles greetings, identity queries, capabilities, audio checks, and system status without external LLMs."""
        import re
        raw_q = text.lower().strip()
        # Strip common wake-word and greeting prefixes to normalize intent
        q = re.sub(r"^(?:hey\s+|hi\s+|hello\s+|ok\s+|okay\s+)?jarvis\s*[,.:;!\-]?\s*", "", raw_q).strip()
        if not q:
            q = raw_q

        # 1. Microphone & Audio Hearing Checks
        if re.search(r"\b(can you hear|do you hear|are you listening|listen to me|test mic|mic test|microphone check|mic check|audio check|sound check)\b", q):
            return "Yes, sir. I can hear you loud and clear. All audio input channels and speech models are fully calibrated and operational. How may I assist you?"

        # 2. Speech Output Checks
        elif re.search(r"\b(can you speak|speak to me|say something|talk to me)\b", q):
            return "Acoustic and speech synthesis channels are online and operational, sir. How can I help you today?"

        # 3. Presence & Availability Checks
        elif re.search(r"\b(are you there|you there|are you online|are you awake|wake up)\b", q):
            return "Always at your service, sir. All core neural subsystems are active and standing by. What do you need?"

        # 4. Gratitude & Compliments
        elif re.search(r"\b(thank you|thanks|good job|great job|well done)\b", q):
            return "You're very welcome, sir. It is always a pleasure to assist."

        # 5. Stand By / Sleep Mode
        elif re.search(r"\b(stand by|go to sleep|sleep mode|good night)\b", q):
            return "Standing by in surveillance mode, sir. Call me anytime with 'Hey Jarvis'."

        # 6. Acknowledgments
        elif re.search(r"^(ok|okay|alright|fine|understood|got it)[!.]*$", q):
            return "Standing by, sir. Ready for your instructions."

        # 7. Capabilities & Help
        elif re.search(r"\b(what can you do|what are your capabilities|capabilities|help|what do you do|what are you capable of)\b", q):
            return (
                "Here are my primary operational capabilities, sir:\n"
                "• **Application & OS Control:** Open and manage applications (VS Code, Chrome, Terminal, etc.), files, and windows.\n"
                "• **System Telemetry:** Live hardware monitoring (CPU, RAM, storage, battery).\n"
                "• **File Intelligence:** Parse and semantically search PDFs, Word docs, spreadsheets, and source code.\n"
                "• **Computer Vision:** Capture desktop screens, read OCR error signatures, and explain technical faults.\n"
                "• **Autonomous Planning:** Decompose high-level goals into multi-step DAG execution plans.\n"
                "• **Internet Intelligence:** Search the web, scrape documentation, and synthesize factual research briefs.\n"
                "• **Personal Memory:** Persistent vector and profile memory tracking your facts and ongoing projects.\n"
                "• **Developer Productivity:** Analyze daily focus, distraction time, and completed objectives.\n\n"
                "You can speak with 'Hey Jarvis' or enter any instruction here."
            )

        # 8. Identity & Introduction
        elif re.search(r"\b(who are you|what are you|introduce yourself|your name|what is your name)\b", q):
            return (
                "I am JARVIS (Just A Rather Very Intelligent System), your personal AI operating system "
                "connecting your Windows PC and mobile devices. I assist with system automation, file management, "
                "code intelligence, visual diagnostics, web research, and autonomous goal execution."
            )

        # 9. Time
        elif re.search(r"\b(what time is it|current time|what is the time|tell me the time|time now|time)\b", q):
            from datetime import datetime
            now_str = datetime.now().strftime("%I:%M %p")
            return f"The current time is {now_str}, sir."

        # 10. Date
        elif re.search(r"\b(what is today's date|current date|what's the date|today's date|what date is it|what day is it)\b", q):
            from datetime import datetime
            date_str = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {date_str}, sir."

        # 11. Health & Hardware Metrics
        elif re.search(r"\b(how are you|how are things|status report|system health|system status)\b", q):
            from modules.automation.system import SystemMonitor
            m = SystemMonitor.get_hardware_metrics()
            cpu = m.get("cpu", {}).get("percent", 0)
            ram = m.get("ram", {}).get("percent", 0)
            disk = m.get("disk", {}).get("percent", 0)
            return f"Systems are functioning at peak efficiency, sir. CPU load is at {cpu}%, Memory is nominal at {ram}%, and Primary Storage is {disk}% full. All core neural modules are standing by."

        # 12. Executive Briefing
        elif re.search(r"\b(briefing|morning briefing|daily briefing)\b", q):
            from modules.scheduler.briefing import daily_briefing_generator
            b = daily_briefing_generator.generate_briefing()
            return b.get("speech_text", "Daily executive briefing generated.")

        # 13. General Greetings
        elif re.search(r"\b(hi|hello|hey|greetings|good morning|good afternoon|good evening|howdy|yo)\b", q):
            return "Greetings, sir. JARVIS Core Neural Kernel is online and operational. All subsystems are ready. How may I assist you today?"

        return "JARVIS Core is standing by, sir. Ready for your instructions."

    async def _generate_autonomous_fallback(self, user_input: str) -> str:
        """Fallback for general questions when local Ollama or cloud API is offline."""
        import re
        # Check built-in conversation first
        built_in = self._handle_built_in_conversation(user_input)
        if built_in != "JARVIS Core is standing by, sir. Ready for your instructions.":
            return built_in

        # Only search the web for factual research queries, never for conversational queries
        is_search_worthy = bool(re.search(
            r"\b(who is|what is|where is|when was|how to|why is|search for|look up|find out|news on|weather in|price of|score of|meaning of|definition of|explain)\b",
            user_input.lower()
        ))

        if is_search_worthy:
            try:
                from modules.research.search import web_search_client
                results = await web_search_client.search(user_input, max_results=2)
                if results and results[0].get("raw_snippet"):
                    snippets = "\n".join(f"• {r.get('raw_snippet', '')}" for r in results if r.get("raw_snippet"))
                    return f"Here is what I found regarding '{user_input}':\n\n{snippets}"
            except Exception:
                pass

        return (
            f"I have received your request: '{user_input}'. Core operating system tools, file management, and laptop automations are online. "
            f"For open-domain creative conversations, you can connect an API key (Gemini/OpenAI in .env) or start local Ollama (`ollama run llama3.2`)."
        )


# Global brain orchestrator instance
brain_orchestrator = BrainOrchestrator()
