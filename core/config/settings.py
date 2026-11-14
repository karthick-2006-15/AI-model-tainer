"""
JARVIS Core Configuration & Settings Management
Uses Pydantic v2 BaseSettings for type-safe environment loading.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
from pathlib import Path


class Settings(BaseSettings):
    # Server & Host
    JARVIS_HOST: str = Field(default="127.0.0.1", description="FastAPI bind host")
    JARVIS_PORT: int = Field(default=8000, description="FastAPI bind port")
    JARVIS_DEBUG: bool = Field(default=False, description="Debug mode")
    JARVIS_SECRET_KEY: str = Field(default="jarvis_super_secret_dev_key_change_in_prod", description="Device pairing secret")

    # Storage Paths
    DATABASE_URL: str = Field(default="sqlite:///./jarvis.db", description="SQLAlchemy DB URL")
    QDRANT_STORAGE_PATH: str = Field(default="./storage/vector_data", description="Vector database path")

    # AI Model Providers
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Local Ollama base URL")
    DEFAULT_LOCAL_MODEL: str = Field(default="llama3.2:3b", description="Default local LLM model")

    # Voice Engine
    WAKE_WORD: str = Field(default="hey_jarvis", description="Wake word")
    WAKE_WORD_SENSITIVITY: float = Field(default=0.5, description="Wake word threshold")
    WHISPER_MODEL_SIZE: str = Field(default="base.en", description="Whisper model tier")
    WHISPER_DEVICE: str = Field(default="cpu", description="Whisper hardware device")
    WHISPER_COMPUTE_TYPE: str = Field(default="int8", description="Whisper quantization")
    TTS_ENGINE: str = Field(default="edge_tts", description="TTS engine (edge_tts | piper)")
    DEFAULT_VOICE_EN: str = Field(default="en-US-ChristopherNeural", description="English neural voice")
    DEFAULT_VOICE_TA: str = Field(default="ta-IN-ValluvarNeural", description="Tamil neural voice")

    # Security & Permissions
    DEFAULT_PERMISSION_LEVEL: int = Field(default=1, description="Default session permission level")
    AUTO_APPROVE_LEVEL_2: bool = Field(default=True, description="Auto approve level 2 operations with toast")
    LEVEL_3_TIMEOUT_SECONDS: int = Field(default=60, description="Timeout for level 3 approval")
    EMERGENCY_STOP_ENABLED: bool = Field(default=True, description="Enable emergency abort")

    # Monitored File Paths
    INDEXED_DIRECTORIES: str = Field(default="~/Downloads,~/Documents,~/Desktop", description="Comma-separated directories to monitor")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def parsed_indexed_directories(self) -> List[str]:
        dirs = []
        for d in self.INDEXED_DIRECTORIES.split(","):
            expanded = os.path.expanduser(d.strip())
            if os.path.exists(expanded):
                dirs.append(expanded)
        return dirs


# Global cached settings instance
settings = Settings()
