"""
OpenAI & Compatible API Provider (GPT-4o, GPT-4o-mini, Groq, DeepSeek)
"""

import httpx
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from core.providers.base import BaseLLMProvider, LLMResponse, ToolCallRequest

logger = logging.getLogger("jarvis.providers.openai")


class OpenAIProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1"
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> LLMResponse:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        message = choice["message"]
        content = message.get("content") or ""

        tool_calls: List[ToolCallRequest] = []
        if "tool_calls" in message and message["tool_calls"]:
            for tc in message["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except Exception:
                    args = {}
                tool_calls.append(ToolCallRequest(
                    id=tc["id"],
                    tool_name=tc["function"]["name"],
                    arguments=args
                ))

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response=data,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            model=data.get("model", self.model),
            finish_reason=choice.get("finish_reason", "stop")
        )

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    line_data = line[6:].strip()
                    if line_data == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(line_data)
                        delta = chunk_json["choices"][0].get("delta", {})
                        text_chunk = delta.get("content", "")
                        if text_chunk:
                            yield text_chunk
                    except Exception:
                        continue
