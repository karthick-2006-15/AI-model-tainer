"""
Google Gemini API Provider (Gemini 1.5 Pro, Flash)
Supports Gemini native function declarations and system instructions.
"""

import httpx
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from core.providers.base import BaseLLMProvider, LLMResponse, ToolCallRequest

logger = logging.getLogger("jarvis.providers.gemini")


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def _format_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Maps OpenAI-compatible tool specifications to Gemini function declarations schema."""
        if not tools:
            return None
        declarations = []
        for tool in tools:
            if "function" in tool:
                fn = tool["function"]
                declarations.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {"type": "object", "properties": {}})
                })
            elif "name" in tool:
                declarations.append({
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                })
        if not declarations:
            return None
        return [{"function_declarations": declarations}]

    def _build_payload(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Dict[str, Any]:
        """Constructs Gemini API JSON payload with system_instruction and contents."""
        system_texts: List[str] = []
        contents: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role in ("system", "developer"):
                if content:
                    system_texts.append(content)
                continue

            gemini_role = "user" if role == "user" else "model"
            parts: List[Dict[str, Any]] = []

            # Check if this message represents tool calls from assistant/model
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    parts.append({
                        "functionCall": {
                            "name": tc.get("function", {}).get("name", tc.get("name", "")),
                            "args": tc.get("function", {}).get("arguments", tc.get("arguments", {}))
                        }
                    })

            # Check if this message represents a tool response
            if role in ("tool", "function"):
                gemini_role = "function"
                parts.append({
                    "functionResponse": {
                        "name": msg.get("name", "tool"),
                        "response": {
                            "name": msg.get("name", "tool"),
                            "content": content
                        }
                    }
                })
            elif content or not parts:
                parts.append({"text": content or ""})

            contents.append({
                "role": gemini_role,
                "parts": parts
            })

        if not contents:
            contents.append({
                "role": "user",
                "parts": [{"text": ""}]
            })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        if system_texts:
            payload["system_instruction"] = {
                "parts": [{"text": "\n\n".join(system_texts)}]
            }

        gemini_tools = self._format_tools(tools)
        if gemini_tools:
            payload["tools"] = gemini_tools

        return payload

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs
    ) -> LLMResponse:
        payload = self._build_payload(messages, tools=tools, temperature=temperature, max_tokens=max_tokens)
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return LLMResponse(content="", model=self.model, raw_response=data)

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        text_parts: List[str] = []
        tool_calls: List[ToolCallRequest] = []

        for p in parts:
            if "text" in p and p["text"]:
                text_parts.append(p["text"])
            if "functionCall" in p:
                fc = p["functionCall"]
                call_id = f"call_{uuid.uuid4().hex[:8]}"
                args = fc.get("args", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                tool_calls.append(ToolCallRequest(
                    id=call_id,
                    tool_name=fc.get("name", ""),
                    arguments=args
                ))

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        finish_reason = candidate.get("finishReason", "stop").lower()

        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            raw_response=data,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=self.model,
            finish_reason=finish_reason
        )

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"
        payload = self._build_payload(messages, tools=tools, temperature=temperature, max_tokens=max_tokens)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        res = await self.generate(messages, tools=tools, temperature=temperature, max_tokens=max_tokens)
                        yield res.content
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        line_data = line[6:].strip()
                        try:
                            chunk_json = json.loads(line_data)
                            candidates = chunk_json.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    if "text" in p and p["text"]:
                                        yield p["text"]
                        except Exception:
                            continue
            except Exception as e:
                logger.warning(f"Gemini SSE streaming failed ({e}), falling back to generate")
                res = await self.generate(messages, tools=tools, temperature=temperature, max_tokens=max_tokens)
                yield res.content

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Convenience alias for stream to satisfy generate_stream contract."""
        async for chunk in self.stream(messages, tools=tools, temperature=temperature, max_tokens=max_tokens, **kwargs):
            yield chunk
