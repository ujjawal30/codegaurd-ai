"""
CodeGuard AI — Application Configuration.

Centralized settings management via Pydantic Settings.
All values are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "CodeGuard AI"
    LOG_LEVEL: str = "INFO"

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://codeguard:codeguard@postgres:5432/codeguard"
    SYNC_DATABASE_URL: str = "postgresql://codeguard:codeguard@postgres:5432/codeguard"

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── Gemini LLM ───────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-lite"
    GEMINI_EMBED_MODEL_NAME: str = "gemini-embedding-001"

    # ── Upload ───────────────────────────────────────────────────
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── RAG ──────────────────────────────────────────────────────
    RAG_COLLECTION_NAME: str = "codeguard_standards"

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "GEMINI_API_KEY must be set in environment variables or .env file"
            )
        return v


settings = Settings()
