"""
Local Ollama Provider (Llama 3, Qwen 2.5, Mistral)
100% offline, local GPU/CPU execution with zero subscription costs.
"""

import httpx
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from core.providers.base import BaseLLMProvider, LLMResponse, ToolCallRequest

logger = logging.getLogger("jarvis.providers.ollama")


class OllamaProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

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
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.warning(f"Ollama local execution failed: {e}")
                return LLMResponse(
                    content="Local Ollama daemon is offline. Please start Ollama or configure a cloud API key.",
                    model=self.model
                )

        msg = data.get("message", {})
        content = msg.get("content", "")
        tool_calls: List[ToolCallRequest] = []

        if "tool_calls" in msg and msg["tool_calls"]:
            for i, tc in enumerate(msg["tool_calls"]):
                tool_calls.append(ToolCallRequest(
                    id=f"ollama_tc_{i}",
                    tool_name=tc.get("function", {}).get("name", ""),
                    arguments=tc.get("function", {}).get("arguments", {})
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response=data,
            model=data.get("model", self.model)
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
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        delta = chunk.get("message", {}).get("content", "")
                        if delta:
                            yield delta
            except Exception as e:
                yield f"[Ollama offline: {e}]"
