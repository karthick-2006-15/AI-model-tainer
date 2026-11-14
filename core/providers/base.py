"""
JARVIS LLM Provider Abstraction Layer
Unified interface for OpenAI, Google Gemini, Anthropic, and Local Ollama models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator


@dataclass
class ToolCallRequest:
    id: str
    tool_name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    content: str
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    finish_reason: str = "stop"


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> LLMResponse:
        """Generates a non-streaming response with optional tool calling."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> AsyncGenerator[str, None]:
        """Streams text chunks token-by-token."""
        pass
