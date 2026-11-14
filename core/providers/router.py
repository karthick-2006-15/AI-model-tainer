"""
LLM Provider Router & Factory
Selects the optimal active model provider based on user settings, task complexity, and network availability.
"""

import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from core.config.settings import settings
from core.providers.base import BaseLLMProvider, LLMResponse
from core.providers.openai_provider import OpenAIProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.ollama_provider import OllamaProvider

logger = logging.getLogger("jarvis.providers.router")


class MockProvider(BaseLLMProvider):
    """Deterministic mock provider used for unit tests and offline CI."""
    def __init__(self, response_text: str = "JARVIS Subsystems Operational."):
        self.response_text = response_text

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> LLMResponse:
        return LLMResponse(content=self.response_text, model="mock-model")

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> AsyncGenerator[str, None]:
        for word in self.response_text.split():
            yield word + " "


class ModelRouter:
    def __init__(self):
        self._active_provider: Optional[BaseLLMProvider] = None

    def get_provider(self, fast_tier: bool = False) -> BaseLLMProvider:
        """Returns the appropriate provider based on credentials and tier."""
        if self._active_provider:
            return self._active_provider

        # 1. Cloud OpenAI / Compatible
        if settings.OPENAI_API_KEY:
            model = "gpt-4o-mini" if fast_tier else "gpt-4o"
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=model)

        # 2. Cloud Gemini
        if settings.GEMINI_API_KEY:
            model = "gemini-1.5-flash" if fast_tier else "gemini-1.5-pro"
            return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=model)

        # 3. Default Local Offline Ollama
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.DEFAULT_LOCAL_MODEL
        )

    def set_override_provider(self, provider: BaseLLMProvider):
        """Allows test harnesses to inject a mock provider."""
        self._active_provider = provider

    def clear_override(self):
        self._active_provider = None


# Global singleton instance
model_router = ModelRouter()
