"""
CodeGuard AI — FastAPI Dependency Injection.

Shared dependencies for API endpoints.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.database import get_db


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_db — yields an async database session."""
    async for session in get_db():
        yield session


def get_settings() -> Settings:
    """Returns the application settings singleton."""
    return settings
