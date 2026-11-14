"""
Google Gemini API Provider (Gemini 1.5 Pro, Flash)
"""

import httpx
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from core.providers.base import BaseLLMProvider, LLMResponse, ToolCallRequest

logger = logging.getLogger("jarvis.providers.gemini")


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> LLMResponse:
        # Convert standard OpenAI message format to Gemini contents format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}]
            })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return LLMResponse(content="", model=self.model)

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        text_content = "".join(p.get("text", "") for p in parts)

        return LLMResponse(
            content=text_content,
            model=self.model,
            raw_response=data
        )

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> AsyncGenerator[str, None]:
        # Fallback to single yield if streaming endpoint not invoked
        res = await self.generate(messages, temperature=temperature, max_tokens=max_tokens)
        yield res.content
