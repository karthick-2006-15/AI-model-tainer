"""
Anthropic Claude API Provider (Claude 3.5 Sonnet, Claude 3.5 Haiku)
Interacts with the Anthropic Messages API with native tool use and streaming.
"""

import httpx
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from core.providers.base import BaseLLMProvider, LLMResponse, ToolCallRequest, ToolCall, LLMProvider

logger = logging.getLogger("jarvis.providers.anthropic")


class AnthropicProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: str = "https://api.anthropic.com/v1"
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _format_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Maps OpenAI-compatible tool specifications to Anthropic tool schemas."""
        if not tools:
            return None
        anthropic_tools = []
        for tool in tools:
            if "function" in tool:
                fn = tool["function"]
                anthropic_tools.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}})
                })
            elif "name" in tool:
                anthropic_tools.append({
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters", {"type": "object", "properties": {}})
                })
        return anthropic_tools if anthropic_tools else None

    def _build_messages_payload(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Dict[str, Any]:
        """Constructs Anthropic Messages API payload, separating system instructions."""
        system_texts: List[str] = []
        anthropic_messages: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role in ("system", "developer"):
                if content:
                    system_texts.append(content)
                continue

            mapped_role = "assistant" if role in ("assistant", "model") else "user"

            # Check if this message has tool call outputs or tool results
            if role in ("tool", "function"):
                mapped_role = "user"
                block_content = [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id", f"call_{uuid.uuid4().hex[:8]}"),
                    "content": content
                }]
                anthropic_messages.append({
                    "role": mapped_role,
                    "content": block_content
                })
                continue

            # Check if assistant message contained tool calls
            if "tool_calls" in msg and msg["tool_calls"]:
                blocks: List[Dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    args = fn.get("arguments", tc.get("arguments", {}))
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                        "name": fn.get("name", tc.get("name", "")),
                        "input": args
                    })
                anthropic_messages.append({
                    "role": "assistant",
                    "content": blocks
                })
                continue

            # Merge consecutive same-role text messages to adhere to Anthropic alternation rules
            if anthropic_messages and anthropic_messages[-1]["role"] == mapped_role and isinstance(anthropic_messages[-1]["content"], str):
                anthropic_messages[-1]["content"] += f"\n\n{content}"
            else:
                anthropic_messages.append({
                    "role": mapped_role,
                    "content": content or ""
                })

        if not anthropic_messages:
            anthropic_messages.append({
                "role": "user",
                "content": ""
            })

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        if system_texts:
            payload["system"] = "\n\n".join(system_texts)

        anthropic_tools = self._format_tools(tools)
        if anthropic_tools:
            payload["tools"] = anthropic_tools

        return payload

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs
    ) -> LLMResponse:
        payload = self._build_messages_payload(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens
        )
        url = f"{self.base_url}/messages"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()

        text_chunks: List[str] = []
        tool_calls: List[ToolCallRequest] = []

        for block in data.get("content", []):
            block_type = block.get("type")
            if block_type == "text":
                text_chunks.append(block.get("text", ""))
            elif block_type == "tool_use":
                call_id = block.get("id", f"call_{uuid.uuid4().hex[:8]}")
                tool_name = block.get("name", "")
                args = block.get("input", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                tool_calls.append(ToolCallRequest(
                    id=call_id,
                    tool_name=tool_name,
                    arguments=args
                ))

        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        stop_reason = data.get("stop_reason") or "stop"

        return LLMResponse(
            content="".join(text_chunks),
            tool_calls=tool_calls,
            raw_response=data,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=data.get("model", self.model),
            finish_reason=stop_reason
        )

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        payload = self._build_messages_payload(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens
        )
        payload["stream"] = True
        url = f"{self.base_url}/messages"

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream("POST", url, json=payload, headers=self._headers()) as response:
                    if response.status_code != 200:
                        res = await self.generate(messages, tools=tools, temperature=temperature, max_tokens=max_tokens)
                        yield res.content
                        return

                    async for raw_line in response.aiter_lines():
                        for line in raw_line.splitlines():
                            line = line.strip()
                            if not line or not line.startswith("data: "):
                                continue
                            line_data = line[6:].strip()
                            if line_data == "[DONE]":
                                break
                            try:
                                event_data = json.loads(line_data)
                                event_type = event_data.get("type")
                                if event_type == "content_block_delta":
                                    delta = event_data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        yield delta.get("text", "")
                            except Exception:
                                continue
            except Exception as e:
                logger.warning(f"Anthropic streaming failed ({e}), falling back to generate")
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
