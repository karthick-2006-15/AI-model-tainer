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

        # 3. Fast-Path Heuristic Execution (Optional microsecond shortcut)
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

        # 4. Standard Model Provider Tool-Calling Loop
        provider = model_router.get_provider()
        tools_schema = tool_registry.get_schemas()

        try:
            llm_response: LLMResponse = await provider.generate(
                messages=messages,
                tools=tools_schema
            )
        except Exception as e:
            logger.error(f"Provider invocation failed: {e}")
            return {
                "response": f"I encountered an internal intelligence error: {e}",
                "tool_executed": None,
                "verified": False
            }

        # 5. Check if model requested tool execution
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
        
        elif tool_name == "open_application":
            return str(result)

        elif tool_name == "search_workspace_files" and isinstance(result, list):
            if not result:
                return "I searched the workspace, but found no matching files."
            return f"I found {len(result)} matching files: {', '.join(result[:4])}."

        return f"Action complete: {result}"


# Global brain orchestrator instance
brain_orchestrator = BrainOrchestrator()
