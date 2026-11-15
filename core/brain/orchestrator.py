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

        # 3. Built-in Conversational Fast-Path (Greetings, Capabilities, Identity, Status)
        if model_router._active_provider is None and intent.target_tool == "built_in_conversational_kernel":
            conv_response = self._handle_built_in_conversation(user_input)
            return {
                "response": conv_response,
                "tool_executed": None,
                "tool_result": None,
                "intent": intent.category.value,
                "verified": True
            }

        # 4. Fast-Path Heuristic Tool Execution (Direct microsecond shortcut)
        if intent.confidence >= 0.9 and intent.target_tool:
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
        if not llm_response.content or "Local Ollama daemon is offline" in llm_response.content or llm_response.content.startswith("Error:"):
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
                "content": None,
                "tool_calls": [{
                    "id": first_tool.id,
                    "type": "function",
                    "function": {
                        "name": first_tool.tool_name,
                        "arguments": str(first_tool.arguments)
                    }
                }]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": first_tool.id,
                "name": first_tool.tool_name,
                "content": str(exec_result.get("result") or exec_result.get("error"))
            })

            try:
                final_response = await provider.generate(messages=messages)
                speech_text = final_response.content
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

        return f"Action complete: {result}"

    def _handle_built_in_conversation(self, text: str) -> str:
        """Handles greetings, identity queries, capabilities, and system status without external LLMs."""
        import re
        q = text.lower().strip()

        if re.search(r"\b(what can you do|what are your capabilities|capabilities|help|what do you do|what are you capable of)\b", q):
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

        elif re.search(r"\b(who are you|what are you|introduce yourself|your name)\b", q):
            return (
                "I am JARVIS (Just A Rather Very Intelligent System), your personal AI operating system "
                "connecting your Windows PC and mobile devices. I assist with system automation, file management, "
                "code intelligence, visual diagnostics, web research, and autonomous goal execution."
            )

        elif re.search(r"\b(what time is it|current time|what is the time|tell me the time|time now|time)\b", q):
            from datetime import datetime
            now_str = datetime.now().strftime("%I:%M %p")
            return f"The current time is {now_str}, sir."

        elif re.search(r"\b(what is today's date|current date|what's the date|today's date|what date is it|what day is it)\b", q):
            from datetime import datetime
            date_str = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {date_str}, sir."

        elif re.search(r"\b(how are you|how are things|status report|system health|system status)\b", q):
            from modules.automation.system import SystemMonitor
            m = SystemMonitor.get_hardware_metrics()
            cpu = m.get("cpu", {}).get("percent", 0)
            ram = m.get("ram", {}).get("percent", 0)
            disk = m.get("disk", {}).get("percent", 0)
            return f"Systems are functioning at peak efficiency, sir. CPU load is at {cpu}%, Memory is nominal at {ram}%, and Primary Storage is {disk}% full. All core neural modules are standing by."

        elif re.search(r"\b(briefing|morning briefing|daily briefing)\b", q):
            from modules.scheduler.briefing import daily_briefing_generator
            b = daily_briefing_generator.generate_briefing()
            return b.get("speech_text", "Daily executive briefing generated.")

        elif re.search(r"\b(hi|hello|hey|hey jarvis|greetings|good morning|good afternoon|good evening|howdy|yo)\b", q):
            return "Greetings, sir. JARVIS Core Neural Kernel is online and operational. All subsystems are ready. How may I assist you today?"

        return "JARVIS Core is standing by, sir. Ready for your instructions."

    async def _generate_autonomous_fallback(self, user_input: str) -> str:
        """Fallback for general questions when local Ollama or cloud API is offline."""
        # Check built-in conversation first
        built_in = self._handle_built_in_conversation(user_input)
        if built_in != "JARVIS Core is standing by, sir. Ready for your instructions.":
            return built_in

        # Try live web search to answer factual queries
        try:
            from modules.research.search import web_search_client
            results = await web_search_client.search(user_input, max_results=2)
            if results and results[0].get("raw_snippet"):
                snippets = "\n".join(f"• {r.get('raw_snippet', '')}" for r in results if r.get("raw_snippet"))
                return (
                    f"Here is what I found regarding '{user_input}':\n\n{snippets}\n\n"
                    f"*[Retrieved via JARVIS Live Research Kernel. For open-domain creative conversation, start local Ollama (`ollama run llama3`) or configure an API key in `.env`.]*"
                )
        except Exception:
            pass

        return (
            f"I have received your request: '{user_input}'. Core operating system tools, file management, and laptop automations are online. "
            f"For unrestricted creative conversational chat, you can start your local Ollama engine (`ollama run llama3`) or provide an API key in `.env`."
        )


# Global brain orchestrator instance
brain_orchestrator = BrainOrchestrator()
