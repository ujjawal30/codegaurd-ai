from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    APP_NAME: str = "CodeGuard AI"
    DATABASE_URL: str = "postgresql+asyncpg://codeguard:codeguard@postgres:5432/codeguard"
    GEMINI_API_KEY: str = ""

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_key(cls, v):
        if not v:
            raise ValueError("GEMINI_API_KEY must be set in environment variables or .env file")
        return v

    class Config:
        env_file = ".env"

settings = Settings()
