"""Configuration module for AI Smart Travel & Itinerary Planner Agent."""

import os
from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=str(Path(__file__).parent.parent / ".env"),
            env_file_encoding="utf-8",
            extra="ignore",
        )

        MOCK_LLM: bool = True
        GEMINI_API_KEY: Optional[str] = None
        GEMINI_MODEL: str = "gemini-2.5-flash"
        DATABASE_URL: str = "sqlite:///./travel_planner.db"
        MAX_AGENT_STEPS: int = 10
        DEFAULT_CURRENCY: str = "INR"
        HOST: str = "127.0.0.1"
        PORT: int = 8000
        DEBUG: bool = True

except ImportError:
    # Lightweight fallback before dependencies are installed
    class Settings:  # type: ignore
        def __init__(self) -> None:
            self.MOCK_LLM: bool = os.getenv("MOCK_LLM", "True").lower() in ("true", "1", "yes")
            self.GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
            self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./travel_planner.db")
            self.MAX_AGENT_STEPS: int = int(os.getenv("MAX_AGENT_STEPS", "10"))
            self.DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "INR")
            self.HOST: str = os.getenv("HOST", "127.0.0.1")
            self.PORT: int = int(os.getenv("PORT", "8000"))
            self.DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

settings = Settings()
