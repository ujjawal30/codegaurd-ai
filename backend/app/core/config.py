"""
CodeGuard AI — Application Configuration.

Centralized settings management via Pydantic Settings.
All values are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "CodeGuard AI"
    LOG_LEVEL: str = "INFO"

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://codeguard:codeguard@postgres:5432/codeguard"
    SYNC_DATABASE_URL: str = "postgresql://codeguard:codeguard@postgres:5432/codeguard"

    # ── Gemini LLM ───────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-lite"
    GEMINI_EMBED_MODEL_NAME: str = "gemini-embedding-001"

    # ── Upload ───────────────────────────────────────────────────
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── RAG ──────────────────────────────────────────────────────
    RAG_COLLECTION_NAME: str = "codeguard_standards"

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "GEMINI_API_KEY must be set in environment variables or .env file"
            )
        return v


settings = Settings()
